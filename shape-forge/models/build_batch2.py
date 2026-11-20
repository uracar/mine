"""Second batch of Iron Tide models: heavy tanks, battleships, the Bastion bomber and the tier-1 starters.

Same conventions as build_iron_tide.py (metres, +X forward, +Y up, +Z starboard; tanks on the ground,
ships on the waterline, planes on the centreline). Built at the real design's proportions; the game
rescales each model to its Service Tree node's length. Import notes from the game session:
turret > recoil (barrels) > flash nesting, flash parts at each muzzle, track links named "...link...",
control surfaces named aileron / rudder / tailplane / flap, under ~800 parts and ~55 moving groups.

    python3 build_batch2.py
"""
import math
from build_iron_tide import Model, convex_hull_2d, resample_loop, DARK_STEEL, STEEL, RUBBER, GLASS, LAMP


def mirror_sides():
    return ((-1, "L"), (1, "R"))


# ================================================================ tanks
def running_gear(m, P, L, W, *, wheels, wheel_r, track_w, sprocket_front, sprocket, idler, rollers=(), interleave=False,
                 wheel_y=None, pitch=0.17, spokes=6, ridge=True, wheel_color=None, fenders=None):
    """A track loop round every wheel it touches, a toothed sprocket, an idler, road wheels and return rollers.
    Every wheel rolls in its own group; each track is one group that circulates."""
    half = W / 2 - track_w / 2
    thick = 0.075
    wc = wheel_color or P["dark"]
    xs, ys, rs = sprocket
    xi, yi, ri = idler
    wy = wheel_y if wheel_y is not None else wheel_r + thick
    road = [(x, wy, wheel_r) for x in wheels]
    pts = []
    for (cx, cy, r) in [sprocket, idler] + road:
        for k in range(40):
            a = 2 * math.pi * k / 40
            pts.append((round(cx + (r + thick / 2) * math.cos(a), 4), round(cy + (r + thick / 2) * math.sin(a), 4)))
    loop = convex_hull_2d(pts)[::-1]          # clockwise: the bottom run moves backward as the tank drives
    for z, side in ((-half, "L"), (half, "R")):
        out = 1 if z > 0 else -1
        gid = m.group(f"track{side}", [0, 0, 0], {"type": "track", "path": [[round(x, 4), round(y, 4)] for x, y in loop]})
        links, _ = resample_loop(loop, pitch)
        for i, (x, y, ang) in enumerate(links):
            deg = math.degrees(ang)
            m.box(f"track link {side}{i}", [pitch * 0.94, thick, track_w], [x, y, z], DARK_STEEL, "metal", rot=[0, 0, deg], group=gid)
            if ridge and i % 2 == 0:
                nx, ny = -math.sin(ang), math.cos(ang)
                m.box(f"track link ridge {side}{i}", [0.05, 0.04, track_w * 0.9], [x + nx * 0.05, y + ny * 0.05, z], "#3a3b37", "metal", rot=[0, 0, deg], group=gid)
        for i, (x, y, r) in enumerate(road):
            g = m.group(f"wheel{side}{i}", [x, y, z], {"type": "roll", "radius": r})
            dzs = ((-0.14, 0.14) if not interleave else ((out * 0.16,) if i % 2 == 0 else (-out * 0.12,)))
            for dz in dzs:
                m.cyl_z(f"road wheel {side}{i}", r - 0.03, 0.11 if not interleave else 0.16, [x, y, z + dz], wc, "paint", group=g)
                m.add(f"road wheel tyre {side}{i}", "torus", [r - 0.03, 0.04], [x, y, z + dz], RUBBER, "rubber", group=g)
            face = z + (max(dzs) if out > 0 else min(dzs)) + out * 0.07
            m.cyl_z(f"hub {side}{i}", r * 0.3, 0.06, [x, y, face], STEEL, "metal", sides=8, group=g)
            for k in range(spokes // 2):
                m.box(f"spoke {side}{i}.{k}", [0.05, r * 1.5, 0.025], [x, y, face], P["light"], "paint", rot=[0, 0, k * 180 / (spokes // 2)], group=g)
        g = m.group(f"sprocket{side}", [xs, ys, z], {"type": "roll", "radius": rs})
        for dz in (-0.18, 0.18):
            m.cyl_z(f"sprocket ring {side}", rs - 0.04, 0.07, [xs, ys, z + dz], STEEL, "metal", group=g)
        for k in range(12):
            a = 2 * math.pi * k / 12
            m.box(f"sprocket tooth {side}{k}", [0.08, 0.09, track_w * 0.75], [xs + (rs - 0.02) * math.cos(a), ys + (rs - 0.02) * math.sin(a), z], STEEL, "metal",
                  rot=[0, 0, math.degrees(a)], group=g)
        m.cyl_z(f"sprocket hub {side}", rs * 0.5, track_w + 0.06, [xs, ys, z], wc, "paint", sides=10, group=g)
        for k in range(3):
            m.box(f"sprocket spoke {side}{k}", [0.05, rs * 1.5, 0.03], [xs, ys, z + out * (track_w / 2 + 0.04)], P["light"], "paint", rot=[0, 0, k * 60], group=g)
        g = m.group(f"idler{side}", [xi, yi, z], {"type": "roll", "radius": ri})
        m.cyl_z(f"idler {side}", ri, track_w * 0.7, [xi, yi, z], wc, "paint", group=g)
        for k in range(3):
            m.box(f"idler spoke {side}{k}", [0.05, ri * 1.6, 0.03], [xi, yi, z + out * (track_w * 0.35 + 0.02)], P["light"], "paint", rot=[0, 0, k * 60], group=g)
        for i, (x, y, r) in enumerate(rollers):
            g = m.group(f"roller{side}{i}", [x, y, z], {"type": "roll", "radius": r})
            m.cyl_z(f"return roller {side}{i}", r, track_w * 0.6, [x, y, z], wc, "paint", group=g)
            m.box(f"roller mark {side}{i}", [0.03, r * 1.6, 0.02], [x, y, z + out * (track_w * 0.3 + 0.01)], P["light"], "paint", group=g)
        if fenders:
            x0, x1, fy = fenders
            m.box(f"fender {side}", [x1 - x0, 0.04, track_w + 0.1], [(x0 + x1) / 2, fy, z], P["top"], "paint")
    return half


def tank_gun(m, T, P, base, length, r, *, sleeve=True, brake="baffle", evac=True, name="gun"):
    """Barrel group (recoils) on the turret, with its muzzle flash group at the tip."""
    gx, gy, gz = base
    G = m.group(name, [gx, gy, gz], {"type": "recoil", "axis": [-1, 0, 0], "amount": 0.35 + length * 0.04}, parent=T)
    m.cyl_x(f"{name} recoil sleeve", r * 1.9, r * 2.1, length * 0.12, [gx + length * 0.06, gy, gz], P["dark"], "paint", group=G)
    m.cyl_x(f"{name} barrel", r * 0.85, r, length, [gx + length / 2, gy, gz], P["top"] if sleeve else STEEL, "paint" if sleeve else "metal", group=G)
    if evac:
        m.cyl_x(f"{name} bore evacuator", r * 1.45, r * 1.45, length * 0.11, [gx + length * 0.55, gy, gz], P["top"], "paint", group=G)
    tip = gx + length
    if brake == "baffle":
        m.cyl_x(f"{name} muzzle brake", r * 1.6, r * 1.6, length * 0.06, [tip + length * 0.01, gy, gz], DARK_STEEL, "metal", sides=8, group=G)
        m.cyl_x(f"{name} muzzle brake front", r * 1.7, r * 1.7, length * 0.03, [tip + length * 0.05, gy, gz], DARK_STEEL, "metal", sides=8, group=G)
        tip += length * 0.07
    elif brake == "box":
        m.rbox(f"{name} muzzle brake", [length * 0.07, r * 2.2, r * 2.8], r * 0.4, [tip + length * 0.02, gy, gz], DARK_STEEL, "metal", group=G)
        tip += length * 0.06
    F = m.group(f"{name} flash", [tip, gy, gz], {"type": "flash"}, parent=G)
    m.add(f"{name} flash outer", "cone", [r * 3.5, length * 0.25], [tip + length * 0.125, gy, gz], "#ff9a2e", "glow", rot=[0, 0, -90], group=F)
    m.add(f"{name} flash inner", "cone", [r * 2, length * 0.15], [tip + length * 0.075, gy, gz], "#fff1b0", "glow", rot=[0, 0, -90], group=F)
    return G


def cupola(m, T, P, x, y, z, r=0.32):
    m.cyl_y("cupola", r, r * 1.08, 0.24, [x, y + 0.12, z], P["top"], "paint", sides=14, group=T)
    m.cyl_y("cupola hatch", r * 0.85, r * 0.85, 0.05, [x, y + 0.26, z], P["light"], "paint", sides=14, group=T)
    for k in range(6):
        a = 2 * math.pi * k / 6
        m.box(f"cupola vision block {k}", [0.08, 0.08, 0.06], [x + r * math.cos(a), y + 0.14, z + r * math.sin(a)], GLASS, "glass", rot=[0, -math.degrees(a), 0], group=T)


def antenna(m, T, x, y, z, h, lamp=True, parent=None):
    m.cyl_y("antenna base", 0.06, 0.08, 0.12, [x, y + 0.06, z], DARK_STEEL, group=T)
    m.cyl_y("antenna whip", 0.008, 0.015, h, [x, y + h / 2, z], "#1f201d", "metal", group=T)
    if lamp:
        g = m.group("antenna lamp", [x, y + h + 0.04, z], {"type": "blink", "rate": 1.0, "duty": 0.4}, parent=T)
        m.add("antenna lamp", "sphere", [0.04], [x, y + h + 0.04, z], "#ff4a3a", "glow", group=g)


PANZER_GREY = {"top": "#6a6f5c", "dark": "#474b3c", "light": "#8a8f78", "under": "#3e4234", "accent": "#e8e4d8"}
DUNKELGELB = {"top": "#a8975f", "dark": "#76683e", "light": "#c2b27c", "under": "#5f5434", "accent": "#5a6b3a"}
OLIVE = {"top": "#5b6331", "dark": "#3c4220", "light": "#737d40", "under": "#33391f", "accent": "#d2aa3c"}


def grimjaw():
    """L3c Grimjaw: a boxy heavy tank with a long gun (after the Tiger I). Interleaved road wheels,
    front drive sprocket, flat armour, a horseshoe turret and a long 88 with a double-baffle brake."""
    m = Model("Iron Tide Grimjaw")
    P = DUNKELGELB
    L, W = 6.3, 3.56
    wheels = [-2.35 + i * 0.66 for i in range(8)]
    half = running_gear(m, P, L, W, wheels=wheels, wheel_r=0.4, track_w=0.72, sprocket_front=True,
                        sprocket=(2.88, 0.78, 0.36), idler=(-2.95, 0.72, 0.3), interleave=True, pitch=0.16, spokes=0)
    # hull: tub between the tracks, superstructure overhanging them with vertical sides, a near-vertical front plate
    zin = half - 0.36 - 0.02
    m.hull("lower hull", [p for z in (-zin, zin) for p in [(-3.0, 0.48, z), (2.7, 0.48, z), (3.15, 0.85, z), (3.15, 1.2, z), (-3.1, 1.2, z)]], P["under"])
    up = []
    for s in (-1, 1):
        up += [(3.2, 1.18, s * 1.8), (-3.15, 1.18, s * 1.8), (3.05, 1.82, s * 1.8), (-3.15, 1.82, s * 1.8), (3.2, 1.6, s * 1.8)]
    m.hull("superstructure", up, P["top"])
    m.box("front plate", [0.12, 0.62, 3.3], [3.18, 1.5, 0], P["top"], "paint", rot=[0, 0, -9])
    m.box("glacis", [0.6, 0.1, 3.3], [3.0, 1.84, 0], P["top"], "paint", rot=[0, 0, -10])
    m.rbox("driver visor", [0.12, 0.14, 0.42], 0.02, [3.25, 1.62, -0.75], P["dark"])
    m.box("driver visor slit", [0.02, 0.04, 0.3], [3.32, 1.62, -0.75], "#111", "matte")
    m.add("hull MG ball", "sphere", [0.15], [3.24, 1.58, 0.75], P["dark"])
    m.cyl_x("hull MG", 0.025, 0.025, 0.5, [3.5, 1.58, 0.75], DARK_STEEL)
    for s, side in mirror_sides():
        m.cyl_y(f"headlamp {side}", 0.09, 0.09, 0.18, [3.08, 1.98, s * 1.35], P["dark"])
        m.add(f"headlamp lens {side}", "sphere", [0.07], [3.16, 1.98, s * 1.35], LAMP, "glow", scale=[0.6, 1, 1])
        m.add(f"tow shackle {side}", "torus", [0.1, 0.03], [3.25, 0.95, s * 1.15], DARK_STEEL, "metal", rot=[90, 0, 0])
        m.box(f"track guard {side}", [0.9, 0.04, 0.78], [2.75, 1.22, s * half], P["top"], "paint", rot=[0, 0, -18])
        m.cyl_x(f"tow cable {side}", 0.03, 0.03, 4.2, [-0.4, 1.6, s * 1.82], "#3c3b35", "metal")
        m.cyl_x(f"spare track rack {side}", 0.02, 0.02, 1.6, [2.1, 1.4, s * 1.83], DARK_STEEL, "metal")
        for k in range(4):
            m.box(f"spare track link {side}{k}", [0.15, 0.42, 0.05], [1.5 + k * 0.17, 1.42, s * 1.84], DARK_STEEL, "metal")
        m.cyl_y(f"exhaust {side}", 0.09, 0.1, 0.6, [-3.25, 1.75, s * 0.55], "#3a2f28", "metal")
        m.box(f"exhaust guard {side}", [0.08, 0.6, 0.28], [-3.32, 1.75, s * 0.55], P["dark"], "paint")
        m.rbox(f"air filter {side}", [0.3, 0.45, 0.3], 0.05, [-3.25, 1.4, s * 1.0], P["dark"])
        m.rbox(f"stowage bin {side}", [0.7, 0.4, 0.3], 0.03, [-2.6, 2.02, s * 1.55], P["light"])
    for k in range(6):
        m.box(f"engine grille {k}", [0.12, 0.03, 1.4], [-2.85 + k * 0.22, 1.84, 0], P["dark"], "paint")
    m.rbox("engine deck hatch", [1.0, 0.05, 0.9], 0.02, [-1.6, 1.85, 0], P["light"])
    m.cyl_y("driver hatch", 0.28, 0.28, 0.05, [2.35, 1.85, -0.75], P["light"], "paint", sides=12)
    m.cyl_y("radio hatch", 0.28, 0.28, 0.05, [2.35, 1.85, 0.75], P["light"], "paint", sides=12)
    # turret: a horseshoe of thick plate, flat sides, a big mantlet
    tp = [-0.2, 1.84, 0]
    m.cyl_y("turret ring", 1.0, 1.05, 0.06, [tp[0], 1.86, 0], P["dark"], "paint")
    T = m.group("turret", tp, {"type": "turret", "amount": 0.6, "speed": 0.45})
    tx, ty = tp[0], tp[1]
    ring = []
    for k in range(18):
        a = math.pi * (0.5 + k / 17)       # the back half round
        for y in (0.04, 0.84):
            ring.append((tx - 0.35 + 1.3 * math.cos(a), ty + y, 1.45 * math.sin(a)))
    for s in (-1, 1):
        ring += [(tx + 1.05, ty + 0.04, s * 1.45), (tx + 1.05, ty + 0.84, s * 1.4)]
    m.hull("turret body", ring, P["top"], group=T)
    m.box("turret roof", [2.6, 0.06, 2.6], [tx - 0.15, ty + 0.87, 0], P["top"], "paint", group=T)
    m.rbox("gun mantlet", [0.38, 0.85, 1.7], 0.12, [tx + 1.2, ty + 0.45, 0], P["top"], group=T)
    m.box("mantlet sight", [0.05, 0.1, 0.12], [tx + 1.4, ty + 0.6, 0.45], GLASS, "glass", group=T)
    m.cyl_x("coaxial MG", 0.02, 0.02, 0.3, [tx + 1.45, ty + 0.5, -0.35], DARK_STEEL, group=T)
    cupola(m, T, P, tx - 0.95, ty + 0.88, -0.65)
    m.cyl_y("loader hatch", 0.27, 0.27, 0.05, [tx - 0.2, ty + 0.91, 0.6], P["light"], "paint", sides=12, group=T)
    for s in (-1, 1):
        for k in range(3):
            m.cyl_x(f"smoke candle", 0.05, 0.05, 0.22, [tx + 0.9, ty + 0.75 - k * 0.12, s * 1.48], DARK_STEEL, group=T)
    m.rbox("stowage bin turret", [0.55, 0.45, 1.3], 0.05, [tx - 1.85, ty + 0.5, 0], P["light"], group=T)
    for k in range(3):
        m.box(f"pistol port {k}", [0.1, 0.12, 0.04], [tx - 1.0 + k * 0.5, ty + 0.45, (-1 if k % 2 else 1) * 1.45], P["dark"], "paint", group=T)
    antenna(m, T, -2.6, 1.9, 1.3, 2.0, lamp=False)
    tank_gun(m, T, P, (tx + 1.35, ty + 0.45, 0), 4.9, 0.085, brake="baffle", evac=False)
    lamp = m.group("antenna lamp", [-2.6, 3.95, 1.3], {"type": "blink", "rate": 1.0, "duty": 0.4})
    m.add("antenna lamp", "sphere", [0.04], [-2.6, 3.95, 1.3], "#ff4a3a", "glow", group=lamp)
    return m.save()


def monolith():
    """L4c Monolith: a super-heavy (after the Maus). Huge slab hull, full-length armoured skirts with the track
    showing below, a rounded turret face and a twin-gun mantlet (main gun plus a short coaxial gun)."""
    m = Model("Iron Tide Monolith")
    P = PANZER_GREY
    L, W = 10.1, 3.71
    wheels = [-3.9 + i * 0.6 for i in range(13)]
    half = running_gear(m, P, L, W, wheels=wheels, wheel_r=0.3, track_w=1.1, sprocket_front=False,
                        sprocket=(-4.62, 0.72, 0.42), idler=(4.6, 0.72, 0.38), rollers=[(-2.4, 1.05, 0.12), (0.0, 1.05, 0.12), (2.4, 1.05, 0.12)],
                        pitch=0.24, ridge=False, spokes=0)
    zin = half - 0.55
    m.hull("lower hull", [p for z in (-zin, zin) for p in [(-4.6, 0.45, z), (4.3, 0.45, z), (5.05, 1.1, z), (4.9, 1.35, z), (-4.95, 1.35, z), (-5.0, 0.8, z)]], P["under"])
    up = []
    for s in (-1, 1):
        up += [(5.05, 1.3, s * 1.86), (-5.05, 1.3, s * 1.86), (3.8, 2.25, s * 1.6), (-4.95, 2.25, s * 1.6), (-5.0, 1.75, s * 1.86), (5.05, 1.65, s * 1.86)]
    m.hull("upper hull", up, P["top"])
    for s, side in mirror_sides():
        m.hull(f"side skirt {side}", [(-4.9, 0.6, s * 1.86), (4.9, 0.6, s * 1.86), (-4.9, 1.4, s * 1.86), (4.9, 1.4, s * 1.86),
                                     (-4.9, 0.6, s * 1.93), (4.9, 0.6, s * 1.93), (-4.9, 1.4, s * 1.93), (4.9, 1.4, s * 1.93)], P["top"])
        for k in range(6):
            m.box(f"skirt bolt row {side}{k}", [0.06, 0.6, 0.02], [-4.0 + k * 1.6, 1.0, s * 1.94], P["dark"], "paint")
        m.cyl_y(f"exhaust {side}", 0.12, 0.14, 0.4, [-3.2, 2.42, s * 0.9], "#3a2f28", "metal")
        m.cyl_y(f"headlamp {side}", 0.09, 0.09, 0.16, [4.4, 1.9, s * 1.4], P["dark"])
        m.add(f"headlamp lens {side}", "sphere", [0.07], [4.48, 1.9, s * 1.4], LAMP, "glow", scale=[0.6, 1, 1])
        m.add(f"tow hook {side}", "torus", [0.13, 0.04], [5.05, 1.0, s * 1.2], DARK_STEEL, "metal", rot=[90, 0, 0])
        m.cyl_x(f"tow cable {side}", 0.035, 0.035, 6, [-0.6, 2.1, s * 1.7], "#3c3b35", "metal")
    for k in range(8):
        m.box(f"engine grille {k}", [0.18, 0.04, 2.2], [-4.3 + k * 0.3, 2.27, 0], P["dark"], "paint")
    m.cyl_y("driver hatch", 0.3, 0.3, 0.05, [3.4, 2.28, -0.8], P["light"], "paint", sides=12)
    m.cyl_y("driver periscope", 0.08, 0.08, 0.14, [3.7, 2.3, -0.8], GLASS, "glass")
    tp = [-1.2, 2.25, 0]
    m.cyl_y("turret ring", 1.25, 1.3, 0.08, [tp[0], 2.28, 0], P["dark"], "paint")
    T = m.group("turret", tp, {"type": "turret", "amount": 0.5, "speed": 0.35})
    tx, ty = tp[0], tp[1]
    body = []
    for k in range(9):              # rounded nose of the turret
        a = -math.pi / 2 + math.pi * k / 8
        for y, sc in ((0.05, 1.0), (1.15, 0.85)):
            body.append((tx + 0.9 + 0.75 * math.cos(a) * sc, ty + y, 1.6 * math.sin(a) * sc))
    for s in (-1, 1):
        body += [(tx - 2.3, ty + 0.05, s * 1.7), (tx - 2.3, ty + 1.15, s * 1.45), (tx - 2.6, ty + 0.6, s * 1.5)]
    m.hull("turret body", body, P["top"], group=T)
    m.rbox("pig snout mantlet", [0.7, 0.9, 1.4], 0.35, [tx + 1.75, ty + 0.55, 0], P["top"], group=T)
    cupola(m, T, P, tx - 1.0, ty + 1.15, -0.8, r=0.35)
    m.rbox("rangefinder housing", [0.5, 0.3, 3.4], 0.1, [tx + 0.1, ty + 1.15, 0], P["dark"], group=T)
    for s in (-1, 1):
        m.cyl_z("rangefinder lens", 0.12, 0.08, [tx + 0.1, ty + 1.15, s * 1.72], GLASS, "glass", group=T)
    m.cyl_y("loader hatch", 0.3, 0.3, 0.05, [tx - 0.8, ty + 1.18, 0.75], P["light"], "paint", sides=12, group=T)
    m.box("turret stowage", [0.6, 0.45, 1.6], [tx - 2.5, ty + 0.6, 0], P["light"], "paint", group=T)
    tank_gun(m, T, P, (tx + 2.05, ty + 0.62, 0.18), 6.2, 0.1, brake="none", evac=True)
    tank_gun(m, T, P, (tx + 2.05, ty + 0.62, -0.32), 2.4, 0.055, brake="none", evac=False, name="coaxial gun")
    antenna(m, T, tx - 2.2, ty + 1.15, 1.2, 2.2, parent=T)
    return m.save()


def jackal():
    """L1 Jackal: the starter light tank (after the M3 Stuart). Tall riveted hull, front sprocket, rear idler on the
    ground, four road wheels on two volute bogies, a small round turret and a 37 mm gun."""
    m = Model("Iron Tide Jackal")
    P = OLIVE
    L, W = 4.5, 2.24
    half = running_gear(m, P, L, W, wheels=[-1.35, -0.75, 0.55, 1.15], wheel_r=0.3, track_w=0.3, sprocket_front=True,
                        sprocket=(1.92, 0.68, 0.3), idler=(-1.95, 0.36, 0.33), rollers=[(-1.05, 0.98, 0.08), (0.85, 0.98, 0.08)],
                        pitch=0.13, ridge=False, spokes=6)
    for s, side in mirror_sides():
        for k, x in enumerate((-1.05, 0.85)):
            m.rbox(f"volute bogie {side}{k}", [0.5, 0.45, 0.2], 0.06, [x, 0.62, s * (half - 0.22)], P["dark"])
            m.cyl_y(f"volute spring {side}{k}", 0.08, 0.08, 0.32, [x, 0.66, s * (half - 0.3)], STEEL, "metal")
    zin = half - 0.18
    m.hull("hull", [p for z in (-zin, zin) for p in [(-2.05, 0.55, z), (1.8, 0.55, z), (2.25, 0.95, z), (2.0, 1.75, z), (-2.0, 1.75, z), (-2.15, 1.0, z)]], P["top"])
    up = []
    for s in (-1, 1):
        up += [(1.95, 1.2, s * 1.05), (-2.05, 1.2, s * 1.05), (1.75, 1.78, s * 1.0), (-2.0, 1.78, s * 1.0)]
    m.hull("sponsons", up, P["top"])
    m.box("drivers front plate", [0.08, 0.55, 1.9], [2.0, 1.5, 0], P["light"], "paint", rot=[0, 0, -18])
    for s, side in mirror_sides():
        m.rbox(f"driver hood {side}", [0.4, 0.28, 0.45], 0.04, [1.8, 1.88, s * 0.45], P["top"])
        m.box(f"vision slit {side}", [0.02, 0.04, 0.25], [2.0, 1.9, s * 0.45], "#111", "matte")
        m.cyl_y(f"headlamp {side}", 0.07, 0.07, 0.12, [2.05, 1.6, s * 0.95], P["dark"])
        m.add(f"headlamp lens {side}", "sphere", [0.055], [2.1, 1.6, s * 0.95], LAMP, "glow", scale=[0.6, 1, 1])
        m.box(f"fender {side}", [4.2, 0.03, 0.42], [0.0, 1.21, s * half], P["top"], "paint")
        m.cyl_x(f"exhaust {side}", 0.07, 0.08, 0.5, [-2.2, 1.35, s * 0.5], "#3a2f28", "metal")
        for k in range(10):
            m.add(f"rivet row {side}{k}", "sphere", [0.025], [-1.8 + k * 0.4, 1.6, s * 1.06], P["light"], "paint")
    m.add("bow MG ball", "sphere", [0.1], [2.12, 1.38, 0.5], P["dark"])
    m.cyl_x("bow MG", 0.02, 0.02, 0.4, [2.35, 1.38, 0.5], DARK_STEEL)
    m.box("star marking", [0.02, 0.4, 0.4], [-2.02, 1.4, 0], OLIVE["accent"], "paint", rot=[45, 0, 0])
    tp = [0.1, 1.78, 0]
    T = m.group("turret", tp, {"type": "turret", "amount": 0.8, "speed": 0.6})
    tx, ty = tp[0], tp[1]
    body = []
    for k in range(16):
        a = 2 * math.pi * k / 16
        for y, r in ((0.02, 0.72), (0.62, 0.6)):
            body.append((tx + r * math.cos(a), ty + y, r * math.sin(a)))
    m.hull("turret body", body, P["top"], group=T)
    m.rbox("turret mantlet", [0.22, 0.32, 0.5], 0.05, [tx + 0.75, ty + 0.3, 0], P["dark"], group=T)
    cupola(m, T, P, tx - 0.15, ty + 0.62, -0.25, r=0.22)
    m.cyl_y("AA MG post", 0.025, 0.025, 0.5, [tx - 0.3, ty + 0.85, 0.35], DARK_STEEL, group=T)
    m.cyl_x("AA MG", 0.02, 0.025, 0.7, [tx - 0.05, ty + 1.1, 0.35], DARK_STEEL, group=T)
    tank_gun(m, T, P, (tx + 0.85, ty + 0.3, 0), 1.9, 0.045, sleeve=False, brake="none", evac=False)
    antenna(m, T, -1.6, 1.78, 0.75, 1.6)
    return m.save()


# ================================================================ ships
def ship_hull(m, P, L, B, *, draft, free, bow_sheer, stern_drop=0.0, flare=0.14, transom=0.8, bow_rake=0.3, stations=None):
    """A hull lofted from sections, in three colour bands (under water, boot-top, topsides) plus a deck."""
    xb, xs = L / 2, -L / 2

    def half_beam(x):
        f = (x - xs) / L
        if f > 0.62:
            return max(0.06, B / 2 * (1 - ((f - 0.62) / 0.38) ** 1.8))
        if f < 0.22:
            return B / 2 * (transom + (1 - transom) * (f / 0.22) ** 0.6)
        return B / 2

    def dr(x):
        f = (x - xs) / L
        if f > 0.85:
            return draft * (1 - (f - 0.85) / 0.15 * (1 - bow_rake))
        if f < 0.08:
            return draft * (0.7 + 0.3 * f / 0.08)
        return draft

    def fb(x):
        f = (x - xs) / L
        return free + max(0.0, (f - 0.55) / 0.45) ** 2 * bow_sheer - max(0.0, (0.15 - f) / 0.15) * stern_drop

    def wat(x, y):
        b = half_beam(x)
        if y <= 0:
            return b * (1 - (min(1, -y / dr(x)) ** 2.4) * 0.72)
        fl = 0.02 + flare * max(0.0, ((x - xs) / L - 0.6) / 0.4)
        return b * (1 + fl * y / fb(x))

    st = stations or [xs + L * f for f in (0, 0.08, 0.22, 0.4, 0.55, 0.68, 0.78, 0.86, 0.92, 0.96, 0.985, 1.0)]
    bands = [("underwater hull", P["under"], lambda x: [-dr(x), -0.6 * dr(x), -0.04 * draft]),
             ("boot-top", P["boot"], lambda x: [-0.04 * draft, 0.03 * free]),
             ("topsides", P["top"], lambda x: [0.03 * free, fb(x) * 0.55, fb(x)])]
    for i in range(len(st) - 1):
        xa, xc = st[i], st[i + 1]
        for name, color, ys in bands:
            pts = []
            for x in (xa, xc):
                for y in ys(x):
                    w = wat(x, y) + (0.02 * B / 15 if name == "boot-top" else 0)
                    pts += [(x, y, -w), (x, y, w)]
            m.hull(f"{name} {i}", pts, color)
        pts = []
        for x in (xa, xc):
            f_, w = fb(x), wat(x, fb(x)) * 0.985
            pts += [(x, f_ + 0.03, -w), (x, f_ + 0.03, w), (x, f_ - 0.3, -w), (x, f_ - 0.3, w)]
        m.hull(f"deck {i}", pts, P["deck"])
    return half_beam, fb, wat


def ship_turret(m, P, gid, x, deck, *, n, calibre, house, aft=False, arc=0.9, barbette=True, raise_h=0.0):
    """A gun house on a barbette: turret group > barrels (recoil) group > flash group at every muzzle."""
    d = -1 if aft else 1
    hl, hw, hh = house
    base = deck + raise_h
    if barbette:
        m.cyl_y(f"{gid} barbette", hw * 0.55, hw * 0.6, 0.6 + raise_h, [x, deck + (0.6 + raise_h) / 2 - 0.3, 0], P["top"], "paint", sides=24)
    y = base + 0.3
    T = m.group(gid, [x, y, 0], {"type": "turret", "amount": arc, "speed": 0.35, "phase": 1.7 if aft else 0})
    pts = []
    for s in (-1, 1):
        pts += [(x + d * hl * 0.55, y, s * hw * 0.42), (x - d * hl * 0.45, y, s * hw * 0.5),
                (x + d * hl * 0.42, y + hh, s * hw * 0.32), (x - d * hl * 0.45, y + hh, s * hw * 0.46),
                (x + d * hl * 0.55, y + hh * 0.55, s * hw * 0.42)]
    m.hull(f"{gid} gun house", pts, P["top"], group=T)
    m.box(f"{gid} roof", [hl * 0.8, hh * 0.04, hw * 0.75], [x - d * hl * 0.05, y + hh + hh * 0.02, 0], P["light"], "paint", group=T)
    for s in (-1, 1):
        m.rbox(f"{gid} rangefinder hood", [hl * 0.15, hh * 0.3, hw * 0.12], hh * 0.05, [x - d * hl * 0.25, y + hh * 0.85, s * hw * 0.5], P["dark"], group=T)
    gy = y + hh * 0.45
    root = x + d * hl * 0.5
    blen = calibre * 50
    G = m.group(f"{gid} barrels", [root, gy, 0], {"type": "recoil", "axis": [-d, 0, 0], "amount": blen * 0.1}, parent=T)
    zs = [(k - (n - 1) / 2) * hw * 0.28 for k in range(n)]
    for z in zs:
        m.box(f"{gid} gun port", [hl * 0.05, hh * 0.3, calibre * 3], [root, gy, z], "#202427", "matte", group=G)
        m.add(f"{gid} barrel", "cylinder", [calibre * 0.75, calibre * 1.1, blen], [root + d * blen / 2, gy, z], P["light"], "metal", rot=[0, 0, -90 * d], group=G)
        m.add(f"{gid} barrel sleeve", "cylinder", [calibre * 1.4, calibre * 1.4, blen * 0.15], [root + d * blen * 0.08, gy, z], P["top"], "paint", rot=[0, 0, -90 * d], group=G)
    tip = root + d * blen
    F = m.group(f"{gid} flash", [tip, gy, 0], {"type": "flash"}, parent=G)
    for z in zs:
        m.add(f"{gid} flash outer", "cone", [calibre * 5, blen * 0.45], [tip + d * blen * 0.22, gy, z], "#ff9a2e", "glow", rot=[0, 0, -90 * d], group=F)
        m.add(f"{gid} flash inner", "cone", [calibre * 2.6, blen * 0.26], [tip + d * blen * 0.13, gy, z], "#fff1b0", "glow", rot=[0, 0, -90 * d], group=F)
    return T


def secondary_mount(m, P, x, y, z, s, aft=False):
    d = -1 if aft else 1
    m.cyl_y("secondary mount base", s * 0.45, s * 0.5, s * 0.3, [x, y + s * 0.15, z], P["dark"], "paint", sides=12)
    m.hull("secondary gun house", [(x + d * s * 0.6, y + s * 0.3, z - s * 0.4), (x + d * s * 0.6, y + s * 0.3, z + s * 0.4), (x - d * s * 0.5, y + s * 0.3, z - s * 0.45), (x - d * s * 0.5, y + s * 0.3, z + s * 0.45),
                                    (x + d * s * 0.4, y + s * 0.9, z - s * 0.3), (x + d * s * 0.4, y + s * 0.9, z + s * 0.3), (x - d * s * 0.5, y + s * 0.9, z - s * 0.4), (x - d * s * 0.5, y + s * 0.9, z + s * 0.4)], P["top"])
    for dz in (-0.18, 0.18):
        m.add("secondary barrel", "cylinder", [s * 0.05, s * 0.07, s * 1.6], [x + d * s * 1.3, y + s * 0.6, z + dz * s], P["light"], "metal", rot=[0, 0, -90 * d])


def lattice_mast(m, P, x, base, h, w=1.2, name="mast"):
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.add(f"{name} leg", "cylinder", [w * 0.06, w * 0.09, h], [x + sx * w * 0.35, base + h / 2, sz * w * 0.35], P["light"], "metal",
                  rot=[sz * math.degrees(math.atan(w * 0.3 / h)), 0, -sx * math.degrees(math.atan(w * 0.3 / h))], sides=8)
    for k in range(4):
        hh = base + h * (0.2 + k * 0.2)
        m.box(f"{name} platform", [w * (1.2 - k * 0.2), 0.12, w * (1.2 - k * 0.2)], [x, hh, 0], P["top"], "paint")


def radar(m, P, gid, x, y, w, speed, kind="bed"):
    R = m.group(gid, [x, y, 0], {"type": "spin", "axis": [0, 1, 0], "speed": speed})
    m.cyl_y(f"{gid} pedestal", w * 0.06, w * 0.08, w * 0.15, [x, y + w * 0.075, 0], P["dark"], "paint", group=R)
    if kind == "bed":
        m.box(f"{gid} bedspring", [w * 0.06, w * 0.35, w], [x + w * 0.05, y + w * 0.32, 0], P["light"], "metal", group=R)
        for k in range(5):
            m.box(f"{gid} dipole row {k}", [w * 0.08, w * 0.015, w * 0.95], [x + w * 0.09, y + w * 0.18 + k * w * 0.07, 0], P["dark"], "metal", group=R)
    else:
        m.add(f"{gid} dish", "sphere", [w * 0.4], [x + w * 0.1, y + w * 0.3, 0], P["light"], "metal", scale=[0.25, 1, 1], group=R)
    return R


def lamp(m, gid, pos, rate=0.8, color="#ff3b2f", r=0.25):
    g = m.group(gid, pos, {"type": "blink", "rate": rate, "duty": 0.4})
    m.add(gid, "sphere", [r], pos, color, "glow", group=g)


def railings(m, P, xs_, xe, fb, wat, step, h):
    for s, side in ((-1, "port"), (1, "starboard")):
        x = xs_
        while x < xe:
            z = s * (wat(x, fb(x)) * 0.97)
            m.cyl_y(f"rail post {side}", h * 0.03, h * 0.03, h, [x, fb(x) + h / 2, z], P["light"], "metal", sides=5)
            x += step


NAVY_1944 = {"top": "#7d8790", "deck": "#6a5a44", "under": "#5a2a26", "boot": "#1d2023", "dark": "#4b5359", "light": "#a3adb5", "accent": "#e9e6da"}
IJN_GREY = {"top": "#8a8f8c", "deck": "#7a6d55", "under": "#6b2d27", "boot": "#1c1f21", "dark": "#585e5d", "light": "#a9aeab", "accent": "#e9e6da"}
HOME_GREY = {"top": "#8f969b", "deck": "#6e604a", "under": "#5d2b27", "boot": "#1d2023", "dark": "#5a6166", "light": "#b4bbbf", "accent": "#e9e6da"}


def battleship(name, P, L, B, *, tower, funnels, radars, sec, bow_sheer, pagoda=False):
    m = Model(name)
    s = L / 225.0
    hb, fb, wat = ship_hull(m, P, L, B, draft=11 * s, free=8.5 * s, bow_sheer=6 * s, flare=0.18, transom=0.55, bow_rake=0.15)
    dy = lambda x: fb(x) + 0.03
    # main battery: two forward (B superfiring), one aft
    hl, hw, hh = 18 * s, 14 * s, 5.2 * s
    cal = 0.45 * s
    ship_turret(m, P, "A turret", 0.30 * L, dy(0.30 * L), n=3, calibre=cal, house=(hl, hw, hh), arc=0.9)
    ship_turret(m, P, "B turret", 0.18 * L, dy(0.18 * L), n=3, calibre=cal, house=(hl, hw, hh), arc=0.8, raise_h=4.0 * s)
    ship_turret(m, P, "X turret", -0.28 * L, dy(-0.28 * L), n=3, calibre=cal, house=(hl, hw, hh), aft=True, arc=0.9)
    # superstructure: armoured citadel deckhouse, the tower, funnels
    d0 = dy(0)
    m.hull("citadel deckhouse", [(x, y, z) for x in (0.12 * L, -0.2 * L) for y in (d0 - 0.4, d0 + 5 * s) for z in (-B * 0.36, B * 0.36)], P["top"])
    m.hull("upper deckhouse", [(x, y, z) for x in (0.1 * L, -0.12 * L) for y in (d0 + 5 * s, d0 + 9 * s) for z in (-B * 0.26, B * 0.26)], P["top"])
    tx = 0.07 * L
    if pagoda:
        levels = [(14, 9), (12, 8), (10, 7), (8, 6), (7, 6), (6, 5), (9, 3)]
    else:
        levels = [(13, 8), (10, 6), (7, 6), (5, 5), (4, 4)]
    y = d0 + 9 * s
    for k, (w, h) in enumerate(levels):
        w *= s
        h *= s
        m.hull(f"tower level {k}", [(xx, yy, zz) for xx in (tx + w * 0.55, tx - w * 0.6) for yy in (y, y + h) for zz in (-w * 0.5, w * 0.5)], P["top"])
        m.box(f"tower windows {k}", [w * 0.02 + 0.05, h * 0.18, w * 0.8], [tx + w * 0.56, y + h * 0.7, 0], "#1b2a33", "glass")
        if k in (1, 3):
            for sd in (-1, 1):
                m.box(f"bridge wing {k}", [w * 0.4, 0.25 * s + 0.1, w * 0.45], [tx + w * 0.2, y + h * 0.35, sd * w * 0.7], P["top"], "paint")
        y += h
    m.rbox("main director", [6 * s, 3 * s, 7 * s], 0.8 * s, [tx, y + 1.5 * s, 0], P["dark"])
    for sd in (-1, 1):
        m.cyl_z("director rangefinder", 0.6 * s, 2 * s, [tx - 0.5 * s, y + 1.5 * s, sd * 4.2 * s], P["dark"], "paint")
    top = y + 3 * s
    m.cyl_y("foremast", 0.4 * s, 0.6 * s, 16 * s, [tx - 2 * s, top + 8 * s, 0], P["light"], "metal")
    m.box("yardarm", [0.4 * s, 0.4 * s, 14 * s], [tx - 2 * s, top + 12 * s, 0], P["light"], "metal")
    radar(m, P, "radar", tx - 2 * s, top + 16 * s, 7 * s, 1.7, "bed")
    lamp(m, "mast lamp", [tx - 2 * s, top + 19 * s, 0], r=0.4 * s)
    for k, (fx, fw, fh, rake) in enumerate(funnels):
        fx *= L
        fw *= s
        fh *= s
        base = d0 + 9 * s
        pts = []
        for sd in (-1, 1):
            pts += [(fx + fw * 0.7, base, sd * fw * 0.45), (fx - fw * 0.7, base, sd * fw * 0.45),
                    (fx + fw * 0.5 - rake * s, base + fh, sd * fw * 0.38), (fx - fw * 0.6 - rake * s, base + fh, sd * fw * 0.38)]
        m.hull(f"funnel {k}", pts, P["top"])
        m.box(f"funnel cap {k}", [fw * 1.2, 0.6 * s, fw * 0.78], [fx - 0.05 * fw - rake * s, base + fh, 0], "#25282a", "matte")
        for j in range(4):
            m.box(f"funnel grating {k}", [0.2 * s, 0.3 * s, fw * 0.7], [fx - fw * 0.45 + j * fw * 0.3 - rake * s, base + fh + 0.35 * s, 0], "#151718", "metal")
    if radars > 1:
        ax = -0.13 * L
        m.cyl_y("mainmast", 0.4 * s, 0.6 * s, 22 * s, [ax, d0 + 9 * s + 11 * s, 0], P["light"], "metal")
        radar(m, P, "aft radar", ax, d0 + 31 * s, 5 * s, -2.4, "dish")
        m.rbox("aft director", [5 * s, 2.5 * s, 6 * s], 0.6 * s, [ax + 6 * s, d0 + 11 * s, 0], P["dark"])
    # secondary battery and light AA along both sides
    for k in range(sec):
        x = 0.1 * L - k * (0.26 * L / max(1, sec - 1))
        for sd in (-1, 1):
            secondary_mount(m, P, x, d0 + 5 * s, sd * B * 0.33, 4.2 * s, aft=x < -0.05 * L)
    for k in range(10):
        x = 0.24 * L - k * 0.05 * L
        if abs(x - 0.18 * L) < 0.04 * L or abs(x + 0.28 * L) < 0.05 * L:
            continue
        for sd in (-1, 1):
            z = sd * wat(x, fb(x)) * 0.86
            m.cyl_y("AA tub", 1.2 * s, 1.2 * s, 1.0 * s, [x, fb(x) + 0.5 * s, z], P["top"], "paint", sides=12)
            m.cyl_x("AA barrels", 0.12 * s, 0.12 * s, 2.4 * s, [x + 1.1 * s, fb(x) + 1.5 * s, z], DARK_STEEL, "metal", sides=6)
    # bow fittings, catapult and floatplane aft, crane, jackstaff lamps
    for sd, side in ((-1, "port"), (1, "starboard")):
        x = 0.43 * L
        y = fb(x) - 2.5 * s
        m.cyl_z(f"hawse hole {side}", 1.0 * s, 0.5 * s, [x, y, sd * (wat(x, y) + 0.1)], "#111315", "matte")
        m.hull(f"anchor {side}", [(x - 1.4 * s, y - 2.2 * s, sd * (wat(x, y) + 0.3)), (x + 1.4 * s, y - 2.2 * s, sd * (wat(x, y) + 0.3)), (x, y - 0.4 * s, sd * (wat(x, y) + 0.3)),
                                  (x, y - 2.6 * s, sd * (wat(x, y) + 0.6)), (x - 1.1 * s, y - 1.6 * s, sd * (wat(x, y) + 0.1)), (x + 1.1 * s, y - 1.6 * s, sd * (wat(x, y) + 0.1))], DARK_STEEL, "metal")
    m.cyl_y("jackstaff", 0.15 * s, 0.2 * s, 5 * s, [0.49 * L, fb(0.49 * L) + 2.5 * s, 0], P["dark"])
    lamp(m, "bow lamp", [0.49 * L, fb(0.49 * L) + 5.2 * s, 0], rate=0.9, color="#fff1c4", r=0.35 * s)
    cx = -0.44 * L
    for sd in (-1, 1):
        m.box("catapult", [18 * s, 0.6 * s, 1.0 * s], [cx + 2 * s, fb(cx) + 1.2 * s, sd * B * 0.22], P["dark"], "metal", rot=[0, sd * -20, 0])
    m.add("floatplane fuselage", "capsule", [0.8 * s, 7 * s], [cx + 2 * s, fb(cx) + 2.6 * s, B * 0.22], "#a3adb5", "paint", rot=[0, 20, 90])
    m.box("floatplane wing", [2 * s, 0.25 * s, 11 * s], [cx + 3 * s, fb(cx) + 3.2 * s, B * 0.22], "#a3adb5", "paint", rot=[0, 20, 0])
    m.add("floatplane float", "capsule", [0.5 * s, 5 * s], [cx + 2 * s, fb(cx) + 1.6 * s, B * 0.22], "#8d969d", "paint", rot=[0, 20, 90])
    m.cyl_y("aircraft crane", 0.5 * s, 0.7 * s, 8 * s, [-0.49 * L + 2 * s, fb(-0.49 * L) + 4 * s, 0], P["dark"])
    m.box("crane jib", [12 * s, 0.6 * s, 0.6 * s], [-0.49 * L + 6 * s, fb(-0.49 * L) + 8.5 * s, 0], P["light"], "paint", rot=[0, 0, 22])
    railings(m, P, -0.48 * L, 0.46 * L, fb, wat, 4.5 * s, 1.1 * s)
    return m.save()


def colossus():
    return battleship("Iron Tide Colossus", NAVY_1944, 224.7, 27.5, tower=None, funnels=[(0.02, 9, 16, 1.5), (-0.07, 9, 16, 1.5)], radars=2, sec=5, bow_sheer=6)


def leviathan():
    return battleship("Iron Tide Leviathan", IJN_GREY, 224.7, 33.2, tower=None, funnels=[(-0.03, 13, 20, 6)], radars=1, sec=3, bow_sheer=8, pagoda=True)


def small_ship(name, P, L, B, *, turrets, funnels, torpedoes=0, catapult=False, hull_no=None, mast_h=20):
    """Tier-1 ships: a destroyer, a light cruiser or a small coastal battleship."""
    m = Model(name)
    s = L / 100.0
    hb, fb, wat = ship_hull(m, P, L, B, draft=3.6 * s, free=4.6 * s, bow_sheer=2.6 * s, flare=0.16, transom=0.6, bow_rake=0.25)
    dy = lambda x: fb(x) + 0.03
    for t in turrets:
        gid, xf, n, cal, size, aft, raise_h = t
        ship_turret(m, P, gid, xf * L, dy(xf * L), n=n, calibre=cal * s, house=(size * s, size * 0.8 * s, size * 0.32 * s), aft=aft, arc=0.9, raise_h=raise_h * s)
    d0 = dy(0.12 * L)
    m.hull("forecastle deckhouse", [(x, y, z) for x in (0.2 * L, -0.02 * L) for y in (d0 - 0.3, d0 + 2.6 * s) for z in (-B * 0.32, B * 0.32)], P["top"])
    bx = 0.17 * L
    m.hull("bridge", [(x, y, z) for x in (bx + 2.5 * s, bx - 3.5 * s) for y in (d0 + 2.6 * s, d0 + 6.2 * s) for z in (-B * 0.28, B * 0.28)], P["top"])
    m.box("bridge windows", [0.1, 0.9 * s, B * 0.5], [bx + 2.55 * s, d0 + 5.4 * s, 0], "#1b2a33", "glass")
    m.box("compass platform", [4 * s, 0.25 * s, B * 0.6], [bx - 0.5 * s, d0 + 6.3 * s, 0], P["light"], "paint")
    for sd in (-1, 1):
        m.box("bridge wing", [2 * s, 0.25 * s, 1.6 * s], [bx + 1.2 * s, d0 + 4.8 * s, sd * B * 0.36], P["top"], "paint")
        m.cyl_x("searchlight", 0.4 * s, 0.35 * s, 0.6 * s, [bx + 1.6 * s, d0 + 5.4 * s, sd * B * 0.36], P["dark"], "paint")
        m.cyl_x("searchlight lens", 0.33 * s, 0.33 * s, 0.05, [bx + 1.92 * s, d0 + 5.4 * s, sd * B * 0.36], "#fff6d8", "glow")
    m.rbox("gun director", [2.2 * s, 1.4 * s, 2.4 * s], 0.3 * s, [bx - 1.5 * s, d0 + 7.0 * s, 0], P["dark"])
    mx = bx - 4.5 * s
    m.cyl_y("foremast", 0.15 * s, 0.25 * s, mast_h * s, [mx, d0 + mast_h * s / 2, 0], P["light"], "metal")
    m.box("yardarm", [0.15 * s, 0.15 * s, B * 0.6], [mx, d0 + mast_h * s * 0.75, 0], P["light"], "metal")
    lamp(m, "mast lamp", [mx, d0 + mast_h * s + 0.3 * s, 0], r=0.25 * s)
    for k, (fxf, fw, fh, rake) in enumerate(funnels):
        fx = fxf * L
        base = dy(fx)
        pts = []
        for sd in (-1, 1):
            pts += [(fx + fw * s * 0.5, base, sd * fw * s * 0.4), (fx - fw * s * 0.5, base, sd * fw * s * 0.4),
                    (fx + fw * s * 0.45 - rake * s, base + fh * s, sd * fw * s * 0.36), (fx - fw * s * 0.5 - rake * s, base + fh * s, sd * fw * s * 0.36)]
        m.hull(f"funnel {k}", pts, P["top"])
        m.box(f"funnel band {k}", [fw * s * 0.98, 0.5 * s, fw * s * 0.75], [fx - rake * s * 0.9, base + fh * s * 0.85, 0], "#2a2c2d", "paint")
        m.box(f"funnel cap {k}", [fw * s * 1.02, 0.25 * s, fw * s * 0.76], [fx - rake * s, base + fh * s, 0], "#151718", "matte")
    for k in range(torpedoes):
        tx_ = -0.08 * L - k * 0.1 * L
        m.cyl_y(f"torpedo mount {k}", 1.2 * s, 1.3 * s, 0.5 * s, [tx_, dy(tx_) + 0.25 * s, 0], P["dark"], "paint")
        for j in (-1, 0, 1):
            m.cyl_x(f"torpedo tube {k}", 0.28 * s, 0.28 * s, 6.5 * s, [tx_, dy(tx_) + 0.85 * s, j * 0.65 * s], P["top"], "paint")
    if catapult:
        cx = -0.05 * L
        m.box("catapult", [14 * s, 0.4 * s, 0.8 * s], [cx, dy(cx) + 3.0 * s, 0], P["dark"], "metal", rot=[0, 35, 0])
        m.cyl_y("catapult pedestal", 0.8 * s, 1.0 * s, 2.6 * s, [cx, dy(cx) + 1.3 * s, 0], P["dark"], "paint")
        m.add("floatplane fuselage", "capsule", [0.55 * s, 5 * s], [cx, dy(cx) + 4.2 * s, 0], "#b9c1c7", "paint", rot=[0, 35, 90])
        m.box("floatplane wing", [1.6 * s, 0.2 * s, 10 * s], [cx + 0.5 * s, dy(cx) + 4.8 * s, 0], "#b9c1c7", "paint", rot=[0, 35, 0])
        m.add("floatplane float", "capsule", [0.4 * s, 3.6 * s], [cx, dy(cx) + 3.4 * s, 0], "#9aa3a9", "paint", rot=[0, 35, 90])
        m.cyl_y("aircraft crane", 0.3 * s, 0.4 * s, 5 * s, [cx - 6 * s, dy(cx) + 2.5 * s, B * 0.3], P["dark"])
    for sd, side in ((-1, "port"), (1, "starboard")):
        m.add(f"ship's boat {side}", "capsule", [0.8 * s, 4.5 * s], [-0.0 * L, dy(0) + 1.6 * s, sd * B * 0.4], "#e6e4dc", "glossy", rot=[0, 0, 90])
        for dx in (-2.6, 2.6):
            m.add(f"davit {side}", "torus", [1.2 * s, 0.1 * s], [dx * s, dy(0) + 1.8 * s, sd * B * 0.42], P["dark"], "metal", rot=[0, 0, 0], scale=[0.4, 1, 1])
        x = 0.42 * L
        y = fb(x) - 1.3 * s
        m.cyl_z(f"hawse hole {side}", 0.5 * s, 0.4 * s, [x, y, sd * (wat(x, y) + 0.05)], "#111315", "matte")
    if hull_no:
        from build_iron_tide import SEVEN_SEG
        seg = {"a": (0.0, 0.0, 1.0, 0.2), "g": (0.0, -1.0, 1.0, 0.2), "d": (0.0, -2.0, 1.0, 0.2), "f": (-0.5, -0.5, 0.2, 1.0), "b": (0.5, -0.5, 0.2, 1.0), "e": (-0.5, -1.5, 0.2, 1.0), "c": (0.5, -1.5, 0.2, 1.0)}
        for sd in (-1, 1):
            for k, digit in enumerate(hull_no):
                x0 = 0.34 * L + (k if sd > 0 else len(hull_no) - 1 - k) * 1.6 * s
                for nm in SEVEN_SEG[digit]:
                    cx_, cy_, w, h = seg[nm]
                    x = x0 + (cx_ if sd > 0 else -cx_) * s
                    y = fb(x0) - 0.8 * s + cy_ * s
                    m.box("hull number", [w * s, h * s, 0.05], [x, y, sd * (wat(x, y) + 0.06)], P["accent"], "paint")
    m.cyl_y("jackstaff", 0.08 * s, 0.1 * s, 3 * s, [0.49 * L, fb(0.49 * L) + 1.5 * s, 0], P["dark"])
    lamp(m, "bow lamp", [0.49 * L, fb(0.49 * L) + 3.2 * s, 0], rate=0.9, color="#fff1c4", r=0.2 * s)
    m.cyl_y("ensign staff", 0.08 * s, 0.1 * s, 3 * s, [-0.49 * L, fb(-0.49 * L) + 1.5 * s, 0], P["dark"])
    railings(m, P, -0.47 * L, 0.45 * L, fb, wat, 3.2 * s, 1.0 * s)
    return m.save()


def lynx():
    return small_ship("Iron Tide Lynx", HOME_GREY, 97, 9.6, turrets=[
        ("A gun", 0.32, 1, 0.12, 4.2, False, 0.0), ("B gun", 0.24, 1, 0.12, 4.2, False, 1.8), ("Y gun", -0.36, 1, 0.12, 4.2, True, 0.0)],
        funnels=[(0.06, 3.4, 6.5, 0.8), (-0.06, 3.4, 6.0, 0.8)], torpedoes=2, hull_no="12")


def sentinel():
    return small_ship("Iron Tide Sentinel", HOME_GREY, 100, 10.7, turrets=[
        ("A turret", 0.3, 2, 0.15, 6.5, False, 0.0), ("B turret", 0.21, 2, 0.15, 6.5, False, 2.2), ("X turret", -0.3, 2, 0.15, 6.5, True, 0.0)],
        funnels=[(0.04, 6.5, 8.5, 1.4)], catapult=True, hull_no="21", mast_h=24)


def bulwark():
    return small_ship("Iron Tide Bulwark", HOME_GREY, 107, 16.7, turrets=[
        ("A turret", 0.28, 2, 0.26, 9.5, False, 0.0), ("B turret", -0.17, 2, 0.26, 9.5, True, 2.6), ("X turret", -0.34, 2, 0.26, 9.5, True, 0.0)],
        funnels=[(0.1, 6.0, 9.0, 1.0)], hull_no="3", mast_h=26)


# ================================================================ planes
def prop(m, gid, x, y, z, r, blades, spinner_c="#2b2f33", tip="#f2c230", parent=None):
    g = m.group(gid, [x, y, z], {"type": "spin", "axis": [1, 0, 0], "speed": 45, "byThrottle": True}, parent=parent)
    m.add(f"{gid} spinner", "cone", [r * 0.16, r * 0.4], [x + r * 0.2, y, z], spinner_c, "glossy", rot=[0, 0, -90], group=g)
    for k in range(blades):
        a = 360 * k / blades
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        m.box(f"{gid} blade {k}", [0.04, r * 0.85, r * 0.12], [x, y + ca * r * 0.5, z + sa * r * 0.5], "#26292b", "paint", rot=[a, 0, 0], group=g)
        m.box(f"{gid} blade tip {k}", [0.045, r * 0.12, r * 0.12], [x, y + ca * r * 0.94, z + sa * r * 0.94], tip, "paint", rot=[a, 0, 0], group=g)
    return g


def fuselage(m, P, stations, *, belly=None, color=None):
    """Round-ish sections [(x, half-width, top, bottom)], lofted pair by pair."""
    def sec(x, w, t, b):
        out = []
        for k in range(14):
            a = 2 * math.pi * k / 14
            c, s_ = math.cos(a), math.sin(a)
            out.append((x, t * s_ if s_ > 0 else b * abs(s_) ** 0.85, w * c))
        return out
    for i in range(len(stations) - 1):
        m.hull(f"fuselage {i}", sec(*stations[i]) + sec(*stations[i + 1]), color or P["top"])


def wing_panel(m, name, P, root, tip, color, group=None):
    """root/tip: (x_le, x_te, z, y, thickness)."""
    pts = []
    for x_le, x_te, z, y, t in (root, tip):
        pts += [(x_le, y, z), (x_te, y, z), (x_le - (x_le - x_te) * 0.3, y + t, z), (x_le - (x_le - x_te) * 0.3, y - t * 0.5, z)]
    m.hull(name, pts, color, group=group)


def control_surface(m, gid, name, P, hinge0, hinge1, chord, color, amount=0.3, speed=1.4, phase=0.0, vertical=False):
    ax = [hinge1[i] - hinge0[i] for i in range(3)]
    ln = math.sqrt(sum(v * v for v in ax))
    g = m.group(gid, list(hinge0), {"type": "wiggle", "axis": [v / ln for v in ax], "amount": amount, "speed": speed, "phase": phase})
    pts = []
    for h in (hinge0, hinge1):
        if vertical:
            pts += [(h[0], h[1], h[2] - 0.03), (h[0], h[1], h[2] + 0.03), (h[0] - chord, h[1], h[2] - 0.01), (h[0] - chord, h[1], h[2] + 0.01)]
        else:
            pts += [(h[0], h[1] - 0.04, h[2]), (h[0], h[1] + 0.04, h[2]), (h[0] - chord, h[1] - 0.01, h[2]), (h[0] - chord, h[1] + 0.01, h[2])]
    m.hull(name, pts, color, group=g)


def gear_leg(m, gid, x, top, z, length, wheel_r, axis, amount, door_color, twin=False):
    G = m.group(gid, [x, top, z], {"type": "fold", "axis": axis, "amount": amount})
    m.cyl_y(f"{gid} oleo", 0.07, 0.09, length * 0.6, [x, top - length * 0.3, z], "#c9cdd0", "metal", group=G)
    m.cyl_y(f"{gid} strut", 0.05, 0.05, length * 0.45, [x, top - length * 0.75, z], "#e3e6e8", "metal", group=G)
    wy = top - length
    for dz in ((-0.16, 0.16) if twin else (0,)):
        m.cyl_z(f"{gid} tyre", wheel_r, wheel_r * 0.55, [x, wy, z + dz], RUBBER, "rubber", group=G)
        m.cyl_z(f"{gid} hub", wheel_r * 0.5, wheel_r * 0.6, [x, wy, z + dz], "#b8bdc1", "metal", sides=10, group=G)
    m.box(f"{gid} gear door", [wheel_r * 2.2, length * 0.5, 0.03], [x, top - length * 0.3, z + wheel_r * 0.5], door_color, "paint", group=G)


OD_GREEN = {"top": "#59613f", "under": "#9aa19e", "dark": "#3e4430", "light": "#7c8562", "accent": "#2c5f8d"}
TRAINER = {"top": "#d9a13a", "under": "#d9a13a", "dark": "#3a4a6a", "light": "#efe6cf", "accent": "#2c5f8d"}


def insignia(m, x, y, z, r, up=True):
    m.cyl_y("insignia", r, r, 0.02, [x, y, z], "#2c5f8d", "paint", sides=6)
    m.cyl_y("insignia ring", r * 0.66, r * 0.66, 0.025, [x, y + 0.003, z], "#e8eef2", "paint", sides=6)
    m.cyl_y("insignia centre", r * 0.32, r * 0.32, 0.03, [x, y + 0.006, z], "#d6a536", "paint", sides=3)


def bastion():
    """A4c Bastion: four-engined heavy bomber with gun positions all round (after the B-17)."""
    m = Model("Iron Tide Bastion")
    P = OD_GREEN
    L = 22.7
    fuselage(m, P, [(11.3, 0.05, 0.1, -0.1), (10.6, 0.75, 0.7, -0.75), (8.5, 1.05, 1.2, -1.05), (5.0, 1.2, 1.5, -1.2),
                    (0.0, 1.2, 1.5, -1.25), (-4.0, 1.05, 1.3, -1.05), (-7.5, 0.7, 0.9, -0.7), (-10.4, 0.35, 0.55, -0.35), (-11.3, 0.25, 0.4, -0.2)])
    m.hull("nose glazing", [(x, y, z) for x in (11.35, 10.0) for y in (-0.6, 0.5) for z in (-0.7 if x < 11 else -0.12, 0.7 if x < 11 else 0.12)], "#33536b", "glass")
    m.hull("cockpit glazing", [(7.6, 1.2, -0.7), (7.6, 1.2, 0.7), (6.0, 1.75, -0.6), (6.0, 1.75, 0.6), (5.3, 1.5, -0.8), (5.3, 1.5, 0.8), (8.3, 1.0, -0.6), (8.3, 1.0, 0.6)], "#33536b", "glass")
    for k in range(5):
        m.box("cockpit frame", [0.05, 0.6, 1.5], [7.8 - k * 0.5, 1.5, 0], P["dark"], "paint")
    # wings: long straight taper, mid-low on the fuselage
    for sd, side in ((-1, "L"), (1, "R")):
        wing_panel(m, f"wing {side}", P, (2.8, -2.6, sd * 1.1, -0.2, 0.55), (-0.6, -2.6, sd * 15.8, 0.35, 0.14), P["top"])
        control_surface(m, f"aileron {side}", f"aileron {side}", P, (-2.0, 0.28, sd * 9.5), (-2.4, 0.36, sd * 15.0), 0.9, P["light"], amount=0.25, phase=0 if sd < 0 else math.pi)
        control_surface(m, f"flap {side}", f"flap {side}", P, (-1.9, -0.05, sd * 2.0), (-1.95, 0.15, sd * 8.8), 0.8, P["light"], amount=0.12, speed=0.6)
        m.add(f"nav light {side}", "sphere", [0.08], [-1.4, 0.4, sd * 15.85], "#ff3b2f" if sd < 0 else "#3bff6a", "glow")
        insignia(m, -0.5, 0.42, sd * 11.5, 0.9)
        for e, ez in enumerate((4.3, 8.6)):
            z = sd * ez
            ex = 2.9 - ez * 0.12
            m.add(f"engine nacelle {side}{e}", "capsule", [0.7, 2.6], [ex - 0.5, 0.05, z], P["top"], "paint", rot=[0, 0, 90])
            m.cyl_x(f"engine cowling {side}{e}", 0.72, 0.76, 0.9, [ex + 0.9, 0.05, z], P["dark"], "paint", sides=18)
            m.cyl_x(f"cowling front {side}{e}", 0.62, 0.7, 0.1, [ex + 1.38, 0.05, z], "#2a2c2d", "matte", sides=18)
            m.cyl_y(f"exhaust stub {side}{e}", 0.1, 0.1, 0.4, [ex - 0.2, -0.65, z], "#5a4a3c", "metal")
            prop(m, f"propeller {side}{e}", ex + 1.55, 0.05, z, 1.75, 3)
    # tail: tall fin with a dorsal fillet, big tailplanes, gun positions
    m.hull("tail fin", [(-6.5, 0.8, -0.12), (-6.5, 0.8, 0.12), (-10.9, 0.5, -0.1), (-10.9, 0.5, 0.1), (-9.7, 5.4, -0.06), (-9.7, 5.4, 0.06), (-11.0, 5.3, -0.06), (-11.0, 5.3, 0.06)], P["top"])
    control_surface(m, "rudder", "rudder", P, (-10.95, 0.6, 0), (-11.05, 5.1, 0), 0.9, P["light"], amount=0.25, speed=0.9, vertical=True)
    for sd, side in ((-1, "L"), (1, "R")):
        wing_panel(m, f"tailplane root {side}", P, (-8.4, -10.6, sd * 0.4, 0.3, 0.25), (-9.8, -10.6, sd * 5.4, 0.3, 0.1), P["top"])
        control_surface(m, f"tailplane {side}", f"tailplane elevator {side}", P, (-10.6, 0.3, sd * 0.6), (-10.6, 0.3, sd * 5.3), 0.7, P["light"], amount=0.18, speed=0.8)
    m.add("dorsal turret", "sphere", [0.65], [5.0, 1.55, 0], "#33536b", "glass", scale=[1, 0.8, 1])
    for sd in (-1, 1):
        m.cyl_x("dorsal guns", 0.03, 0.03, 1.4, [5.7, 1.75, sd * 0.15], DARK_STEEL)
    m.add("ball turret", "sphere", [0.6], [-1.5, -1.3, 0], "#2b2f33", "glossy")
    m.add("ball turret window", "sphere", [0.35], [-1.15, -1.3, 0], "#33536b", "glass")
    m.add("chin turret", "sphere", [0.4], [10.0, -0.85, 0], P["dark"], "paint")
    for sd in (-1, 1):
        m.cyl_x("chin guns", 0.025, 0.025, 1.0, [10.6, -0.9, sd * 0.12], DARK_STEEL)
        m.box("waist window", [1.0, 0.6, 0.05], [-4.6, 0.35, sd * 1.04], "#33536b", "glass")
        m.cyl_z("waist gun", 0.03, 0.9, [-4.6, 0.35, sd * 1.3], DARK_STEEL)
    m.hull("tail gunner", [(-10.6, 0.55, -0.35), (-10.6, 0.55, 0.35), (-11.8, 0.3, -0.25), (-11.8, 0.3, 0.25), (-10.6, -0.2, -0.3), (-10.6, -0.2, 0.3), (-11.8, -0.1, -0.2), (-11.8, -0.1, 0.2)], "#33536b", "glass")
    for sd in (-1, 1):
        m.cyl_x("tail guns", 0.03, 0.03, 1.0, [-12.2, 0.15, sd * 0.12], DARK_STEEL)
    for k in range(4):
        m.box("bomb bay door seam", [0.04, 0.02, 1.4], [1.5 - k * 0.8, -1.25, 0], P["dark"], "paint")
    # gear: two mains fold forward into the inner nacelles, a tail wheel
    for sd, side in ((-1, "L"), (1, "R")):
        gear_leg(m, f"main gear {side}", 2.0, -0.55, sd * 4.3, 2.3, 0.62, [0, 0, 1], 1.6, P["under"])
    gear_leg(m, "tail gear", -8.8, -0.5, 0, 0.9, 0.25, [0, 0, 1], 1.4, P["under"])
    lamp(m, "tail beacon", [-10.3, 5.5, 0], rate=1.2, r=0.08)
    return m.save()


def sparrow():
    """A1 Sparrow: the two-seat prop trainer every pilot starts in (after the T-6 Texan)."""
    m = Model("Iron Tide Sparrow")
    P = TRAINER
    fuselage(m, P, [(4.3, 0.55, 0.55, -0.55), (3.6, 0.62, 0.62, -0.62), (2.0, 0.62, 0.7, -0.68), (0.0, 0.58, 0.68, -0.65),
                    (-2.0, 0.45, 0.55, -0.5), (-3.8, 0.22, 0.4, -0.25), (-4.4, 0.12, 0.3, -0.15)])
    m.cyl_x("engine cowling", 0.62, 0.66, 0.9, [3.95, 0.0, 0], P["dark"], "paint", sides=18)
    m.cyl_x("cowling front", 0.5, 0.6, 0.1, [4.42, 0.0, 0], "#2a2c2d", "matte", sides=18)
    prop(m, "propeller", 4.55, 0.0, 0, 1.3, 2, spinner_c="#c9cdd0", tip="#f2c230")
    can = [(x, y, z) for x, w in ((2.2, 0.38), (1.6, 0.45), (-0.8, 0.45), (-1.5, 0.3)) for y, k in ((0.62, 1.0), (1.2, 0.8)) for z in (-w * k, w * k)]
    m.hull("canopy greenhouse", can, "#4a6f88", "glass")
    for k in range(5):
        x = 1.9 - k * 0.75
        m.box("canopy frame top", [0.05, 0.04, 0.6], [x, 1.18, 0], "#2a2d30", "paint")
        for sd in (-1, 1):
            m.box("canopy frame post", [0.05, 0.56, 0.04], [x, 0.9, sd * 0.4], "#2a2d30", "paint", rot=[sd * 12, 0, 0])
    m.box("canopy rail", [3.8, 0.04, 1.0], [0.4, 0.64, 0], P["dark"], "paint")
    for sd, side in ((-1, "L"), (1, "R")):
        wing_panel(m, f"wing {side}", P, (1.4, -1.0, sd * 0.5, -0.45, 0.32), (0.3, -0.6, sd * 5.8, -0.2, 0.1), P["top"])
        control_surface(m, f"aileron {side}", f"aileron {side}", P, (-0.55, -0.22, sd * 3.2), (-0.62, -0.18, sd * 5.6), 0.35, P["light"], phase=0 if sd < 0 else math.pi)
        control_surface(m, f"flap {side}", f"flap {side}", P, (-0.9, -0.38, sd * 0.7), (-0.6, -0.26, sd * 3.0), 0.35, P["light"], amount=0.1, speed=0.6)
        m.add(f"nav light {side}", "sphere", [0.05], [0.0, -0.18, sd * 5.85], "#ff3b2f" if sd < 0 else "#3bff6a", "glow")
        insignia(m, -0.1, -0.12, sd * 4.0, 0.45)
        gear_leg(m, f"main gear {side}", 0.4, -0.45, sd * 1.5, 1.3, 0.32, [1, 0, 0], -sd * 1.57, P["under"])
        wing_panel(m, f"tailplane root {side}", P, (-3.5, -4.0, sd * 0.2, 0.15, 0.1), (-3.8, -4.1, sd * 2.1, 0.15, 0.05), P["top"])
        control_surface(m, f"tailplane {side}", f"tailplane elevator {side}", P, (-4.05, 0.15, sd * 0.25), (-4.1, 0.15, sd * 2.1), 0.35, P["light"], amount=0.2, speed=0.8)
    m.hull("tail fin", [(-3.2, 0.4, -0.06), (-3.2, 0.4, 0.06), (-4.3, 0.3, -0.05), (-4.3, 0.3, 0.05), (-4.0, 1.7, -0.03), (-4.0, 1.7, 0.03), (-4.4, 1.65, -0.03), (-4.4, 1.65, 0.03)], P["top"])
    control_surface(m, "rudder", "rudder", P, (-4.35, 0.35, 0), (-4.42, 1.6, 0), 0.4, P["dark"], amount=0.3, speed=1.0, vertical=True)
    m.box("fuselage stripe", [5.0, 0.12, 1.32], [-1.2, 0.0, 0], P["dark"], "paint")
    gear_leg(m, "tail gear", -3.9, -0.15, 0, 0.35, 0.12, [0, 0, 1], 1.2, P["under"])
    m.cyl_y("antenna mast", 0.02, 0.03, 0.5, [1.0, 1.0, 0], P["dark"])
    lamp(m, "tail beacon", [-4.4, 1.72, 0], rate=1.2, r=0.05)
    m.cyl_x("pitot", 0.012, 0.015, 0.6, [0.9, -0.35, 5.0], "#c9cdd0", "metal")
    return m.save()


if __name__ == "__main__":
    for f in (grimjaw, monolith, jackal, colossus, leviathan, lynx, sentinel, bulwark, bastion, sparrow):
        f()
