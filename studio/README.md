# AI Game Studio

A head AI (the **Director**) runs a studio of smaller AIs (the **departments**) that design, build,
draw, score, playtest and keep polishing an original browser game.

```
                      ┌────────────┐
       your idea ───▶ │  Director  │ ◀── reads QA reports, decides what's next
                      └─────┬──────┘
      ┌──────────┬──────────┼──────────┬──────────┐
      ▼          ▼          ▼          ▼          ▼
   Design   Engineering    Art       Audio        QA
 design.md   game/*.js  game/art/  game/audio/  plays the game in a real
                                                browser, screenshots, scores
```

The loop is **design → build → QA review → fix → QA review → ...** until every QA score reaches
the target (8/10 by default), or the round or money limit is hit.

## Rules the studio follows

- **Original only.** No copying existing games' names, characters, levels, art or music. Genres and
  mechanics are fine.
- **Everything made in-house, in code.** No downloaded images, sounds, fonts or libraries. Art is drawn
  with code, sound and music are synthesized with Web Audio. QA flags any outside network request.
- **Each department only edits its own folder.** Art can't overwrite Engineering's code, etc.
  The AIs can't touch anything outside the project folder.

## Setup

You need Node.js 20+ and an Anthropic API key (https://console.anthropic.com).

```bash
cd studio
npm install
npm install playwright && npx playwright install chromium   # the browser QA plays the game in
export ANTHROPIC_API_KEY=your-key-here                       # never commit this
```

## Use it

```bash
# Make a new game
node studio.js make skyforge "A fast arcade game where you pilot a tiny glowing drone through a collapsing crystal cave"

# Options: --rounds 4 (QA reviews)  --target 8 (score to reach)  --budget 20 (dollars)
node studio.js make skyforge "..." --rounds 6 --target 9 --budget 40

# Keep improving a game you already made, with your own notes
node studio.js continue skyforge "Make the boss fights harder and add a combo meter" --rounds 2 --budget 10

# Free (no AI): playtest only, saves screenshots to projects/<name>/qa/screenshots
node studio.js test skyforge

# Play it in your browser at http://127.0.0.1:8080
node studio.js play skyforge

# Free self-check of the whole studio using a fake AI
npm test
```

Each game lives in `projects/<name>/`: `design.md`, the game in `game/`, QA reports in `qa/round-N.md`,
and the Director's wrap-up in `DIRECTOR-SUMMARY.md`.

## Cost

It uses Claude Opus 5.5 for every AI. A full run with 4 QA rounds will probably cost somewhere around
$5–20 depending on the game. The `--budget` setting is a hard stop: once spend reaches it, departments
stop and the Director writes its summary. To spend less, lower `--rounds`, or lower the effort levels in
`src/config.js`.

## Being realistic about "AAA"

Real AAA games take hundreds of people years. This studio aims for the **most polished game it can
make**: a tight, juicy, good-looking browser game with real menus, sound and difficulty, roughly
like a strong indie game. The QA department is told to be tough and scores against that bar,
so the scores tell you honestly how close it got.

## How the code is laid out

| File | What it does |
|---|---|
| `studio.js` | The commands above |
| `src/director.js` | The head AI: its instructions and the `assign` tool it hands out work with |
| `src/departments.js` | Every department's job description, the folder it owns and its tools |
| `src/agent.js` | The engine every AI runs on: talk to Claude, run its tools, repeat; tracks spend |
| `src/playtest.js` | QA's browser: serves the game, presses keys, measures FPS, counts sounds, takes screenshots |
| `src/workspace.js` | The safe project folder the AIs read and write |
| `src/config.js` | Model, effort levels, limits and prices |

Want a new department (Level Design, Writing, Marketing)? Add one entry to `DEPARTMENTS` in
`src/departments.js` and a line about it in the Director's instructions in `src/director.js`.
