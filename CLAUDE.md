# Iron Tide — start here (hub)

Iron Tide is the owner's WebGL naval/combined-arms war game in `iron-tide/`. Work on branch `claude/iron-tide-access-4m21lt`.
This file is the hub of a small linked memory ("neural net"): read only the node you need, follow its links, and avoid
reading `js/game.js` (15k lines) whole — use the code map to jump to lines.

| Node | Read it when |
|---|---|
| [rules](iron-tide/brain/rules.md) | always, before changing anything (owner's standing rules) |
| [architecture](iron-tide/brain/architecture.md) | finding where a system lives; files, render passes, quality |
| [vehicles](iron-tide/brain/vehicles.md) | tech trees, vehicle stats/meshes, moving parts, AI players |
| [forge](iron-tide/brain/forge.md) | Shape Forge 3D models and the modelling session |
| [world](iron-tide/brain/world.md) | water, trees, terrain, towns |
| [testing](iron-tide/brain/testing.md) | checking anything in the browser, releasing a version |
| [pitfalls](iron-tide/brain/pitfalls.md) | before editing game.js (mistakes that cost hours) |
| [codemap](iron-tide/brain/codemap.md) | every section and function with line numbers (generated) |
| [NOTES.md](iron-tide/NOTES.md) | the owner's feature backlog and its status |

Fast path for a typical request: rules → codemap (find lines) → edit → `node iron-tide/tools/test/it.js …` → `tools/release.sh X.Y` → commit, push, send the HTML.
Update the node you learned something in before you finish (one line is enough), so the next session starts smarter.
