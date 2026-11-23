# Architecture — links: [hub](../../CLAUDE.md) · [codemap](codemap.md) · [vehicles](vehicles.md) · [world](world.md)

**Files** (`iron-tide/`): `index.html` → `js/boot.js` loads `js/terrain.js` as text (also run inside chunk workers), then `js/shaders.js`
(all GLSL), `js/models.js` (Shape Forge data, generated), `js/game.js` (everything else, ~15k lines, many statements per line).
`tools/bundle.py` inlines it all into `dist/iron-tide.html`. `sw.js` caches the site (bump VERSION each release). `NOTES.md` = backlog.
Accounts/war server: `https://iron-tide-game.netlify.app/api` (/login /register /me /save /sync /pilots), works from file://.

**Renderer**: custom WebGL2. Log depth via gl_FragDepth (VDEPTH moves it to the vertex stage for terrain/trees/water only), HDR +
bloom + ACES, sun shadow map (`shadowPass`), one noise texture on unit 7. Main loop `frame()` (search `function frame(now)`).
Quality presets `QUALITY` + governor `applyQuality` (user's choice never lowered: `qLocked`).

**Units** (everything that isn't terrain): instanced vertex-colour meshes. Mesh = `{P,N,C(rgb+part code),G(group per vertex),parts}`,
built with the mesh kit (`box` chamfered, `cyl`, `wedge`, `loft`, `surface`, `prism`) and `part(M,def,build)` for moving groups.
`addUnitKind(M)` registers a kind; `unitList[k]` receives instances via `emit`; `drawUnitKinds` draws. Per-kind rules in `unitFlags`
(rad, roll, det, lod, lodD). Moving parts: uniforms `uPA/uPB/uPC` (pivot+angle / axis+scale / slide+parent), `PART_SLOTS` 97 or 57
(so ≤56 groups per model). AI units use the `aiPart` shader path with per-kind uniforms `KIND_AIU`.
Colour part codes: 0 paint, 1–4 soldier limbs, 5 faction colour, 6 bird wings, 7 self-lit (lamps, glow), 8 foam, >8.5 decals;
plants (`uMatte`): 0 bark, 2.xx leaf (2.2–2.3 dense crown mass), 7 glow (v6.6).

**Shaders** (`js/shaders.js`): `UNIT_VS/UNIT_FS` (units, plants), `WATER_VS/WATER_FS` (Gerstner sea; `WATER_C_*` simple fallback),
terrain, trees (giants), sky. GLSL_HEAD/GLSL_COMMON shared helpers (`vnoise`, `lin`, `fogColor`, `sunShadow`, `skyBase`).

**Gameplay systems** (search names): weapons `initWeapons`/`modMounts`/`fireFromPart`/`gunShot`; ship AA `shipAATick`; battle finder
`fightsNear`/`joinFight` (H key), town battles `startBattle(local)`; world war groups `CW`; subs `subTick` (Space dives);
save/progress `salvLoad`/`salvBank`/`deathPenalty`; owner mode `ownerReady` (account jimbo).
