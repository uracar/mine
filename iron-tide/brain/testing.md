# Testing and releasing — links: [hub](../../CLAUDE.md) · [pitfalls](pitfalls.md) · [rules](rules.md)

Serve first: `cd iron-tide && python3 -m http.server 8765 &` (Chromium + Playwright are preinstalled; swiftshader is slow: ~10 s per view).
All checks are one tool, `node tools/test/it.js <cmd>` (run from `iron-tide/`; header of the file lists usage):

| cmd | what it proves |
|---|---|
| `nodes [file-url]` | every vehicle in every tree builds (catches swallowed code); lists tris/parts/Forge model |
| `shot OUT ID [views]` | close-up pictures of one vehicle → `OUT.png` (Read it to look) |
| `fire ID AIM …` | turrets train, barrels lay, shells leave the muzzle (`shells+N`) |
| `drive ID` | wheels / track runs / props animate while driving |
| `water OUT` / `forest OUT [hash]` | scenery views; night: `'#play&q=2&still&t=0.95'` |
| `gallery OUT ID…` | contact sheet of several vehicles |

Page hooks (game.js, search `window.__dev=`): `setVehicle`, `nodeSpec(id)`, `VS`, `parts()`, `pp()` (part defs), `gs(d)` (gunShot),
`ff(d)` (fire one flash now), `allNodes()`, `treeList()`, `aiKinds()`, `forestAt(x,z)`; `window.__world` (player, orbit, `__T` terrain),
`window.__parts()`, `window.__fire()`. URL hash: `#play&q=0..3` quality, `&still` no weather, `&t=0..1` time of day.

Release: `tools/release.sh X.Y` (bump GAME_VERSION + sw.js, syntax check, bundle, copy to dist, regenerate codemap) →
`it.js nodes file:///…/dist/iron-tide-vX.Y.html#play&q=1&still` → update NOTES.md → commit + push → SendUserFile the HTML.
Keep scratch screenshots in the session scratchpad; copy only pictures worth keeping to `docs/`.

**Blender** (v7 era): not preinstalled — `pip install bpy` (Blender 5.3 as a Python module, ~1 min). Only **Cycles on CPU** renders
headless (EEVEE/Workbench crash). `python3 tools/blender/forge_anim.py MODEL_ID OUT.mp4 [frames] [width] [samples]` rebuilds any Shape
Forge model (same axes/shapes as the game) and renders an animated showcase (turrets sweep, guns recoil+flash, wheels/props spin,
camera orbits) + a still; ffmpeg is installed. Cost: 720p, 12 samples ≈ 7 s/frame (4 cores); test with `30 320 4` first (~20 s).
