# Iron Tide

The main version of Iron Tide: a static site, no build step, live at https://iron-tide-play.netlify.app.
The original claude.ai artifact is no longer updated; all changes happen here.

```
index.html            page shell
css/style.css         interface styles
js/boot.js            loads terrain -> shaders -> game, registers the service worker
js/terrain.js         terrain generator (also run as text inside the chunk workers)
js/shaders.js         GLSL shaders
js/game.js            engine + game
sw.js                 offline cache (bump VERSION on every release)
netlify.toml          Netlify config (publish this folder)
```

Run locally: `python3 -m http.server` in this folder, then open http://localhost:8000/.
Accounts and the shared war use the API on iron-tide-game.netlify.app, which the game calls directly.

Useful URL flags: `#q=0..3` quality, `#play` skip the menu, `#fragdepth` old depth path (for comparing), F3 performance overlay.

## v5.0 performance changes
- Value noise in every shader now reads one 256x256 lattice texture instead of hashing four corners per call (the ground shader alone made ~80 such calls per pixel).
- Terrain, trees and sea set their log depth per vertex instead of writing gl_FragDepth, so the GPU's early depth test can skip hidden pixels again.
- Files cached by a service worker; repeat visits don't re-download 1.3 MB.
