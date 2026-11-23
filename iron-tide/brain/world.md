# World: water, trees, terrain — links: [hub](../../CLAUDE.md) · [architecture](architecture.md) · [forge](forge.md)

**Water** (`WATER_VS/WATER_FS` in shaders.js): 7 Gerstner waves (mirrored by `WAVES` in game.js — ships ride them, so don't change
amplitudes in one place only), ship wakes `shipWake`, shore swell map `uShore` → `vDeep` (0 shore … 1 deep). v6.6 look: deep blue
offshore, turquoise only in shallows, whitecaps only on sharp crests (`cap`), lace, wind streaks near only, Fresnel and sun highlight on a
calmer normal (the swell normal is exaggerated ×2.3), glitter broken by ripples, ripple octaves fade by distance (no hairlines).

**Trees**: giants 150–260 m (`giantAt`, meshes `makeTreeMeshes`: `tree` near, `low` far — v6.6 rounded), woods streamed in 150 m blocks
(`woodBlock`/`emitWoods`, mask `forestAt`): procedural Pandora kinds `UNIT.PINE/BROAD/SPRUCE/BIRCH/BUSH` built by `pd*M(hi)` with a
stand-in past `lodD` (v6.6: rounded clumped crowns, colours `PD`), plus Shape Forge kinds `FTREE.RAIN/LEAF/PALM/CONE/SHRUB/GLOW`
(palms on coast h<12, conifers above 240 m, glow beads bright at night). Plants draw with `uMatte` (ragged leaf edges, wind sway).

**Terrain**: `js/terrain.js` (`T.height`, `T.moisture`, `T.pave`, `T.roadDist`, `T.portW`), chunk streaming + LOD in game.js, Pandora
ground glow at night. Towns `inTown`, harbours `portStructs`.
Backlog here (NOTES.md): fronts 50–100 km, rivers/bridges, map types (desert, snow, city), smoke/fire/explosion quality.
