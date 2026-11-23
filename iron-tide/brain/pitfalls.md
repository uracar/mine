# Pitfalls (each cost real time) — links: [hub](../../CLAUDE.md) · [testing](testing.md)

- **Never append a `//` comment in the middle of a line of code.** game.js packs many statements per line; a comment inserted
  mid-line silently swallows the rest. This broke every TT2 vehicle from v6.3 to v6.5 (tt2Dress `let x0` lost) and twice more.
  Put comments on their own line. After editing, run `it.js nodes` — it builds all 98 vehicles and catches this.
- `node -e "new Function(src)"` only checks syntax; a swallowed declaration still parses. The real check is `it.js nodes`.
- `uploadUnitMesh` uploads the per-vertex group buffer only if `M.parts.length>0` — give a mesh placeholder parts if its groups must animate.
- Inserting into `PAINTS` shifts saved paint indices: append only.
- `nodeOpen`/salvLoad: TT2 tier 1 must not be auto-owned (`!n.tt2`).
- A gun only fires when `gunShot().onTarget` (laid on the aim point). Tests that fire immediately, or aim at water off the bow
  (below ship depression), see no shells — aim at the horizon and wait ~9 s (`it.js fire`).
- The turret-clearance check (`turretClearance`) lifts barrels over anything rigid in their swing and won't fire through the ship.
  A model whose gun is boxed in (taller deck fittings, gun facing a funnel) is a model bug: send it back to the modelling session.
- Tests that drop a plane on random land can crash it into a tree (fireball). Spawn planes on the runway (`setVehicle` does).
- The local test server dies between sessions: `cd iron-tide && python3 -m http.server 8765 &`.
- scaleMesh does not scale `M.aa` / `M.exhaust`; the Forge hook scales its own and keeps the class's original AA (`O.aa`).
