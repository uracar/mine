"""Iron Tide - Blender remaster of Shape Forge models.

Run with the bpy module (Blender as a Python module):
    python forge_to_blender.py forge_models.json out_dir [model-key ...] [--preview]

For every model it
  1. rebuilds each Forge part as a proper Blender mesh (more segments on curved parts, true rounded boxes),
  2. merges a ship's hull slices into one welded hull and drops the faces the slices shared,
  3. bevels hard edges (width set by the part's size and the vehicle class) so light rolls round the edges,
  4. dissolves flat detail that adds no shape, drops faces sealed inside other parts of the same moving piece,
  5. sets weighted (hardened) normals: flat panels stay flat, bevels carry the curve,
  6. bakes ambient occlusion, edge wear, cavity grime, ground dirt and tonal variation into one shade per vertex,
  7. writes the result as compact 'mesh' parts for the game's forgeMesh(), keeping every moving group and pivot.
Geometry is built in game space (y up); only the preview render converts to Blender's z up.
"""
import bpy, bmesh, json, math, sys, os, struct, random
from mathutils import Vector, Matrix, noise
from mathutils.bvhtree import BVHTree

# ---------------------------------------------------------------- settings by vehicle class
CLASS = {
    #        bevel(m)  segs  max tris  AO reach (x length)  dirt
    'tank':  dict(bevel=.035, seg=2, budget=16000, reach=.16, dirt='mud'),
    'ship':  dict(bevel=.10,  seg=2, budget=22000, reach=.06, dirt='sea'),
    'plane': dict(bevel=.018, seg=2, budget=9000,  reach=.14, dirt='soot'),
    'tree':  dict(bevel=0.0,  seg=0, budget=1400,  reach=.25, dirt='none'),
}
# groups whose parts stay as the original Forge parts: track links slide one by one, flashes and lamps are tiny glowing bits
PASS_ANIM = {'track', 'flash', 'blink'}
RIGID_ANIM = {'turret', 'recoil', 'roll', 'spin', 'fold', 'flame', 'wiggle', 'track', 'flash', 'blink'}


def classify(key, model):
    k = key.lower()
    if 'tree' in k: return 'tree'
    an = {g.get('anim', {}).get('type') for g in model.get('groups', [])}
    if 'track' in an or 'roll' in an: return 'tank'
    if an & {'wiggle', 'fold', 'flame'}: return 'plane'
    return 'ship'


# ---------------------------------------------------------------- the game's own maths
def rot_m(r):
    """three.js Euler XYZ, exactly as fgRotM in the game: R = Rx Ry Rz"""
    x, y, z = [d * math.pi / 180 for d in (r or [0, 0, 0])]
    a, b, c, d, e, f = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    ae, af, be, bf = a * e, a * f, b * e, b * f
    return Matrix(((c * e, -c * f, d), (af + be * d, ae - bf * d, -b * c), (bf - ae * d, be + af * d, a * c)))


def hexcol(h):
    try: n = int(str(h)[1:], 16)
    except Exception: n = 0x9aa5a0
    return ((n >> 16 & 255) / 255, (n >> 8 & 255) / 255, (n & 255) / 255)


SEG_K = 1.0


def segs(r, cls):
    return max(6, int(round(_segs(r, cls) * SEG_K / 2) * 2))


def _segs(r, cls):
    # rounder than the game's own 6-24: curved parts were the most obviously polygonal thing on every model
    if cls == 'tree': return 6 if r < .3 else 8 if r < 1.5 else 10
    return 8 if r < .05 else 12 if r < .15 else 16 if r < .5 else 24 if r < 2.5 else 32 if r < 8 else 40


# ---------------------------------------------------------------- one Forge part as a bmesh in its own frame (game axes, y up)
def zprim_to_game(bm):
    # bmesh primitives are built round Blender's z; the game's round parts are round y. (a,b,c) -> (a,c,-b) is a proper rotation.
    for v in bm.verts:
        a, b, c = v.co
        v.co = Vector((a, c, -b))


def lathe(bm, prof, seg):
    """solid of revolution round y from a profile [(radius, y), ...] bottom to top, with poles where radius is 0"""
    rings = []
    for r, y in prof:
        if r < 1e-6:
            rings.append([bm.verts.new((0, y, 0))])
        else:
            rings.append([bm.verts.new((r * math.cos(t), y, r * math.sin(t))) for t in [k / seg * 2 * math.pi for k in range(seg)]])
    for A, B in zip(rings, rings[1:]):
        for k in range(seg):
            a0, a1 = A[k % len(A)], A[(k + 1) % len(A)]
            b0, b1 = B[k % len(B)], B[(k + 1) % len(B)]
            vs = [a0, b0, b1, a1] if len(A) > 1 and len(B) > 1 else ([a0, b0, a1] if len(B) == 1 else [a0, b0, b1])
            vs = list(dict.fromkeys(vs))
            if len(vs) >= 3:
                try: bm.faces.new(vs)
                except ValueError: pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)


def build_part(p, cls):
    bm = bmesh.new()
    s = p.get('size') or []
    sh = p['shape']
    sides = p.get('sides')
    if sh in ('box', 'rbox'):
        w, h, d = (s[0] if len(s) > 0 and s[0] else .5), (s[1] if len(s) > 1 and s[1] else .5), (s[2] if len(s) > 2 and s[2] else .5)
        bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * h, v.co.z * d))
        if sh == 'rbox':
            rad = min(s[3] if len(s) > 3 and s[3] else .1, min(w, h, d) * .49)
            bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=rad, segments=3 if cls != 'ship' or rad < .5 else 4,
                            profile=.5, affect='EDGES', clamp_overlap=True)
            p['_rounded'] = True
    elif sh == 'sphere':
        r = s[0] if s and s[0] else .25
        n = segs(r * max(map(abs, p.get('scale') or [1, 1, 1])), cls)
        bmesh.ops.create_uvsphere(bm, u_segments=n, v_segments=max(6, n // 2), radius=r)
        zprim_to_game(bm)
    elif sh in ('cylinder', 'cone'):
        if sh == 'cylinder':
            rt = s[0] if len(s) > 0 and s[0] is not None else .2
            rb = s[1] if len(s) > 1 and s[1] is not None else .2
            h = s[2] if len(s) > 2 and s[2] else .5
        else:
            rt, rb, h = 0.0, (s[0] if s and s[0] else .25), (s[1] if len(s) > 1 and s[1] else .5)
        sc = p.get('scale') or [1, 1, 1]
        n = sides if sides else segs(max(rt, rb) * max(abs(sc[0]), abs(sc[2])), cls)
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=int(n), radius1=rb, radius2=rt, depth=h)
        zprim_to_game(bm)
        if sides and sides <= 8: p['_faceted'] = True
    elif sh == 'torus':
        R, r = (s[0] if s and s[0] else .3), (s[1] if len(s) > 1 and s[1] else .08)
        nu, nv = max(12, segs(R, cls) + 4), (6 if r < .05 else 10)
        grid = [[bm.verts.new(((R + r * math.cos(v)) * math.cos(u), (R + r * math.cos(v)) * math.sin(u), r * math.sin(v)))
                 for v in [j / nv * 2 * math.pi for j in range(nv)]] for u in [i / nu * 2 * math.pi for i in range(nu)]]
        for i in range(nu):
            for j in range(nv):
                bm.faces.new([grid[i][j], grid[(i + 1) % nu][j], grid[(i + 1) % nu][(j + 1) % nv], grid[i][(j + 1) % nv]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    elif sh == 'capsule':
        r, L = (s[0] if s and s[0] else .15), (s[1] if len(s) > 1 and s[1] else .4)
        n = segs(r, cls)
        prof = [(math.cos(a) * r, -L / 2 + math.sin(a) * r) for a in [-math.pi / 2 + j / 6 * math.pi / 2 for j in range(7)]]
        prof += [(math.cos(a) * r, L / 2 + math.sin(a) * r) for a in [j / 6 * math.pi / 2 for j in range(7)]]
        prof[0] = (0, prof[0][1]); prof[-1] = (0, prof[-1][1])
        lathe(bm, prof, n)
    elif sh == 'hull':
        pts = p.get('points') or []
        uniq = []
        for q in pts:
            if not any((Vector(q) - Vector(u)).length < 1e-6 for u in uniq): uniq.append(q)
        if len(uniq) < 4: bm.free(); return None
        vs = [bm.verts.new(q) for q in uniq]
        res = bmesh.ops.convex_hull(bm, input=vs, use_existing_faces=False)
        kill = list({g for g in res['geom_interior'] + res['geom_unused'] if isinstance(g, bmesh.types.BMVert)})
        if kill: bmesh.ops.delete(bm, geom=kill, context='VERTS')
        bmesh.ops.dissolve_limit(bm, angle_limit=math.radians(.5), verts=bm.verts, edges=bm.edges)   # quads instead of fans of slivers
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    else:
        bm.free(); return None
    # scale, rotation, position, exactly as the game does: v' = pos + R (S v)
    S = p.get('scale') or [1, 1, 1]
    R = rot_m(p.get('rotation'))
    pos = Vector(p.get('position') or [0, 0, 0])
    for v in bm.verts:
        v.co = pos + R @ Vector((v.co.x * S[0], v.co.y * S[1], v.co.z * S[2]))
    if S[0] * S[1] * S[2] < 0: bmesh.ops.reverse_faces(bm, faces=bm.faces)
    return bm


def min_dim(p):
    s = p.get('size') or [.5]
    S = [abs(v) for v in (p.get('scale') or [1, 1, 1])]
    sh = p['shape']
    if sh in ('box', 'rbox'): return min(s[0] * S[0], s[1] * S[1], s[2] * S[2])
    if sh == 'cylinder': return min(2 * max(s[0] or 0, s[1] or 0) * min(S[0], S[2]), (s[2] if len(s) > 2 else .5) * S[1])
    if sh == 'cone': return min(2 * s[0] * min(S[0], S[2]), (s[1] if len(s) > 1 else .5) * S[1])
    return 1e9   # spheres, tori, capsules: already round


def bevel_bm(bm, width, segments, angle=30):
    if width <= 0 or not bm.edges: return
    eds = [e for e in bm.edges if e.is_manifold and len(e.link_faces) == 2 and e.calc_face_angle(0) > math.radians(angle)]
    if not eds: return
    try:
        bmesh.ops.bevel(bm, geom=eds, offset=width, offset_type='OFFSET', segments=segments, profile=.5,
                        affect='EDGES', clamp_overlap=True, loop_slide=True)
    except Exception as ex:
        print('   bevel skipped:', ex)


def merge_into(dst, src):
    """append a bmesh into another"""
    vmap = {}
    for v in src.verts:
        vmap[v.index] = dst.verts.new(v.co)
    src.verts.index_update()
    for f in src.faces:
        try: dst.faces.new([vmap[v.index] for v in f.verts])
        except ValueError: pass


def drop_shared_faces(bm):
    """faces two touching slices share (same corners, opposite way round) are inside the merged hull"""
    seen = {}
    for f in bm.faces:
        k = frozenset(v.index for v in f.verts)
        seen.setdefault(k, []).append(f)
    kill = [f for fs in seen.values() if len(fs) > 1 for f in fs]
    if kill: bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose: bmesh.ops.delete(bm, geom=loose, context='VERTS')


# ---------------------------------------------------------------- shading: the bake
HEMI = None


def hemi_dirs(n=48, seed=3):
    global HEMI
    if HEMI: return HEMI
    rnd = random.Random(seed)
    out = []
    for i in range(n):            # cosine-weighted, stratified
        u = (i + rnd.random()) / n
        v = rnd.random()
        r, t = math.sqrt(u), 2 * math.pi * v
        out.append((r * math.cos(t), r * math.sin(t), math.sqrt(max(0, 1 - u))))
    HEMI = out
    return out


def frame(n):
    a = Vector((1, 0, 0)) if abs(n.x) < .9 else Vector((0, 1, 0))
    t = n.cross(a).normalized()
    return t, n.cross(t)


def ao_at(bvh, co, n, reach, dirs):
    t, b = frame(n)
    o = co + n * (reach * .004 + 1e-4)
    hit = 0.0
    for x, y, z in dirs:
        d = t * x + b * y + n * z
        loc, nn, idx, dist = bvh.ray_cast(o, d, reach)
        if loc is not None: hit += 1 - (dist / reach) ** 2 * .6   # near hits darken most
    return 1 - hit / len(dirs)


def sealed(bvh, co, n, reach):
    """a face is sealed when every ray out of it hits its own moving piece"""
    for x, y, z in hemi_dirs()[::4]:
        t, b = frame(n)
        d = t * x + b * y + n * z
        loc, *_ = bvh.ray_cast(co + n * 1e-3, d, reach * 4)
        if loc is None: return False
    return True


# ---------------------------------------------------------------- the model
LEVELS = [dict(seg=2, big=.45, cyl=1.0), dict(seg=1, big=.8, cyl=.8), dict(seg=1, big=1e9, cyl=.65), dict(seg=1, big=1e9, cyl=.5, nobevel=.12)]


def remaster(key, model, out_dir, preview=False, budget=None, lvl=0):
    cls = classify(key, model)
    C = dict(CLASS[cls])
    LV = LEVELS[lvl]
    global SEG_K
    SEG_K = LV['cyl']
    groups = model.get('groups', [])
    by_id = {g['id']: g for g in groups}

    def makes_part(g):
        a = g.get('anim')
        if not a or a.get('type') not in RIGID_ANIM: return False
        if a['type'] == 'wiggle':
            import re
            return bool(re.search(r'aileron|rudder|elev|tailplane|stab|flap', g['id'].lower()))
        return True

    def rigid_of(gid):   # the nearest group (itself or up the chain) that the game turns into a moving part
        q, k = by_id.get(gid), 0
        while q and k < 9:
            if makes_part(q): return q['id']
            q = by_id.get(q.get('parent')); k += 1
        return ''

    def passthrough(p):
        g = by_id.get(p.get('group') or '')
        r = rigid_of(p.get('group') or '')
        return bool(r) and by_id[r]['anim']['type'] in PASS_ANIM

    parts = model['parts']
    xs = [p['position'][0] for p in parts]; ys = [p['position'][1] for p in parts]
    L = max(1.0, max(xs) - min(xs))
    bevel_w = C['bevel']
    reach = max(.4, C['reach'] * L)

    # 1-3: build, bevel, bucket by (moving piece, colour, material, thin)
    buckets = {}
    hulls = {}
    keep = []
    for p in parts:
        if passthrough(p):
            keep.append(p); continue
        if p['shape'] == 'hull' and cls == 'tree':
            pass
        rig = rigid_of(p.get('group') or '')
        thin = False
        if cls == 'ship' and not rig:
            md = min_dim(p)
            s = p.get('size') or []
            thin = p['shape'] in ('box', 'rbox', 'cylinder') and md < .35
        leaf = ''
        if cls == 'tree':
            import re
            if p.get('material') != 'glow' and re.search(r'crown|canopy|frond|leaf|foliage|needle', p.get('name') or '', re.I):
                leaf = 'mass' if p['shape'] == 'hull' else 'panel'
        bk = (rig, p.get('color', '#9aa5a0'), p.get('material', 'paint'), thin, leaf)
        bm = build_part(p, cls)
        if bm is None: continue
        if p['shape'] == 'hull' and cls != 'tree':
            hulls.setdefault(bk, []).append(bm)          # welded and bevelled together below
            continue
        md = min_dim(p)
        if cls != 'tree' and not p.get('_rounded') and not p.get('_faceted') and md < 1e8 and md > max(bevel_w * 2.2, LV.get('nobevel', 0) * L / 10):
            w = min(bevel_w * (1.0 if md > bevel_w * 8 else .6), md * .18)
            bevel_bm(bm, w, LV['seg'] if md > LV['big'] * (L / 10 if cls == 'ship' else 1) else 1)
        elif p.get('_faceted') and md > bevel_w * 2.2:
            bevel_bm(bm, min(bevel_w * .6, md * .15), 1, angle=50)
        buckets.setdefault(bk, bmesh.new())
        merge_into(buckets[bk], bm)
        bm.free()

    for bk, lst in hulls.items():
        hb = bmesh.new()
        for bm in lst: merge_into(hb, bm); bm.free()
        bmesh.ops.remove_doubles(hb, verts=hb.verts, dist=max(1e-4, L * 2e-5))
        hb.verts.index_update()
        drop_shared_faces(hb)
        bmesh.ops.remove_doubles(hb, verts=hb.verts, dist=max(1e-4, L * 2e-5))
        bmesh.ops.dissolve_limit(hb, angle_limit=math.radians(1.0), verts=hb.verts, edges=hb.edges)
        bmesh.ops.recalc_face_normals(hb, faces=hb.faces)
        bevel_bm(hb, bevel_w * 1.2, LV['seg'], angle=38)
        buckets.setdefault(bk, bmesh.new())
        merge_into(buckets[bk], hb)
        hb.free()

    # 4: tidy, budget, seal test
    for bk, bm in buckets.items():
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=max(5e-5, L * 1e-5))
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
    by_rig = {}
    for bk, bm in buckets.items(): by_rig.setdefault(bk[0], []).append(bm)
    culled = 0
    if cls != 'tree':
        for rig, bms in by_rig.items():
            tmp = bmesh.new()
            for bm in bms: merge_into(tmp, bm)
            bvh = BVHTree.FromBMesh(tmp)
            for bm in bms:
                bm.faces.ensure_lookup_table()
                kill = [f for f in bm.faces if all(sealed(bvh, q, f.normal, reach) for q in
                        [f.calc_center_median()] + [v.co.lerp(f.calc_center_median(), .08) for v in f.verts])]
                culled += len(kill)
                if kill: bmesh.ops.delete(bm, geom=kill, context='FACES')
            tmp.free()
    # the whole model at rest, for occlusion
    allbm = bmesh.new()
    for bm in buckets.values(): merge_into(allbm, bm)
    for p in keep:
        b = build_part(p, cls)
        if b: merge_into(allbm, b); b.free()
    bvh_all = BVHTree.FromBMesh(allbm)
    ymin = min(v.co.y for v in allbm.verts) if allbm.verts else 0
    ymax = max(v.co.y for v in allbm.verts) if allbm.verts else 1
    allbm.free()
    wl = model_waterline(model) if cls == 'ship' else None

    # 5-6: normals and shade, then pack
    dirs = hemi_dirs()
    out_parts = []
    previews = []
    nseed = random.Random(hash(key) & 0xffff).random() * 100
    for bk, bm in buckets.items():
        rig, col, mat, thin, leaf = bk
        if not bm.faces: bm.free(); continue
        me = bpy.data.meshes.new(f'{key}|{rig}|{col}|{mat}')
        bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(me.name, me)
        bpy.context.scene.collection.objects.link(ob)
        me.set_sharp_from_angle(angle=math.radians(34 if cls != 'tree' else 70))
        wn = ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); wn.keep_sharp = True; wn.mode = 'FACE_AREA'; wn.weight = 50
        dg = bpy.context.evaluated_depsgraph_get()
        ev = ob.evaluated_get(dg)
        em = ev.to_mesh()
        cn = [Vector(c.vector) for c in em.corner_normals]
        # convexity per vertex: negative when the surface bends away (an edge), positive in a crease
        conv = [0.0] * len(em.vertices)
        cnt = [0] * len(em.vertices)
        vn = [Vector((0, 0, 0)) for _ in em.vertices]
        for poly in em.polygons:
            for li in poly.loop_indices:
                vn[em.loops[li].vertex_index] += Vector(poly.normal) * poly.area
        for e in em.edges:
            a, b = e.vertices
            d = (em.vertices[b].co - em.vertices[a].co)
            if d.length < 1e-9: continue
            d.normalize()
            na, nb_ = vn[a].normalized(), vn[b].normalized()
            conv[a] += na.dot(d); cnt[a] += 1
            conv[b] -= nb_.dot(d); cnt[b] += 1
        conv = [conv[i] / cnt[i] if cnt[i] else 0 for i in range(len(conv))]
        ao_v = {}
        verts, idx, vmap = [], [], {}
        for poly in em.polygons:
            tri = []
            for li in poly.loop_indices:
                vi = em.loops[li].vertex_index
                n = cn[li]
                kq = (vi, round(n.x, 3), round(n.y, 3), round(n.z, 3))
                if kq not in vmap:
                    co = Vector(em.vertices[vi].co)
                    if (vi, kq[1:]) not in ao_v:
                        ao_v[(vi, kq[1:])] = ao_at(bvh_all, co, n, reach, dirs) if mat != 'glow' else 1.0
                    ao = ao_v[(vi, kq[1:])]
                    sh = shade(cls, mat, leaf, co, n, ao, conv[vi], ymin, ymax, wl, L, nseed)
                    vmap[kq] = len(verts)
                    verts.append((co, n, sh))
                tri.append(vmap[kq])
            if len(tri) == 3: idx.append(tri)
        ev.to_mesh_clear()
        if preview: previews.append((ob, verts, idx, col, mat))
        else:
            bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
        part = dict(name=bucket_name(rig, mat, thin, leaf), shape='mesh', position=[0, 0, 0], color=col, material=mat)
        if rig: part['group'] = rig
        if leaf: part['leaf'] = leaf
        if thin: part['thin'] = 1
        part['_v'] = verts; part['_i'] = idx
        out_parts.append(part)
    out = dict(name=model['name'], groups=groups)
    out['parts'] = keep + out_parts
    # the bits forgeMesh still reads by name: barrels (bore, rest bearing), hull underwater (waterline), main paint
    out['logic'] = [dict(name=p.get('name', ''), shape=p['shape'], size=p.get('size', []), position=p['position'], group=p.get('group'))
                    for p in parts if (not passthrough(p)) and (
                        (p.get('group') and by_id.get(p['group'], {}).get('anim', {}).get('type') == 'recoil') or named(p))]
    if wl is not None: out['wl'] = wl
    ref = main_paint(parts)
    if ref: out['ref'] = ref
    tris = sum(len(p['_i']) for p in out_parts) + sum(est_tris(p) for p in keep)
    out['_tris'] = tris
    print(f'{key:34s} L{lvl} {cls:5s} parts {len(parts):4d} -> buckets {len(out_parts):3d} + kept {len(keep):3d}  tris {tris:6d}  sealed faces dropped {culled}')
    return out, previews, cls


def named(p):
    import re
    n = p.get('name') or ''
    return bool((re.search(r'funnel$|^funnel\b|smokestack|stack$', n, re.I) and not re.search(r'stain|grating|rail', n, re.I))
                or (re.search(r'CIWS|AA |flak|oerlikon|bofors', n, re.I) and re.search(r'base|mount|dome', n, re.I)))


def bucket_name(rig, mat, thin, leaf):
    if leaf: return 'crown ' + leaf
    return ' '.join(x for x in [rig or 'body', mat, 'thin rail' if thin else ''] if x)


def est_tris(p):
    return {'box': 12, 'rbox': 12, 'sphere': 120, 'cylinder': 48, 'cone': 24, 'torus': 200, 'capsule': 100, 'hull': 20}.get(p['shape'], 20)


def main_paint(parts):
    n = {}
    for p in parts:
        if p.get('material') == 'paint': n[p['color']] = n.get(p['color'], 0) + 1
    return max(n, key=n.get) if n else None


def model_waterline(model):
    wl = -1e9
    for p in model['parts']:
        if 'underwater' in (p.get('name') or '').lower():
            for q in (p.get('points') or [[0, (p.get('size') or [0, 0])[1] / 2 if len(p.get('size') or []) > 1 else 0, 0]]):
                wl = max(wl, q[1] + p['position'][1])
    return wl if wl > -1e8 else None


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))) if b != a else 0.0
    return t * t * (3 - 2 * t)


def shade(cls, mat, leaf, co, n, ao, conv, ymin, ymax, wl, L, seed):
    """one multiplier for the vertex colour: light that reaches it, worn edges, dirt in the creases and near the ground"""
    h = (co.y - ymin) / max(1e-3, ymax - ymin)
    nz = noise.noise(Vector((co.x, co.y, co.z)) * (1.6 / max(1, L ** .5)) + Vector((seed, 0, 0)))          # broad tonal variation
    nf = noise.noise(Vector((co.x, co.y * 2.5, co.z)) * (9 / max(1, L ** .5)) + Vector((0, seed, 0)))      # fine streaks
    occ = .42 + .58 * ao ** 1.25
    if cls == 'tree':
        if leaf: return max(.2, min(1.6, (.5 + .5 * ao) * (1 + .15 * nz) * (.85 + .3 * h)))
        return max(.2, min(1.5, (.45 + .55 * ao)))
    if mat == 'glow': return 1.0
    # the game's shader already lays camouflage, mud, dust, grain, wet hulls and anti-fouling: the bake only adds what it cannot know
    edge = smooth(.04, .35, -conv)      # convex: chipped, rubbed bright
    crease = smooth(.05, .45, conv)     # concave: grime collects
    s = occ * (1 - .16 * crease)
    if mat in ('paint', 'matte'):
        s *= 1 + .14 * edge
    elif mat in ('metal', 'glossy'):
        s *= 1 + .18 * edge
    elif mat == 'rubber':
        s *= 1 + .10 * edge
    elif mat == 'glass':
        s = .6 + .4 * occ
    if cls == 'ship' and wl is not None:
        above = co.y - wl
        rust = smooth(.3, .75, nf * .5 + .5) * (1 - smooth(0, 6, above)) * smooth(-.5, .3, above)   # faint streaks from the scuppers
        s *= 1 - .08 * rust
    return max(.12, min(1.08, s))       # never brighter than the paint itself by much: the game's camouflage keys off brightness


# ---------------------------------------------------------------- pack: one binary blob per model, deflated, base64
def pack(model_out):
    """vertices in first-use order; positions as zigzag deltas, indices as distance below the high-water mark,
    every stream split into byte planes so deflate finds the repeats"""
    import zlib, base64
    blob = bytearray()
    parts = []
    for p in model_out['parts']:
        if p.get('shape') != 'mesh':
            parts.append(p); continue
        V, I = p.pop('_v'), p.pop('_i')
        order, remap = [], {}
        for t in I:
            for v in t:
                if v not in remap: remap[v] = len(order); order.append(v)
        V = [V[i] for i in order]; I = [[remap[v] for v in t] for t in I]
        assert len(V) < 65536
        lo = [min(v[0][k] for v in V) for k in range(3)]
        hi = [max(v[0][k] for v in V) for k in range(3)]
        sp = [max(1e-6, hi[k] - lo[k]) for k in range(3)]
        p['box'] = [round(x, 5) for x in lo + sp]
        p['nv'] = len(V); p['nt'] = len(I); p['at'] = len(blob)
        q = [[int(round((co[k] - lo[k]) / sp[k] * 65535)) for k in range(3)] for co, n, s in V]
        d, prev = [], [0, 0, 0]
        for v in q:
            for k in range(3):
                x = ((v[k] - prev[k] + 32768) & 0xffff) - 32768          # wraps: the decoder adds modulo 65536
                d.append(x << 1 if x >= 0 else (-x << 1) - 1)
            prev = v
        blob += bytes(x & 255 for x in d) + bytes(x >> 8 for x in d)
        ox, oy = [], []
        for co, n, s in V:
            l1 = abs(n.x) + abs(n.y) + abs(n.z) or 1
            x, y = n.x / l1, n.y / l1
            if n.z < 0: x, y = (1 - abs(y)) * (1 if x >= 0 else -1), (1 - abs(x)) * (1 if y >= 0 else -1)
            ox.append(int(round(x * 127)) & 255); oy.append(int(round(y * 127)) & 255)
        blob += bytes(ox) + bytes(oy)
        blob += bytes(int(round(min(1.7, s) / 1.7 * 255)) for co, n, s in V)
        hw, c = 0, []
        for t in I:
            for v in t:
                c.append(hw - v)
                if v == hw: hw += 1
        blob += bytes(x & 255 for x in c) + bytes(x >> 8 for x in c)
        parts.append(p)
    model_out['parts'] = parts
    z = zlib.compress(bytes(blob), 9)[2:-4]          # raw deflate for the game's inflate
    model_out['blob'] = base64.b64encode(z).decode()
    model_out['blobN'] = len(blob)
    return model_out


# ---------------------------------------------------------------- preview render (Cycles, CPU)
def render_preview(key, previews, cls, path, kept=()):
    import bpy
    sc = bpy.context.scene
    for p in kept:
        b = build_part(dict(p), cls)
        if not b: continue
        b.verts.ensure_lookup_table()
        V = [(v.co.copy(), Vector((0, 1, 0)), .8) for v in b.verts]
        bmesh.ops.triangulate(b, faces=b.faces)
        I = [[v.index for v in f.verts] for f in b.faces]
        b.free()
        me = bpy.data.meshes.new('k'); ob = bpy.data.objects.new('k', me); sc.collection.objects.link(ob)
        previews.append((ob, V, I, p.get('color', '#333333'), p.get('material', 'metal')))
    mats = {}
    pal = {'tank': (.36, .38, .27)}
    for ob, verts, idx, col, mat in previews:
        me = ob.data
        me.clear_geometry()
        me.vertices.add(len(verts)); me.loops.add(len(idx) * 3); me.polygons.add(len(idx))
        flat = []
        for co, n, s in verts: flat += [co.x, -co.z, co.y]
        me.vertices.foreach_set('co', flat)
        me.loops.foreach_set('vertex_index', [i for t in idx for i in t])
        me.polygons.foreach_set('loop_start', [k * 3 for k in range(len(idx))])
        me.update()
        (me.normals_split_custom_set if ob.name != 'k' and not ob.name.startswith('k.') else (lambda x: None))([(verts[i][1].x, -verts[i][1].z, verts[i][1].y) for t in idx for i in t])
        ca = me.color_attributes.new('Shade', 'FLOAT_COLOR', 'CORNER')
        c = hexcol(col)
        if cls == 'tank' and mat == 'paint': c = (.30, .32, .22)
        ca.data.foreach_set('color', [x for t in idx for i in t for x in (c[0] * verts[i][2] ** 1.0 * .9, c[1] * verts[i][2] * .9, c[2] * verts[i][2] * .9, 1)])
        m = bpy.data.materials.new('m'); m.use_nodes = True
        nt = m.node_tree; bsdf = nt.nodes['Principled BSDF']
        attr = nt.nodes.new('ShaderNodeVertexColor'); attr.layer_name = 'Shade'
        # vertex colours come out sRGB-ish from the game palette: treat as display colours
        gam = nt.nodes.new('ShaderNodeGamma'); gam.inputs[1].default_value = 2.2
        nt.links.new(attr.outputs[0], gam.inputs[0]); nt.links.new(gam.outputs[0], bsdf.inputs['Base Color'])
        bsdf.inputs['Roughness'].default_value = {'metal': .45, 'glossy': .3, 'glass': .05, 'rubber': .9}.get(mat, .62)
        bsdf.inputs['Metallic'].default_value = .6 if mat == 'metal' else 0
        if mat == 'glow':
            bsdf.inputs['Emission Color'].default_value = (*c, 1); bsdf.inputs['Emission Strength'].default_value = 4
        me.materials.append(m)
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 48; sc.cycles.device = 'CPU'
    sc.render.resolution_x, sc.render.resolution_y = 1400, 800
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.film_transparent = False
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    bg = world.node_tree.nodes['Background']; bg.inputs[0].default_value = (.55, .62, .72, 1); bg.inputs[1].default_value = .6
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 4.2; sun.data.angle = math.radians(3); sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-35))
    sc.collection.objects.link(sun)
    # ground
    bmin = Vector((1e9,) * 3); bmax = Vector((-1e9,) * 3)
    for ob, *_ in previews:
        for v in ob.data.vertices: bmin = Vector(map(min, bmin, v.co)); bmax = Vector(map(max, bmax, v.co))
    ctr = (bmin + bmax) / 2; size = (bmax - bmin).length
    gme = bpy.data.meshes.new('g'); gb = bmesh.new(); bmesh.ops.create_grid(gb, x_segments=1, y_segments=1, size=size * 4); gb.to_mesh(gme)
    g = bpy.data.objects.new('g', gme); g.location = (ctr.x, ctr.y, bmin.z - (0 if cls == 'tank' else size * .02)); sc.collection.objects.link(g)
    gm = bpy.data.materials.new('gm'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.16, .15, .12, 1) if cls != 'ship' else (.03, .07, .09, 1)
    gm.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .95 if cls != 'ship' else .15
    gme.materials.append(gm)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.lens = 55
    cam.location = ctr + Vector((-.62, -.95, .42)).normalized() * size * 1.55
    cam.rotation_euler = (ctr - cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    preview = '--preview' in sys.argv
    src, out_dir = args[0], args[1]
    keys = args[2:]
    os.makedirs(out_dir, exist_ok=True)
    models = json.load(open(src))
    orig = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'orig_tris.json')))
    for k in keys or list(models):
        o_ = orig.get(k, 4000)
        cls_ = classify(k, models[k])
        budget = o_ * 1.1 if cls_ == 'tree' else o_ * 1.25 if cls_ == 'plane' else o_ * 1.15   # never heavier than the game can carry
        for lvl in range(len(LEVELS)):
            reset()
            out, prev, cls = remaster(k, models[k], out_dir, preview, budget, lvl)
            if out['_tris'] <= budget or lvl == len(LEVELS) - 1: break
        print(f'   game had {orig.get(k)} tris, budget {budget:.0f}, now {out["_tris"]}')
        out.pop('_tris')
        if preview: render_preview(k, prev, cls, os.path.join(out_dir, k + '.png'), [p for p in out['parts'] if p.get('shape') != 'mesh'])
        packed = pack(out)
        json.dump(packed, open(os.path.join(out_dir, k + '.json'), 'w'), separators=(',', ':'))
        print(f'   packed {len(packed["blob"]) / 1024:.0f} KB base64')
