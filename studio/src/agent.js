// The engine every AI in the studio runs on: send a task to Claude, let it
// call tools, run those tools, feed the results back, repeat until it's done.
import Anthropic from "@anthropic-ai/sdk";
import { z } from "zod";
import { MODEL, LIMITS, PRICE_PER_MTOK } from "./config.js";

let client; // created on first use, so tools that don't call Claude work without a key
export function setClient(c) { client = c; } // lets tests swap in a fake Claude

// Spend tracker shared by every agent in a run.
export const spend = {
  limit: Infinity, // departments stop when spend passes this (set by the studio)
  input: 0, output: 0, cacheWrite: 0, cacheRead: 0,
  add(usage) {
    if (!usage) return;
    this.input += usage.input_tokens ?? 0;
    this.output += usage.output_tokens ?? 0;
    this.cacheWrite += usage.cache_creation_input_tokens ?? 0;
    this.cacheRead += usage.cache_read_input_tokens ?? 0;
  },
  get usd() {
    return (this.input * PRICE_PER_MTOK.input + this.output * PRICE_PER_MTOK.output +
      this.cacheWrite * PRICE_PER_MTOK.cacheWrite + this.cacheRead * PRICE_PER_MTOK.cacheRead) / 1e6;
  },
};

// Define a tool once with a zod schema; the JSON schema sent to Claude is generated from it.
export function tool({ name, description, schema, run }) {
  return { name, description, schema, run };
}

function toApiTool(t) {
  const jsonSchema = z.toJSONSchema(t.schema);
  delete jsonSchema.$schema;
  return {
    name: t.name,
    description: t.description,
    input_schema: jsonSchema,
    eager_input_streaming: true, // stream big inputs (whole files) as they're written
  };
}

/**
 * Run one AI until it finishes its task.
 * @returns {Promise<string>} the AI's final written answer
 */
export async function runAgent({ name, system, tools, task, effort, maxTurns, respectBudget = true, log = console.log }) {
  const apiTools = tools.map(toApiTool);
  const byName = new Map(tools.map((t) => [t.name, t]));
  const messages = [{ role: "user", content: task }];
  let retries = 0;
  let lastText = "";

  for (let turn = 0; turn < maxTurns; turn++) {
    if (respectBudget && spend.usd >= spend.limit) {
      return `${name} stopped early: the studio budget is spent. Last note: ${lastText || "(none)"}`;
    }
    let message;
    try {
      client ??= new Anthropic();
      const stream = client.beta.messages.stream({
        model: MODEL,
        max_tokens: LIMITS.maxTokens,
        betas: ["server-side-fallback-2026-07-01"],
        fallbacks: "default", // if a request is declined, the API retries it on a fallback model
        output_config: { effort },
        cache_control: { type: "ephemeral" }, // reuse the long prompt prefix between turns
        system,
        tools: apiTools,
        messages,
      });
      message = await stream.finalMessage();
      retries = 0;
    } catch (err) {
      // Real API errors (bad key, rate limit after SDK retries, etc.) stop the run.
      // A dropped connection or an unparseable streamed tool input gets re-tried.
      if (err instanceof Anthropic.APIError || retries++ >= 2) throw err;
      log(`  [${name}] stream problem (${err.message}); retrying turn`);
      continue;
    }
    spend.add(message.usage);

    const text = message.content.filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
    if (text) lastText = text;

    if (message.stop_reason === "refusal") {
      return `${name} declined this task (${message.stop_details?.category ?? "no category"}). ${lastText}`;
    }
    if (message.stop_reason === "pause_turn") {
      messages.push({ role: "assistant", content: message.content });
      continue;
    }

    const calls = message.content.filter((b) => b.type === "tool_use");
    if (calls.length === 0) return lastText || `${name} finished without a summary.`;

    // Keep the full reply (thinking blocks included, unchanged) in the history.
    messages.push({ role: "assistant", content: message.content });

    // Several calls in one reply run at the same time (e.g. Art, Audio and
    // Engineering working in parallel); all results go back in one message.
    const results = await Promise.all(calls.map((call) => runTool(call, byName, message.stop_reason, name, log)));
    messages.push({ role: "user", content: results });
  }
  return `${name} ran out of turns. Last note: ${lastText || "(none)"}`;
}

async function runTool(call, byName, stopReason, agentName, log) {
  const fail = (msg) => ({ type: "tool_result", tool_use_id: call.id, is_error: true, content: msg });

  // A tool call cut off by the length limit may look valid but be missing its end.
  if (stopReason === "max_tokens") {
    return fail("Your reply hit the length limit, so this tool input was cut off and was NOT run. " +
      "Write smaller pieces (split big files into several modules) and try again.");
  }
  const t = byName.get(call.name);
  if (!t) return fail(`unknown tool ${call.name}`);
  const parsed = t.schema.safeParse(call.input);
  if (!parsed.success) {
    return fail(`INVALID_INPUT: ${parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; ")}`);
  }
  try {
    const out = await t.run(parsed.data);
    log(`  [${agentName}] ${call.name} ${summarize(parsed.data)}`);
    return { type: "tool_result", tool_use_id: call.id, content: out };
  } catch (err) {
    log(`  [${agentName}] ${call.name} failed: ${err.message}`);
    return fail(err.message);
  }
}

function summarize(input) {
  const s = input.path ?? input.department ?? input.focus ?? "";
  return typeof s === "string" ? s.slice(0, 80) : "";
}
