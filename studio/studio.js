#!/usr/bin/env node
// Command line for the AI game studio.
//
//   node studio.js make <project> "<your game idea>" [--rounds 4] [--target 8] [--budget 20]
//   node studio.js continue <project> ["extra notes"] [--rounds 2] ...
//   node studio.js test <project>      (free: playtest only, no AI)
//   node studio.js play <project>      (free: serve the game at http://127.0.0.1:8080)
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Workspace } from "./src/workspace.js";
import { runStudio } from "./src/director.js";
import { spend } from "./src/agent.js";
import { playtest, serve } from "./src/playtest.js";
import { LIMITS } from "./src/config.js";

const here = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const opts = { rounds: 4, target: 8, budget: LIMITS.defaultBudgetUsd };
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) opts[a.slice(2)] = Number(argv[++i]);
    else rest.push(a);
  }
  return { opts, rest };
}

const USAGE = `Usage:
  node studio.js make <project> "<game idea>" [--rounds 4] [--target 8] [--budget 20]
  node studio.js continue <project> ["notes for the director"] [--rounds 2] [--budget 10]
  node studio.js test <project>
  node studio.js play <project>`;

async function main() {
  const [command, name, ...more] = process.argv.slice(2);
  const { opts, rest } = parseArgs(more);
  if (!command || !name || !/^[\w-]+$/.test(name)) { console.log(USAGE); process.exit(1); }
  const ws = new Workspace(path.join(here, "projects", name));

  if (command === "play") {
    const server = await serve(ws.resolve("game"), 8080);
    console.log(`Playing ${name} at http://127.0.0.1:${server.address().port}/  (Ctrl+C to stop)`);
    return;
  }

  if (command === "test") {
    const { report, shots } = await playtest(ws.resolve("game"));
    const outDir = ws.resolve("qa/screenshots");
    fs.mkdirSync(outDir, { recursive: true });
    shots.forEach((s, i) => fs.writeFileSync(path.join(outDir, `${i + 1}-${s.label.replace(/\W+/g, "-")}.jpg`), Buffer.from(s.data, "base64")));
    console.log(JSON.stringify(report, null, 2));
    console.log(`Screenshots saved in ${outDir}`);
    return;
  }

  if (command !== "make" && command !== "continue") { console.log(USAGE); process.exit(1); }
  const pitch = command === "make"
    ? rest.join(" ")
    : `Continue improving the existing game. ${rest.join(" ") || "Raise the QA scores further."}`;
  if (!pitch.trim()) { console.log(USAGE); process.exit(1); }

  console.log(`AI Game Studio: project "${name}" | rounds ${opts.rounds} | target ${opts.target}/10 | budget $${opts.budget}\n`);
  const summary = await runStudio({
    ws, pitch, targetScore: opts.target, maxRounds: opts.rounds, budgetUsd: opts.budget,
  });
  ws.write("DIRECTOR-SUMMARY.md", summary + "\n");
  console.log(`\n===== Director's summary =====\n${summary}`);
  console.log(`\nTotal spend: about $${spend.usd.toFixed(2)}. Play it: node studio.js play ${name}`);
}

main().catch((err) => {
  console.error(`\nStudio stopped: ${err.message}`);
  console.error(`Spend before stopping: about $${spend.usd.toFixed(2)}`);
  process.exit(1);
});
