# Iron Tide: Blender remaster pipeline

Rebuilds every Shape Forge model (vehicles and trees) in Blender and feeds it back into the game.

1. `blender/forge_to_blender.py`: run with the `bpy` module (Blender 5.1). Rebuilds each part as a real mesh, welds ship hulls,
   bevels hard edges, drops faces sealed inside other parts, sets weighted normals and bakes ambient occlusion, edge wear
   and crease grime into one shade per vertex. Each model is held to its old triangle count (+15%, planes +25%, trees +10%),
   stepping detail down until it fits.
2. `tools/engine_patch.js`: a small synchronous inflate and the decoder for the new `mesh` parts.
3. `tools/apply_patch.js original.html out.html`: puts the models and engine hooks into the game.

```
python3 -m venv bvenv && bvenv/bin/pip install bpy==5.1.2
sed -n '/^const FORGE_MODELS=/p' iron-tide.html | sed 's/^const FORGE_MODELS=//; s/;$//' > blender/forge_models.json
node -e '...'   # orig_tris.json: see tools/harness.js
bvenv/bin/python blender/forge_to_blender.py blender/forge_models.json blender/out [model ...] [--preview]
node tools/apply_patch.js iron-tide.html iron-tide-v7.0.html
```
