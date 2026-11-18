# Iron Tide — design notes and backlog

Typed up from the handwritten pages shared on 2026-11-18 so nothing gets lost between sessions.
Words I couldn't read for sure are marked **(?)**. Status: ✅ done · 🔨 in progress · ⬜ not started · ❓ needs checking against the game.

## The feedback that matters most
> It feels like you haven't been listening to me. A lot if not most of the new and important features aren't being added to the game,
> which turns into a laggy game, and it never gets smooth like I asked. There is a long list of things not added; I have made several
> pages of game improvements with only a few added. **When I ask for changes I need full systems that work put in place for the thing I ask.**
> This game is so close to being good but these many issues not being changed are holding it back.

Rules that follow from it:
- Every request gets a **complete, working system**, not a token version.
- **All models must be accurate, with no floating or invisible parts; everything attached to the vehicle.**
- **All models should be very, very different from each other.**
- Smooth play comes first (target: ~20 fps on a school Chromebook, HP / Intel).

## Lore
Humans learned to clone and sent most of their population to this world, **Griffy-55 (?)**. It is habitable and easy to fly over, but has too
much atmosphere to leave; leaving needs a resource nobody has found yet. They've been locked in a world war ever since — so long that nobody
remembers why it started. They just keep fighting.

## World and maps
| | Item | Status |
|---|---|---|
| | Trees need better models; the world should feel like Pandora (Avatar) | 🔨 |
| | Battles are hard to find / not fun — there should be cities and military outposts to fight over | ❓ |
| | Front lines are real fronts: 50–100 km wide with a no-man's-land, "not some small little trench" | ⬜ |
| | Bigger maps with more cities | ⬜ |
| | Rivers and bridges | ⬜ |
| | Map types: large city, desert, forest, snowy, naval (more islands) | ⬜ |
| | More realistic terrain | ⬜ |
| | Trenches and bunkers | ❓ |
| | Destructible buildings | ❓ |

## Gameplay
| | Item | Status |
|---|---|---|
| | Repair stations; resupply from bases | ❓ |
| | Vehicles can get stuck in mud / snow | ⬜ |
| | More realistic damage (tracks, wings, etc.) | ⬜ |
| | Custom battles: choose map, nations, vehicles | ⬜ |
| | AI difficulty settings (easy → extreme) | ⬜ |
| | **Events — Kraken boss fight** anyone can join. Killing it unlocks a new LIMITED fuel that adds speed; the nation that does the most damage gets the technology (access) to gather that fuel | ⬜ |
| | Planes: W = more throttle, S = less throttle | ⬜ |
| | Planes must fly smooth, with no lag — more than boats or tanks | ⬜ |
| | Show where to shoot (aim indicator / lead marker) | ⬜ |
| | Full game + multiplayer servers (long term) | 🔨 site + shared war server exist |

## Graphics
| | Item | Status |
|---|---|---|
| | Better lighting | ✅ sun shadows (v5.1) |
| | Getting hit: a small flash, not a whole fireball | ⬜ |
| | Dust, fire, explosions, smoke at the same quality as the water — real smoke and fire | ⬜ |
| | Improved water | ⬜ |
| | Detailed models | 🔨 |
| | Less lag / smooth | 🔨 v5.0 shader + governor fixes; needs Chromebook test |

## Tech tree 2 (TT2)
- A second, more advanced tech tree that dwarfs TT1 and makes it look weak.
- Balance: TT2 vehicles earn almost zero credits from kills on TT1, so progressing TT2 is nearly impossible if a player camps TT1 vehicles.
- TT2 vehicles are much better: better radar, better AA systems, better materials, better weapons such as **(?) blasters**.
- Name key: first letters = name, second letters = role: **I** interceptor, **A** attack, **T** tank, **C** command, **M** mixed, **F** fighter, **H** heli.
- TT2 aircraft tree (engine heli → …): ZAR, Eve-fly-1 (?), KAM-I4, XOL-44E, BRT-T1A, SPFY-M4F, CA-CST (?), HEL-H3A, SAL-H4I.

## Nations
- Nation tech trees: US, Germany, USSR, UK, Japan — each with unique vehicles.

## Tanks
- Tank classes: heavy, medium, light; upgrades (armour, engine, …).
- **Each tier at least 0.75 of a tank bigger than the last.**
- Tree: Light tank → Light AA tank / "most-used US tank"-like → AA tank, Mixed tank, Tiger-like → AA fire tank (?), Artillery tank (long range, slow reload),
  wheeled (?) tank, M1 Abrams-like (less armour), T-90-like, Leopard-like → "make your own" → **Armoured Titan**.

## Ships
- More variety; cruisers and destroyers; battleships rare / expensive. Each tier noticeably larger.
- Tree: Small destroyer / Light cruiser / Light battleship ("tanks on water") →
  torpedo boat, AA destroyer, frigate, monitor / ironclad → WW2 destroyer, missile destroyer, AA cruiser, Iowa-like →
  Arleigh Burke-like (less tech), "mix all three", aircraft carrier (with planes), … → **flagship: a mix of everything**.
- **T7 ship sketch** (page with 90 m / 140 m / 20 m): long-range missiles ×4, short-range missiles ×4, AA tower(s), **(?) cannon** at the bow. 🔨

## Planes
- Ammo types: bombs, rockets, machine guns. Fighter upgrades (guns, speed). Bombers for large strikes.
- Tree: Light plane → Light fighters / Light bomber → P-51-like, F-35-like (stealth fighter-bomber mix), heavy bomber (?) → stealth bomber (flies high, stealthy), seaplane (?)
- T7 plane: "the plane idea that was supposed to be a **(?) fortress** — we made it."
