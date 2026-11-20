"""For every turret: is anything rigid inside the barrels' swing circle taller than the trunnion?
(The game's turret-clearance rule.) Usage: python3 check_clearance.py iron-tide-*.json"""
import json, sys, math

def top_and_xz(p):
    x, y, z = p["position"]
    sc = p.get("scale", [1, 1, 1])
    if p["shape"] == "hull":
        pts = [(x + q[0], y + q[1], z + q[2]) for q in p["points"]]
        return max(q[1] for q in pts), [(q[0], q[2]) for q in pts]
    s = p["size"]
    r = max(s[:3]) / 2 * max(sc) if p["shape"] in ("box", "rbox") else (max(s) * max(sc))
    sh = p["shape"]
    if sh in ("box", "rbox", "cone"):
        ext = s[1] / 2
    elif sh == "sphere":
        ext = s[0]
    elif sh == "cylinder":
        ext = s[2] / 2
    elif sh == "torus":
        ext = s[0] + s[1]
    else:
        ext = s[0] + s[1] / 2
    ext *= max(sc)
    if p.get("rotation"):
        ext = max(ext, r)
    return y + ext, [(x, z)]

bad = 0
for f in sys.argv[1:]:
    m = json.load(open(f))
    groups = {g["id"]: g for g in m.get("groups", [])}
    def root_of(gid):
        while gid and groups[gid].get("parent"):
            gid = groups[gid]["parent"]
        return gid
    for g in groups.values():
        if (g.get("anim") or {}).get("type") != "recoil" or not g.get("parent"):
            continue
        tur = root_of(g["id"])
        if groups[tur]["anim"]["type"] != "turret":
            continue
        px, ty, pz = groups[tur]["pivot"][0], g["pivot"][1], groups[tur]["pivot"][2]
        reach = max(math.dist((px, pz), (q["position"][0], q["position"][2])) for q in m["parts"] if q.get("group") == g["id"]) + 2
        for p in m["parts"]:
            if p.get("group"):                     # moving parts (other turrets, radar, lamps) are the game's business
                continue
            if any(k in p["name"] for k in ("barbette", "rail", "gun deck", "whip", "antenna")):
                continue
            top, xz = top_and_xz(p)
            if top <= ty:
                continue
            facing = 1 if g["anim"].get("axis", [-1, 0, 0])[0] < 0 else -1      # recoil slides backwards: barrels point the other way
            def in_arc(q):
                dx, dz = q[0] - px, q[1] - pz
                return dx * facing > -0.1 * abs(dz)            # anywhere in the half-plane the guns face (a wide margin)
            near = [q for q in xz if in_arc(q)]
            d = min((math.dist((px, pz), q) for q in near), default=1e9)
            if d < reach:
                bad += 1
                print(f"{m['name']}: {tur} trunnion y={ty:.2f} reach={reach:.1f}: '{p['name']}' top {top:.2f} at {d:.1f} m")
print("problems:", bad)
