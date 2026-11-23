# Rules (owner's standing instructions) — links: [hub](../../CLAUDE.md) · [testing](testing.md)

- **Every change applies to ALL tech trees**: TT1 and TT2, land, sea and air, player and AI.
- **No Netlify.** Deliver `dist/iron-tide-vX.Y.html` (version in the menu footer + loading screen) via SendUserFile. Bump with `tools/release.sh`.
- **Finish whole systems**; don't stop half-way or ask many questions. "Make it work and look right": verify in the browser before saying done.
- **Realistic, not goofy**: nothing floating, turrets turn, guns fire from the muzzle, real colours.
- Smooth play first: ~20 fps on a school Chromebook (Low), smooth High on a GTX 1070 Ti. Check triangle counts against peers (`it.js nodes`).
- TT2 has **tiers 1–6 only**; TT1 keeps tier 7. TT2 tanks are **hover tanks**. The three tier-1 ships (S1, S1b, S1c) must always exist.
- Account **jimbo** gets owner mode (full access). Owner auto-unlock otherwise only with `#owner`.
- Commit on the branch and push; no PRs unless asked. Commit messages end with the Co-Authored-By / Claude-Session lines from the system reminder.
- The owner's email is private: never in requests, commits or files.
- Talk to the owner in plain words (they're not a programmer); show before/after pictures for visual work.
