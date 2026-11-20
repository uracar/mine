"""Third batch: tier 2 of Service Tree 1 (S2a-S2d, L2a, L2b, A2a, A2b) and extra tree seeds.

    python3 build_batch3.py
"""
import math
from build_iron_tide import Model, DARK_STEEL, STEEL, RUBBER, GLASS, LAMP
from build_batch2 import (running_gear, tank_gun, cupola, antenna, ship_hull, ship_turret, small_ship, lattice_mast, radar, lamp,
                          railings, prop, fuselage, wing_panel, control_surface, gear_leg, insignia, OLIVE, HOME_GREY, OD_GREEN)
import build_trees


# ---------------------------------------------------------------- ships
def viper():
    """S2a Viper torpedo boat (after the Schnellboot): a long low hull, a forward gun, torpedo tubes in the bow."""
    m = Model("Iron Tide Viper")
    P = {"top": "#9aa2a6", "deck": "#7d756a", "under": "#3d4446", "boot": "#1d2023", "dark": "#5c6468", "light": "#c3c9cc", "accent": "#e9e6da"}
    L, B = 35.0, 5.3
    s = L / 35
    hb, fb, wat = ship_hull(m, P, L, B, draft=1.6 * s, free=2.4 * s, bow_sheer=1.0 * s, flare=0.25, transom=0.85, bow_rake=0.35)
    dy = lambda x: fb(x) + 0.03
    for sd, side in ((-1, "port"), (1, "starboard")):
        m.hull(f"bow torpedo tube {side}", [(x, y, z) for x in (0.42 * L, 0.18 * L) for y in (dy(0.3 * L) - 0.2, dy(0.3 * L) + 0.75) for z in (sd * 0.5, sd * 1.55)], P["top"])
        m.cyl_x(f"torpedo tube mouth {side}", 0.3, 0.3, 0.1, [0.42 * L + 0.05, dy(0.3 * L) + 0.25, sd * 1.0], "#151718", "matte")
    m.hull("wheelhouse", [(x, y, z) for x in (0.12 * L, -0.06 * L) for y in (dy(0), dy(0) + 1.9) for z in (-1.5, 1.5)], P["top"])
    m.box("wheelhouse windows", [0.08, 0.45, 2.4], [0.12 * L + 0.04, dy(0) + 1.45, 0], "#1b2a33", "glass")
    m.cyl_y("mast", 0.06, 0.08, 4.0, [0.0, dy(0) + 3.9, 0], P["light"], "metal")
    lamp(m, "mast lamp", [0.0, dy(0) + 6.0, 0], r=0.12)
    ship_turret(m, P, "A gun", 0.24 * L, dy(0.24 * L), n=1, calibre=0.04, house=(1.4, 1.2, 0.9), arc=1.0)
    for k, x in enumerate((-0.2 * L, -0.38 * L)):
        m.cyl_y(f"AA mount {k}", 0.5, 0.6, 0.5, [x, dy(x) + 0.25, 0], P["dark"], "paint")
        m.cyl_x(f"AA barrels {k}", 0.05, 0.05, 1.6, [x + 0.9, dy(x) + 0.75, 0], DARK_STEEL, "metal")
    m.add("liferaft", "torus", [0.5, 0.15], [-0.1 * L, dy(-0.1 * L) + 0.2, 1.5], "#e8622a", "matte", rot=[90, 0, 0])
    railings(m, P, -0.45 * L, 0.4 * L, fb, wat, 1.6, 0.6)
    lamp(m, "bow lamp", [0.47 * L, dy(0.47 * L) + 0.5, 0], rate=0.9, color="#fff1c4", r=0.08)
    return m.save()


def hornet_dd():
    """S2b Hornet AA destroyer (after the Akizuki): three twin high-angle mounts, a trunked funnel, close-in guns."""
    return small_ship("Iron Tide Hornet AA Destroyer", HOME_GREY, 134, 11.6, turrets=[
        ("A turret", 0.31, 2, 0.1, 5.4, False, 0.0), ("B turret", 0.23, 2, 0.1, 5.4, False, 1.8), ("X turret", -0.32, 2, 0.1, 5.4, True, 0.0)],
        funnels=[(0.0, 5.0, 7.0, 2.4)], torpedoes=1, hull_no="51")


def warden():
    """S2c Warden frigate (after the Oliver Hazard Perry): one gun, a missile launcher forward, a helicopter hangar and pad aft."""
    m = Model("Iron Tide Warden")
    P = {"top": "#a3abb1", "deck": "#6c7378", "under": "#5a2a26", "boot": "#1d2023", "dark": "#5e666b", "light": "#c7cdd1", "accent": "#e9e6da"}
    L, B = 136.0, 14.0
    s = L / 136
    hb, fb, wat = ship_hull(m, P, L, B, draft=5 * s, free=6.0 * s, bow_sheer=3.0 * s, flare=0.12, transom=0.75, bow_rake=0.3)
    dy = lambda x: fb(x) + 0.03
    # missile launcher forward (counts as a turret: rotating arm with one rail)
    x = 0.33 * L
    m.cyl_y("launcher magazine", 2.4, 2.6, 0.8, [x, dy(x) + 0.4, 0], P["dark"], "paint", sides=16)
    T = m.group("missile launcher", [x, dy(x) + 0.8, 0], {"type": "turret", "amount": 0.9, "speed": 0.4})
    m.cyl_y("launcher pedestal", 0.6, 0.8, 1.6, [x, dy(x) + 1.6, 0], P["top"], "paint", group=T)
    m.box("launcher arm", [3.4, 0.5, 0.6], [x + 0.6, dy(x) + 2.6, 0], P["light"], "paint", rot=[0, 0, 12], group=T)
    G = m.group("missile launcher rail", [x + 0.6, dy(x) + 3.0, 0], {"type": "recoil", "axis": [-1, 0, 0], "amount": 0.3}, parent=T)
    m.cyl_x("missile", 0.17, 0.17, 4.6, [x + 0.9, dy(x) + 3.1, 0], "#e9ece9", "glossy", group=G)
    m.add("missile seeker", "cone", [0.17, 0.6], [x + 3.5, dy(x) + 3.1, 0], "#2b2f33", "glossy", rot=[0, 0, -90], group=G)
    F = m.group("missile launcher flash", [x - 1.5, dy(x) + 3.1, 0], {"type": "flash"}, parent=G)
    m.add("launch blast", "cone", [0.8, 3.0], [x - 3.0, dy(x) + 3.1, 0], "#ffb04a", "glow", rot=[0, 0, 90], group=F)
    # long deckhouse, bridge, lattice mast with spinning radar, funnel
    d0 = dy(0.0)
    m.hull("deckhouse", [(xx, yy, zz) for xx in (0.22 * L, -0.28 * L) for yy in (d0 - 0.3, d0 + 5.5 * s) for zz in (-B * 0.42, B * 0.42)], P["top"])
    m.hull("bridge", [(xx, yy, zz) for xx in (0.22 * L, 0.12 * L) for yy in (d0 + 5.5 * s, d0 + 9 * s) for zz in (-B * 0.36, B * 0.36)], P["top"])
    m.box("bridge windows", [0.1, 0.9 * s, B * 0.6], [0.22 * L + 0.05, d0 + 8.1 * s, 0], "#1b2a33", "glass")
    lattice_mast(m, P, 0.1 * L, d0 + 9 * s, 14 * s, 2.2 * s)
    radar(m, P, "radar", 0.1 * L, d0 + 23 * s, 5 * s, 1.7, "bed")
    lamp(m, "mast lamp", [0.1 * L, d0 + 26 * s, 0], r=0.25)
    fx = -0.05 * L
    m.hull("funnel", [(xx, yy, zz) for xx in (fx + 3 * s, fx - 3 * s) for yy in (d0 + 5.5 * s, d0 + 11 * s) for zz in (-2.4 * s, 2.4 * s)], P["top"])
    m.box("funnel cap", [6.4 * s, 0.6 * s, 5 * s], [fx, d0 + 11 * s, 0], "#25282a", "matte")
    # the gun on top of the deckhouse amidships (as on the real ship), a close-in weapon on the hangar
    ship_turret(m, P, "main gun", -0.12 * L, d0 + 5.5 * s, n=1, calibre=0.08, house=(4.0, 3.2, 2.0), aft=False, arc=1.2, barbette=False)
    m.hull("hangar", [(xx, yy, zz) for xx in (-0.28 * L, -0.38 * L) for yy in (d0 - 0.3, d0 + 6.5 * s) for zz in (-B * 0.45, B * 0.45)], P["top"])
    m.box("hangar door", [0.1, 5 * s, B * 0.7], [-0.38 * L - 0.05, d0 + 2.9 * s, 0], P["dark"], "paint")
    m.cyl_y("CIWS base", 1.0, 1.2, 1.0, [-0.33 * L, d0 + 7 * s, 0], P["top"], "paint")
    m.add("CIWS dome", "capsule", [0.9, 1.3], [-0.33 * L, d0 + 8.7 * s, 0], "#e9ecef", "glossy")
    fd = dy(-0.45 * L)
    m.box("flight deck", [0.12 * L, 0.1, B * 0.86], [-0.44 * L, fd + 0.05, 0], "#53595d", "paint")
    m.add("landing circle", "torus", [B * 0.25, 0.1], [-0.44 * L, fd + 0.12, 0], "#f4f1e6", "paint", rot=[90, 0, 0])
    m.add("helicopter body", "capsule", [1.0, 6.0], [-0.44 * L, fd + 1.6, 0], "#5f686e", "paint", rot=[0, 0, 90])
    m.box("helicopter rotor", [11.0, 0.08, 0.4], [-0.44 * L, fd + 2.9, 0], "#2a2d30", "paint", rot=[0, 40, 0])
    m.box("helicopter tail boom", [6.0, 0.5, 0.4], [-0.44 * L - 6, fd + 2.0, 0], "#5f686e", "paint")
    railings(m, P, -0.48 * L, 0.45 * L, fb, wat, 3.4, 1.0)
    lamp(m, "bow lamp", [0.49 * L, dy(0.49 * L) + 2.5, 0], rate=0.9, color="#fff1c4", r=0.2)
    return m.save()


def anvil():
    """S2d Anvil monitor (after the Erebus class): a broad shallow raft with anti-torpedo bulges and one huge twin turret."""
    m = Model("Iron Tide Anvil")
    P = {"top": "#7f878b", "deck": "#6a604c", "under": "#5a2a26", "boot": "#1d2023", "dark": "#53595d", "light": "#a9b0b3", "accent": "#e9e6da"}
    L, B = 123.0, 27.0
    s = L / 123
    hb, fb, wat = ship_hull(m, P, L, B, draft=3.6 * s, free=4.0 * s, bow_sheer=1.5 * s, flare=0.05, transom=0.8, bow_rake=0.4)
    dy = lambda x: fb(x) + 0.03
    for sd, side in ((-1, "port"), (1, "starboard")):
        m.hull(f"bulge {side}", [(x, y, sd * z) for x in (0.3 * L, -0.35 * L) for y in (-2.8 * s, 0.6 * s) for z in (B * 0.38, B * 0.52)], P["under"])
    ship_turret(m, P, "main turret", 0.2 * L, dy(0.2 * L), n=2, calibre=0.38, house=(17, 14, 5.5), arc=0.7, raise_h=1.5)
    d0 = dy(0)
    m.hull("superstructure", [(x, y, z) for x in (0.06 * L, -0.12 * L) for y in (d0 - 0.3, d0 + 7) for z in (-7, 7)], P["top"])
    m.hull("bridge", [(x, y, z) for x in (0.06 * L, -0.02 * L) for y in (d0 + 7, d0 + 11) for z in (-5.5, 5.5)], P["top"])
    m.box("bridge windows", [0.1, 1.0, 9.0], [0.06 * L + 0.05, d0 + 10, 0], "#1b2a33", "glass")
    m.add("tripod leg", "cylinder", [0.4, 0.6, 26], [0.02 * L, d0 + 13, 0], P["light"], "metal")
    for sd in (-1, 1):
        m.add("tripod strut", "cylinder", [0.3, 0.45, 25], [-0.02 * L, d0 + 12.5, sd * 2.5], P["light"], "metal", rot=[sd * -6, 0, -8])
    m.rbox("spotting top", [6, 3, 6], 0.5, [0.02 * L, d0 + 26, 0], P["top"])
    lamp(m, "mast lamp", [0.02 * L, d0 + 28.5, 0], r=0.3)
    m.hull("funnel", [(x, y, z) for x in (-0.14 * L, -0.22 * L) for y in (d0, d0 + 13) for z in (-3, 3)], P["top"])
    m.box("funnel cap", [10, 0.6, 6.2], [-0.18 * L, d0 + 13, 0], "#25282a", "matte")
    for sd in (-1, 1):
        for k in range(3):
            x = -0.05 * L - k * 0.1 * L
            m.cyl_y("secondary mount", 1.2, 1.4, 1.0, [x, d0 + 0.5, sd * B * 0.36], P["dark"], "paint")
            m.cyl_x("secondary gun", 0.12, 0.15, 4.0, [x + 2.0, d0 + 1.3, sd * B * 0.36], P["light"], "metal")
    railings(m, P, -0.47 * L, 0.44 * L, fb, wat, 4.0, 1.1)
    lamp(m, "bow lamp", [0.49 * L, dy(0.49 * L) + 2.5, 0], rate=0.9, color="#fff1c4", r=0.25)
    return m.save()


# ---------------------------------------------------------------- land
def hornet_aa():
    """L2a Hornet: an eight-wheeled air-defence car with a rotary gun and missile pods."""
    m = Model("Iron Tide Hornet AA Car")
    P = {"top": "#6b7046", "dark": "#474b2e", "light": "#8a9060", "under": "#3a3d26", "accent": "#d2aa3c"}
    hull = []
    for sd in (-1, 1):
        hull += [(3.3, 0.75, sd * 0.9), (2.7, 1.55, sd * 1.25), (-3.2, 1.6, sd * 1.25), (-3.4, 0.8, sd * 1.1), (2.6, 0.55, sd * 1.15), (-3.0, 0.55, sd * 1.15)]
    m.hull("hull", hull, P["top"])
    m.hull("upper hull", [(x, y, z) for x in (2.4, -3.2) for y in (1.55, 2.2) for z in (-1.15, 1.15)] + [(2.9, 1.55, -1.0), (2.9, 1.55, 1.0)], P["top"])
    for k, x in enumerate((2.1, 0.9, -0.9, -2.1)):
        for sd, side in ((-1, "L"), (1, "R")):
            g = m.group(f"wheel{side}{k}", [x, 0.55, sd * 1.25], {"type": "roll", "radius": 0.55})
            m.cyl_z(f"tyre {side}{k}", 0.55, 0.38, [x, 0.55, sd * 1.25], RUBBER, "rubber", group=g)
            m.cyl_z(f"hub {side}{k}", 0.25, 0.4, [x, 0.55, sd * 1.25], P["dark"], "paint", sides=8, group=g)
            for j in range(2):
                m.box(f"hub bolt bar {side}{k}{j}", [0.05, 0.4, 0.03], [x, 0.55, sd * 1.46], STEEL, "metal", rot=[0, 0, j * 90], group=g)
            m.box(f"wheel arch {side}{k}", [1.25, 0.06, 0.45], [x, 1.18, sd * 1.25], P["dark"], "paint")
    m.box("trim vane", [0.06, 0.6, 2.0], [3.35, 1.2, 0], P["dark"], "paint", rot=[0, 0, 30])
    for sd in (-1, 1):
        m.box("driver vision block", [0.15, 0.12, 0.3], [2.5, 2.25, sd * 0.55], GLASS, "glass")
        m.cyl_y("headlamp", 0.08, 0.08, 0.14, [3.05, 1.3, sd * 0.9], P["dark"])
        m.add("headlamp lens", "sphere", [0.06], [3.12, 1.3, sd * 0.9], LAMP, "glow", scale=[0.6, 1, 1])
        m.rbox("stowage box", [1.0, 0.35, 0.3], 0.03, [-1.6, 2.0, sd * 1.25], P["light"])
    T = m.group("turret", [-0.6, 2.2, 0], {"type": "turret", "amount": 1.0, "speed": 0.7})
    m.hull("turret body", [(x, y, z) for x in (0.6, -1.5) for y in (2.2, 3.1) for z in (-0.95, 0.95)] + [(1.0, 2.5, -0.6), (1.0, 2.5, 0.6)], P["top"], group=T)
    m.box("search radar", [0.1, 0.8, 1.5], [-1.4, 3.6, 0], P["light"], "paint", group=T)
    m.cyl_y("radar mast", 0.06, 0.06, 0.5, [-1.4, 3.3, 0], P["dark"], group=T)
    for sd, side in ((-1, "L"), (1, "R")):
        m.rbox(f"missile pod {side}", [1.6, 0.6, 0.55], 0.06, [-0.4, 2.9, sd * 1.25], P["dark"], group=T)
        for j in range(2):
            m.cyl_x(f"missile cap {side}{j}", 0.12, 0.12, 0.05, [0.42, 2.9 + (j - 0.5) * 0.28, sd * 1.25], "#c8382c", "paint", group=T)
    G = m.group("gun", [0.9, 2.7, 0], {"type": "recoil", "axis": [-1, 0, 0], "amount": 0.08}, parent=T)
    m.cyl_x("rotary gun housing", 0.2, 0.22, 0.6, [1.2, 2.7, 0], P["dark"], "paint", group=G)
    for k in range(6):
        a = k * math.pi / 3
        m.cyl_x(f"rotary barrel {k}", 0.025, 0.025, 1.8, [2.3, 2.7 + 0.09 * math.sin(a), 0.09 * math.cos(a)], DARK_STEEL, "metal", group=G)
    F = m.group("gun flash", [3.25, 2.7, 0], {"type": "flash"}, parent=G)
    m.add("gun flash outer", "cone", [0.3, 1.0], [3.75, 2.7, 0], "#ff9a2e", "glow", rot=[0, 0, -90], group=F)
    antenna(m, T, -1.2, 3.1, -0.7, 1.8, parent=T)
    return m.save()


def ironhorse():
    """L2b Ironhorse: the workhorse (after the M4 Sherman). Tall cast hull with a sloped glacis, three volute bogies a side,
    front sprocket, a rounded cast turret and a 75 mm gun."""
    m = Model("Iron Tide Ironhorse")
    P = OLIVE
    L, W = 5.9, 2.62
    wheels = [-1.85, -1.4, -0.35, 0.1, 1.15, 1.6]
    half = running_gear(m, P, L, W, wheels=wheels, wheel_r=0.26, track_w=0.42, sprocket_front=True,
                        sprocket=(2.55, 0.72, 0.32), idler=(-2.55, 0.4, 0.3), rollers=[(-1.6, 1.0, 0.08), (-0.1, 1.0, 0.08), (1.4, 1.0, 0.08)],
                        pitch=0.14, ridge=True, spokes=6)
    for sd, side in ((-1, "L"), (1, "R")):
        for k, x in enumerate((-1.62, -0.12, 1.38)):
            m.rbox(f"volute bogie {side}{k}", [0.65, 0.5, 0.22], 0.08, [x, 0.6, sd * (half - 0.25)], P["dark"])
    zin = half - 0.22
    hull = []
    for sd in (-1, 1):
        hull += [(2.95, 0.75, sd * zin), (2.2, 1.95, sd * 1.25), (-2.6, 1.95, sd * 1.3), (-2.9, 1.35, sd * 1.3), (-2.8, 0.55, sd * zin), (2.5, 0.55, sd * zin), (2.8, 1.25, sd * 1.25)]
    m.hull("cast hull", hull, P["top"])
    m.hull("transmission cover", [(x, y, z) for x in (3.05, 2.6) for y in (0.55, 1.2) for z in (-1.0, 1.0)] + [(3.15, 0.85, -0.9), (3.15, 0.85, 0.9)], P["dark"])
    for sd, side in ((-1, "L"), (1, "R")):
        m.rbox(f"driver hood {side}", [0.5, 0.25, 0.5], 0.08, [2.0, 2.05, sd * 0.55], P["top"])
        m.cyl_y(f"driver periscope {side}", 0.06, 0.06, 0.12, [2.0, 2.22, sd * 0.55], GLASS, "glass")
        m.cyl_y(f"headlamp {side}", 0.07, 0.07, 0.15, [2.7, 1.6, sd * 1.05], P["dark"])
        m.add(f"headlamp lens {side}", "sphere", [0.055], [2.76, 1.6, sd * 1.05], LAMP, "glow", scale=[0.6, 1, 1])
        m.add(f"headlamp guard {side}", "torus", [0.11, 0.015], [2.78, 1.6, sd * 1.05], DARK_STEEL, "metal", rot=[0, 90, 0])
        m.box(f"sandshield {side}", [5.4, 0.03, 0.5], [0.0, 1.96, sd * half], P["top"], "paint")
        m.box(f"applique armour {side}", [0.9, 0.5, 0.05], [0.6, 1.6, sd * 1.32], P["light"], "paint")
    m.add("bow MG ball", "sphere", [0.1], [2.55, 1.6, 0.5], P["dark"])
    m.cyl_x("bow MG", 0.02, 0.02, 0.45, [2.8, 1.62, 0.5], DARK_STEEL)
    for k in range(5):
        m.box(f"engine grille {k}", [0.1, 0.03, 1.5], [-1.8 - k * 0.18, 1.97, 0], P["dark"], "paint")
    m.box("star marking side", [0.02, 0.5, 0.5], [-1.0, 1.55, 1.31], "#e8e4d8", "paint", rot=[45, 0, 0])
    m.box("star marking side L", [0.02, 0.5, 0.5], [-1.0, 1.55, -1.31], "#e8e4d8", "paint", rot=[45, 0, 0])
    tp = [0.05, 1.95, 0]
    T = m.group("turret", tp, {"type": "turret", "amount": 0.8, "speed": 0.5})
    body = []
    for k in range(18):
        a = 2 * math.pi * k / 18
        r = 0.95 if math.cos(a) > 0 else 1.05
        for y, sc in ((0.02, 1.0), (0.55, 0.92), (0.82, 0.72)):
            body.append((tp[0] + r * sc * math.cos(a) - (0.25 if math.cos(a) < 0 else 0), tp[1] + y, 0.95 * sc * math.sin(a)))
    m.hull("cast turret", body, P["top"], group=T)
    m.rbox("gun mantlet", [0.3, 0.55, 1.0], 0.1, [tp[0] + 1.05, tp[1] + 0.4, 0], P["top"], group=T)
    cupola(m, T, P, tp[0] - 0.4, tp[1] + 0.82, 0.45, r=0.28)
    m.cyl_y("loader hatch", 0.25, 0.25, 0.05, [tp[0] - 0.35, tp[1] + 0.84, -0.4], P["light"], "paint", sides=12, group=T)
    m.cyl_y("AA MG post", 0.025, 0.025, 0.45, [tp[0] - 0.4, tp[1] + 1.25, 0.45], DARK_STEEL, group=T)
    m.cyl_x("AA MG", 0.02, 0.028, 1.0, [tp[0] - 0.05, tp[1] + 1.45, 0.45], DARK_STEEL, group=T)
    tank_gun(m, T, P, (tp[0] + 1.2, tp[1] + 0.4, 0), 2.6, 0.06, sleeve=False, brake="none", evac=False)
    antenna(m, T, -2.2, 1.95, 0.9, 2.0)
    return m.save()


# ---------------------------------------------------------------- planes
def kestrel():
    """A2a Kestrel: a prop fighter with a bubble canopy and a belly radiator scoop (after the P-51)."""
    m = Model("Iron Tide Kestrel")
    P = {"top": "#b8bfc4", "under": "#b8bfc4", "dark": "#2a2d30", "light": "#d5dadd", "accent": "#2c5f8d"}
    fuselage(m, P, [(4.9, 0.4, 0.45, -0.45), (4.0, 0.52, 0.6, -0.62), (2.0, 0.55, 0.62, -0.7), (0.0, 0.55, 0.62, -0.7),
                    (-2.0, 0.42, 0.55, -0.55), (-4.2, 0.18, 0.45, -0.3), (-4.9, 0.1, 0.35, -0.15)], color=P["top"])
    m.cyl_x("spinner base", 0.42, 0.45, 0.2, [4.95, 0.0, 0], P["accent"], "paint", sides=18)
    prop(m, "propeller", 5.1, 0.0, 0, 1.65, 4, spinner_c=P["accent"])
    m.add("bubble canopy", "sphere", [0.55], [0.6, 0.72, 0], "#4a6f88", "glass", scale=[2.4, 0.9, 0.8])
    m.box("canopy frame", [0.04, 0.4, 0.8], [1.7, 0.85, 0], P["dark"], "paint")
    m.hull("belly scoop", [(x, y, z) for x in (0.5, -2.2) for y in (-0.65, -1.15) for z in (-0.35, 0.35)] + [(0.8, -0.7, -0.3), (0.8, -0.7, 0.3)], P["top"])
    m.box("scoop mouth", [0.05, 0.4, 0.6], [0.52, -0.9, 0], "#151718", "matte")
    for k in range(3):
        m.box(f"exhaust stub L{k}", [0.2, 0.1, 0.12], [3.6 - k * 0.25, 0.2, -0.52], "#5a4a3c", "metal")
        m.box(f"exhaust stub R{k}", [0.2, 0.1, 0.12], [3.6 - k * 0.25, 0.2, 0.52], "#5a4a3c", "metal")
    m.box("anti-glare panel", [2.2, 0.03, 0.5], [3.0, 0.62, 0], "#202326", "matte")
    for sd, side in ((-1, "L"), (1, "R")):
        wing_panel(m, f"wing {side}", P, (1.9, -0.6, sd * 0.4, -0.5, 0.36), (0.6, -0.4, sd * 5.65, -0.25, 0.1), P["top"])
        control_surface(m, f"aileron {side}", f"aileron {side}", P, (-0.38, -0.25, sd * 3.3), (-0.4, -0.22, sd * 5.4), 0.35, P["light"], phase=0 if sd < 0 else math.pi)
        control_surface(m, f"flap {side}", f"flap {side}", P, (-0.58, -0.45, sd * 0.6), (-0.42, -0.3, sd * 3.2), 0.4, P["light"], amount=0.1, speed=0.6)
        insignia(m, 0.2, -0.2, sd * 3.6, 0.45)
        for j in range(3):
            m.cyl_x(f"wing gun {side}{j}", 0.025, 0.025, 0.6, [1.6, -0.42, sd * (1.9 + j * 0.25)], DARK_STEEL)
        m.add(f"nav light {side}", "sphere", [0.05], [0.5, -0.25, sd * 5.68], "#ff3b2f" if sd < 0 else "#3bff6a", "glow")
        gear_leg(m, f"main gear {side}", 0.6, -0.5, sd * 1.7, 1.45, 0.35, [1, 0, 0], -sd * 1.57, P["under"])
        wing_panel(m, f"tailplane root {side}", P, (-3.8, -4.4, sd * 0.2, 0.05, 0.1), (-4.1, -4.5, sd * 2.1, 0.05, 0.05), P["top"])
        control_surface(m, f"tailplane {side}", f"tailplane elevator {side}", P, (-4.45, 0.05, sd * 0.25), (-4.5, 0.05, sd * 2.05), 0.35, P["light"], amount=0.2, speed=0.8)
    m.hull("tail fin", [(-3.3, 0.4, -0.06), (-3.3, 0.4, 0.06), (-4.8, 0.3, -0.05), (-4.8, 0.3, 0.05), (-4.3, 1.75, -0.03), (-4.3, 1.75, 0.03), (-4.85, 1.7, -0.03), (-4.85, 1.7, 0.03)], P["top"])
    control_surface(m, "rudder", "rudder", P, (-4.8, 0.35, 0), (-4.85, 1.65, 0), 0.4, P["accent"], amount=0.3, speed=1.0, vertical=True)
    gear_leg(m, "tail gear", -4.0, -0.25, 0, 0.35, 0.12, [0, 0, 1], 1.2, P["under"])
    lamp(m, "tail beacon", [-4.85, 1.78, 0], rate=1.2, r=0.05)
    return m.save()


def rook():
    """A2b Rook: a twin-engined light bomber with a glazed nose (after the A-20)."""
    m = Model("Iron Tide Rook")
    P = OD_GREEN
    fuselage(m, P, [(7.3, 0.2, 0.25, -0.3), (6.6, 0.65, 0.65, -0.75), (4.5, 0.75, 0.85, -0.9), (1.0, 0.75, 0.9, -0.9),
                    (-2.5, 0.6, 0.75, -0.7), (-5.5, 0.3, 0.45, -0.35), (-7.3, 0.15, 0.3, -0.15)])
    m.hull("glass nose", [(x, y, z) for x, w in ((7.4, 0.15), (6.4, 0.6)) for y in (-0.6, 0.45) for z in (-w, w)], "#3f6a85", "glass")
    for k in range(4):
        m.box("nose frame", [0.03, 1.0, 1.2], [7.0 - k * 0.25, -0.05, 0], P["dark"], "paint")
    m.add("cockpit canopy", "sphere", [0.55], [4.6, 0.9, 0], "#3f6a85", "glass", scale=[1.8, 0.75, 0.9])
    m.add("dorsal gunner", "sphere", [0.5], [-1.5, 0.8, 0], "#3f6a85", "glass", scale=[1.5, 0.7, 0.9])
    m.cyl_x("dorsal guns", 0.025, 0.025, 1.1, [-2.6, 1.0, 0], DARK_STEEL)
    for sd, side in ((-1, "L"), (1, "R")):
        wing_panel(m, f"wing {side}", P, (2.4, -0.9, sd * 0.6, 0.0, 0.42), (0.4, -0.7, sd * 9.3, 0.25, 0.12), P["top"])
        control_surface(m, f"aileron {side}", f"aileron {side}", P, (-0.75, 0.22, sd * 5.8), (-0.72, 0.26, sd * 9.0), 0.5, P["light"], phase=0 if sd < 0 else math.pi)
        control_surface(m, f"flap {side}", f"flap {side}", P, (-0.88, 0.05, sd * 0.9), (-0.82, 0.17, sd * 5.6), 0.55, P["light"], amount=0.1, speed=0.6)
        insignia(m, 0.6, 0.32, sd * 7.0, 0.6)
        z = sd * 3.1
        m.add(f"engine nacelle {side}", "capsule", [0.6, 3.2], [0.4, -0.1, z], P["top"], "paint", rot=[0, 0, 90])
        m.cyl_x(f"engine cowling {side}", 0.65, 0.7, 1.0, [2.6, -0.1, z], P["dark"], "paint", sides=18)
        prop(m, f"propeller {side}", 3.25, -0.1, z, 1.6, 3)
        gear_leg(m, f"main gear {side}", 0.8, -0.6, z, 1.6, 0.45, [0, 0, 1], 1.6, P["under"])
        m.add(f"nav light {side}", "sphere", [0.06], [0.0, 0.27, sd * 9.35], "#ff3b2f" if sd < 0 else "#3bff6a", "glow")
        wing_panel(m, f"tailplane root {side}", P, (-5.6, -6.6, sd * 0.25, 0.3, 0.15), (-6.0, -6.7, sd * 3.2, 0.35, 0.06), P["top"])
        control_surface(m, f"tailplane {side}", f"tailplane elevator {side}", P, (-6.65, 0.32, sd * 0.3), (-6.7, 0.36, sd * 3.1), 0.45, P["light"], amount=0.18, speed=0.8)
    m.hull("tail fin", [(-4.8, 0.4, -0.08), (-4.8, 0.4, 0.08), (-7.2, 0.3, -0.06), (-7.2, 0.3, 0.06), (-6.6, 2.9, -0.04), (-6.6, 2.9, 0.04), (-7.3, 2.85, -0.04), (-7.3, 2.85, 0.04)], P["top"])
    control_surface(m, "rudder", "rudder", P, (-7.25, 0.35, 0), (-7.3, 2.8, 0), 0.5, P["light"], amount=0.25, speed=0.9, vertical=True)
    gear_leg(m, "nose gear", 5.6, -0.7, 0, 1.5, 0.3, [0, 0, 1], -1.57, P["under"])
    for k in range(3):
        m.box("bomb bay seam", [0.03, 0.02, 1.0], [2.0 - k * 0.7, -0.9, 0], P["dark"], "paint")
    lamp(m, "tail beacon", [-7.3, 2.95, 0], rate=1.2, r=0.06)
    return m.save()


# ---------------------------------------------------------------- extra tree seeds
def tree_seeds():
    """Two more variants of each tree species: the same builders with other random seeds and a little size change."""
    import random as _r
    orig_random = build_trees.random.Random
    out = []
    for seed in (2, 3):
        build_trees.random.Random = lambda s, _seed=seed, _orig=orig_random: _orig(s * 101 + _seed)
        for f, base in ((build_trees.rainforest_giant, "Rainforest"), (build_trees.broadleaf, "Broadleaf"), (build_trees.palm, "Palm"),
                        (build_trees.conifer, "Conifer"), (build_trees.shrub, "Shrub"), (build_trees.glow_willow, "Glow Willow")):
            orig_init = Model.__init__

            def init(self, name, _seed=seed, _base=base, _orig=orig_init):
                _orig(self, f"Iron Tide Tree {_base} {_seed}")
            Model.__init__ = init
            try:
                data = f()
            finally:
                Model.__init__ = orig_init
            # a different build as well as different lumps: wider/shorter for seed 2, slimmer/taller for seed 3
            kx, ky = (1.15, 0.88) if seed == 2 else (0.88, 1.14)
            for p in data["parts"]:
                p["position"] = [round(p["position"][0] * kx, 4), round(p["position"][1] * ky, 4), round(p["position"][2] * kx, 4)]
                if "points" in p:
                    p["points"] = [[round(q[0] * kx, 4), round(q[1] * ky, 4), round(q[2] * kx, 4)] for q in p["points"]]
                if "points" in p:
                    continue
                rot = p.get("rotation", [0, 0, 0])
                sc = p.get("scale", [1, 1, 1])
                if abs(rot[0]) < 1e-6 and abs(rot[2]) < 1e-6:      # upright or only turned about Y: stretch along its own axes
                    p["scale"] = [round(sc[0] * kx, 4), round(sc[1] * ky, 4), round(sc[2] * kx, 4)]
                else:                                              # tilted limbs: an even size change so they still meet
                    k = (kx + ky) / 2
                    p["scale"] = [round(v * k, 4) for v in sc]
            import json as _j, os as _o
            with open(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), data["name"].lower().replace(" ", "-") + ".json"), "w") as fh:
                _j.dump(data, fh, separators=(",", ":"))
            out.append(data)
    build_trees.random.Random = orig_random
    return out


if __name__ == "__main__":
    for f in (viper, hornet_dd, warden, anvil, hornet_aa, ironhorse, kestrel, rook):
        f()
    tree_seeds()
