"""Builds Iron Tide vehicle models for Shape Forge, following the IRON TIDE model brief.

Axes and units follow the brief: metres, the model faces +X, +Y is up, +Z is starboard.
Origin: ground level for tanks, the waterline for ships, the centreline for planes.
Every animated part from the brief's animation table is its own group with its own pivot.

    python3 build_iron_tide.py      -> writes one JSON file per model next to this script
"""
import json
import math
import os

OUT = os.path.dirname(os.path.abspath(__file__))


class Model:
    def __init__(self, name):
        self.name = name
        self.parts = []
        self.groups = []

    def group(self, gid, pivot, anim=None, parent=None):
        g = {"id": gid, "pivot": [round(v, 4) for v in pivot]}
        if parent:
            g["parent"] = parent
        if anim:
            g["anim"] = anim
        self.groups.append(g)
        return gid

    def add(self, name, shape, size, pos, color, material="paint", rot=None, scale=None, group=None, points=None, sides=None, flat=False):
        p = {"name": name, "shape": shape, "size": [round(v, 4) for v in size], "position": [round(v, 4) for v in pos],
             "color": color, "material": material}
        if rot and any(rot):
            p["rotation"] = [round(v, 3) for v in rot]
        if scale:
            p["scale"] = [round(v, 4) for v in scale]
        if group:
            p["group"] = group
        if points:
            p["points"] = [[round(v, 4) for v in q] for q in points]
        if sides:
            p["sides"] = sides
        if flat:
            p["flat"] = True
        self.parts.append(p)

    def box(self, name, size, pos, color, material="paint", **kw):
        self.add(name, "box", size, pos, color, material, **kw)

    def rbox(self, name, size, r, pos, color, material="paint", **kw):
        self.add(name, "rbox", list(size) + [r], pos, color, material, **kw)

    def hull(self, name, points, color, material="paint", group=None, pos=(0, 0, 0)):
        self.add(name, "hull", [], pos, color, material, points=[[q[0] - pos[0], q[1] - pos[1], q[2] - pos[2]] for q in points], group=group)

    def cyl_x(self, name, r1, r2, length, pos, color, material="metal", sides=None, group=None):
        """Cylinder lying along X. r1 is the radius at the +X end."""
        self.add(name, "cylinder", [r1, r2, length], pos, color, material, rot=[0, 0, -90], sides=sides, group=group)

    def cyl_z(self, name, r, width, pos, color, material="metal", sides=None, group=None):
        self.add(name, "cylinder", [r, r, width], pos, color, material, rot=[90, 0, 0], sides=sides, group=group)

    def cyl_y(self, name, r1, r2, h, pos, color, material="metal", sides=None, group=None):
        self.add(name, "cylinder", [r1, r2, h], pos, color, material, sides=sides, group=group)

    def save(self):
        data = {"name": self.name, "parts": self.parts, "groups": self.groups}
        fname = self.name.lower().replace(" ", "-") + ".json"
        with open(os.path.join(OUT, fname), "w") as f:
            json.dump(data, f, separators=(",", ":"))
        print(f"{self.name}: {len(self.parts)} parts, {len(self.groups)} groups -> {fname}")
        return data


def mirror(z_values):
    return [(z, "L" if z < 0 else "R") for z in z_values]


def convex_hull_2d(pts):
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]  # counter-clockwise


def resample_loop(loop, step):
    """Points every `step` metres along a closed polyline, with the direction (angle) at each."""
    n = len(loop)
    seg = [math.dist(loop[i], loop[(i + 1) % n]) for i in range(n)]
    total = sum(seg)
    count = max(8, int(total / step))
    step = total / count
    out, i, acc = [], 0, 0.0
    for k in range(count):
        s = k * step
        while acc + seg[i] < s:
            acc += seg[i]
            i += 1
        t = (s - acc) / seg[i]
        a, b = loop[i], loop[(i + 1) % n]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, math.atan2(b[1] - a[1], b[0] - a[0])))
    return out, total


# ---------------------------------------------------------------- tanks
OLIVE = {"top": "#5b6331", "dark": "#3c4220", "light": "#737d40", "under": "#33391f", "accent": "#d2aa3c"}
STEEL = "#4a4c47"
DARK_STEEL = "#2c2e2b"
RUBBER = "#1d1f1d"
GLASS = "#5fa8c8"
LAMP = "#fff1c4"


def tank_running_gear(m, length, width, paint, road_wheels=6, wheel_r=0.33, track_w=0.62):
    """Real track loop with link ridges, a toothed rear drive sprocket, a front idler, return rollers
    and spoked road wheels. Every wheel is its own rolling group; each track is a group that circulates."""
    half = width / 2 - track_w / 2
    x_front, x_rear = length / 2 - 0.42, -length / 2 + 0.42
    sprocket = (x_rear, 0.74, 0.34)
    idler = (x_front, 0.74, 0.29)
    span = (x_front - 0.62) - (x_rear + 0.62)
    road = [(x_rear + 0.62 + span * i / (road_wheels - 1), wheel_r + 0.06, wheel_r) for i in range(road_wheels)]
    rollers = [(x_rear + 0.62 + span * f, 0.96, 0.09) for f in (0.2, 0.5, 0.8)]
    thick = 0.07

    # the loop the track follows: wrap every wheel the track touches, then push out by half the track thickness
    pts = []
    for (cx, cy, r) in [sprocket, idler] + road:
        for k in range(48):
            a = 2 * math.pi * k / 48
            pts.append((round(cx + (r + thick / 2) * math.cos(a), 4), round(cy + (r + thick / 2) * math.sin(a), 4)))
    loop = convex_hull_2d(pts)  # counter-clockwise: the bottom run goes from rear to front ...
    loop = loop[::-1]  # ... so reverse it: the bottom run must move backward (-X) as the tank drives forward

    for z, side in mirror([-half, half]):
        out = 1 if z > 0 else -1
        gid = m.group(f"track{side}", [0, 0, 0], {"type": "track", "path": [[round(x, 4), round(y, 4)] for x, y in loop]})
        links, total = resample_loop(loop, 0.155)
        for i, (x, y, ang) in enumerate(links):
            deg = math.degrees(ang)
            m.box(f"track link {side}{i}", [0.15, thick, track_w], [x, y, z], DARK_STEEL, "metal", rot=[0, 0, deg], group=gid)
            # outer ridge (grouser): the loop runs clockwise, so the outside is to the left of the travel direction
            nx, ny = -math.sin(ang), math.cos(ang)
            m.box(f"track ridge {side}{i}", [0.045, 0.035, track_w * 0.92], [x + nx * 0.045, y + ny * 0.045, z], "#3a3b37", "metal", rot=[0, 0, deg], group=gid)

        # road wheels: twin discs, rubber tyres, hub and six spokes on the outer face
        for i, (x, y, r) in enumerate(road):
            g = m.group(f"wheel{side}{i}", [x, y, z], {"type": "roll", "radius": r})
            for dz in (-0.17, 0.17):
                m.cyl_z(f"road wheel {side}{i}", r - 0.035, 0.13, [x, y, z + dz], paint["dark"], "paint", group=g)
                m.add(f"tyre {side}{i}", "torus", [r - 0.035, 0.045], [x, y, z + dz], RUBBER, "rubber", group=g)
            m.cyl_z(f"hub {side}{i}", 0.1, 0.42, [x, y, z], STEEL, "metal", sides=8, group=g)
            for k in range(6):
                m.box(f"spoke {side}{i}.{k}", [0.05, r * 1.55, 0.03], [x, y, z + out * 0.245], paint["light"], "paint", rot=[0, 0, k * 30], group=g)
            m.cyl_z(f"hub cap {side}{i}", 0.06, 0.03, [x, y, z + out * 0.26], "#8d918a", "metal", sides=6, group=g)

        # drive sprocket with teeth
        cx, cy, r = sprocket
        g = m.group(f"sprocket{side}", [cx, cy, z], {"type": "roll", "radius": r})
        for dz in (-0.2, 0.2):
            m.cyl_z(f"sprocket ring {side}", r - 0.04, 0.08, [cx, cy, z + dz], STEEL, "metal", group=g)
            for k in range(13):
                a = 2 * math.pi * k / 13
                m.box(f"sprocket tooth {side}{k}", [0.08, 0.09, 0.08], [cx + (r - 0.02) * math.cos(a), cy + (r - 0.02) * math.sin(a), z + dz], STEEL, "metal", rot=[0, 0, math.degrees(a)], group=g)
        m.cyl_z(f"sprocket hub {side}", 0.17, 0.5, [cx, cy, z], paint["dark"], "paint", sides=10, group=g)
        for k in range(5):
            m.box(f"sprocket bolt {side}{k}", [0.04, 0.04, 0.04], [cx + 0.11 * math.cos(k * 1.2566), cy + 0.11 * math.sin(k * 1.2566), z + out * 0.27], "#8d918a", "metal", group=g)

        # idler
        cx, cy, r = idler
        g = m.group(f"idler{side}", [cx, cy, z], {"type": "roll", "radius": r})
        for dz in (-0.17, 0.17):
            m.cyl_z(f"idler disc {side}", r, 0.12, [cx, cy, z + dz], paint["dark"], "paint", group=g)
        m.cyl_z(f"idler hub {side}", 0.09, 0.44, [cx, cy, z], STEEL, "metal", sides=8, group=g)
        for k in range(4):
            m.box(f"idler spoke {side}{k}", [0.05, r * 1.6, 0.03], [cx, cy, z + out * 0.235], paint["light"], "paint", rot=[0, 0, k * 45], group=g)

        # return rollers
        for i, (x, y, r) in enumerate(rollers):
            g = m.group(f"roller{side}{i}", [x, y, z], {"type": "roll", "radius": r})
            m.cyl_z(f"return roller {side}{i}", r, 0.36, [x, y, z], paint["dark"], "paint", group=g)
            m.box(f"roller mark {side}{i}", [0.03, r * 1.7, 0.02], [x, y, z + out * 0.185], paint["light"], "paint", group=g)

        # suspension arms (fixed), one per road wheel
        for i, (x, y, r) in enumerate(road):
            m.box(f"suspension arm {side}{i}", [0.42, 0.09, 0.08], [x + 0.18, y + 0.14, z - out * 0.33], paint["dark"], "paint", rot=[0, 0, 22])
    return {"half": half, "track_w": track_w, "sprocket": sprocket, "idler": idler}


def medium_tank():
    m = Model("Iron Tide Medium Tank")
    P = OLIVE
    L, W = 7.2, 3.3
    gear = tank_running_gear(m, L, W, P)
    zin = gear["half"] - gear["track_w"] / 2 - 0.02  # inner edge of the tracks

    # lower hull between the tracks, with a sloped lower nose plate and sloped rear
    lower = []
    for z in (-zin, zin):
        lower += [(-3.35, 0.5, z), (2.95, 0.5, z), (3.5, 0.92, z), (3.1, 1.15, z), (-3.45, 1.15, z), (-3.55, 0.75, z)]
    m.hull("lower hull", lower, P["under"])

    # upper hull: bevelled sponsons over the tracks, a long sloped glacis, angled side plates, sloped rear plate
    upper = []
    for s in (-1, 1):
        upper += [(3.15, 1.12, s * 1.62), (-3.5, 1.12, s * 1.62),             # bottom edge over the tracks
                  (-3.45, 1.42, s * 1.66), (2.75, 1.42, s * 1.66),             # the side plate bulges out a little
                  (2.15, 1.66, s * 1.5), (-3.25, 1.66, s * 1.5),               # bevelled top edge
                  (3.55, 1.0, s * 1.15)]                                       # nose
    m.hull("upper hull", upper, P["top"])
    m.box("deck stripe", [3.2, 0.012, 0.22], [-1.6, 1.667, 0], P["accent"], "paint")

    # glacis details: driver's hatch and periscopes, hull machine gun, headlamps with guards, tow hooks, spare track links
    m.cyl_y("driver hatch", 0.3, 0.32, 0.06, [2.0, 1.69, -0.45], P["light"], "paint", sides=12)
    m.box("driver hatch hinge", [0.08, 0.05, 0.4], [1.72, 1.71, -0.45], DARK_STEEL, "metal")
    for i, dz in enumerate((-0.2, 0.0, 0.2)):
        m.box(f"driver periscope {i}", [0.1, 0.07, 0.12], [2.32, 1.69, -0.45 + dz], GLASS, "glass", rot=[0, 0, -20])
    m.add("hull MG ball", "sphere", [0.13], [3.02, 1.3, 0.55], P["dark"])
    m.cyl_x("hull MG barrel", 0.025, 0.025, 0.6, [3.35, 1.32, 0.55], DARK_STEEL)
    for s, side in ((-1, "L"), (1, "R")):
        m.rbox(f"headlamp housing {side}", [0.14, 0.16, 0.22], 0.03, [2.95, 1.36, s * 1.42], P["dark"])
        m.box(f"headlamp {side}", [0.03, 0.11, 0.16], [3.03, 1.36, s * 1.42], LAMP, "glow")
        m.add(f"headlamp guard {side}", "torus", [0.13, 0.015], [3.05, 1.36, s * 1.42], DARK_STEEL, "metal", rot=[0, 90, 0])
        m.add(f"tow hook front {side}", "torus", [0.08, 0.025], [3.48, 0.86, s * 0.75], DARK_STEEL, "metal", rot=[90, 0, 0])
        m.add(f"tow hook rear {side}", "torus", [0.08, 0.025], [-3.55, 0.82, s * 0.75], DARK_STEEL, "metal", rot=[90, 0, 0])
        m.box(f"mud flap {side}", [0.03, 0.42, 0.56], [-3.52, 0.92, s * gear["half"]], RUBBER, "rubber")
        m.box(f"front mud guard {side}", [0.03, 0.3, 0.58], [3.25, 1.0, s * gear["half"]], P["dark"], "paint", rot=[0, 0, 30])
    for i in range(6):
        m.box(f"spare track link {i}", [0.14, 0.05, 0.56], [2.6 + i * 0.12, 1.47 - i * 0.065, 0.0], DARK_STEEL, "metal", rot=[0, 0, -28])

    # fender stowage boxes, tools, exhausts and engine deck louvres
    for s, side in ((-1, "L"), (1, "R")):
        m.rbox(f"stowage box front {side}", [0.9, 0.32, 0.36], 0.03, [0.9, 1.82, s * 1.4], P["light"])
        m.rbox(f"stowage box rear {side}", [1.1, 0.34, 0.36], 0.03, [-2.3, 1.83, s * 1.4], P["light"])
        for k in range(2):
            m.box(f"box latch {side}{k}", [0.05, 0.08, 0.02], [-2.6 + k * 0.6, 1.86, s * 1.585], DARK_STEEL, "metal")
        m.cyl_x(f"tow cable {side}", 0.035, 0.035, 2.4, [-0.6, 1.7, s * 1.58], "#3c3b35", "metal")
        m.cyl_x(f"exhaust pipe {side}", 0.09, 0.11, 0.5, [-3.55, 1.38, s * 1.05], "#3a2f28", "metal")
        m.cyl_x(f"exhaust heat shield {side}", 0.14, 0.14, 0.32, [-3.45, 1.38, s * 1.05], P["dark"], "paint", sides=8)
    m.rbox("engine deck", [2.3, 0.06, 2.3], 0.02, [-2.25, 1.69, 0], P["dark"])
    for k in range(9):
        m.box(f"louvre {k}", [0.16, 0.035, 2.0], [-3.2 + k * 0.24, 1.73, 0], P["top"], "paint", rot=[0, 0, 25])
    for k in range(2):
        m.cyl_y(f"filter cap {k}", 0.16, 0.16, 0.12, [-1.35, 1.75, -0.6 + k * 1.2], P["dark"], "paint", sides=10)

    # turret ring (part of the hull) and the turret
    tp = [0.25, 1.68, 0]
    m.cyl_y("turret ring", 1.05, 1.1, 0.08, [tp[0], 1.7, 0], DARK_STEEL, "metal")
    T = m.group("turret", tp, {"type": "turret", "axis": [0, 1, 0], "amount": 0.7, "speed": 0.55})
    tx, ty = tp[0], tp[1]

    def tpt(x, y, z):
        return (tx + x, ty + y, z)

    body = []
    for s in (-1, 1):
        body += [tpt(1.6, 0.06, s * 0.5), tpt(1.25, 0.06, s * 1.28), tpt(-1.35, 0.06, s * 1.3), tpt(-1.8, 0.14, s * 1.0),
                 tpt(1.15, 0.62, s * 0.55), tpt(0.85, 0.72, s * 1.1), tpt(-1.3, 0.72, s * 1.12), tpt(-1.75, 0.62, s * 0.9)]
    m.hull("turret body", body, P["top"], group=T)
    # add-on side armour panels and the bustle basket
    for s, side in ((-1, "L"), (1, "R")):
        m.hull(f"turret side panel {side}", [tpt(0.9, 0.12, s * 1.3), tpt(-0.9, 0.12, s * 1.32), tpt(0.7, 0.62, s * 1.14), tpt(-0.9, 0.62, s * 1.16),
                                            tpt(0.9, 0.12, s * 1.36), tpt(-0.9, 0.12, s * 1.38), tpt(0.7, 0.62, s * 1.2), tpt(-0.9, 0.62, s * 1.22)], P["light"], group=T)
        # smoke dischargers: 4 angled tubes per side on the turret cheeks
        for k in range(4):
            m.add(f"smoke discharger {side}{k}", "cylinder", [0.055, 0.055, 0.26], [tx + 0.95 - k * 0.04, ty + 0.5 + k * 0.035, s * (1.18 + k * 0.03)],
                  DARK_STEEL, "metal", rot=[s * -60, 0, -55], group=T)
    for k, (y, z) in enumerate([(0.15, 0), (0.55, 0)]):
        m.box(f"bustle rail {k}", [0.05, 0.05, 2.0], [tx - 2.25, ty + y, z], DARK_STEEL, "metal", group=T)
    for s in (-1, 1):
        m.box(f"bustle side rail", [0.6, 0.05, 0.05], [tx - 2.0, ty + 0.55, s * 1.0], DARK_STEEL, "metal", group=T)
        m.box(f"bustle post", [0.05, 0.45, 0.05], [tx - 2.25, ty + 0.35, s * 1.0], DARK_STEEL, "metal", group=T)
    m.rbox("bustle bedroll", [0.45, 0.32, 0.8], 0.12, [tx - 2.0, ty + 0.38, -0.45], "#6e6a4a", "matte", group=T)
    m.rbox("bustle crate", [0.4, 0.3, 0.55], 0.03, [tx - 2.02, ty + 0.36, 0.5], P["dark"], group=T)
    # commander's cupola with periscopes (right), loader's hatch (left), gunner's sight, antenna bases
    cx, cz = tx - 0.45, 0.6
    m.cyl_y("cupola", 0.34, 0.37, 0.2, [cx, ty + 0.82, cz], P["top"], "paint", sides=14, group=T)
    m.cyl_y("cupola hatch", 0.27, 0.27, 0.05, [cx, ty + 0.945, cz], P["light"], "paint", sides=14, group=T)
    for k in range(7):
        a = 2 * math.pi * k / 7
        m.box(f"cupola periscope {k}", [0.09, 0.09, 0.07], [cx + 0.34 * math.cos(a), ty + 0.84, cz + 0.34 * math.sin(a)], GLASS, "glass", rot=[0, -math.degrees(a), 0], group=T)
    m.cyl_y("loader hatch", 0.3, 0.3, 0.05, [tx - 0.4, ty + 0.75, -0.55], P["light"], "paint", sides=12, group=T)
    m.cyl_y("loader MG mount", 0.04, 0.05, 0.3, [tx - 0.4, ty + 0.9, -0.95], DARK_STEEL, group=T)
    m.cyl_x("loader MG", 0.025, 0.03, 0.9, [tx - 0.15, ty + 1.07, -0.95], DARK_STEEL, group=T)
    m.box("loader MG body", [0.35, 0.1, 0.08], [tx - 0.45, ty + 1.07, -0.95], DARK_STEEL, "metal", group=T)
    m.rbox("gunner sight", [0.45, 0.32, 0.36], 0.04, [tx + 0.55, ty + 0.88, 0.75], P["dark"], group=T)
    m.box("gunner sight glass", [0.03, 0.2, 0.28], [tx + 0.79, ty + 0.9, 0.75], GLASS, "glass", group=T)
    m.rbox("commander sight", [0.3, 0.34, 0.3], 0.05, [tx - 0.05, ty + 0.92, 0.95], P["dark"], group=T)
    m.box("commander sight glass", [0.02, 0.18, 0.2], [tx + 0.11, ty + 0.94, 0.95], GLASS, "glass", group=T)
    for s, side in ((-1, "L"), (1, "R")):
        m.cyl_y(f"antenna base {side}", 0.07, 0.09, 0.14, [tx - 1.35, ty + 0.79, s * 0.85], DARK_STEEL, group=T)
    m.cyl_y("antenna whip", 0.008, 0.016, 2.3, [tx - 1.35, ty + 2.0, 0.85], "#1f201d", "metal", group=T)
    m.cyl_y("antenna whip short", 0.008, 0.016, 1.3, [tx - 1.35, ty + 1.5, -0.85], "#1f201d", "metal", group=T)
    lamp = m.group("antenna lamp", [tx - 1.35, ty + 3.17, 0.85], {"type": "blink", "rate": 1.0, "duty": 0.4}, parent=T)
    m.add("antenna lamp", "sphere", [0.045], [tx - 1.35, ty + 3.17, 0.85], "#ff4a3a", "glow", group=lamp)
    # gun mantlet (rides on the turret, does not recoil)
    m.hull("gun mantlet", [tpt(1.45, 0.12, -0.42), tpt(1.45, 0.12, 0.42), tpt(1.45, 0.62, -0.38), tpt(1.45, 0.62, 0.38),
                           tpt(1.85, 0.2, -0.3), tpt(1.85, 0.2, 0.3), tpt(1.85, 0.55, -0.28), tpt(1.85, 0.55, 0.28)], P["dark"], group=T)

    # the 120 mm gun: recoil housing, thermal sleeve sections with clamp bands, bore evacuator, muzzle brake
    gy = ty + 0.38
    gx0 = tx + 1.85
    G = m.group("gun", [gx0, gy, 0], {"type": "recoil", "axis": [-1, 0, 0], "amount": 0.5}, parent=T)
    m.cyl_x("recoil housing", 0.17, 0.2, 0.6, [gx0 + 0.25, gy, 0], P["dark"], "paint", group=G)
    m.cyl_x("barrel root", 0.11, 0.12, 0.5, [gx0 + 0.75, gy, 0], P["top"], "paint", group=G)
    x = gx0 + 1.0
    for k, ln in enumerate((1.15, 0.6, 1.2, 1.1)):
        r = 0.105 - k * 0.006
        if k == 1:
            m.cyl_x("bore evacuator", r + 0.05, r + 0.05, ln, [x + ln / 2, gy, 0], P["top"], "paint", group=G)
            m.cyl_x("evacuator taper front", r, r + 0.05, 0.08, [x + ln + 0.04, gy, 0], P["top"], "paint", group=G)
            m.cyl_x("evacuator taper rear", r + 0.05, r, 0.08, [x - 0.04, gy, 0], P["top"], "paint", group=G)
        else:
            m.cyl_x(f"thermal sleeve {k}", r, r, ln, [x + ln / 2, gy, 0], P["top"], "paint", group=G)
        m.cyl_x(f"sleeve clamp {k}", r + 0.018, r + 0.018, 0.05, [x + ln, gy, 0], P["dark"], "paint", group=G)
        x += ln
    muzzle = x + 0.05
    m.cyl_x("muzzle reference", 0.075, 0.075, 0.1, [muzzle, gy, 0], DARK_STEEL, group=G)
    m.rbox("muzzle brake", [0.42, 0.2, 0.26], 0.04, [muzzle + 0.25, gy, 0], DARK_STEEL, "metal", group=G)
    for s in (-1, 1):
        m.box("muzzle brake port", [0.12, 0.12, 0.02], [muzzle + 0.25, gy, s * 0.13], "#111211", "matte", group=G)
    tip = muzzle + 0.47
    F = m.group("muzzle flash", [tip, gy, 0], {"type": "flash"}, parent=G)
    m.add("flash outer", "cone", [0.32, 1.3], [tip + 0.65, gy, 0], "#ff9a2e", "glow", rot=[0, 0, -90], group=F)
    m.add("flash inner", "cone", [0.17, 0.8], [tip + 0.4, gy, 0], "#fff1b0", "glow", rot=[0, 0, -90], group=F)
    for s in (-1, 1):
        m.add("flash side", "cone", [0.12, 0.6], [muzzle + 0.25, gy, s * 0.42], "#ffb04a", "glow", rot=[s * 90, 0, 0], group=F)
    return m.save()


# ---------------------------------------------------------------- ships
NAVY = {"top": "#7f8a93", "deck": "#5b636a", "under": "#5a2a26", "boot": "#1d2023", "accent": "#e9e6da", "dark": "#4b5359", "light": "#a3adb5"}

SEVEN_SEG = {  # segments a b c d e f g
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def destroyer():
    m = Model("Iron Tide Destroyer")
    P = NAVY
    LEN, BEAM = 130.0, 15.6
    xb, xs = LEN / 2, -LEN / 2

    def half_beam(x):
        b = BEAM / 2
        if x > 12:
            return max(0.12, b * (1 - ((x - 12) / (xb - 12)) ** 1.9))
        if x < -28:
            return b - (-28 - x) / (xb - 28) * 1.5
        return b

    def draft(x):
        if x > 44:
            return 4.6 - (x - 44) / (xb - 44) * 3.8
        if x < -45:
            return 4.6 - (-45 - x) / 20 * 1.2
        return 4.6

    def freeboard(x):
        return 6.0 + max(0.0, (x - 5) / (xb - 5)) ** 2 * 3.4 - max(0.0, (-40 - x) / 25) * 0.6

    def width_at(x, y):
        b, d, f = half_beam(x), draft(x), freeboard(x)
        if y <= 0:
            return b * (1 - (min(1, -y / d) ** 2.4) * 0.72)
        flare = 0.03 + 0.14 * max(0.0, (x - 15) / (xb - 15))
        return b * (1 + flare * y / f)

    stations = [xs, -50, -30, -12, 6, 22, 36, 46, 54, 60, 63.5, xb]
    bands = [("underwater hull", P["under"], lambda x: [-draft(x), -0.6 * draft(x), -0.4]),
             ("boot-top", P["boot"], lambda x: [-0.4, 0.35]),
             ("topsides", P["top"], lambda x: [0.35, freeboard(x) * 0.55, freeboard(x)])]
    for i in range(len(stations) - 1):
        xa, xc = stations[i], stations[i + 1]
        for name, color, ys in bands:
            pts = []
            for x in (xa, xc):
                for y in ys(x):
                    w = width_at(x, y) + (0.04 if name == "boot-top" else 0)
                    pts += [(x, y, -w), (x, y, w)]
            m.hull(f"{name} {i}", pts, color)
        # deck surface
        pts = []
        for x in (xa, xc):
            f, w = freeboard(x), width_at(x, freeboard(x)) - 0.1
            pts += [(x, f + 0.04, -w), (x, f + 0.04, w), (x, f - 0.2, -w), (x, f - 0.2, w)]
        m.hull(f"deck {i}", pts, P["deck"])

    def deck_y(x):
        return freeboard(x) + 0.04

    # accent stripe along the sides
    for s, side in ((-1, "port"), (1, "starboard")):
        for i in range(len(stations) - 2):
            xa, xc = stations[i], stations[i + 1]
            ya, yc = freeboard(xa) - 0.7, freeboard(xc) - 0.7
            pts = [(xa, ya, s * (width_at(xa, ya) + 0.03)), (xc, yc, s * (width_at(xc, yc) + 0.03)),
                   (xa, ya - 0.35, s * (width_at(xa, ya - 0.35) + 0.03)), (xc, yc - 0.35, s * (width_at(xc, yc - 0.35) + 0.03)),
                   (xa, ya, s * (width_at(xa, ya) - 0.05)), (xc, yc, s * (width_at(xc, yc) - 0.05)),
                   (xa, ya - 0.35, s * (width_at(xa, ya - 0.35) - 0.05)), (xc, yc - 0.35, s * (width_at(xc, yc - 0.35) - 0.05))]
            m.hull(f"accent stripe {side} {i}", pts, "#2f4f6a")

    # hull number "117" in 7-segment style on both bows
    for s, side in ((-1, "port"), (1, "starboard")):
        for k, digit in enumerate("117"):
            x0 = 46 + k * 2.2 if s > 0 else 46 + (2 - k) * 2.2   # read from outside: left to right
            y0 = freeboard(x0) - 1.5
            slope = (half_beam(x0 + 1) - half_beam(x0 - 1)) / 2
            ang = math.degrees(math.atan(slope)) * -s
            seg = {"a": (0.0, 0.0, 1.2, 0.25), "g": (0.0, -1.2, 1.2, 0.25), "d": (0.0, -2.4, 1.2, 0.25),
                   "f": (-0.6, -0.6, 0.25, 1.2), "b": (0.6, -0.6, 0.25, 1.2), "e": (-0.6, -1.8, 0.25, 1.2), "c": (0.6, -1.8, 0.25, 1.2)}
            for name in SEVEN_SEG[digit]:
                cx, cy, w, h = seg[name]
                x = x0 + (cx if s > 0 else -cx)
                y = y0 + cy
                z = s * (width_at(x, y) + 0.08)
                m.box(f"hull number {side} {digit}{name}", [w, h, 0.06], [x, y, z], P["accent"], "paint", rot=[0, ang, 0])

    # bow: anchors, hawse holes, windlass, chains, jackstaff with the blinking bow lamp
    for s, side in ((-1, "port"), (1, "starboard")):
        x = 56
        y = freeboard(x) - 2.0
        z = s * (width_at(x, y) + 0.12)
        m.cyl_z(f"hawse hole {side}", 0.55, 0.3, [x, y + 0.3, z - s * 0.12], "#111315", "matte")
        m.box(f"anchor shank {side}", [0.25, 1.6, 0.25], [x, y - 0.4, z], DARK_STEEL, "metal", rot=[s * 8, 0, 0])
        m.hull(f"anchor flukes {side}", [(x - 0.9, y - 1.2, z), (x + 0.9, y - 1.2, z), (x, y - 1.6, z), (x - 0.7, y - 0.9, z + 0.2), (x + 0.7, y - 0.9, z + 0.2), (x, y - 1.4, z - 0.2)], DARK_STEEL, "metal")
        m.cyl_y(f"windlass {side}", 0.55, 0.55, 0.6, [52.5, deck_y(52.5) + 0.3, s * 1.6], P["dark"], "paint")
        for k in range(6):
            m.add(f"anchor chain {side}{k}", "torus", [0.12, 0.04], [53.2 + k * 0.45, deck_y(53.2 + k * 0.45) + 0.08, s * 1.6 + s * k * 0.25], DARK_STEEL, "metal", rot=[90, (k % 2) * 90, 0])
    m.cyl_y("jackstaff", 0.06, 0.08, 3.0, [63.0, deck_y(63) + 1.5, 0], P["dark"])
    bl = m.group("bow lamp", [63.0, deck_y(63) + 3.1, 0], {"type": "blink", "rate": 0.9, "duty": 0.35})
    m.add("bow lamp", "sphere", [0.18], [63.0, deck_y(63) + 3.1, 0], "#fff1c4", "glow", group=bl)

    # bollards and cleats along the deck edge
    for x in (58, 44, 20, -20, -44, -58):
        for s in (-1, 1):
            z = s * (width_at(x, freeboard(x)) - 0.9)
            for dx in (-0.35, 0.35):
                m.cyl_y("bollard", 0.17, 0.2, 0.55, [x + dx, deck_y(x) + 0.27, z], P["dark"], "paint", sides=10)

    # railings: posts every 2.5 m and two rails, from the stern to the bow
    for s, side in ((-1, "port"), (1, "starboard")):
        x = xs + 1.0
        while x < 60:
            z = s * (width_at(x, freeboard(x)) - 0.25)
            m.cyl_y(f"rail post {side}", 0.03, 0.03, 1.1, [x, deck_y(x) + 0.55, z], P["light"], "metal", sides=6)
            x += 2.5
        for i in range(len(stations) - 3):
            xa, xc = max(xs + 1, stations[i]), min(60, stations[i + 1])
            for hgt in (0.55, 1.08):
                ya, yc = deck_y(xa) + hgt, deck_y(xc) + hgt
                za, zc = s * (width_at(xa, freeboard(xa)) - 0.25), s * (width_at(xc, freeboard(xc)) - 0.25)
                ln = math.dist((xa, ya, za), (xc, yc, zc))
                yaw = math.degrees(math.atan2(-(zc - za), xc - xa))
                pitch = math.degrees(math.atan2(yc - ya, math.hypot(xc - xa, zc - za)))
                m.add(f"rail {side}", "cylinder", [0.025, 0.025, ln], [(xa + xc) / 2, (ya + yc) / 2, (za + zc) / 2], P["light"], "metal",
                      rot=[0, yaw, pitch - 90], sides=6)

    # main guns: two twin 127 mm, A position on deck and B position raised, both firing forward
    def ship_gun(gid, x, raise_h, arc):
        base = deck_y(x) + raise_h
        if raise_h > 0:
            m.hull(f"{gid} gun deck", [(x - 4.5, deck_y(x) - 0.3, -3.6), (x + 3.8, deck_y(x) - 0.3, -3.2), (x - 4.5, base, -3.4), (x + 3.4, base, -3.0),
                                       (x - 4.5, deck_y(x) - 0.3, 3.6), (x + 3.8, deck_y(x) - 0.3, 3.2), (x - 4.5, base, 3.4), (x + 3.4, base, 3.0)], P["top"])
        m.cyl_y(f"{gid} barbette", 2.5, 2.7, 0.9, [x, base + 0.45, 0], P["dark"], "paint", sides=20)
        T = m.group(gid, [x, base + 0.9, 0], {"type": "turret", "amount": arc, "speed": 0.4})
        y = base + 0.9
        m.hull(f"{gid} gun house", [(x + 3.1, y, -1.6), (x + 3.1, y, 1.6), (x - 2.8, y, -2.4), (x - 2.8, y, 2.4),
                                   (x + 1.6, y + 2.3, -1.1), (x + 1.6, y + 2.3, 1.1), (x - 2.6, y + 2.3, -1.7), (x - 2.6, y + 2.3, 1.7),
                                   (x + 2.6, y + 1.2, -1.75), (x + 2.6, y + 1.2, 1.75)], P["top"], group=T)
        for s in (-1, 1):
            m.box(f"{gid} rangefinder ear", [0.8, 0.5, 0.6], [x - 1.2, y + 1.9, s * 2.0], P["dark"], "paint", group=T)
            m.cyl_z(f"{gid} rangefinder lens", 0.18, 0.1, [x - 1.2, y + 1.9, s * 2.32], GLASS, "glass", group=T)
        m.cyl_y(f"{gid} roof hatch", 0.5, 0.5, 0.12, [x - 1.4, y + 2.36, 0.6], P["dark"], "paint", sides=10, group=T)
        gy = y + 1.15
        G = m.group(f"{gid} barrels", [x + 2.9, gy, 0], {"type": "recoil", "amount": 0.7}, parent=T)
        for s in (-0.75, 0.75):
            m.box(f"{gid} gun shield slot", [0.3, 0.9, 0.55], [x + 2.95, gy, s], "#202427", "matte", group=G)
            m.cyl_x(f"{gid} barrel", 0.13, 0.18, 6.6, [x + 6.1, gy, s], P["light"], "metal", group=G)
            m.cyl_x(f"{gid} barrel sleeve", 0.26, 0.26, 1.2, [x + 3.6, gy, s], P["top"], "paint", group=G)
            m.cyl_x(f"{gid} bore evacuator", 0.21, 0.21, 0.9, [x + 6.2, gy, s], P["light"], "metal", group=G)
            m.cyl_x(f"{gid} muzzle", 0.17, 0.17, 0.35, [x + 9.25, gy, s], DARK_STEEL, "metal", group=G)
        F = m.group(f"{gid} flash", [x + 9.45, gy, 0], {"type": "flash"}, parent=G)
        for s in (-0.75, 0.75):
            m.add(f"{gid} flash outer", "cone", [0.9, 4.0], [x + 11.4, gy, s], "#ff9a2e", "glow", rot=[0, 0, -90], group=F)
            m.add(f"{gid} flash inner", "cone", [0.45, 2.4], [x + 10.6, gy, s], "#fff1b0", "glow", rot=[0, 0, -90], group=F)

    ship_gun("A turret", 41.0, 0.0, 0.9)
    ship_gun("B turret", 31.5, 1.9, 0.8)

    # vertical launch cells in front of the bridge
    for i in range(4):
        for j in range(6):
            m.box("missile cell hatch", [1.0, 0.12, 1.0], [23.4 + i * 1.15, deck_y(24) + 0.06, -2.9 + j * 1.15], P["dark"], "paint")
    m.box("missile cell frame", [5.0, 0.08, 7.3], [25.1, deck_y(24) + 0.02, 0], "#3c4348", "paint")

    # deckhouse and bridge: faceted stealth shapes, window band, bridge wings, searchlights
    d0 = deck_y(10)
    dh = []
    for s in (-1, 1):
        dh += [(21.5, d0 - 0.3, s * 5.6), (-14, d0 - 0.3, s * 6.0), (20.0, d0 + 4.2, s * 4.9), (-13.5, d0 + 4.2, s * 5.3)]
    m.hull("deckhouse", dh, P["top"])
    br = []
    for s in (-1, 1):
        br += [(20.0, d0 + 4.1, s * 4.8), (8.5, d0 + 4.1, s * 5.0), (17.2, d0 + 8.6, s * 3.8), (9.0, d0 + 8.6, s * 4.0)]
    m.hull("bridge", br, P["top"])
    m.hull("bridge window band", [(19.0, d0 + 6.7, -4.25), (19.0, d0 + 6.7, 4.25), (18.25, d0 + 7.9, -3.95), (18.25, d0 + 7.9, 3.95),
                                  (18.9, d0 + 6.7, -4.1), (18.9, d0 + 6.7, 4.1), (18.15, d0 + 7.9, -3.8), (18.15, d0 + 7.9, 3.8)], "#1b2a33", "glass")
    for k in range(8):
        z = -3.6 + k * 1.03
        m.box("window frame", [0.12, 1.25, 0.1], [18.65, d0 + 7.3, z], P["light"], "paint", rot=[0, 0, 33])
    for s, side in ((-1, "port"), (1, "starboard")):
        m.box(f"bridge wing {side}", [3.0, 0.25, 3.0], [16.5, d0 + 6.6, s * 5.6], P["top"], "paint")
        m.box(f"bridge wing screen {side}", [3.0, 1.1, 0.12], [16.5, d0 + 7.25, s * 7.05], P["top"], "paint")
        m.cyl_x(f"searchlight {side}", 0.38, 0.34, 0.6, [17.3, d0 + 7.5, s * 6.1], P["dark"], "paint")
        m.cyl_x(f"searchlight lens {side}", 0.32, 0.32, 0.05, [17.62, d0 + 7.5, s * 6.1], "#fff6d8", "glow")
        for k in range(3):
            m.rbox(f"window row {side}{k}", [2.4, 0.7, 0.08], 0.05, [4.0 - k * 6.5, d0 + 2.6, s * (5.3 - (k * 0.05))], "#1b2a33", "glass")
        # lifeboats and liferaft canisters
        for k in range(2):
            m.add(f"lifeboat {side}{k}", "capsule", [0.9, 4.2], [-3.0 - k * 6.5, d0 + 1.4, s * 6.9], "#e8622a", "glossy", rot=[0, 0, 90])
            m.box(f"davit {side}{k}", [0.3, 2.2, 0.3], [-3.0 - k * 6.5 - 2.4, d0 + 1.2, s * 6.6], P["dark"], "paint")
        for k in range(4):
            m.add(f"liferaft {side}{k}", "capsule", [0.38, 0.9], [-16.5 - k * 1.2, deck_y(-17) + 1.0, s * 6.5], "#f1efe8", "glossy", rot=[90, 0, 0])
    m.box("bridge roof", [8.6, 0.25, 8.2], [13.1, d0 + 8.72, 0], P["light"], "paint")

    # lattice mast with spinning radar and a blinking mast lamp
    mx, mb = 11.0, d0 + 8.8
    top = mb + 12.0
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add("mast leg", "cylinder", [0.14, 0.18, 12.2], [mx + sx * 0.75, mb + 6.0, sz * 0.75], P["light"], "metal",
                  rot=[sz * 6.5, 0, -sx * 6.5], sides=8)
    for k in range(5):
        h = mb + 1.5 + k * 2.3
        w = 1.4 - k * 0.2
        for sx, sz, ry in ((0, 1, 0), (0, -1, 0), (1, 0, 90), (-1, 0, 90)):
            m.box("mast brace", [w * 1.9, 0.1, 0.1], [mx + sx * w / 2, h, sz * w / 2], P["light"], "metal", rot=[0, ry, 0])
    m.box("mast platform", [2.8, 0.2, 2.8], [mx, mb + 9.0, 0], P["top"], "paint")
    m.box("yardarm", [0.2, 0.2, 7.0], [mx, mb + 9.8, 0], P["light"], "metal")
    for s in (-1, 1):
        m.cyl_y("whip antenna", 0.02, 0.05, 6.0, [mx - 0.3, mb + 12.8, s * 3.3], "#2a2e31", "metal", sides=6)
    m.cyl_y("radar pedestal", 0.35, 0.45, 1.2, [mx, top + 0.6, 0], P["dark"], "paint")
    R = m.group("radar", [mx, top + 1.2, 0], {"type": "spin", "axis": [0, 1, 0], "speed": 1.7})
    m.box("radar array", [0.5, 1.6, 6.4], [mx + 0.3, top + 2.2, 0], P["light"], "paint", group=R)
    m.box("radar array back", [0.6, 1.2, 5.6], [mx - 0.25, top + 2.2, 0], P["dark"], "paint", group=R)
    m.box("radar feed arm", [1.2, 0.15, 0.15], [mx + 0.6, top + 1.4, 0], P["dark"], "paint", group=R)
    ml = m.group("mast lamp", [mx, top + 3.5, 0], {"type": "blink", "rate": 0.8, "duty": 0.4})
    m.cyl_y("mast lamp stalk", 0.05, 0.05, 0.6, [mx, top + 3.2, 0], P["dark"])
    m.add("mast lamp", "sphere", [0.2], [mx, top + 3.55, 0], "#ff3b2f", "glow", group=ml)
    # fixed phased-array panels on the bridge front corners
    for s in (-1, 1):
        m.box("phased array panel", [0.15, 2.6, 2.6], [15.8, d0 + 10.0, s * 2.2], "#69737b", "paint", rot=[0, s * 40, 0])
        m.box("phased array mount", [1.6, 2.0, 1.2], [14.8, d0 + 9.6, s * 2.0], P["top"], "paint")

    # funnel: raked stack, grating top, heat-stain band
    fx, fb = -5.0, d0 + 4.2
    fun = []
    for s in (-1, 1):
        fun += [(fx + 3.4, fb, s * 2.6), (fx - 3.6, fb, s * 2.8), (fx + 1.4, fb + 6.0, s * 2.0), (fx - 3.4, fb + 6.0, s * 2.2)]
    m.hull("funnel", fun, P["top"])
    m.hull("funnel heat stain", [(fx + 1.55, fb + 5.0, -2.15), (fx + 1.55, fb + 5.0, 2.15), (fx - 3.5, fb + 5.0, -2.35), (fx - 3.5, fb + 5.0, 2.35),
                                 (fx + 1.38, fb + 6.05, -2.04), (fx + 1.38, fb + 6.05, 2.04), (fx - 3.46, fb + 6.05, -2.24), (fx - 3.46, fb + 6.05, 2.24)], "#25282a", "matte")
    for k in range(6):
        m.box("funnel grating", [0.12, 0.12, 3.9], [fx - 2.9 + k * 0.8, fb + 6.1, 0], "#1a1c1d", "metal")
    m.box("funnel grating rail", [4.6, 0.1, 0.12], [fx - 1.0, fb + 6.12, 0], "#1a1c1d", "metal")

    # torpedo tubes amidships
    for s, side in ((-1, "port"), (1, "starboard")):
        for k in range(3):
            m.cyl_x(f"torpedo tube {side}{k}", 0.3, 0.3, 4.2, [-17.5, deck_y(-17.5) + 0.7 + k * 0.62, s * 5.2], P["dark"], "paint", group=None)
        m.box(f"torpedo mount {side}", [1.4, 0.5, 1.2], [-17.5, deck_y(-17.5) + 0.25, s * 5.2], P["top"], "paint")

    # hangar, crane and close-in gun aft, flight deck at the stern
    h0 = deck_y(-25)
    m.hull("hangar", [(-14.0, h0 - 0.3, -6.0), (-14.0, h0 - 0.3, 6.0), (-36.0, h0 - 0.3, -6.3), (-36.0, h0 - 0.3, 6.3),
                      (-14.5, h0 + 5.0, -5.2), (-14.5, h0 + 5.0, 5.2), (-36.0, h0 + 5.0, -5.6), (-36.0, h0 + 5.0, 5.6)], P["top"])
    m.box("hangar door", [0.1, 4.2, 8.0], [-36.05, h0 + 2.2, 0], P["dark"], "paint")
    for k in range(6):
        m.box("hangar door seam", [0.12, 0.08, 8.0], [-36.1, h0 + 0.6 + k * 0.7, 0], "#3b4247", "paint")
    m.cyl_y("CIWS base", 1.0, 1.2, 1.2, [-24.0, h0 + 5.6, 0], P["top"], "paint")
    m.add("CIWS dome", "capsule", [0.95, 1.4], [-24.0, h0 + 7.3, 0], "#e9ecef", "glossy")
    m.cyl_x("CIWS barrels", 0.16, 0.16, 2.2, [-22.6, h0 + 6.6, 0], DARK_STEEL, "metal", sides=6)
    m.cyl_y("crane post", 0.3, 0.35, 3.0, [-15.5, h0 + 6.5, 4.5], P["dark"], "paint")
    m.box("crane boom", [6.0, 0.35, 0.35], [-18.0, h0 + 8.2, 4.5], P["light"], "paint", rot=[0, 0, 18])
    fdy = deck_y(-50) + 0.05
    m.box("flight deck", [27.0, 0.12, 13.0], [-50.0, fdy, 0], "#4e5459", "paint")
    m.add("landing circle", "torus", [4.5, 0.12], [-50.0, fdy + 0.08, 0], "#f4f1e6", "paint", rot=[90, 0, 0])
    m.box("deck centre line", [24.0, 0.04, 0.3], [-50.0, fdy + 0.08, 0], "#f4f1e6", "paint")
    m.box("deck cross line", [0.3, 0.04, 10.0], [-46.0, fdy + 0.08, 0], "#f4f1e6", "paint")
    for k in range(5):
        m.box("deck edge light", [0.3, 0.08, 0.3], [-62.0 + k * 5.5, fdy + 0.08, -6.2], "#9fe58f", "glow")
        m.box("deck edge light", [0.3, 0.08, 0.3], [-62.0 + k * 5.5, fdy + 0.08, 6.2], "#9fe58f", "glow")
    m.box("transom", [0.2, 3.4, 12.6], [xs - 0.05, freeboard(xs) - 1.9, 0], P["top"], "paint")
    m.cyl_y("ensign staff", 0.05, 0.06, 3.0, [xs + 0.5, fdy + 1.5, 0], P["dark"])
    return m.save()


# ---------------------------------------------------------------- planes
HAZE = {"top": "#8a949d", "under": "#b9c1c7", "accent": "#2c5f8d", "dark": "#4c5359", "light": "#a8b1b8"}


def strike_fighter():
    m = Model("Iron Tide Strike Fighter")
    P = HAZE
    L, R = 16.0, 1.1
    xn, xt = L / 2, -L / 2

    # fuselage stations: (x, half-width, top, bottom). Flatter belly, blended chines.
    st = [(xn, 0.02, 0.02, -0.02), (7.0, 0.32, 0.3, -0.28), (5.6, 0.62, 0.55, -0.5), (4.2, 0.82, 0.7, -0.62),
          (2.6, 1.0, 0.82, -0.7), (0.5, 1.12, 0.85, -0.75), (-2.0, 1.15, 0.8, -0.75), (-4.5, 1.1, 0.7, -0.68),
          (-6.5, 1.05, 0.58, -0.6), (xt, 0.98, 0.5, -0.5)]

    def section(x, w, t, b):
        pts = []
        for k in range(14):
            a = 2 * math.pi * k / 14
            c, s = math.cos(a), math.sin(a)
            y = t * s if s > 0 else b * abs(s) ** 0.6   # rounder top, flatter belly
            sx = math.copysign(abs(c) ** 0.7, c)          # squarer sides: chines
            pts.append((x, y, w * sx))
        return pts

    for i in range(len(st) - 1):
        a, b = st[i], st[i + 1]
        color = P["top"]
        m.hull(f"fuselage {i}", section(*a) + section(*b), color)
    m.hull("radome", section(*st[0]) + section(*st[1]), "#5f676d")
    # belly panel (lighter underside) and panel-join rings
    for i in range(2, len(st) - 1):
        x, w, t, bt = st[i]
        m.box(f"belly panel {i}", [abs(st[i][0] - st[i + 1][0]) * 0.98, 0.04, w * 1.2], [(st[i][0] + st[i + 1][0]) / 2, bt * 0.62 - 0.02, 0], P["under"], "paint")
    for x in (3.4, -1.0, -4.0):
        m.add("panel join", "torus", [1.04, 0.012], [x, 0.04, 0], P["dark"], "paint", rot=[0, 90, 0], scale=[1, 0.78, 1.05])
    m.box("dorsal spine", [7.5, 0.25, 0.7], [-2.8, 0.82, 0], P["top"], "paint")

    # canopy: lofted glass bubble with a frame bow
    can = []
    for x, w, h in ((5.9, 0.05, 0.5), (5.2, 0.42, 0.88), (4.0, 0.52, 1.12), (2.9, 0.5, 1.12), (1.9, 0.38, 0.95), (1.2, 0.2, 0.8)):
        for k in range(7):
            a = math.pi * k / 6
            can.append((x, 0.55 + (h - 0.55) * math.sin(a), w * math.cos(a)))
    m.hull("canopy", can, "#33536b", "glass")
    m.add("canopy frame", "torus", [0.56, 0.035], [3.0, 0.62, 0], P["dark"], "paint", rot=[0, 90, 0], scale=[1, 1.05, 0.98])
    m.box("canopy sill", [4.6, 0.06, 1.12], [3.5, 0.58, 0], P["dark"], "paint")
    m.box("seat headrest", [0.3, 0.45, 0.35], [2.6, 0.95, 0], "#2a2d30", "matte")

    # intakes with dark lips
    for s, side in ((-1, "L"), (1, "R")):
        z = s * 1.2
        m.hull(f"intake {side}", [(2.0, -0.55, z - s * 0.05), (2.0, 0.25, z - s * 0.05), (2.0, -0.55, z + s * 0.45), (2.0, 0.2, z + s * 0.45),
                                  (-3.0, -0.6, z - s * 0.2), (-3.0, 0.4, z - s * 0.2), (-3.0, -0.6, z + s * 0.2), (-3.0, 0.4, z + s * 0.1)], P["top"])
        m.box(f"intake mouth {side}", [0.08, 0.68, 0.42], [2.02, -0.16, z + s * 0.2], "#151719", "matte")
        m.box(f"intake lip {side}", [0.1, 0.06, 0.52], [2.05, 0.22, z + s * 0.2], P["dark"], "paint")
        m.box(f"cooling vent {side}", [0.5, 0.08, 0.04], [-1.0, 0.25, s * 1.42], "#24282b", "matte")

    # wings: swept, tapering in thickness, with slat and flap lines, insignia and separate ailerons
    span = L * 0.76 * 1.0 / 2  # half-span
    root_le, root_te, tip_le, tip_te = 1.0, -5.2, -4.3, -6.0
    for s, side in ((-1, "L"), (1, "R")):
        zr, zt = s * 1.0, s * span
        wing = [(root_le, 0.05, zr), (root_te, 0.05, zr), (root_le - 0.6, 0.22, zr), (root_te + 0.5, 0.18, zr), (root_le - 0.4, -0.12, zr), (root_te + 0.4, -0.1, zr),
                (tip_le, 0.0, zt), (tip_te + 0.75, 0.0, zt), (tip_le - 0.2, 0.06, zt), (tip_te + 0.85, 0.05, zt)]
        m.hull(f"wing {side}", wing, P["top"])
        m.hull(f"wing underside {side}", [(root_le - 0.4, -0.13, zr), (root_te + 0.4, -0.11, zr), (tip_le - 0.2, -0.02, zt), (tip_te + 0.85, -0.02, zt),
                                          (root_le - 0.4, -0.08, zr), (root_te + 0.4, -0.06, zr), (tip_le - 0.2, 0.0, zt), (tip_te + 0.85, 0.0, zt)], P["under"])
        # slat line along the leading edge
        for k in range(4):
            f0, f1 = k / 4, (k + 1) / 4
            xa, za = root_le + (tip_le - root_le) * f0 - 0.45, zr + (zt - zr) * f0
            xc, zc = root_le + (tip_le - root_le) * f1 - 0.45, zr + (zt - zr) * f1
            m.box("slat line", [math.hypot(xc - xa, zc - za), 0.02, 0.04], [(xa + xc) / 2, 0.18 - 0.12 * f1, (za + zc) / 2], P["dark"], "paint",
                  rot=[0, -math.degrees(math.atan2(zc - za, xc - xa)), 0])
        # flap (fixed) and aileron (moving), hinged along the trailing edge
        hx0, hz0 = root_te + 0.5 + (tip_te + 0.75 - root_te - 0.5) * 0.12, zr + (zt - zr) * 0.12
        hx1, hz1 = root_te + 0.5 + (tip_te + 0.75 - root_te - 0.5) * 0.55, zr + (zt - zr) * 0.55
        hx2, hz2 = root_te + 0.5 + (tip_te + 0.75 - root_te - 0.5) * 0.92, zr + (zt - zr) * 0.92
        m.hull(f"flap {side}", [(hx0, 0.12, hz0), (hx1, 0.06, hz1), (hx0 - 0.85, 0.05, hz0), (hx1 - 0.7, 0.02, hz1),
                                (hx0, 0.0, hz0), (hx1, 0.0, hz1), (hx0 - 0.85, 0.0, hz0), (hx1 - 0.7, 0.0, hz1)], P["light"])
        ax, az = hx2 - hx1, hz2 - hz1
        ln = math.hypot(ax, az)
        A = m.group(f"aileron {side}", [hx1, 0.04, hz1], {"type": "wiggle", "axis": [ax / ln, 0, az / ln], "amount": 0.3, "speed": 1.6,
                                                          "phase": 0 if s < 0 else math.pi})
        m.hull(f"aileron {side}", [(hx1, 0.07, hz1), (hx2, 0.04, hz2), (hx1 - 0.65, 0.03, hz1), (hx2 - 0.5, 0.02, hz2),
                                   (hx1, 0.0, hz1), (hx2, 0.0, hz2), (hx1 - 0.65, 0.0, hz1), (hx2 - 0.5, 0.0, hz2)], P["light"], group=A)
        # wing fence, insignia, wingtip rail missile and the steady nav light
        fx, fz = root_le + (tip_le - root_le) * 0.45 - 1.2, zr + (zt - zr) * 0.45
        m.box(f"wing fence {side}", [2.0, 0.18, 0.03], [fx, 0.2, fz], P["dark"], "paint", rot=[0, -s * 20, 0])
        rz = zr + (zt - zr) * 0.62
        rx = root_le + (tip_le - root_le) * 0.62 - 1.6
        # Iron Tide insignia (original): a blue hexagon, a pale ring and a gold centre
        m.cyl_y(f"insignia {side}", 0.64, 0.64, 0.02, [rx, 0.12, rz], P["accent"], "paint", sides=6)
        m.cyl_y(f"insignia ring {side}", 0.42, 0.42, 0.025, [rx, 0.125, rz], "#e8eef2", "paint", sides=6)
        m.cyl_y(f"insignia centre {side}", 0.2, 0.2, 0.03, [rx, 0.13, rz], "#d6a536", "paint", sides=3)
        m.box(f"wingtip rail {side}", [2.2, 0.08, 0.1], [tip_le - 0.7, -0.02, zt + s * 0.05], P["dark"], "paint")
        m.cyl_x(f"wingtip missile {side}", 0.07, 0.07, 2.6, [tip_le - 0.6, -0.12, zt + s * 0.1], "#e9ece9", "glossy")
        m.add(f"wingtip missile seeker {side}", "cone", [0.07, 0.25], [tip_le + 0.82, -0.12, zt + s * 0.1], "#2b2f33", "glossy", rot=[0, 0, -90])
        for k in range(4):
            m.box(f"missile fin {side}{k}", [0.25, 0.22, 0.02], [tip_le - 1.75, -0.12, zt + s * 0.1], "#cfd3d0", "paint", rot=[k * 45 + 45, 0, 0])
        m.add(f"nav light {side}", "sphere", [0.07], [tip_te + 1.4, 0.04, zt + s * 0.02], "#ff3b2f" if s < 0 else "#3bff6a", "glow")
        # under-wing pylons with strike missiles
        for k, f in enumerate((0.35, 0.68)):
            px = root_le + (tip_le - root_le) * f - 1.6
            pz = zr + (zt - zr) * f
            m.hull(f"pylon {side}{k}", [(px + 0.8, -0.08, pz - 0.05), (px - 1.0, -0.08, pz - 0.05), (px + 0.5, -0.4, pz - 0.05), (px - 0.8, -0.4, pz - 0.05),
                                        (px + 0.8, -0.08, pz + 0.05), (px - 1.0, -0.08, pz + 0.05), (px + 0.5, -0.4, pz + 0.05), (px - 0.8, -0.4, pz + 0.05)], P["dark"])
            m.cyl_x(f"strike missile {side}{k}", 0.15, 0.15, 3.2, [px, -0.6, pz], "#e2e4dd", "glossy")
            m.add(f"strike missile seeker {side}{k}", "sphere", [0.15], [px + 1.6, -0.6, pz], "#2b2f33", "glossy", scale=[1.6, 1, 1])
            for q in range(4):
                m.box(f"strike missile fin {side}{k}{q}", [0.4, 0.42, 0.02], [px - 1.35, -0.6, pz], "#c8ccc6", "paint", rot=[q * 90 + 45, 0, 0])
            m.box(f"missile band {side}{k}", [0.08, 0.31, 0.31], [px + 0.9, -0.6, pz], "#d6b23a", "paint")

    # twin canted fins with moving rudders, all-moving tailplanes
    for s, side in ((-1, "L"), (1, "R")):
        z0 = s * 0.85
        cant = math.radians(14)
        def fin_pt(x, h, dz=0.0):
            return (x, 0.55 + h * math.cos(cant), z0 + s * h * math.sin(cant) + dz)
        m.hull(f"tail fin {side}", [fin_pt(-3.6, 0.0, -0.08), fin_pt(-3.6, 0.0, 0.08), fin_pt(-7.4, 0.0, -0.06), fin_pt(-7.4, 0.0, 0.06),
                                     fin_pt(-6.2, 3.1, -0.03), fin_pt(-6.2, 3.1, 0.03), fin_pt(-7.6, 3.1, -0.03), fin_pt(-7.6, 3.1, 0.03)], P["top"])
        m.hull(f"fin stripe {side}", [fin_pt(-6.3, 2.5, -0.045), fin_pt(-6.3, 2.5, 0.045), fin_pt(-7.55, 2.5, -0.045), fin_pt(-7.55, 2.5, 0.045),
                                       fin_pt(-6.2, 3.1, -0.045), fin_pt(-6.2, 3.1, 0.045), fin_pt(-7.6, 3.1, -0.045), fin_pt(-7.6, 3.1, 0.045)], P["accent"])
        hinge0, hinge1 = fin_pt(-7.0, 0.4), fin_pt(-7.35, 2.4)
        ax = [hinge1[i] - hinge0[i] for i in range(3)]
        ln = math.sqrt(sum(v * v for v in ax))
        Rg = m.group(f"rudder {side}", list(hinge0), {"type": "wiggle", "axis": [v / ln for v in ax], "amount": 0.25, "speed": 1.1})
        m.hull(f"rudder {side}", [fin_pt(-7.0, 0.4, -0.04), fin_pt(-7.0, 0.4, 0.04), fin_pt(-7.35, 2.4, -0.03), fin_pt(-7.35, 2.4, 0.03),
                                   fin_pt(-7.75, 0.4, -0.02), fin_pt(-7.75, 0.4, 0.02), fin_pt(-7.95, 2.4, -0.02), fin_pt(-7.95, 2.4, 0.02)], P["light"], group=Rg)
        Tg = m.group(f"tailplane {side}", [-6.3, 0.05, s * 1.5], {"type": "wiggle", "axis": [0, 0, 1], "amount": 0.15, "speed": 0.9})
        m.hull(f"tailplane {side}", [(-5.2, 0.08, s * 1.2), (-7.9, 0.06, s * 1.2), (-7.3, 0.03, s * 3.9), (-8.3, 0.03, s * 3.9),
                                     (-5.2, -0.04, s * 1.2), (-7.9, -0.03, s * 1.2), (-7.3, 0.0, s * 3.9), (-8.3, 0.0, s * 3.9)], P["top"], group=Tg)
    beacon = m.group("tail beacon", fin_pt(-7.6, 3.15), {"type": "blink", "rate": 1.2, "duty": 0.3})
    m.add("tail beacon", "sphere", [0.08], list(fin_pt(-7.6, 3.15)), "#ff3b2f", "glow", group=beacon)

    # twin engine nozzles with petals and afterburner flames
    for s, side in ((-1, "L"), (1, "R")):
        z = s * 0.55
        m.cyl_x(f"nozzle ring {side}", 0.5, 0.5, 0.4, [xt - 0.1, -0.05, z], "#55524c", "metal", sides=16)
        for k in range(12):
            a = 2 * math.pi * k / 12
            m.box(f"nozzle petal {side}{k}", [0.65, 0.2, 0.05], [xt - 0.55, -0.05 + 0.43 * math.sin(a), z + 0.43 * math.cos(a)], "#3e3b37", "metal",
                  rot=[math.degrees(a) + 90, 0, 0])
        m.cyl_x(f"nozzle core {side}", 0.36, 0.36, 0.3, [xt - 0.25, -0.05, z], "#ff8a3a", "glow")
        Fl = m.group(f"afterburner {side}", [xt - 0.85, -0.05, z], {"type": "flame"})
        m.add(f"afterburner flame {side}", "cone", [0.38, 3.2], [xt - 2.45, -0.05, z], "#ff7a26", "glow", rot=[0, 0, 90], group=Fl)
        m.add(f"afterburner core {side}", "cone", [0.2, 1.8], [xt - 1.75, -0.05, z], "#fff1c8", "glow", rot=[0, 0, 90], group=Fl)

    # landing gear: three legs, each one group that folds about the top of its leg (and shrinks out of sight)
    def leg(gid, x, z, length, wheel_r, axis, amount, twin=False):
        top = -0.7
        G = m.group(gid, [x, top, z], {"type": "fold", "axis": axis, "amount": amount})
        m.cyl_y(f"{gid} oleo", 0.07, 0.09, length * 0.6, [x, top - length * 0.3, z], "#c9cdd0", "metal", group=G)
        m.cyl_y(f"{gid} strut", 0.06, 0.06, length * 0.45, [x, top - length * 0.75, z], "#e3e6e8", "metal", group=G)
        m.box(f"{gid} brake line", [0.02, length * 0.8, 0.02], [x - 0.08, top - length * 0.45, z + 0.06], "#202224", "matte", group=G)
        wy = top - length
        for dz in ((-0.18, 0.18) if twin else (0,)):
            m.cyl_z(f"{gid} tyre", wheel_r, 0.2, [x, wy, z + dz], RUBBER, "rubber", group=G)
            m.cyl_z(f"{gid} hub", wheel_r * 0.55, 0.22, [x, wy, z + dz], "#b8bdc1", "metal", sides=10, group=G)
        m.box(f"{gid} gear door", [0.9, length * 0.55, 0.03], [x, top - length * 0.3, z + 0.22], P["under"], "paint", group=G)
    leg("nose gear", 4.6, 0.0, 1.5, 0.28, [0, 0, 1], -1.57, twin=True)
    leg("main gear L", -2.4, -1.55, 1.5, 0.38, [1, 0, 0], -1.57)
    leg("main gear R", -2.4, 1.55, 1.5, 0.38, [1, 0, 0], 1.57)
    m.cyl_y("nose gear light", 0.06, 0.06, 0.1, [4.75, -1.4, 0.0], LAMP, "glow")
    # antennas, pitot and gun port
    m.cyl_x("pitot probe", 0.02, 0.03, 0.9, [8.3, 0.0, 0.0], "#c9cdd0", "metal")
    m.box("blade antenna", [0.35, 0.3, 0.03], [-0.5, 1.0, 0], P["dark"], "paint", rot=[0, 0, -20])
    m.box("belly antenna", [0.3, 0.25, 0.03], [1.5, -0.88, 0], P["dark"], "paint", rot=[0, 0, 20])
    m.box("gun port", [0.6, 0.12, 0.05], [3.2, 0.2, 0.86], "#1b1d1f", "matte")
    return m.save()


if __name__ == "__main__":
    medium_tank()
    destroyer()
    strike_fighter()
