# Vehicles, tech trees, AI players — links: [hub](../../CLAUDE.md) · [forge](forge.md) · [architecture](architecture.md)

**Service Tree** `const TREE={sea,land,air}`: nodes `{id,t(tier),name,role,p(garage parts),perk,next}`; `NODE` map; ids like S1, S2a,
L4d, A5a; tier 7 capstones S7/L7/A7 (+ I3 rail gun). **TT2** `TT2_DEF` rows `[id,tier,look,role,next,pOver,model]` appended to TREE
with `tt2:1` (tiers 1–6, opened by the branch's tier 7, paid in TECH `S.tech`; perks +hp/fp/speed/reload). `nodeSpec(n)` builds the spec
(`s.node = n.model||n.look||n.id`, `s.tt2 = id`). Full list with in-game sizes: `docs/service-tree-sizes.json` (`__dev.treeList()`).

**Stats and meshes**: `vehicleStats(spec)` = `STATS[type]` (sized by tier: `sizeK`, `TANK_K=1.45`); `vehicleMesh(spec)` = `MESHES[type]`.
Wrapper chain (search `MESHES[t]=spec=>`): Forge model if `FORGE_USE[spec.node]` → else builder (`shipMesh`→`shipMeshTree`+`SHIP_DES`,
`tankMesh`, `planeMesh`) → `hoverTank` (TT2 tanks: drops running gear, adds hover body) → `tt2Dress` (TT2 finish).
`setVehicle(spec)` uploads the player mesh, `initParts`, `initWeapons`, `turretClearance`, `buildHullField`, `shipAAInit`.

**Moving part kinds** (`animateParts`): turret (aims at crosshair; `rest`, `arc`, `rate`, clearance `clr/lo/hi/home`), barrel (elevates,
recoils; `cr/sr` = cos/sin of rest), flash (fires the shell: `bz` lateral barrel offsets, `bore`, `med` = secondary damage, `noShot` =
launcher), wheel (`r`), tread (track run slides by link pitch `r`, `dir`), prop, radar, gear (`sign`), ail/elev/rud/flap, blink, ab, aa/aael.

**AI as players** (v6.2–6.4): AI ships `addFoe` → `foeShipNode` → `foeShipKind(id)` (turrets aim via mode 5, bearing in roll slot);
AI tanks `aiCrew`/`aiTankKinds`/`emitAITank` (hull + turret kinds, within 1.2 km), AI planes `aiPlaneKind` (2.5 km); stand-ins beyond.
They pick a node within a tier of the player (TT2 when the player is in TT2) and get that node's hp.
Open: AI damage scaled by firepower, AI prop/gear animation, smarter player-like behaviour.
