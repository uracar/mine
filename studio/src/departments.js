// The departments of the studio. Each one is its own AI with its own job,
// its own instructions and its own part of the project it is allowed to change.
import { z } from "zod";
import { tool } from "./agent.js";
import { playtest } from "./playtest.js";

// Rules every department follows.
const STUDIO_RULES = `
You work at a small game studio made of AI departments, run by a Director AI.
The studio builds ONE browser game, in the project folder you can read and write with your tools.

Hard rules for everyone:
- ORIGINAL WORK ONLY. Never copy or recreate an existing game: no names, characters, story, levels,
  art, music, logos or distinctive look from any existing game, film or brand. Using a genre or a
  common mechanic (platforming, deck-building, twin-stick shooting...) is fine; the game's identity is ours.
- EVERYTHING IS MADE IN-HOUSE, IN CODE. No external libraries, frameworks, CDNs, web fonts, downloaded
  images, sounds or music. Art is drawn with Canvas 2D / WebGL / SVG written by us. Sound and music are
  synthesized with the Web Audio API. The game must work offline.
- Tech: plain JavaScript ES modules. Entry point is game/index.html, which loads game/main.js as a module.
  Design for a 1280x720 logical resolution that scales to fit the window. Keyboard and mouse controls.
  Target a steady 60 frames per second.
- Quality bar: we are aiming for the most polished, premium-feeling game we can make: tight controls,
  strong game feel ("juice": easing, screen shake, hit-stop, particles, squash and stretch, impact flashes),
  a cohesive art direction, layered sound, clear readable UI, a title screen, pause (Escape), game over and
  restart, and a difficulty curve that keeps a player hooked for at least 10 minutes.
- Read before you change: open the files you depend on (especially design.md) so your work fits the rest.
- Only write files in the area your department owns. If something outside it needs changing, say so in
  your final summary and the Director will hand it to the right department.
- Keep files focused: split big systems into several modules instead of one giant file.
- When you finish, reply with a short summary (under 200 words): what you made or changed, which files,
  anything other departments must know, and any known problems. No code in the summary.
`.trim();

const DEPARTMENTS = {
  design: {
    title: "Design Department (Game Designer)",
    owns: ["design.md", "notes/"],
    brief: `You own the game design document, design.md. It is the single source of truth for the team.
It must cover: an original title and premise; the core loop; exact controls; player abilities and enemies or
obstacles with real numbers (speeds, health, timings); progression and difficulty curve; scoring or win/lose
conditions; screens and UI flow; art direction (palette with hex codes, shapes, lighting, animation style);
audio direction (instruments, mood, list of every sound effect, music behaviour); the list of "juice" effects;
and a FILE PLAN with the module interfaces other departments must follow, especially:
  - game/art/index.js  (owned by Art): what it exports, e.g. drawing functions and their parameters
  - game/audio/index.js (owned by Audio): what it exports, e.g. playSfx(name), startMusic(state)
  - everything else in game/ (owned by Engineering)
Make the scope ambitious but finishable. When asked to revise, update design.md rather than starting over.`,
    effortKey: "design",
  },
  engineering: {
    title: "Engineering Department (Gameplay Programmer)",
    owns: ["game/"],
    notOwns: ["game/art/", "game/audio/"],
    brief: `You write the game itself: game/index.html, game/main.js and the other modules in game/
(game loop with fixed timestep, input, state machine for screens, entities, physics/collision, camera,
UI, saving the high score in localStorage, particles and screen effects). Follow design.md and its module
interfaces. Art lives in game/art/ and audio in game/audio/ (other departments own those): import and
call them through the interfaces in design.md. If they don't exist yet, guard the calls so the game
still runs, and draw simple placeholder shapes until art arrives. Fix every bug QA reports that is in
your area. Never leave the game in a broken state: after edits, re-read the files you touched and
check imports, exports and names line up.`,
    effortKey: "engineering",
  },
  art: {
    title: "Art Department (Technical Artist)",
    owns: ["game/art/"],
    brief: `You create all visuals as code in game/art/: characters, enemies, environments, backgrounds with
parallax, lighting and glow, particle looks, UI panels and icons, a title logo drawn with paths, and
animation (frames or procedural motion). Follow the art direction and the game/art/index.js interface
in design.md exactly, so Engineering can call your functions. Make it cohesive and striking, not
placeholder rectangles: gradients, outlines, shading, silhouettes that read clearly at game size.
Pre-render expensive drawings to offscreen canvases so the game stays at 60fps.`,
    effortKey: "art",
  },
  audio: {
    title: "Audio Department (Sound Designer and Composer)",
    owns: ["game/audio/"],
    brief: `You create all sound as Web Audio code in game/audio/: every sound effect in design.md
(layered synthesis: oscillators, noise, envelopes, filters, pitch sweeps, small random variation so
repeats don't sound identical), and original music that changes with game state (title, play, intensity,
game over), with a master volume and mute. Follow the game/audio/index.js interface in design.md.
Browsers only allow audio after a user gesture, so create or resume the AudioContext on the first key
or click. Never crash if audio is unavailable.`,
    effortKey: "audio",
  },
  qa: {
    title: "QA Department (Playtester and Critic)",
    owns: ["qa/"],
    brief: `You test the game and judge it against a premium, near-AAA bar. Be honest and tough: a score
of 8+ means it would hold up next to well-reviewed commercial games in that category.
1. Run the playtest tool (use your own action scripts to test specific things: menus, controls, losing,
   restarting, pausing). Look carefully at the screenshots.
2. Read the code to find bugs the playtest can't show (logic errors, broken imports, missing features
   from design.md, performance problems).
3. Write your report to qa/round-<N>.md (N is given in your task) with:
   - SCORES 1-10: Stability, Controls & Game Feel, Visuals, Audio, UI/UX, Polish & Juice, Content & Depth,
     and OVERALL.
   - BUGS, worst first, each with the file and which department should fix it.
   - TOP 5 IMPROVEMENTS that would raise the scores most, each tagged with a department.
   - ORIGINALITY CHECK: anything that looks copied from an existing game, and any external requests.
Your final summary must include all the scores and the top bugs.`,
    effortKey: "qa",
  },
};

export const DEPARTMENT_NAMES = Object.keys(DEPARTMENTS);

function canWrite(dept, relPath) {
  const p = relPath.replace(/\\/g, "/").replace(/^\.\//, "");
  if (dept.notOwns?.some((d) => p.startsWith(d))) return false;
  return dept.owns.some((o) => (o.endsWith("/") ? p.startsWith(o) : p === o));
}

// Tools that every department gets: look at files, and change files in its own area.
function fileTools(ws, dept) {
  const guard = (p) => {
    if (!canWrite(dept, p)) {
      throw new Error(`${dept.title} may only write in: ${dept.owns.join(", ")}` +
        (dept.notOwns ? ` (not ${dept.notOwns.join(", ")})` : "") + ". Ask the Director for other changes.");
    }
  };
  return [
    tool({
      name: "list_files",
      description: "List every file in the project (or in one folder of it) with sizes.",
      schema: z.object({ folder: z.string().optional().describe("e.g. game/art; omit for the whole project") }),
      run: ({ folder }) => ws.list(folder || ".").join("\n") || "(no files yet)",
    }),
    tool({
      name: "read_file",
      description: "Read a text file from the project. Lines are numbered for reference.",
      schema: z.object({ path: z.string().describe("project-relative path, e.g. game/main.js") }),
      run: ({ path }) => ws.read(path).split("\n").map((l, i) => `${i + 1}\t${l}`).join("\n"),
    }),
    tool({
      name: "write_file",
      description: "Create or completely replace a file in your department's area. Prefer edit_file for small changes.",
      schema: z.object({ path: z.string(), contents: z.string().describe("the full file contents") }),
      run: ({ path, contents }) => { guard(path); return `wrote ${path} (${ws.write(path, contents)} lines)`; },
    }),
    tool({
      name: "edit_file",
      description: "Replace one exact piece of text in a file in your area. old_str must appear exactly once; copy it exactly (without the line-number prefix read_file shows).",
      schema: z.object({ path: z.string(), old_str: z.string(), new_str: z.string() }),
      run: ({ path, old_str, new_str }) => { guard(path); ws.edit(path, old_str, new_str); return `edited ${path}`; },
    }),
  ];
}

function qaTools(ws) {
  return [
    tool({
      name: "playtest",
      description: "Open the game in a real headless browser, run an input script, and return errors, frame rate, " +
        "sound activity and screenshots (1280x720). With no actions, a default 'press everything' session runs. " +
        "Action steps: {wait: ms}, {key: 'Space'|'Enter'|'ArrowLeft'|'KeyW'|...}, {hold: key, ms}, {click: [x, y]}, " +
        "{shot: 'label'} (max 8 screenshots).",
      schema: z.object({
        focus: z.string().describe("what this session is testing"),
        actions: z.array(z.object({
          wait: z.number().optional(), key: z.string().optional(), hold: z.string().optional(),
          ms: z.number().optional(), click: z.array(z.number()).length(2).optional(), shot: z.string().optional(),
        })).optional(),
      }),
      run: async ({ actions }) => {
        const { report, shots } = await playtest(ws.resolve("game"), actions?.length ? actions : undefined);
        return [
          { type: "text", text: JSON.stringify(report, null, 2) },
          ...shots.flatMap((s) => [
            { type: "text", text: `Screenshot: ${s.label}` },
            { type: "image", source: { type: "base64", media_type: "image/jpeg", data: s.data } },
          ]),
        ];
      },
    }),
  ];
}

export function getDepartment(name, ws) {
  const dept = DEPARTMENTS[name];
  if (!dept) throw new Error(`no department called ${name}`);
  return {
    title: dept.title,
    effortKey: dept.effortKey,
    system: `${STUDIO_RULES}\n\nYOUR ROLE: ${dept.title}\nYou may write in: ${dept.owns.join(", ")}` +
      `${dept.notOwns ? ` (except ${dept.notOwns.join(", ")})` : ""}\n\n${dept.brief}`,
    tools: [...fileTools(ws, dept), ...(name === "qa" ? qaTools(ws) : [])],
  };
}
