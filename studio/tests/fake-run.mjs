// Free test: runs the whole studio with a scripted fake Claude (no API key, no cost).
// Checks departments, parallel work, file ownership, input validation and the browser playtest.
//   node tests/fake-run.mjs
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { setClient, spend } from "../src/agent.js";
import { runStudio } from "../src/director.js";
import { Workspace } from "../src/workspace.js";

const GAME_HTML = `<!doctype html><html><body style="margin:0;background:#111"><canvas id=c width=1280 height=720></canvas><script type="module" src="main.js"></script></body></html>`;
const GAME_JS = `const c=document.getElementById('c'),g=c.getContext('2d');let x=640;const k={};
addEventListener('keydown',e=>{k[e.code]=1;if(!window.ac){window.ac=new AudioContext();}const o=ac.createOscillator();o.connect(ac.destination);o.start();o.stop(ac.currentTime+0.05)});
addEventListener('keyup',e=>k[e.code]=0);
(function f(){x+=(k.ArrowRight?5:0)-(k.ArrowLeft?5:0);g.fillStyle='#123';g.fillRect(0,0,1280,720);g.fillStyle='#f80';g.fillRect(x-20,340,40,40);requestAnimationFrame(f)})();`;

let id = 0;
const use = (name, input) => ({ type: "tool_use", id: "t" + id++, name, input });
const msg = (content, stop = "tool_use") => ({ content, stop_reason: stop, usage: { input_tokens: 1000, output_tokens: 500 } });
const scripts = {
  director: [
    msg([use("assign", { department: "design", task: "write design.md" }), use("assign", { department: "art", task: "try to write main.js" })]),
    msg([use("assign", { department: "engineering", task: "build it" })]),
    msg([use("assign", { department: "qa", task: "review" })]),
    msg([{ type: "text", text: "FINAL: done" }], "end_turn"),
  ],
  design: [msg([use("write_file", { path: "design.md", contents: "# Test game" })]), msg([{ type: "text", text: "design ok" }], "end_turn")],
  art: [
    msg([use("write_file", { path: "game/main.js", contents: "bad" }), use("write_file", { path: "../escape.txt", contents: "x" })]),
    msg([use("write_file", { path: "game/art/index.js", contents: "export const x=1" })]),
    msg([{ type: "text", text: "art ok" }], "end_turn"),
  ],
  engineering: [
    msg([use("write_file", { path: "game/index.html", contents: GAME_HTML }), use("write_file", { path: "game/main.js", contents: GAME_JS })]),
    msg([use("write_file", { path: "game/x.js" })]), // invalid input: missing contents
    msg([{ type: "text", text: "eng ok" }], "end_turn"),
  ],
  qa: [msg([use("playtest", { focus: "smoke" })]), msg([{ type: "text", text: "qa ok" }], "end_turn")],
};
const seen = {};
setClient({ beta: { messages: { stream(params) {
  const role = params.system.startsWith("You are the Director") ? "director" : params.system.match(/YOUR ROLE: (\w+)/)[1].toLowerCase();
  const key = { design: "design", engineering: "engineering", art: "art", audio: "audio", qa: "qa" }[role] ?? "director";
  const last = params.messages.at(-1);
  if (Array.isArray(last.content)) for (const r of last.content) {
    const c = typeof r.content === "string" ? r.content : r.content.filter(b=>b.type==="text").map(b=>b.text).join(" | ") + ` [+${r.content.filter(b=>b.type==="image").length} images]`;
    console.log(`   -> result to ${key}: ${r.is_error ? "ERROR " : ""}${c.slice(0, 300).replace(/\n/g, " ")}`);
  }
  if (key === "director" && !seen.tools) { seen.tools = 1; console.log("director tool schema:", JSON.stringify(params.tools[0].input_schema)); }
  const i = (seen[key] = (seen[key] ?? -1) + 1);
  return { finalMessage: async () => scripts[key][i] };
} } } });

const dir = process.argv[2] ?? path.join(os.tmpdir(), "studio-fake-run");
fs.rmSync(dir, { recursive: true, force: true });
const ws = new Workspace(dir);
const out = await runStudio({ ws, pitch: "test", targetScore: 8, maxRounds: 2, budgetUsd: 20 });
console.log("SUMMARY:", out, "| spend $", spend.usd.toFixed(3));
console.log(ws.list());
