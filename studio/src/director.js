// The head AI. It never writes game files itself: it plans, hands work to
// departments, reads QA reports and keeps going until the game is good enough.
import { z } from "zod";
import { runAgent, tool, spend } from "./agent.js";
import { getDepartment, DEPARTMENT_NAMES } from "./departments.js";
import { EFFORT, LIMITS } from "./config.js";

const DIRECTOR_SYSTEM = `
You are the Director of a small game studio whose staff are AI departments:
- design: writes and revises design.md (the game design document and the module interfaces)
- engineering: writes the game code in game/ (except game/art/ and game/audio/)
- art: makes all visuals as code in game/art/
- audio: makes all sound effects and music as Web Audio code in game/audio/
- qa: playtests the game in a real browser, reads the code, and writes a scored report to qa/round-N.md

Your job is to deliver the most polished, premium (near-AAA) ORIGINAL browser game the studio can make
within the budget. All art, sound and code are made in-house; nothing is copied from existing games or
downloaded.

How you work:
1. Have design write design.md from the pitch. Read it yourself and send it back for changes if it is
   vague, unoriginal, or missing numbers or module interfaces.
2. Production: assign engineering, art and audio. You may call assign several times in one reply to run
   departments IN PARALLEL; do that when their work doesn't depend on each other (they own separate folders).
3. Review: assign qa with the round number. Read its report.
4. Fix and polish: turn the report into specific tasks for each department (quote the bugs and the
   requested improvements; name files). Fix crashes and stability problems before adding features.
5. Repeat review and fix rounds. Stop when every QA score is at or above the target, or when the budget
   or round limit is reached.
Write precise tasks: departments only know what design.md, the files, and your task say.
When you stop, reply with a final summary for the studio owner: the game's title, what it is, how to play,
the final QA scores, what improved each round, and what you would do next with more budget.
`.trim();

export async function runStudio({ ws, pitch, targetScore, maxRounds, budgetUsd, log = console.log }) {
  let qaRounds = 0;
  spend.limit = budgetUsd;

  const assign = tool({
    name: "assign",
    description: "Give a task to one department and wait for its summary. For qa, each call counts as one review round.",
    schema: z.object({
      department: z.enum(DEPARTMENT_NAMES),
      task: z.string().describe("precise instructions: what to make or fix, which files, which QA findings"),
    }),
    run: async ({ department, task }) => {
      if (spend.usd >= budgetUsd) {
        return `BUDGET SPENT ($${spend.usd.toFixed(2)} of $${budgetUsd}). No more work can be assigned; write your final summary now.`;
      }
      if (department === "qa") {
        if (qaRounds >= maxRounds) return `Round limit (${maxRounds}) reached. Write your final summary now.`;
        qaRounds++;
        task = `This is review round ${qaRounds}. Write your report to qa/round-${qaRounds}.md.\n\n${task}`;
      }
      const dept = getDepartment(department, ws);
      log(`\n>> ${dept.title}: ${task.split("\n")[0].slice(0, 120)}`);
      const summary = await runAgent({
        name: department,
        system: dept.system,
        tools: dept.tools,
        task,
        effort: EFFORT[dept.effortKey],
        maxTurns: LIMITS.maxDepartmentTurns,
        log,
      });
      log(`<< ${department} done. Spend so far: $${spend.usd.toFixed(2)}`);
      return `${summary}\n\n[studio: spend so far $${spend.usd.toFixed(2)} of $${budgetUsd}; QA rounds used ${qaRounds} of ${maxRounds}]`;
    },
  });

  const readOnly = [
    tool({
      name: "list_files",
      description: "List every file in the project with sizes.",
      schema: z.object({}),
      run: () => ws.list().join("\n") || "(no files yet)",
    }),
    tool({
      name: "read_file",
      description: "Read a project file, e.g. design.md or qa/round-1.md.",
      schema: z.object({ path: z.string() }),
      run: ({ path }) => ws.read(path),
    }),
  ];

  const existing = ws.list();
  const task = [
    `PITCH FROM THE STUDIO OWNER:\n${pitch}`,
    `TARGET: every QA score at ${targetScore}/10 or higher. Limits: ${maxRounds} QA rounds, $${budgetUsd} budget.`,
    existing.length
      ? `This project already has files (continue from them; read design.md and the latest qa/ report first):\n${existing.join("\n")}`
      : "The project folder is empty: start from design.",
  ].join("\n\n");

  return runAgent({
    name: "director",
    system: DIRECTOR_SYSTEM,
    tools: [assign, ...readOnly],
    task,
    effort: EFFORT.director,
    maxTurns: LIMITS.maxDirectorTurns,
    respectBudget: false, // the director still gets to write its summary after the money runs out
    log,
  });
}
