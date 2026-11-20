"""Iron Tide trees: small part counts (drawn thousands at a time), no moving groups (the game sways them in its shader).
Base of the trunk at y=0, centred on x=0,z=0, real sizes in metres. Bark is "matte"; leaf parts are named
leaf / crown / canopy / frond, wood parts trunk / branch / root. Only the small glowing bits use "glow".

    python3 build_trees.py
"""
import math
import random
from build_iron_tide import Model


def blob(m, name, c, r, color, rnd, n=14, squash=1.0, material="matte"):
    """A lumpy leaf mass: the hull of points scattered on a squashed sphere."""
    pts = []
    for k in range(n):
        u, v = rnd.random(), rnd.random()
        th, ph = 2 * math.pi * u, math.acos(2 * v - 1)
        k_ = 0.8 + 0.35 * rnd.random()
        pts.append((c[0] + r * k_ * math.sin(ph) * math.cos(th), c[1] + r * squash * k_ * math.cos(ph), c[2] + r * k_ * math.sin(ph) * math.sin(th)))
    m.hull(name, pts, color, material)


def limb(m, name, a, b, r0, r1, color, sides=7):
    """A tapered cylinder from point a to point b."""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz)
    # rotate the Y axis onto (dx,dy,dz): tilt about Z then turn about Y (Euler XYZ: x=0, y=yaw, z=-tilt)
    tilt = math.degrees(math.acos(max(-1, min(1, dy / ln))))
    yaw = math.degrees(math.atan2(-dz, dx))
    m.add(name, "cylinder", [r1, r0, ln], [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2], color, "matte", rot=[0, yaw, -tilt], sides=sides)


def rainforest_giant():
    m = Model("Iron Tide Tree Rainforest")
    rnd = random.Random(1)
    bark, bark2 = "#6b5a46", "#4e4033"
    H = 48.0
    limb(m, "trunk lower", (0, 0, 0), (0, H * 0.45, 0), 1.6, 1.25, bark, 10)
    limb(m, "trunk upper", (0, H * 0.45, 0), (0.4, H * 0.78, 0.2), 1.25, 0.8, bark, 10)
    for k in range(6):  # plank buttress roots: thin tall fins
        a = k * math.pi / 3 + 0.3
        c, s = math.cos(a), math.sin(a)
        m.hull(f"root buttress {k}", [(0, 0, 0), (c * 5.5, 0, s * 5.5), (c * 1.2, 7.5, s * 1.2), (c * 0.6, 0, s * 0.6),
                                      (c * 5.5 - s * 0.25, 0, s * 5.5 + c * 0.25), (c * 1.2 - s * 0.25, 7.5, s * 1.2 + c * 0.25)], bark2)
    tops = []
    for k in range(5):  # great limbs carrying the layered crown
        a = k * 2 * math.pi / 5 + 0.5
        end = (math.cos(a) * 9, H * 0.86 + rnd.random() * 3, math.sin(a) * 9)
        limb(m, f"branch {k}", (0.3, H * 0.72, 0.1), end, 0.6, 0.25, bark)
        tops.append(end)
    greens = ["#3f6b2a", "#4a7a30", "#365e25", "#527f36"]
    for k, e in enumerate(tops):
        blob(m, f"crown layer {k}", (e[0] * 1.3, e[1] + 1.0, e[2] * 1.3), 9.0, greens[k % 4], rnd, squash=0.45)
    blob(m, "crown top", (0.4, H * 0.95, 0.2), 10.5, greens[1], rnd, squash=0.5)
    blob(m, "canopy lower", (0.2, H * 0.8, 0), 13.0, greens[2], rnd, squash=0.35)
    for k in range(6):  # hanging lianas
        a = rnd.random() * 2 * math.pi
        x, z = math.cos(a) * 7, math.sin(a) * 7
        limb(m, f"branch liana {k}", (x, H * 0.82, z), (x * 1.05, H * 0.82 - 10 - rnd.random() * 8, z * 1.05), 0.08, 0.05, "#4c5a30", 5)
    return m.save()


def broadleaf():
    m = Model("Iron Tide Tree Broadleaf")
    rnd = random.Random(2)
    bark = "#5f513f"
    limb(m, "trunk", (0, 0, 0), (0.2, 6.0, 0), 0.45, 0.32, bark, 9)
    ends = []
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        e = (math.cos(a) * 3.2, 9.0 + rnd.random() * 1.5, math.sin(a) * 3.2)
        limb(m, f"branch {k}", (0.2, 5.5, 0), e, 0.25, 0.12, bark, 7)
        ends.append(e)
    for k in range(3):
        a = rnd.random() * 2 * math.pi
        x, z = math.cos(a) * 0.4, math.sin(a) * 0.4
        m.add(f"root flare {k}", "cone", [0.5, 1.2], [x, 0.5, z], bark, "matte", rot=[math.cos(a) * 20, 0, -math.sin(a) * 20], sides=6)
    greens = ["#4f7d31", "#5b8a37", "#456f2b"]
    for k, e in enumerate(ends):
        blob(m, f"crown {k}", e, 3.2, greens[k % 3], rnd, squash=0.75)
    blob(m, "crown top", (0.2, 11.2, 0), 3.6, greens[1], rnd, squash=0.7)
    blob(m, "crown core", (0.2, 9.5, 0), 3.8, greens[2], rnd, squash=0.65)
    return m.save()


def palm():
    m = Model("Iron Tide Tree Palm")
    rnd = random.Random(3)
    bark = "#8a7a5c"
    pts, x = [], 0.0
    for k in range(7):  # a curving, ringed stem
        y0, y1 = k * 1.6, (k + 1) * 1.6
        x0, x1 = 0.06 * k * k, 0.06 * (k + 1) * (k + 1)
        limb(m, f"trunk ring {k}", (x0, y0, 0), (x1, y1, 0), 0.3 - k * 0.02, 0.27 - k * 0.02, bark if k % 2 else "#7a6b50", 8)
    top = (0.06 * 49, 11.2, 0)
    m.add("crown heart", "sphere", [0.45], [top[0], top[1], top[2]], "#5d6b2f", "matte")
    for k in range(9):  # long arching fronds, each two flat hull panels
        a = k * 2 * math.pi / 9 + rnd.random() * 0.2
        c, s = math.cos(a), math.sin(a)
        mid = (top[0] + c * 2.6, top[1] + 0.8, top[2] + s * 2.6)
        tip = (top[0] + c * 5.0, top[1] - 1.2, top[2] + s * 5.0)
        w = 0.7
        for j, (p, q) in enumerate(((top, mid), (mid, tip))):
            m.hull(f"frond {k}.{j}", [p, q, (p[0] - s * w * (1 - j * 0.5), p[1] - 0.05, p[2] + c * w * (1 - j * 0.5)), (p[0] + s * w * (1 - j * 0.5), p[1] - 0.05, p[2] - c * w * (1 - j * 0.5)),
                                    (q[0] - s * w * 0.6 * (1 - j), q[1] - 0.05, q[2] + c * w * 0.6 * (1 - j)), (q[0] + s * w * 0.6 * (1 - j), q[1] - 0.05, q[2] - c * w * 0.6 * (1 - j))],
                   "#4f8a35" if k % 2 else "#5c9a3c")
    for k in range(3):
        m.add(f"coconut {k}", "sphere", [0.18], [top[0] + math.cos(k * 2.1) * 0.35, top[1] - 0.4, math.sin(k * 2.1) * 0.35], "#6a5531", "matte")
    return m.save()


def conifer():
    m = Model("Iron Tide Tree Conifer")
    bark = "#5a4434"
    limb(m, "trunk", (0, 0, 0), (0, 15.5, 0), 0.4, 0.08, bark, 8)
    greens = ["#2f4f2e", "#34573a", "#2a4728"]
    for k in range(6):  # stacked drooping tiers, each a cone, snow-dusted at the edge on the upper side
        y = 2.2 + k * 2.1
        r = 3.6 - k * 0.52
        m.add(f"canopy tier {k}", "cone", [r, 3.0], [0, y + 1.3, 0], greens[k % 3], "matte", sides=9, rot=[0, k * 17, 0])
    m.add("crown tip", "cone", [0.6, 1.8], [0, 16.0, 0], greens[0], "matte", sides=7)
    m.add("root flare", "cone", [0.65, 0.9], [0, 0.4, 0], bark, "matte", sides=7)
    return m.save()


def shrub():
    m = Model("Iron Tide Tree Shrub")
    rnd = random.Random(5)
    for k in range(3):
        a = k * 2.1
        limb(m, f"branch stem {k}", (0, 0, 0), (math.cos(a) * 0.5, 0.9, math.sin(a) * 0.5), 0.07, 0.04, "#5a4a36", 5)
    greens = ["#4c7a32", "#5a8a3a", "#42692b", "#567f34"]
    for k in range(5):
        a = k * 2 * math.pi / 5 + rnd.random() * 0.5
        r = 0.7 + rnd.random() * 0.4
        blob(m, f"leaf clump {k}", (math.cos(a) * 0.6, 0.8 + rnd.random() * 0.5, math.sin(a) * 0.6), r, greens[k % 4], rnd, n=11, squash=0.8)
    blob(m, "leaf clump top", (0, 1.4, 0), 0.8, greens[1], rnd, n=11, squash=0.8)
    return m.save()


def glow_willow():
    """An original bioluminescent tree: a twisting pale trunk, a domed violet-green canopy, and drooping tendrils with
    glowing beads along them (only the beads glow)."""
    m = Model("Iron Tide Tree Glow Willow")
    rnd = random.Random(6)
    bark = "#5d5866"
    prev = (0, 0, 0)
    for k in range(5):  # a slowly twisting trunk
        nxt = (math.sin(k * 0.9) * 0.8, (k + 1) * 3.2, math.cos(k * 0.9) * 0.5 - 0.5)
        limb(m, f"trunk segment {k}", prev, nxt, 1.0 - k * 0.12, 0.88 - k * 0.12, bark, 9)
        prev = nxt
    for k in range(4):
        a = k * math.pi / 2 + 0.6
        m.hull(f"root fin {k}", [(0, 0, 0), (math.cos(a) * 3.2, 0, math.sin(a) * 3.2), (math.cos(a) * 0.6, 3.5, math.sin(a) * 0.6),
                                 (math.cos(a) * 3.2 - math.sin(a) * 0.2, 0, math.sin(a) * 3.2 + math.cos(a) * 0.2), (0.2, 0, 0.2)], bark)
    top = prev
    canopy_colors = ["#3d6a4a", "#46705a", "#3a5f52"]
    for k in range(4):
        a = k * math.pi / 2
        blob(m, f"canopy dome {k}", (top[0] + math.cos(a) * 3.5, top[1] + 1.2, top[2] + math.sin(a) * 3.5), 4.2, canopy_colors[k % 3], rnd, squash=0.45)
    blob(m, "canopy crown", (top[0], top[1] + 2.4, top[2]), 4.6, canopy_colors[1], rnd, squash=0.5)
    for k in range(8):  # drooping tendrils, a glowing bead at each tip and one halfway
        a = k * 2 * math.pi / 8 + 0.2
        r = 6.0 + rnd.random() * 1.5
        x, z = top[0] + math.cos(a) * r, top[2] + math.sin(a) * r
        drop = 7 + rnd.random() * 4
        y0 = top[1] + 0.5
        limb(m, f"branch tendril {k}", (x, y0, z), (x * 1.04, y0 - drop, z * 1.04), 0.07, 0.04, "#4a6a5c", 5)
        m.add(f"glow bead {k}", "sphere", [0.22], [x * 1.04, y0 - drop - 0.1, z * 1.04], "#7ff0e0" if k % 2 else "#b48cff", "glow")
        m.add(f"glow bead mid {k}", "sphere", [0.13], [x * 1.02, y0 - drop * 0.5, z * 1.02], "#7ff0e0", "glow")
    for k in range(5):  # small glowing spots on the trunk
        m.add(f"glow spot trunk {k}", "sphere", [0.12], [math.sin(k * 0.9) * 0.6 + 0.85, 1.5 + k * 2.8, math.cos(k * 0.9) * 0.4 - 0.5], "#7ff0e0", "glow", scale=[0.4, 1, 1])
    return m.save()


if __name__ == "__main__":
    for f in (rainforest_giant, broadleaf, palm, conifer, shrub, glow_willow):
        f()
