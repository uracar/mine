#!/usr/bin/env python3
"""Render a Shape Forge model as an animated showcase in Blender (bpy, Cycles on the CPU - works headless).
Install once: pip install bpy   (Blender 5.x as a Python module)
Usage (from iron-tide/):  python3 tools/blender/forge_anim.py MODEL_ID OUT.mp4 [frames=96] [width=960] [samples=24]
  MODEL_ID: a key of js/models.js, e.g. iron-tide-medium-tank, iron-tide-destroyer, iron-tide-strike-fighter
The model is rebuilt from its part list (same shapes/axes as the game's importer), its moving groups are animated
(turrets sweep, guns recoil and flash, wheels roll, props/radars spin, lamps blink) and the camera circles it."""
import bpy, bmesh, json, math, pathlib, re, subprocess, sys, tempfile
from mathutils import Matrix, Euler, Vector

root = pathlib.Path(__file__).resolve().parents[2]
mid, out = sys.argv[1], pathlib.Path(sys.argv[2]).resolve()
FR = int(sys.argv[3]) if len(sys.argv) > 3 else 96
W = int(sys.argv[4]) if len(sys.argv) > 4 else 960
SAMPLES = int(sys.argv[5]) if len(sys.argv) > 5 else 24
src = (root / 'js' / 'models.js').read_text()
model = json.loads(src[src.index('{', src.index('FORGE_MODELS=')):src.rindex('}') + 1])[mid]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
FPS = 24

# ---------- geometry: each part becomes bmesh geometry in model coordinates (Forge: +X forward, +Y up, +Z starboard) ----------
Y_UP = Matrix.Rotation(-math.pi / 2, 4, 'X')        # Blender primitives run along Z; Forge cylinders/capsules along Y
def part_matrix(p):
    s = p.get('scale', [1, 1, 1]); r = [math.radians(a) for a in p.get('rotation', [0, 0, 0])]
    return Matrix.Translation(p['position']) @ Euler(r, 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*s, 1))
def add_part(bm, p):
    s, M, sh = p.get('size', []), part_matrix(p), p['shape']
    if sh in ('box', 'rbox'):
        g = bmesh.ops.create_cube(bm, size=1, matrix=M @ Matrix.Diagonal((s[0], s[1], s[2], 1)))
    elif sh == 'sphere':
        g = bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=12, radius=s[0], matrix=M)
    elif sh in ('cylinder', 'cone'):
        rt, rb, h = (s[0], s[1], s[2]) if sh == 'cylinder' else (0, s[0], s[1])
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=p.get('sides', 20), radius1=rb, radius2=rt, depth=h, matrix=M @ Y_UP)
    elif sh == 'capsule':
        r, L = s[0], s[1]
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=r, radius2=r, depth=L, matrix=M @ Y_UP)
        for y in (-L / 2, L / 2):
            bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=8, radius=r, matrix=M @ Matrix.Translation((0, y, 0)))
    elif sh == 'torus':
        R, r, nu, nv = s[0], s[1], 24, 8; vs = []
        for i in range(nu):
            for j in range(nv):
                u, v = i / nu * 2 * math.pi, j / nv * 2 * math.pi
                vs.append(bm.verts.new(M @ Vector(((R + r * math.cos(v)) * math.cos(u), (R + r * math.cos(v)) * math.sin(u), r * math.sin(v)))))
        for i in range(nu):
            for j in range(nv):
                a, b, c, d = i * nv + j, ((i + 1) % nu) * nv + j, ((i + 1) % nu) * nv + (j + 1) % nv, i * nv + (j + 1) % nv
                bm.faces.new((vs[a], vs[b], vs[c], vs[d]))
    elif sh == 'hull' and len(p.get('points', [])) >= 4:
        T = Matrix.Translation(p['position']) @ Euler([math.radians(a) for a in p.get('rotation', [0, 0, 0])], 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*p.get('scale', [1, 1, 1]), 1))
        vs = [bm.verts.new(T @ Vector(q)) for q in p['points']]
        res = bmesh.ops.convex_hull(bm, input=vs)
        bmesh.ops.delete(bm, geom=[g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert)], context='VERTS')

# ---------- materials ----------
mats = {}
def mat_for(p):
    key = (p.get('color', '#9aa5a0'), p.get('material', 'matte'))
    if key in mats: return mats[key]
    h = key[0].lstrip('#'); c = [((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4)]
    m = bpy.data.materials.new('m%d' % len(mats)); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (*c, 1)
    rough, metal = {'paint': (.55, .2), 'glossy': (.2, 0), 'metal': (.35, .85), 'rubber': (.95, 0), 'glass': (.05, 0), 'glow': (.4, 0)}.get(key[1], (.85, 0))
    b.inputs['Roughness'].default_value, b.inputs['Metallic'].default_value = rough, metal
    if key[1] == 'glow': b.inputs['Emission Color'].default_value = (*c, 1); b.inputs['Emission Strength'].default_value = 6
    if key[1] == 'glass': b.inputs['Transmission Weight'].default_value = .6
    mats[key] = m; return m

# ---------- objects: one per moving group (origin at its pivot), parented like the model's groups; the rest is the hull ----------
groups = {g['id']: g for g in model.get('groups', [])}
rootobj = bpy.data.objects.new('model', None); sc.collection.objects.link(rootobj)
rootobj.rotation_euler = (math.pi / 2, 0, 0)          # Forge Y-up -> Blender Z-up
objs = {}
def make_obj(gid):
    if gid in objs: return objs[gid]
    g = groups.get(gid); pv = Vector(g['pivot']) if g else Vector((0, 0, 0))
    me = bpy.data.meshes.new(gid or 'hull'); ob = bpy.data.objects.new(gid or 'hull', me); sc.collection.objects.link(ob)
    par = make_obj(g['parent']) if g and g.get('parent') in groups else None
    ob.parent = par or rootobj
    ob.location = pv - (Vector(groups[g['parent']]['pivot']) if par else Vector((0, 0, 0)))
    ob['pivot'] = pv; objs[gid] = ob; return ob
by_group = {}
for p in model['parts']: by_group.setdefault(p.get('group') if p.get('group') in groups else '', []).append(p)
for gid, parts in by_group.items():
    ob = make_obj(gid); pv = Vector(ob['pivot']); bm = bmesh.new()
    slots = []
    for p in parts:
        n0 = len(bm.faces); add_part(bm, p); bm.faces.ensure_lookup_table()
        m = mat_for(p)
        if m not in slots: slots.append(m)
        for f in bm.faces[n0:]:
            f.material_index = slots.index(m); f.smooth = p['shape'] in ('sphere', 'cylinder', 'cone', 'capsule', 'torus')
    bmesh.ops.translate(bm, vec=-pv, verts=bm.verts)
    bm.to_mesh(ob.data); bm.free()
    for m in slots: ob.data.materials.append(m)
for gid in groups: make_obj(gid)

# ---------- animation ----------
fire_frames = [int(FR * k) for k in (.3, .62, .9)]
def key(ob, path, f, v, idx=None):
    setattr(ob, path, v) if idx is None else getattr(ob, path).__setitem__(idx, v)
    ob.keyframe_insert(path, frame=f, index=-1 if idx is None else idx)
speed = 3.0                                          # ground speed for wheels, m/s
for gid, g in groups.items():
    a, ob = g.get('anim') or {}, objs[gid]; t = a.get('type'); ax = Vector(a.get('axis', [0, 1, 0])).normalized()
    if t == 'turret':
        amt = a.get('amount', .6)
        for i, f in enumerate(range(1, FR + 1, max(1, FR // 8))):
            ob.rotation_mode = 'AXIS_ANGLE'; ob.rotation_axis_angle = (amt * math.sin(i * .9), *ax); ob.keyframe_insert('rotation_axis_angle', frame=f)
    elif t in ('roll', 'spin'):
        rate = speed / a.get('radius', .3) if t == 'roll' else a.get('speed', 2)
        ob.rotation_mode = 'AXIS_ANGLE'
        for f in (1, FR):
            ob.rotation_axis_angle = (-rate * (f - 1) / FPS, *ax); ob.keyframe_insert('rotation_axis_angle', frame=f)
        for fc in ob.animation_data.action.fcurves if hasattr(ob.animation_data.action, 'fcurves') else []:
            for k in fc.keyframe_points: k.interpolation = 'LINEAR'
    elif t == 'recoil':
        rest = ob.location.copy(); d = Vector(a.get('axis', [-1, 0, 0])).normalized() * a.get('amount', .4)
        key(ob, 'location', 1, rest)
        for f in fire_frames:
            key(ob, 'location', f - 1, rest); key(ob, 'location', f + 1, rest + d); key(ob, 'location', f + 10, rest)
    elif t == 'flash':
        for f, on in [(1, False)] + [(x, v) for f0 in fire_frames for x, v in ((f0, True), (f0 + 3, False))]:
            ob.hide_render = not on; ob.keyframe_insert('hide_render', frame=f)
            for c in ob.children_recursive: c.hide_render = not on; c.keyframe_insert('hide_render', frame=f)
    elif t == 'blink':
        per = max(2, int(FPS / a.get('rate', 1)))
        for f in range(1, FR + 1, per):
            ob.hide_render = False; ob.keyframe_insert('hide_render', frame=f)
            ob.hide_render = True; ob.keyframe_insert('hide_render', frame=f + max(1, int(per * a.get('duty', .4))))
    elif t == 'flame':
        ob.hide_render = False

# ---------- stage: ground, sun, sky, orbiting camera framed on the model ----------
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in objs.values() for c in o.bound_box if o.data and len(o.data.vertices)]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
ctr, rad = (lo + hi) / 2, (hi - lo).length / 2
bpy.ops.mesh.primitive_plane_add(size=rad * 30, location=(ctr.x, ctr.y, lo.z))
gm = bpy.data.materials.new('ground'); gm.use_nodes = True; gb = gm.node_tree.nodes['Principled BSDF']
gb.inputs['Base Color'].default_value = (.16, .2, .12, 1); gb.inputs['Roughness'].default_value = .95; bpy.context.object.data.materials.append(gm)
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sc.collection.objects.link(sun)
sun.data.energy = 4; sun.data.angle = math.radians(3); sun.rotation_euler = (math.radians(50), 0, math.radians(35))
sc.world = bpy.data.worlds.new('sky'); sc.world.use_nodes = True
bg = sc.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value = (.45, .6, .85, 1); bg.inputs['Strength'].default_value = .8
pivot = bpy.data.objects.new('orbit', None); pivot.location = ctr; sc.collection.objects.link(pivot)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 40; cam.parent = pivot; cam.location = (0, -rad * 2.6, rad * .9)
trk = cam.constraints.new('TRACK_TO'); trk.target = pivot; trk.track_axis = 'TRACK_NEGATIVE_Z'; trk.up_axis = 'UP_Y'
pivot.rotation_euler = (0, 0, math.radians(-40)); pivot.keyframe_insert('rotation_euler', frame=1)
pivot.rotation_euler = (0, 0, math.radians(80)); pivot.keyframe_insert('rotation_euler', frame=FR)

# ---------- render ----------
r = sc.render; r.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = SAMPLES; sc.cycles.use_denoising = True
r.resolution_x, r.resolution_y = W, W * 9 // 16; r.fps = FPS; sc.frame_start, sc.frame_end = 1, FR
sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
tmp = pathlib.Path(tempfile.mkdtemp()); r.filepath = str(tmp / 'f_'); r.image_settings.file_format = 'PNG'
bpy.ops.render.render(animation=True)
out.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(tmp / 'f_%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', str(out)], check=True)
subprocess.run(['cp', str(tmp / ('f_%04d.png' % fire_frames[0])), str(out.with_suffix('.png'))])
print('wrote', out, 'and a still', out.with_suffix('.png'))
