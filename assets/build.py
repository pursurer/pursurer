"""Build the profile banner and project cards as SVG.

Run from the repository root: python3 assets/build.py

The banner is a koi pond seen from above, drawn in character cells like the
koi pond on my n8n course page, with its koi at the size of that page's
opening screen. Each koi is stepped the way the page steps it: the head
wanders and steers, a chain of spine nodes trails it, so the body curves
through every turn, and a body wave runs down it. Every cell is sampled
against the spine, classified as body, fin, eye, ridge or barbel, coloured by
the fish's markings and shaded by a light from the upper left. The koi keep
to the middle of the pond, each on a loop of its own through one spot. Once a
cycle a handful of pellets lands on that spot, the koi rush it, eat it and
circle for more, and then the course page's cat paw pats the water and they
scatter. An SVG image cannot run scripts, so each koi's cycle is drawn as
frames in <defs>, fifteen a second, and one SMIL animation per koi shows them
in turn; every change falls on one shared beat and there are no filters, so
GitHub can draw the banner smoothly. A tile and its glyph are one cell-sized
pattern, so a frame is a few paths. The title sits top left as an even dot
matrix, the way the course page draws its small masthead (its font is
rasterised with Pillow). Reduced-motion users get a still pond. The live,
click-to-feed pond is pond/index.html.
"""

from math import atan2, ceil, cos, exp, floor, hypot, inf, pi, sin, sqrt
from pathlib import Path

OUT = Path(__file__).resolve().parent

SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
# The title's font is rasterised at build time; the course page used Noto Serif Display, then Didot.
TITLE_FONTS = {"georgia": ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", 0),
               "didot": ("/System/Library/Fonts/Supplemental/Didot.ttc", 2)}
GLINT_SPEED, GLINT_HALF = 0.16, 0.022       # share of the word the glint crosses per second; half its width
GLINT_PERIOD = 1.9 / GLINT_SPEED
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

INK = "#f7f1e3"
AMBER = "#e9a23b"

# "normal" is the course page's own pond; "lake" is lake water with the page's dark-mode koi.
PONDS = {
    "normal": {"water": "#d6cebf", "accent": "#9e3214", "light": "#f7f2e8", "black": "#2b2723",
               "ink": "#1c1a17", "dark": False},
    "lake": {"water": "#2d6a68", "accent": "#e8784f", "light": "#ece6da", "black": "#3a3632",
             "ink": "#f3efe4", "dark": True},
    # the course page's own lake-blue trial, dark scheme
    "deep": {"water": "#0d2a32", "accent": "#e8784f", "light": "#ece6da", "black": "#3a3632",
             "ink": "#f3efe4", "dark": True},
}
# Shadow on the pond floor: colour as a share of the water, and its strength.
SHADOW = {"normal": (0.55, 0.22), "lake": (0.35, 0.36), "deep": (0.3, 0.55)}
POND = "deep"
# Koi colours to compare: red, white and black skin. "course" keeps the course page's own.
KOI_COLOURS = {
    "course": None,
    "vermilion": {"red": (214, 58, 36), "white": (246, 242, 234), "black": (24, 22, 20)},
    "gold": {"red": (230, 164, 52), "white": (222, 228, 232), "black": (98, 74, 42)},
    "sakura": {"red": (238, 132, 128), "white": (250, 240, 228), "black": (66, 60, 70)},
}
KOI = "course"

N = 10                      # spine nodes per koi
RAMP = " .:-=+*#%@"         # sparse glyphs on lit skin, dense ones in shadow
SUB = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
FRAME = 1 / 15              # seconds per drawn frame (15 a second): koi, pellets, rings and the title's glint
SIM_DT = FRAME / 8          # the course page steps its pond at screen rate; this steps 8 times a frame
LIT_STEP = 0.2              # skin shading in three steps keeps each frame to a few paths
BEND = 0.42                 # no joint of a koi's chain bends further than this (radians)
BODY_END = 0.76
M32 = 0xFFFFFFFF


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def num(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


# ── small maths, matching the course page ──

def clamp(v, a, b):
    return a if v < a else b if v > b else v


def sstep(a, b, x):
    k = clamp((x - a) / (b - a), 0, 1)
    return k * k * (3 - 2 * k)


def lerp(a, b, e):
    return a + (b - a) * e


def imul(a, b):
    return (a & M32) * (b & M32) & M32


def h2(a, b):
    x = imul(a, 0x27D4EB2D) ^ imul(b, 0x165667B1)
    x = imul(x ^ (x >> 15), 0x85EBCA6B)
    x ^= x >> 13
    x = imul(x, 0xC2B2AE35)
    return (x ^ (x >> 16)) / 4294967296


def noise(x, y, seed):
    xi, yi = floor(x), floor(y)
    u, v = sstep(0, 1, x - xi), sstep(0, 1, y - yi)
    a, b = h2(xi + seed * 131, yi), h2(xi + 1 + seed * 131, yi)
    c, d = h2(xi + seed * 131, yi + 1), h2(xi + 1 + seed * 131, yi + 1)
    return lerp(lerp(a, b, u), lerp(c, d, u), v)


def rgb(hex_):
    n = int(hex_.lstrip("#"), 16)
    return (n >> 16, (n >> 8) & 255, n & 255)


def mix(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def mul(c, k):
    return tuple(v * k for v in c)


def hexc(c):
    return "#" + "".join(f"{clamp(int(v), 0, 255):02x}" for v in c)


def palette(name, koi=None):
    p = PONDS[name]
    dark, water, light, black, accent = p["dark"], rgb(p["water"]), rgb(p["light"]), rgb(p["black"]), rgb(p["accent"])
    skin = KOI_COLOURS[koi or KOI]
    P = {
        "dark": dark, "water": water, "ink": p["ink"],
        "white": light if dark else mix(light, (255, 255, 255), 0.4),
        "red": mix(accent, (232, 92, 52), 0.5) if dark else mix(accent, (214, 72, 34), 0.7),
        "black": mix(black, (0, 0, 0), 0.2) if dark else black,
        "eye": (16, 15, 14) if dark else (30, 27, 24),
        "fin": mix(light, water, 0.25) if dark else mix(light, water, 0.15),
        "dot": light if dark else rgb(p["ink"]),
        "shadow": mul(water, SHADOW[name][0]), "shade": SHADOW[name][1],
        "food": (212, 160, 92) if dark else (150, 98, 46),
        # the course page's title runs white to grey; grey is mixed with the water here so it stays readable
        "title": ((255, 255, 255), mix((255, 255, 255), water, 0.42)) if dark else ((0, 0, 0), (102, 102, 102)),
        "glint": accent,
    }
    if skin:
        P.update(red=skin["red"], white=skin["white"], black=skin["black"], dot=skin["white"] if dark else P["dot"],
                 fin=mix(skin["white"], water, 0.25) if dark else mix(skin["white"], water, 0.15))
    return P


# ── koi body, as fractions of length: s runs from snout (0) to tail tip (1) ──

def half_w(s):
    if s < 0.1:
        return 0.118 * sin(s / 0.1 * pi / 2) ** 0.6
    if s < 0.3:
        return 0.118 + 0.02 * sstep(0.1, 0.3, s)
    return 0.03 + 0.108 * (1 - sstep(0.3, BODY_END, s))


def tail_w(s):
    return 0.028 + 0.165 * sstep(0.72, 1, s) ** 0.85


def fin(s, a, root_s, angle, reach, width):
    """A fin: an ellipse leaning back from a root on the body's edge."""
    ra, ca, sa = half_w(root_s) * 0.85, cos(angle), sin(angle)
    ds, da = s - root_s, a - ra
    along, perp = ds * ca + da * sa - reach, -ds * sa + da * ca
    if (along / reach) ** 2 + (perp / width) ** 2 > 1:
        return None
    return 2, 1, ds, da


def classify(s, a, past, flare, ahead, lateral):
    """(kind, across, rs, ra) or None. Kinds: 1 body, 2 fin, 4 ridge, 5 barbel; rasterise() places the eyes (3)."""
    if ahead > 0:
        if ahead < 0.05 and abs(lateral - (0.042 + ahead * 0.75)) < 0.015:
            return 5, 1, 1, 0
        return None
    w = half_w(s)
    if s <= BODY_END and a <= w:
        across = a / w if w else 0
        kind = 4 if 0.3 < s < 0.6 and across < 0.13 else 1
        return kind, across, 1, 0
    if s > 0.7 and past <= 0:
        tw = tail_w(s) * flare
        if a <= tw and s <= 0.88 + 0.12 * (a / tw):
            return 2, 1, 1, (a / tw) * 0.8
    return fin(s, a, 0.2, 0.9 + 0.45 * (flare - 1), 0.07 * flare, 0.038) or fin(s, a, 0.47, 0.75, 0.038, 0.019)


def markings(variety, seed):
    """Kohaku: red saddles. Sanke: plus black spots. Tancho: a red crown only."""
    def r(j):
        return h2(seed, j)
    if variety == "tancho":
        return {"red": [(0.1, 0, 0.052, 0.06)], "black": []}
    red = []
    if r(1) < 0.7:
        red.append((0.09, (r(2) - 0.5) * 0.03, 0.05 + r(3) * 0.03, 0.1))
    n = 2 + int(r(4) * 2)
    span = 0.42 / n
    for j in range(n):
        red.append((0.25 + span * (j + 0.5) + (r(10 + j) - 0.5) * span * 0.35, (r(20 + j) - 0.5) * 0.05,
                    span * (0.42 + r(30 + j) * 0.14), 0.09 + r(40 + j) * 0.05))
    black = []
    if variety == "sanke":
        for j in range(4 + int(r(50) * 3)):
            black.append((0.25 + r(60 + j) * 0.42, (r(70 + j) - 0.5) * 0.15, 0.021, 0.025))
    return {"red": red, "black": black}


def skin(marks, seed, s, vn, across):
    if across > 0.9 or s > 0.74:
        return 0
    wob = (noise(s * 13 + seed, vn * 28, seed) - 0.5) * 0.65

    def inside(m):
        return ((s - m[0]) / m[2]) ** 2 + ((vn - m[1]) / m[3]) ** 2 < 1 + wob
    if any(inside(m) for m in marks["black"]):
        return 2
    if any(inside(m) for m in marks["red"]):
        return 1
    return 0


def line_glyph(dx, dy):
    d = hypot(dx, dy) or 1
    return "-" if abs(dy) < 0.38 * d else "|" if abs(dx) < 0.38 * d else "\\" if dx * dy > 0 else "/"


# ── the koi crossing the pond, stepped like the course page ──

def wrap(a):
    return (a + pi) % (2 * pi) - pi


GULP = 0.6                  # seconds a koi takes to swallow a pellet before it can take the next
SETTLE = 4                  # seconds at the end of the cycle over which the koi ease into the calm cycle
PAW_WAIT = 1.4              # seconds after the last pellet goes before the cat's paw pats the spot
PAST = 1.15                 # koi lengths past the edge a koi swims before it comes back in at the other side
PAUSE = (12, 6)             # over this many seconds from the pellets landing a feeding koi's crossing runs this many late
BAND = (0.1, 0.9)           # the koi turn back toward the middle above and below these shares of the height


def swim(fish, feed, w, h):
    """The koi of a banner swimming together through one feed cycle, the way the course page's pond swims them.

    Each koi swims across the pond, left or right, wanders as it goes, turns back
    toward the middle near the top and bottom, never tilts more than a radian off
    level, and once it is out past one side comes back in at the other, as on the
    course page. Here it also crosses exactly once a cycle and keeps near its lane's
    height, so the cycle can repeat: it speeds up when it is behind time and eases
    off when it is ahead. A koi that feeds has its time run late (PAUSE) while it is
    at the pellets, and swims faster the rest of the cycle. The head leads and the chain trails it, no joint bending
    more than BEND, so the body curves through every turn. The pond is first stepped
    this way, cycle after cycle, until a cycle ends where it began: the calm cycle.

    The cycle as drawn starts from the calm one's start. Once the pellets land, every
    koi that `feeds` goes for them after its own `notice` delay: it darts over, slows down near them,
    and the koi pick the pellets off between them, each taking the one nearest its snout,
    one per GULP. Fed, they drift by the spot until the cat's paw pats it, PAW_WAIT after
    the last pellet goes (see paw_pose): as on the course page, every koi in reach darts
    away, here on toward the side its lane goes (turning along the bank rather than out
    of the banner), so none circles back. Then each swims on across, catching up with
    its time, and the first time it is out past the side together with its calm self,
    they change places; one that never is eases into the calm cycle over the last
    SETTLE seconds, so the loop has no seam. Returns each
    koi's frames, one every FRAME, as (time, spine, flare_l, flare_r), when each pellet was
    eaten, when the paw comes, and how far (px) a koi that had to ease in still was from the
    calm cycle when it began to."""
    C, paw = feed["cycle"], feed["paw"]
    steps, every = round(C / SIM_DT), round(FRAME / SIM_DT)
    # The course page's beat and wander, at whole numbers per cycle so they repeat; the body
    # wave's base rate is nudged so the wave (and the sculling, at half its rate) repeat too.
    om = 2 * pi / C
    wave = round((2.6 + 2.5) * C / (4 * pi)) * 2 * om - 2.5
    y_lo, y_hi = h * BAND[0], h * BAND[1]
    # Where the paw's toes hit the water, whenever it comes.
    pose = paw_pose(paw, paw["born"] + DIP)
    tip = tip_of(pose) - 3
    hit = (pose["cx"] + pose["ux"] * tip * pose["k"], pose["cy"] + pose["uy"] * tip * pose["k"])
    def late(f):
        """A koi's time on its crossing: a feeding koi's runs late while it is at the pellets."""
        if not f.get("feeds"):
            return lambda t: t
        return lambda t: t - PAUSE[1] * sstep(feed["land"], feed["land"] + PAUSE[0], t)
    koi = []
    for f in fish:
        L, (lane_y, way, at) = f["L"], (f["lane"][q] for q in ("y", "dir", "pass"))
        span, due = w + 2 * PAST * L, late(f)
        v = span / due(C)
        # its head at t = 0, so it passes the spot's x at `pass` seconds
        x = (feed["at"][0] - way * v * due(at) + PAST * L) % span - PAST * L
        a, seg = (0 if way > 0 else pi), L / (N - 1)
        koi.append({"f": f, "span": span, "way": way, "lane": lane_y, "x0": x, "v": v, "due": due,
                    "x": x, "y": lane_y, "a": a, "turn": 0.0, "phase": h2(f["seed"], 5) * 2 * pi,
                    "nodes": [(x - cos(a) * seg * j, lane_y - sin(a) * seg * j) for j in range(N)]})
    state = ("x", "y", "a", "turn", "phase")

    def across(k, dx):
        """dx between two points of a koi's crossing, the shorter way round."""
        return (dx + k["span"] / 2) % k["span"] - k["span"] / 2

    def cycle(events):
        """Steps the pond through one cycle, from the koi as they are; returns when the pellets went and the paw came."""
        left, eaten, born, dip = dict(enumerate(feed["pellets"])) if events else {}, {}, inf, inf
        for k in koi:
            k.update(frames=[], gulp=0, flee=0.0, flee_a=0.0, off=False, busy=0)
        for i in range(steps):
            t = i * SIM_DT
            if events and t >= dip and born is not None:
                # The paw hits the water: dart away from it.
                reach = 280 * paw["k"]
                for k in koi:
                    d = hypot(k["x"] - hit[0], k["y"] - hit[1])
                    if d < reach:
                        # away from it, on toward the side its lane goes, so it need not turn back after
                        fa = atan2(k["y"] - hit[1], k["x"] - hit[0])
                        k["flee"], k["flee_a"] = max(k["flee"], 1 - d / reach * 0.7), fa if cos(fa) * k["way"] >= 0 else pi - fa
                paw_born, born = born, None
            for k in koi:
                f = k["f"]
                L, seed, x, y, a = f["L"], f["seed"], k["x"], k["y"], k["a"]
                beat = 0.5 + 0.5 * sin(2 * om * t + seed)
                # the course page's wander, and its band: turn back toward the middle near the top
                # and bottom, and never tilt more than a radian off level
                right = cos(a) > 0
                turn = sin(om * t + seed) * 0.32 + sin(3 * om * t + seed * 1.7) * 0.22
                if y < y_lo:
                    turn += 0.7 if right else -0.7
                if y > y_hi:
                    turn += -0.7 if right else 0.7
                tilt = wrap(a - (0 if right else pi))
                if abs(tilt) > 1.0:
                    turn -= 1.4 if tilt > 0 else -1.4
                goal = None
                if k["flee"] > 0.02:
                    fa = k["flee_a"]
                    if (y < h * 0.2 and sin(fa) < 0) or (y > h * 0.8 and sin(fa) > 0):
                        k["flee_a"] = fa = 0 if cos(fa) >= 0 else pi
                    k["turn"] = lerp(k["turn"], turn, min(1, SIM_DT * 2))
                    k["turn"] = lerp(k["turn"], clamp(wrap(fa - a) * 5, -4, 4), min(1, SIM_DT * 8 * k["flee"]))
                    speed = f["cruise"] * (1 + 2.6 * k["flee"])
                    k["flee"] *= exp(-1.3 * SIM_DT)
                elif left and f.get("feeds") and t >= feed["land"] + f.get("notice", 0):
                    j, (gx, gy) = min(left.items(), key=lambda kv: hypot(kv[1][0] - x, kv[1][1] - y))
                    dist = hypot(gx - x, gy - y)
                    if dist < L * 0.09 and t >= k["gulp"]:
                        eaten[j], k["gulp"] = t, t + GULP
                        del left[j]
                        if not left:
                            born = t + PAW_WAIT
                            dip = born + DIP
                    goal, k["off"] = (gx, gy), True
                    speed = f["cruise"] * lerp(0.5, 1.9, sstep(L * 0.15, L * 0.7, dist))
                elif events and feed["land"] < t < dip and k["off"]:
                    # fed, it drifts by the spot, slowly, nosing for more
                    k["turn"] = lerp(k["turn"], turn, min(1, SIM_DT * 2))
                    speed = f["cruise"] * 0.5
                else:
                    # its crossing: keep near its lane's height, and to time; back from a chase,
                    # it first turns the way its lane goes if it faces the other way
                    if cos(a) * k["way"] < 0:
                        turn += clamp(wrap((0 if k["way"] > 0 else pi) - a) * 2, -2.4, 2.4)
                    else:
                        # level out, toward its lane's height
                        turn += clamp((k["lane"] - y) / h * 3, -0.8, 0.8) * (1 if right else -1) - 0.9 * tilt
                    k["turn"] = lerp(k["turn"], turn, min(1, SIM_DT * 2))
                    ahead = across(k, k["way"] * (x - k["x0"]) - k["v"] * k["due"](t))
                    speed = k["v"] * clamp(1 - ahead / (L * 0.45), 0.5, 2.0)
                if events and (k["flee"] > 0.02 or goal or (k["off"] and t < dip)):
                    k["busy"] = t
                if goal:
                    d = wrap(atan2(goal[1] - y, goal[0] - x) - a)
                    k["turn"] = lerp(k["turn"], turn * 0.4 + clamp(d * 2.6, -2.4, 2.4), min(1, SIM_DT * 3))
                a += k["turn"] * SIM_DT
                speed *= 0.65 + 0.7 * beat
                x, y = x + cos(a) * speed * SIM_DT, y + sin(a) * speed * SIM_DT
                nodes, seg = k["nodes"], L / (N - 1)
                # out past one side, it comes back in at the other
                shift = -k["span"] if x > w + PAST * L else k["span"] if x < -PAST * L else 0
                if shift:
                    x += shift
                    nodes[:] = [(px + shift, py) for px, py in nodes]
                k["x"], k["y"], k["a"] = x, y, a
                nodes[0] = (x, y)
                bx, by = -cos(a), -sin(a)
                for j in range(1, N):
                    px, py = nodes[j - 1]
                    vx, vy = nodes[j][0] - px, nodes[j][1] - py
                    dd = hypot(vx, vy) or 1
                    vx, vy = vx / dd, vy / dd
                    bend = atan2(bx * vy - by * vx, bx * vx + by * vy)
                    if abs(bend) > BEND:
                        r = BEND if bend > 0 else -BEND
                        vx, vy = bx * cos(r) - by * sin(r), bx * sin(r) + by * cos(r)
                    nodes[j] = (px + vx * seg, py + vy * seg)
                    bx, by = vx, vy
                k["phase"] += SIM_DT * (wave + 5 * beat)
                if (i + 1) % every == 0:
                    sw = 0.25 + 0.9 * beat
                    spine = []
                    for n in range(N):
                        s = n / (N - 1)
                        ax, ay = nodes[max(0, n - 1)]
                        cx, cy = nodes[min(N - 1, n + 1)]
                        tl = hypot(ax - cx, ay - cy) or 1
                        tx, ty = (ax - cx) / tl, (ay - cy) / tl
                        off = L * 0.045 * (0.05 + 0.95 * s ** 2.2) * sw * sin(k["phase"] - s * 4.6)
                        spine.append((nodes[n][0] - ty * off, nodes[n][1] + tx * off))
                    bank, scull = clamp(k["turn"] * 0.5, -0.3, 0.3), 0.15 * (1 - beat) * sin(k["phase"] * 0.5)
                    k["frames"].append(((i + 1) // every % round(C / FRAME) * FRAME, spine, 1 + scull - bank, 1 - scull + bank))
        if events:
            assert not left and born is None, "the pellets are not all eaten in time for the paw"
            return eaten, paw_born

    def apart(k, p, q):
        return hypot(across(k, p[0] - q[0]), p[1] - q[1])
    # The calm cycle. The course page's turns at the band and the tilt limit are sudden, so it
    # settles only to within a few px; the last SETTLE seconds close that up too.
    for _ in range(12):
        start = [(dict((q, k[q]) for q in state), list(k["nodes"])) for k in koi]
        cycle(False)
        if max(apart(k, p, q) for k, (_, s) in zip(koi, start) for p, q in zip(k["nodes"], s)) < 0.1:
            break
    drift = max(apart(k, p, q) for k, (_, s) in zip(koi, start) for p, q in zip(k["nodes"], s))
    assert drift < 12, f"the calm cycle still drifts {drift:.1f} px a cycle"
    calm = []
    for k, (_, s) in zip(koi, start):
        off = [(across(k, q[0] - p[0]), q[1] - p[1]) for p, q in zip(k["nodes"], s)]
        calm.append([(t, [(x + u * ox, y + u * oy) for (x, y), (ox, oy) in zip(spine, off)], fl, fr)
                     for t, spine, fl, fr in sorted(k["frames"], key=lambda fr: fr[0])
                     for u in [1 if t == 0 else sstep(C - SETTLE, C, t)]])
    for k, (st, nodes) in zip(koi, start):
        k.update(st, nodes=list(nodes))
    eaten, born = cycle(True)
    busy = [sorted(k["frames"], key=lambda fr: fr[0]) for k in koi]
    # Once a koi is back on its crossing, it changes places with its calm self the first time
    # both are out past the side together, where no one sees it. A koi that never is eases
    # into the calm cycle over the last SETTLE seconds instead, moved across first if it has
    # come back in at the other side than its calm self. The loop has no seam either way.
    def hidden(spine, L):
        xs = [p[0] for p in spine]
        return max(xs) + L * 0.3 < 0 or min(xs) - L * 0.3 > w
    m, gap, loops = round((C - SETTLE) / FRAME), 0, []
    for k, frames, quiet in zip(koi, busy, calm):
        L = k["f"]["L"]
        swap = next((n for n in range(ceil(k["busy"] / FRAME) + 1, len(frames))
                     if hidden(frames[n][1], L) and hidden(quiet[n][1], L)), None)
        if swap:
            loops.append(quiet[:1] + frames[1:swap] + quiet[swap:])
            continue
        gap = max(gap, apart(k, frames[m][1][0], quiet[m][1][0]))
        out = []
        for (t, spine, fl, fr), (_, spine2, fl2, fr2) in zip(frames, quiet):
            u = 1 if t == 0 else sstep(C - SETTLE, C - 0.3, t)
            dx = spine2[0][0] + across(k, spine[0][0] - spine2[0][0]) - spine[0][0]
            out.append((t, [(lerp(p[0] + dx, q[0], u), lerp(p[1], q[1], u)) for p, q in zip(spine, spine2)],
                        lerp(fl, fl2, u), lerp(fr, fr2, u)))
        loops.append(out)
    return loops, eaten, born, gap


# ── the cat's paw, from the course page ──
#
# A cat paw fishes in the water. We look down on it, so only the back of the black paw
# shows; the pads face the water. The paw is one round little cylinder with four soft
# scallops at its tip. It shoots straight in from the nearer edge, dips its tip under
# the surface, curls its toes down and hooks the water back toward the cat in two quick
# tugs, flicks out with a spray of drops and shakes itself off as it leaves. The koi
# scatter, and a moment later the curious ones swim back to look.

DIP, PULL, FLICK, SHAKE, END = 0.24, 0.42, 0.72, 0.78, 1.25
DROP_LIFE = 1.2
# the leg's radius, the round hand's radius, and where the four toes sit around its tip (radians)
LEG, HAND, TOES = 8.4, 10, (-1.12, -0.38, 0.38, 1.12)
# Keyframes (time, value, ease into it): o eases out, i eases in, l is linear, anything else eases both ways.
EASE = {"o": lambda u: 1 - (1 - u) ** 2.2, "i": lambda u: u ** 2.2, "l": lambda u: u}


def track(a, keys):
    if a <= keys[0][0]:
        return keys[0][1]
    for j in range(1, len(keys)):
        t1, v1, *e = keys[j]
        if a > t1:
            continue
        t0, v0 = keys[j - 1][:2]
        u = (a - t0) / (t1 - t0)
        return v0 + (v1 - v0) * EASE.get(e[0] if e else None, lambda x: x * x * (3 - 2 * x))(u)
    return keys[-1][1]


# The whole catch, channel by channel (time in seconds): in a little past the spot, dip, curl, tug, tug, flick, away.
BACK = [(0, 70), (0.17, -4, "o"), (DIP, 0), (PULL, 0, "l"), (0.52, 13), (0.57, 12), (0.68, 27), (FLICK, 29), (END, 84, "i")]
HIGH = [(0, 0.5), (0.17, 0.15, "o"), (DIP, 0, "i"), (FLICK - 0.02, 0, "l"), (0.86, 0.6, "o"), (END, 1.05)]
SWAY = [(0, 0.06), (0.17, -0.02, "o"), (0.3, 0), (0.52, 0.03), (0.68, -0.03), (FLICK, 0), (END, 0)]
CURL = [(0, 0), (0.27, 0.05), (0.38, 1, "o"), (0.52, 1, "l"), (0.56, 0.75), (0.6, 1), (FLICK, 1, "l"), (0.95, 0.5), (END, 0.3)]
SINK = [(0.2, 0), (0.3, 1, "o"), (0.68, 1, "l"), (FLICK + 0.04, 0, "o")]
SQUASH = [(0, -0.12), (0.17, -0.18, "l"), (0.22, 0.2, "o"), (0.3, 0), (0.44, 0.12), (0.52, -0.1), (0.58, 0.1), (0.68, -0.12),
          (FLICK, -0.2), (0.86, 0.05), (END, 0)]
SEEN = [(0, 0), (0.06, 1, "o"), (1.1, 1, "l"), (END, 0)]


def paw_at(x, y, k, born, h):
    """A paw sent at (x, y) in a pond h high: straight in from the nearer edge, swaying and shaking to a side left to chance."""
    ey = -46 * k if y <= h - y else h + 46 * k
    return {"x": x, "y": y, "k": k, "ex": x, "ey": ey, "side": -1 if h2(round(x), round(y)) < 0.5 else 1, "born": born}


def paw_pose(p, t):
    """Where a paw is in its catch at time t: how far it is drawn back, how high, how it sways, how curled and how
    deep its toes are; and on screen, where the leg turns about a shoulder beyond the edge: centre, axis u toward
    the toes, v across, size k (high up it looks bigger)."""
    a = t - p["born"]
    # two quick wet shakes as it leaves, turning the paw
    u = (a - SHAKE) / 0.3
    shake = 0.14 * sin(u * 4 * pi) * (1 - u) if 0 < u < 1 else 0
    s = {"back": track(a, BACK), "h": track(a, HIGH), "swing": (track(a, SWAY) + shake) * p["side"], "curl": track(a, CURL),
         "sink": track(a, SINK), "squash": track(a, SQUASH), "seen": track(a, SEEN)}
    K, arm = p["k"] * 1.9, 120
    ux, uy = p["x"] - p["ex"], p["y"] - p["ey"]
    ul = hypot(ux, uy) or 1
    ux, uy = ux / ul, uy / ul
    c, n = cos(s["swing"]), sin(s["swing"])
    dx, dy = ux * c - uy * n, ux * n + uy * c
    sx, sy, r = p["x"] - ux * arm * K, p["y"] - uy * arm * K, (arm - s["back"]) * K
    return dict(s, ux=dx, uy=dy, vx=-dy, vy=dx, cx=sx + dx * r, cy=sy + dy * r, k=K * (1 + 0.5 * s["h"]))


def tip_of(s):
    """How far the tip reaches in paw units: curled toes fold under, so the paw gets shorter."""
    return 5 - 4 * s["curl"] + HAND * 1.08


def paw_drops(p):
    """Flicking out of the water, the paw throws five drops back toward the cat; each of the
    shakes throws one off the side of the tip it swings toward. (x0, y0, x1, y1, born, dur)."""
    s, seed, out = paw_pose(p, p["born"] + FLICK), round(p["born"] * 1000), []
    for j in range(5):
        side, d = (j - 2) / 2, (30 + 36 * h2(j, seed)) * p["k"]
        x0 = s["cx"] + (s["ux"] * tip_of(s) + s["vx"] * side * 8) * s["k"]
        y0 = s["cy"] + (s["uy"] * tip_of(s) + s["vy"] * side * 8) * s["k"]
        out.append((x0, y0, x0 - s["ux"] * d + s["vx"] * side * 18 * p["k"], y0 - s["uy"] * d + s["vy"] * side * 18 * p["k"],
                    p["born"] + FLICK + j * 0.035, 0.34 + 0.14 * h2(j + 7, seed)))
    for n in range(3):
        t = p["born"] + SHAKE + 0.3 * (0.12 + n * 0.25)
        s, way = paw_pose(p, t), (-1 if n % 2 else 1) * p["side"]
        a0, s0, sd = tip_of(s) - 4, way * 8, seed + n
        x = s["cx"] + (s["ux"] * a0 + s["vx"] * s0) * s["k"]
        y = s["cy"] + (s["uy"] * a0 + s["vy"] * s0) * s["k"]
        d = (26 + 20 * h2(sd, 3)) * p["k"]
        out.append((x, y, x + s["vx"] * way * d - s["ux"] * 8 * p["k"], y + s["vy"] * way * d - s["uy"] * 8 * p["k"], t, 0.3))
    return out


def paw_cells(p, t, cw, ch, w, h, P):
    """The paw at time t drawn the way the course page draws the cat: in cells half the pond's size,
    black fur edged with ':' and a little '#%' texture; toes under the surface seen through the water.
    In paw units al runs toward the toes and sd across: a round little hand on a round leg, its four
    toes only four faint arcs along the tip. Returns its cells, its shadow's cells and strength, and
    the toe arcs as (x, y, radius, angle, alpha)."""
    pose = paw_pose(p, t)
    ux, uy, vx, vy, cx, cy, k = (pose[q] for q in ("ux", "uy", "vx", "vy", "cx", "cy", "k"))
    high, sink, curl, squash, seen = (pose[q] for q in ("h", "sink", "curl", "squash", "seen"))
    # squashed as it pushes in, stretched as it shoots and flicks: shorter and wider, or longer and narrower
    ka, ks = k * (1 - 0.16 * squash), k * (1 + 0.16 * squash)
    # Curled toes fold under the tip, and their knuckles stand out a little more.
    cb, toe = tip_of(pose) - HAND * 1.08, 2.5 + 0.3 * curl
    ring_r = HAND - toe - 1.1

    def part(al, sd):
        """How far outside the paw (al, sd) is, and what is there: -1 water, 0 foreleg, 1 paw.
        A round little hand on a round leg, melted together."""
        leg = (hypot(al - cb, sd) if al > cb else abs(sd)) - LEG
        hand = hypot((al - cb) / 1.08, sd) - HAND
        q = max(6 - abs(leg - hand), 0) / 6
        dist = min(leg, hand) - q * q * 6 / 4
        return dist, -1 if dist > 0 else 0 if al < -6 else 1
    fw, fh = cw / 2, ch / 2
    # the box the paw and its foreleg can cover
    corners = [(cx + ux * al * ka + vx * sd * ks, cy + uy * al * ka + vy * sd * ks) for al in (-31, 16) for sd in (-11.5, 11.5)]
    i0, i1 = max(0, floor(min(x for x, _ in corners) / fw)), min(ceil(w / fw), ceil(max(x for x, _ in corners) / fw))
    j0, j1 = max(0, floor(min(y for _, y in corners) / fh)), min(ceil(h / fh), ceil(max(y for _, y in corners) / fh))
    # Each cell takes the part under its samples; a cell only partly covered is drawn fainter, so the toes stay round.
    g, A, cover = {}, {}, {}
    near_edge = 0.6 * hypot(fw, fh) / min(ka, ks) + 0.3

    def al_of(x, y):
        return ((x - cx) * ux + (y - cy) * uy) / ka

    def sd_of(x, y):
        return ((x - cx) * vx + (y - cy) * vy) / ks
    for j in range(j0, j1 + 1):
        for i in range(i0, i1 + 1):
            x, y = i * fw, j * fh
            ac, sc = al_of(x + fw / 2, y + fh / 2), sd_of(x + fw / 2, y + fh / 2)
            A[(i, j)] = ac
            if ac < -31 or ac > 17 or abs(sc) > 13:
                continue
            # a cell well inside or outside needs no more samples than its centre
            dist, vc = part(ac, sc)
            if abs(dist) > near_edge:
                g[(i, j)], cover[(i, j)] = vc, 1 if vc >= 0 else 0
                continue
            n, top = 0, -1
            for q in (1, 3, 5):
                for r in (1, 3, 5):
                    sx, sy = x + q / 6 * fw, y + r / 6 * fh
                    v = part(al_of(sx, sy), sd_of(sx, sy))[1]
                    if v >= 0:
                        n += 1
                        if top < 0 or v > 1:
                            top = v
            g[(i, j)], cover[(i, j)] = top if n >= 5 else -2 if n else -1, n / 9

    def at(i, j):
        return max(-1, g.get((i, j), -1))
    wl = tip_of(pose) + 2 - 8 * sink if sink > 0 else inf
    half_u = 0.5 * (abs(ux) * fw + abs(uy) * fh) / ka

    def fade(al):
        """the foreleg fades out toward the bank the cat sits on"""
        return max(0, 1 - (-8 - al) / 22) ** 1.5 if al < -8 else 1
    # The shadow falls on the water, offset more while the paw is high.
    sx, sy = 2 + round(high * 8), 2 + round(high * 6)
    shadow = {(i + sx, j + sy) for (i, j), v in g.items() if v >= 0 and fade(A[(i, j)]) > 0.4 and A[(i, j)] < wl}
    shade = (0.5 if P["dark"] else 0.24) * (1 - 0.5 * high) * seen
    fur, tex, rim = ((16, 18, 21), (44, 49, 54), (150, 160, 166)) if P["dark"] else ((16, 15, 14), (54, 50, 46), (85, 80, 74))
    # On dark water the fur catches a little light along its edge, or the paw would vanish.
    lit = mix(fur, rim, 0.22) if P["dark"] else fur
    dry = [hexc(c) for c in (fur, rim, lit)]
    wet = [hexc(mix(c, P["water"], 0.3)) for c in (fur, rim, lit)]
    dot = hexc(P["dot"])

    def a10(v):
        return round(clamp(v, 0, 1) * 10) / 10
    cells = {}
    for (i, j), v in g.items():
        al = A[(i, j)]
        under, f = al > wl, fade(al)
        if v == -1 or f <= 0:
            continue
        fur_c, rim_c, lit_c = wet if under else dry
        edge = min(at(i - 1, j), at(i + 1, j), at(i, j - 1), at(i, j + 1)) < 0
        if v == -2:
            cells[(i, j)] = ((fur_c, a10(cover[(i, j)] * 1.3 * f * seen)), (" ", dot, 0))
            continue
        if not under and f == 1 and not edge:
            tile = (dry[0], a10(seen))
        else:
            tile = (lit_c if edge else fur_c, a10((0.8 if under else 1) * f * seen))
        if sink > 0 and abs(al - wl) < half_u:
            glyph = ("~", dot, a10(0.7 * seen))
        elif edge:
            glyph = (":", rim_c, a10((0.9 if P["dark"] else 0.55) * f * seen))
        elif not under and (i * 7 + j * 13) % 4 == 0:
            glyph = ("#" if (i + j) % 3 else "%", hexc(tex), a10(0.45 * f * seen))
        else:
            glyph = (" ", dot, 0)
        cells[(i, j)] = (tile, glyph)
    # The four toes are only four faint arcs along the tip, stroked like the cat's whiskers.
    arcs = []
    for th in TOES:
        c, n = cos(th), sin(th)
        al, sd = cb + ring_r * c * 1.08, ring_r * n
        arcs.append((cx + ux * al * ka + vx * sd * ks, cy + uy * al * ka + vy * sd * ks, toe * k,
                     atan2(uy * c + vy * n, ux * c + vx * n), a10((0.3 if al + toe > wl else 0.5) * seen)))
    return cells, shadow, round(shade * 20) / 20, arcs, dry[1], max(0.8, 0.11 * k)


# ── one frame of a koi, its spine in banner coordinates, rasterised into cells ──

def rasterise(fish, spine, flare_l, flare_r, cw, ch, P):
    L, depth = fish["L"], fish["depth"]
    arc = [0.0]
    for n in range(1, N):
        arc.append(arc[-1] + hypot(spine[n][0] - spine[n - 1][0], spine[n][1] - spine[n - 1][1]))
    total = arc[-1] or 1
    # Each eye is the one cell under its centre, so both eyes always show at banner size.
    s_eye, n = 0.07 * total, 0
    while arc[n + 1] < s_eye:
        n += 1
    ex, ey = spine[n + 1][0] - spine[n][0], spine[n + 1][1] - spine[n][1]
    el = hypot(ex, ey) or 1
    k = (s_eye - arc[n]) / el
    side_off = 0.64 * half_w(0.07) * L
    eyes = {(floor((spine[n][0] + ex * k + sg * -ey / el * side_off) / cw),
             floor((spine[n][1] + ey * k + sg * ex / el * side_off) / ch)) for sg in (1, -1)}

    def sample(px, py):
        best = inf
        for n in range(N - 1):
            ax, ay = spine[n]
            sx, sy = spine[n + 1][0] - ax, spine[n + 1][1] - ay
            len2 = sx * sx + sy * sy or 1
            raw = ((px - ax) * sx + (py - ay) * sy) / len2
            u = clamp(raw, 0, 1)
            d2 = (px - ax - sx * u) ** 2 + (py - ay - sy * u) ** 2
            if d2 < best:
                ln, cross = sqrt(len2), sx * (py - ay) - sy * (px - ax)
                best, bs, sign = d2, (arc[n] + u * ln) / total, 1 if cross >= 0 else -1
                past = max(0, raw - 1) * ln if n == N - 2 else 0
                ahead = max(0, -raw) * ln if n == 0 else 0
                lateral, tx, ty = abs(cross) / ln, sx / ln, sy / ln
        d = sqrt(best)
        hit = classify(bs, d / L, past / L, flare_l if sign > 0 else flare_r, ahead / L, lateral / L)
        return hit, bs, d * sign, tx, ty, d

    xs, ys = [p[0] for p in spine], [p[1] for p in spine]
    reach = L * 0.27
    diag = hypot(cw, ch)
    alpha = (0.82 if P["dark"] else 0.9) * (0.55 + 0.45 * depth)
    sdc, sdr = 1 + round(depth * 2), 1 + round(depth)
    shade = P["shade"] * (0.5 + 0.5 * depth)
    lx, ly = -0.6, -0.8
    cells, shadow = {}, set()
    for r in range(floor((min(ys) - reach) / ch), floor((max(ys) + reach) / ch) + 1):
        for c in range(floor((min(xs) - reach) / cw), floor((max(xs) + reach) / cw) + 1):
            x, y = c * cw, r * ch
            first = sample(x + cw / 2, y + ch / 2)
            hit, s, v, tx, ty, d = first
            if not hit and d > L * (0.15 if 0.4 < s < 0.62 else 0.26) + diag:
                continue
            hits = 1 if hit else 0
            deep = hit and hit[0] == 1 and 0.05 < s < 0.7 and half_w(s) * L - d > diag * 0.4
            if deep:
                hits = 5
            for qx, qy in ([] if deep else SUB):
                got = sample(x + qx * cw, y + qy * ch)
                if not got[0]:
                    continue
                if hits == 0:
                    hit, s, v, tx, ty, d = got
                hits += 1
            if not hits:
                continue
            kind, across, rs, ra = hit
            if (c, r) in eyes and kind in (1, 4):
                kind = 3
            cover = hits / 5
            side = 1 if v >= 0 else -1
            tile = None
            if kind == 5:
                g, g_c, g_a = line_glyph(tx, ty), P["fin"], 0.7 * alpha
            elif kind == 2:
                nx, ny = -ty * side, tx * side
                g = line_glyph(rs * tx + ra * nx, rs * ty + ra * ny)
                tile, t_a = P["fin"], (0.26 if P["dark"] else 0.3) * (1 if cover >= 0.6 else 0.5) * alpha
                g_c, g_a = mul(P["fin"], 1.1 if P["dark"] else 0.62), (0.55 if P["dark"] else 0.42) * alpha
            else:
                nz = sqrt(max(0, 1 - across * across))
                lit = clamp(0.76 + 0.26 * nz + 0.2 * (-ty * side * across * lx + tx * side * across * ly), 0.62, 1.08)
                lit = round(lit / LIT_STEP) * LIT_STEP
                sk = None if kind == 3 else skin(fish["marks"], fish["seed"], s, v / L, across)
                base = P["eye"] if kind == 3 else P["red"] if sk == 1 else P["black"] if sk == 2 else P["white"]
                tile, t_a = mul(base, lit), (1 if cover >= 0.4 else 0.5) * alpha
                if kind == 3:
                    g, g_c, g_a = "o", P["white"], 0.95 * alpha
                else:
                    idx = clamp(1 + round((1.08 - lit) / 0.46 * 6) + (2 if kind == 4 else 0), 1, len(RAMP) - 1)
                    g = RAMP[idx]
                    g_c = mul(base, (0.55 if sk == 0 else 1.35) if P["dark"] else 0.5)
                    g_a = 0.62 * alpha
                if cover >= 0.6:
                    shadow.add((c + sdc, r + sdr))
            cells[(c, r)] = (tile and (hexc(tile), round(t_a * 5) / 5), (g, hexc(g_c), round(g_a * 10) / 10))
    return cells, shadow, round(shade * 20) / 20


def cell_path(cells, cw=1, ch=1, gap=0):
    """Cells as thick horizontal strokes, one per run of neighbours in a row.

    Drawn with stroke-width ch - gap and a dash of cw - gap, each run still
    shows separate tiles with a gap between them. With the default cw = ch = 1
    the path is in cells, for a group scaled to the cell size."""
    runs = []
    for c, r in sorted(cells, key=lambda k: (k[1], k[0])):
        if runs and runs[-1][1] == r and runs[-1][0] + runs[-1][2] == c:
            runs[-1][2] += 1
        else:
            runs.append([c, r, 1])
    out, end = [], None
    for c, r, n in runs:
        x, y, ln = c * cw, r * ch + ch // 2, n * cw - gap
        out.append(f"M{x} {y}" if end is None else f"m{x - end[0]} {y - end[1]}")
        out.append(f"h{ln}")
        end = (x + ln, y)
    return "".join(out)


def paint_paths(cells, cls, size):
    """Cells {(c, r): paint} as one path per paint. A paint is a tile and its glyph in one
    cell-sized pattern (see banner), so the cells write no glyphs of their own."""
    runs = {}
    for cell, paint in cells.items():
        runs.setdefault(paint, []).append(cell)
    return "".join(f'<path class="{cls("p", size, paint)}" d="{cell_path(d)}"/>' for paint, d in runs.items())


def frame_svg(cells, shadow, shade, cls, P, size, colour=None):
    """One frame of a koi (or the paw) in cells from its top-left cell: its shadow, then its paints."""
    every = list(cells) + list(shadow)
    c0, r0 = min(c for c, _ in every), min(r for _, r in every)
    out = f'<path class="{cls("s", colour or hexc(P["shadow"]), shade)}" d="{cell_path((c - c0, r - r0) for c, r in shadow)}"/>' if shadow else ""
    return c0, r0, out + paint_paths({(c - c0, r - r0): p for (c, r), p in cells.items()}, cls, size)


def flipbook(ids, times, cycle, T0):
    """A <use> that shows each frame id at its time in a cycle of `cycle` seconds, and nothing
    where there is no frame, already T0 seconds in when the banner loads. One SMIL animation
    does what one CSS animation per frame did, so the browser has far less to keep track of."""
    keys, vals = ([0.0], ["z"]) if times[0] > 0 else ([], [])
    for i, t in zip(ids, times):
        if not vals or vals[-1] != (i or "z"):
            keys.append(t / cycle)
            vals.append(i or "z")
    if times[-1] + FRAME < cycle - FRAME / 2:
        keys.append((times[-1] + FRAME) / cycle)
        vals.append("z")
    return (f'<use class="live" xlink:href="#z"><animate attributeName="xlink:href" calcMode="discrete" repeatCount="indefinite" '
            f'dur="{cycle:g}s" begin="{-T0:g}s" keyTimes="{";".join(f"{k:.5f}" for k in keys)}" '
            f'values="{";".join("#" + v for v in vals)}"/></use>')


def wordmark(title, P):
    """The title the way the course page draws its small masthead "One Page": the letters
    sampled from the font outline into small cells, and every cell they cover enough an even
    "#", fainter where they cover less. Small marks read better as an even dot matrix."""
    from PIL import Image, ImageDraw, ImageFont
    cw, ch = title["cell"]
    ss = 4
    path, index = TITLE_FONTS[title["font"]]
    font = ImageFont.truetype(path, round(title["size"] * ss), index=index)
    ink, cells = hexc(rgb(P["ink"])), {}
    for text, row in title["lines"]:
        left, upper, right, lower = font.getbbox(text)
        img = Image.new("L", (right - left, lower - upper), 0)
        ImageDraw.Draw(img).text((-left, -upper), text, font=font, fill=255)
        img = img.resize((round(img.width * title["squeeze"]), img.height), Image.LANCZOS)
        cols, rows = -(-img.width // (cw * ss)), -(-img.height // (ch * ss))
        pad = Image.new("L", (cols * cw * ss, rows * ch * ss), 0)
        pad.paste(img, (0, 0))
        cover = pad.resize((cols, rows), Image.BOX).load()
        for r in range(rows):
            for c in range(cols):
                v = cover[c, r] / 255
                if v >= 0.3:
                    cells[(c, row + r)] = (None, ("#", ink, round(min(1, 0.4 + v) * 10) / 10))
    return cells


# ── the pellets thrown to the feeding koi ──

FLIGHT = 0.6                # seconds a pellet is in the air
RING_LIFE = 1.35            # a landing or a gulp leaves a small ring for this long
SPATTER = 0.15              # seconds between one pellet of the handful landing and the next
SPLASH_LIFE = 2.6           # the handful hitting the water leaves a wide double ring this long, like the paw on the course page


def ring(cx, cy, R, cw, ch):
    """The cells on a ring of radius R around (cx, cy), each with a glyph along the ring, as on the course page."""
    out = []
    for r in range(floor((cy - R - ch) / ch), floor((cy + R + ch) / ch) + 1):
        for c in range(floor((cx - R - cw) / cw), floor((cx + R + cw) / cw) + 1):
            dx, dy = c * cw + cw / 2 - cx, r * ch + ch / 2 - cy
            if abs(hypot(dx, dy) - R) <= cw * 0.62:
                out.append((c, r, line_glyph(-dy, dx)))
    return out


def scatter(feed, cw, ch):
    """The cells the pellets land in: spread around feed["at"], never two touching."""
    fx, fy = feed["at"]
    taken, tries = [], 0
    while len(taken) < feed["count"]:
        tries += 1
        a, d = h2(tries, 7) * 2 * pi, sqrt(h2(tries, 11)) * feed["spread"]
        cell = (floor((fx + cos(a) * d) / cw), floor((fy + sin(a) * d * 0.8) / ch))
        gap = 1 if tries < 400 else 0       # a crowded patch may put pellets side by side
        if all(max(abs(cell[0] - c), abs(cell[1] - r)) > gap for c, r in taken):
            taken.append(cell)
    return taken


def feeding(feed, spots, eaten, cw, ch, P):
    """The throw and the paw, one frame of cells per FRAME: pellets in the air (an "o" high up,
    a "." low, a shadow parting from it), pellets afloat until eaten, a small ring where each
    lands and where each is eaten, and a wide double ring where the handful hits the water;
    then the same wide rings where the paw dips, and its drops flying off, each leaving a small
    ring where it lands, as on the course page."""
    food, food_g, dot, shadow = hexc(P["food"]), hexc(mul(P["food"], 0.55)), hexc(P["dot"]), hexc(P["shadow"])
    (hx, hy), (cx, cy), k = feed["hand"], feed["at"], feed["k"]
    (px_, py_), dip, drops = feed["hit"], feed["paw"]["born"] + DIP, feed["drops"]
    end = max(max(eaten.values()) + RING_LIFE, dip + SPLASH_LIFE, max(b + d for *_, b, d in drops) + DROP_LIFE)
    frames = []
    for m in range(floor(feed["throw"] / FRAME), floor(end / FRAME) + 1):
        t, cells, rings = m * FRAME, {}, []
        for j, (c0, r0) in enumerate(spots):
            land, gone = feed["lands"][j], eaten[j]
            px, py = c0 * cw + cw / 2, r0 * ch + ch / 2
            if land - FLIGHT <= t < land:
                u = (t - land + FLIGHT) / FLIGHT
                x, y, hh = lerp(hx, px, u), lerp(hy, py, u), 4 * u * (1 - u)
                c, r = floor(x / cw), floor(y / ch)
                cells.setdefault((c + round(hh * 3), r + round(hh * 2)), ((shadow, 0.3), (" ", dot, 0)))
                cells[(c, r)] = (None, ("o" if hh > 0.4 else ".", food, 1.0))
            elif land <= t < gone:
                cells[(c0, r0)] = ((food, 1.0), ("o", food_g, 1.0))
            for t0, strength in ((land, 0.32), (gone, 0.6)):
                if 0 < t - t0 < RING_LIFE:
                    rings.append((px, py, ((t - t0) * 34 + 4) * k, (1 - (t - t0) / RING_LIFE) ** 1.5 * strength, None))
        for x0, y0, x1, y1, born, dur in drops:
            u = (t - born) / dur
            if 0 <= u < 1:
                x, y, hh = lerp(x0, x1, u), lerp(y0, y1, u), 4 * u * (1 - u)
                c, r = floor(x / cw), floor(y / ch)
                if round(hh * 3) or round(hh * 2):
                    cells.setdefault((c + round(hh * 3), r + round(hh * 2)), ((shadow, 0.3), (" ", dot, 0)))
                cells[(c, r)] = (None, ("o" if hh > 0.4 else ".", dot, 0.9))
            elif 0 < t - born - dur < DROP_LIFE:
                age = t - born - dur
                rings.append((x1, y1, (age * 34 + 4) * k, (1 - age / DROP_LIFE) ** 1.5 * 0.45, None))
        for (sx, sy), t0 in (((cx, cy), feed["land"]), ((px_, py_), dip)):
            for lag, glyph, strength in ((0, None, 0.62), (0.38, "·", 0.32)):
                age = t - t0
                if lag < age < SPLASH_LIFE:
                    rings.append((sx, sy, ((age - lag) * 74 + 26) * k, (1 - age / SPLASH_LIFE) ** 1.5 * strength, glyph))
        for x, y, R, alpha, glyph in rings:
            alpha = round(alpha * 10) / 10
            for c, r, g in ring(x, y, R, cw, ch):
                if alpha and (c, r) not in cells:
                    cells[(c, r)] = (None, (glyph or g, dot, alpha))
        if cells:
            frames.append((t, cells))
    return frames


def sized(fish, k):
    """The koi at scale k: longer, and faster in proportion, as on the course page."""
    return [dict(f, L=f["L"] * k, cruise=f["cruise"] * k) for f in fish]


def banner(w, h, pond, cell, fish, title, subtitle, feed, koi=None, k=1):
    P = palette(pond, koi)
    cw, ch = cell
    fs = round(ch * 0.74)
    size = (cw, ch, fs, round(ch / 2 + fs * 0.36))
    dot = hexc(P["dot"])
    names = {}

    def cls(kind, *key):
        return names.setdefault((kind,) + key, f"{kind}{len(names)}")

    def grid(cells, x=0, y=0, sz=size):
        """Cells drawn in a group scaled to cells of size sz, its first cell at (x, y)."""
        return f'<g transform="matrix({sz[0]} 0 0 {sz[1]} {x} {y + sz[1] / 2:g})">{paint_paths(cells, cls, sz)}</g>'

    frames_def, lives, stills = [], [], []
    # All the koi swim on the feed's cycle and share its pellets.
    fish = sized(fish, k)
    spots = scatter(feed, cw, ch)
    lands = [feed["throw"] + FLIGHT + SPATTER * round(h2(j, 3) * (len(spots) - 1) / 2) for j in range(len(spots))]
    feed = dict(feed, k=k, lands=lands, land=min(lands), pellets=[(c * cw + cw / 2, r * ch + ch / 2) for c, r in spots],
                paw=paw_at(*feed["at"], k, 0, h))
    loops, eaten, born, gap = swim(fish, feed, w, h)
    assert gap < 150, f"the koi are still {gap:.0f} px from the calm cycle as they ease into it"
    feed["paw"]["born"] = born
    pose = paw_pose(feed["paw"], born + DIP)
    tip = tip_of(pose) - 3
    feed.update(hit=(pose["cx"] + pose["ux"] * tip * pose["k"], pose["cy"] + pose["uy"] * tip * pose["k"]), drops=paw_drops(feed["paw"]))
    # The cycle and start in whole frames, so every change in the banner falls on one shared beat.
    cycle, T0 = round(feed["cycle"] / FRAME) * FRAME, round(feed["at_load"] / FRAME) * FRAME
    for i, (f, frames) in enumerate(sorted(zip(fish, loops), key=lambda fl: fl[0]["depth"])):
        f = dict(f, marks=markings(f["variety"], f["seed"]))
        skin = palette(pond, f.get("colours", koi))     # a koi may carry its own colour scheme
        ids, trail = [], []
        reach = f["L"] * 0.3
        for n, (t, spine, fl, fr) in enumerate(frames[-12:] + frames, -12):
            # The wake: the cells the tail tip has just left, fading behind it. The cycle's
            # last frames come just before its first, so they lay the first frames' wake.
            tc = (floor(spine[-1][0] / cw), floor(spine[-1][1] / ch))
            if not trail or trail[-1] != tc:
                trail = (trail + [tc])[-8:]
            if n < 0:
                continue
            xs = [p[0] for p in spine]
            if max(xs) + reach < 0 or min(xs) - reach > w:     # out past the side, before it comes back in
                ids.append(None)
                continue
            cells, shadow, shade = rasterise(f, spine, fl, fr, cw, ch, skin)
            for j, wc in enumerate(reversed(trail[:-1])):
                if wc not in cells:
                    cells[wc] = (None, (":" if j < 3 else "·", dot, round(0.42 * (1 - j / 8) * 10) / 10))
            c0, r0, body = frame_svg(cells, shadow, shade, cls, P, size)
            ids.append(f"k{i}_{n}")
            frames_def.append(f'<g id="{ids[-1]}" transform="matrix({cw} 0 0 {ch} {c0 * cw} {r0 * ch + ch / 2:g})">{body}</g>')
        lives.append(flipbook(ids, [t for t, *_ in frames], cycle, T0))
        if "still_at" in f:     # with reduced motion, the koi with a still_at hold still at that moment of the cycle
            seen = [n for n in range(len(frames)) if ids[n]]
            stills.append(f'<use class="still" xlink:href="#{ids[min(seen, key=lambda n: abs(frames[n][0] - f["still_at"]))]}"/>')
    ids, times = [], []
    for n, (t, cells) in enumerate(feeding(feed, spots, eaten, cw, ch, P)):
        c0, r0 = min(c for c, _ in cells), min(r for _, r in cells)
        ids.append(f"e{n}")
        times.append(t)
        frames_def.append(f'<g id="e{n}" transform="matrix({cw} 0 0 {ch} {c0 * cw} {r0 * ch + ch / 2:g})">'
                          f'{paint_paths({(c - c0, r - r0): p for (c, r), p in cells.items()}, cls, size)}</g>')
    lives.append(flipbook(ids, times, cycle, T0))
    # The cat's paw, over the koi, in cells half their size.
    fw, fh = cw / 2, ch / 2
    pfs = max(3, round(fh * 0.8))
    psize, ids, times = (fw, fh, pfs, round(fh / 2 + pfs * 0.36)), [], []
    paw = feed["paw"]
    for m in range(ceil(paw["born"] / FRAME), floor((paw["born"] + END) / FRAME) + 1):
        t = m * FRAME
        cells, shadow, shade, arcs, rim, lw = paw_cells(paw, t, cw, ch, w, h, P)
        if not cells:
            continue
        c0, r0, body = frame_svg(cells, shadow, shade, cls, P, psize, "#000000" if P["dark"] else hexc(mul(P["water"], 0.55)))
        toes = {}
        for x, y, R, phi, alpha in arcs:
            if alpha:
                toes.setdefault(alpha, []).append(f"M{x + R * cos(phi - 1.05):.1f} {y + R * sin(phi - 1.05):.1f}"
                                                  f"A{R:.1f} {R:.1f} 0 0 1 {x + R * cos(phi + 1.05):.1f} {y + R * sin(phi + 1.05):.1f}")
        toes_svg = "".join(f'<path d="{"".join(d)}" stroke="{rim}" stroke-opacity="{num(a)}" stroke-width="{lw:.2f}" '
                           f'stroke-linecap="round" stroke-dasharray="none"/>' for a, d in toes.items())
        ids.append(f"w{len(ids)}")
        times.append(t)
        frames_def.append(f'<g id="{ids[-1]}"><g transform="matrix({fw:g} 0 0 {fh:g} {c0 * fw:g} {r0 * fh + fh / 2:g})" '
                          f'stroke-width="1" stroke-dasharray="none">{body}</g>{toes_svg}</g>')
    lives.append(flipbook(ids, times, cycle, T0))
    specks = {(c, r): (None, ("·", dot, 0.2)) for r in range(h // ch + 1) for c in range(w // cw + 1) if h2(c, r) < 0.022}
    # The title, top left, with a thin accent glint crossing it now and then, a column at a time.
    tcw, tch = title["cell"]
    tfs = round(tch * 0.9)
    tsize = (tcw, tch, tfs, round(tch / 2 + tfs * 0.36))
    mark = wordmark(title, P)
    tx, ty = title["x"], title["y"]
    cols = max(c for c, _ in mark) + 1
    tw, th = cols * tcw, (max(r for _, r in mark) + 1) * tch
    glint_cells = {cell: (None, ("#", hexc(P["glint"]), 1.0)) for cell in mark}
    period = round(GLINT_PERIOD / FRAME) * FRAME
    band = max(2 * tcw, round(2 * GLINT_HALF * tw / tcw) * tcw)
    xs, last = [], None
    for m in range(round(period / FRAME)):
        u = ((m * FRAME * GLINT_SPEED) % 1.9) - 0.45
        x = tx + round(u * tw / tcw) * tcw - band // 2 if -0.05 < u < 1.05 else -band - 10
        xs.append(x)
    keys = ";".join(f"{m / len(xs):.5f}" for m in range(len(xs)))
    glint = (f'<clipPath id="gl"><rect x="{xs[0]}" y="{ty}" width="{band}" height="{th}">'
             f'<animate attributeName="x" calcMode="discrete" repeatCount="indefinite" dur="{period:g}s" keyTimes="{keys}" '
             f'values="{";".join(map(str, xs))}"/></rect></clipPath>')
    # Drawn before the paints are listed, so every paint they use gets its pattern.
    specks_svg = grid(specks)
    title_svg = f'{grid(mark, tx, ty, tsize)}<g class="glint" clip-path="url(#gl)">{grid(glint_cells, tx, ty, tsize)}</g>'
    # Koi pass under the title through a soft patch of water that hides most of them.
    vx0, vy0 = tx - 3 * tcw, ty - 2 * tch
    vx1, vy1 = max(tx + tw, subtitle["x"] + subtitle["width"]) + 4 * tcw, subtitle["ys"][-1] + subtitle["size"]
    paints, colours = [], []
    for key, n in names.items():
        if key[0] == "s":
            colours.append(f".{n} {{ stroke: {key[1]}; stroke-opacity: {num(key[2])}; stroke-width: 1px; stroke-dasharray: none; }}")
            continue
        (pcw, pch, pfs, pgy), (tile, (g, g_c, g_a)) = key[1], key[2]
        rect = f'<rect width="1" height="1" fill="{tile[0]}" fill-opacity="{num(tile[1])}"/>' if tile else ""
        glyph = (f'<text transform="scale({1 / pcw:.5g} {1 / pch:.5g})" x="{pcw / 2:g}" y="{pgy}" font-size="{pfs}" '
                 f'fill="{g_c}" fill-opacity="{num(g_a)}">{esc(g)}</text>') if g != " " and g_a else ""
        paints.append(f'<pattern id="{n}" width="1" height="1" y="-.5" patternUnits="userSpaceOnUse">{rect}{glyph}</pattern>')
        colours.append(f".{n} {{ stroke: url(#{n}); }}")
    tiles = f'stroke-width="{(ch - 1) / ch:.5g}" stroke-dasharray="{(cw - 1) / cw:.5g} {1 / cw:.5g}"'
    sub = "".join(f'<text x="{subtitle["x"]}" y="{y}">{esc(line)}</text>' for line, y in zip(subtitle["lines"], subtitle["ys"]))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Song of Hero. Haojie Song, an AI explorer at the dawn of a magnificent age.">
  <style>
    {" ".join(colours)}
    .still {{ display: none; }}
    @media (prefers-reduced-motion: reduce) {{ .live, .glint {{ display: none; }} .still {{ display: inline; }} }}
  </style>
  <defs>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="{14 if w > 1000 else 18}"/></clipPath>
    {glint}
    <radialGradient id="veil"><stop offset="0.55" stop-color="{hexc(P["water"])}" stop-opacity="0.9"/><stop offset="1" stop-color="{hexc(P["water"])}" stop-opacity="0"/></radialGradient>
    <g font-family="{MONO}" font-weight="700" text-anchor="middle">{"".join(paints)}</g>
    <g id="z"/>
    {"".join(frames_def)}
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{hexc(P["water"])}"/>
    {specks_svg}
    <g fill="none" {tiles}>{"".join(lives)}{"".join(stills)}</g>
    <ellipse cx="{(vx0 + vx1) / 2:g}" cy="{(vy0 + vy1) / 2:g}" rx="{(vx1 - vx0) * 0.62:g}" ry="{(vy1 - vy0) * 0.8:g}" fill="url(#veil)"/>
  </g>
  <g fill="none" stroke-width="1">{title_svg}</g>
  <g font-family="{MONO}" font-size="{subtitle["size"]}" font-weight="500" letter-spacing="0.02em" fill="{P["ink"]}">{sub}</g>
</svg>
"""


def card(w, h, eyebrow, title_lines, line, chip, mobile):
    s = 2 if mobile else 1
    pad = 44 if mobile else 36
    icon = "" if mobile else (
        '<rect x="500" y="62" width="14" height="14" rx="2" fill="#8f4512"/>'
        '<rect x="518" y="62" width="14" height="14" rx="2" fill="#d8711f"/>'
        '<rect x="518" y="44" width="14" height="14" rx="2" fill="#f2a23a"/>'
        '<rect x="536" y="62" width="14" height="14" rx="2" fill="#f2a23a"/>'
        '<rect x="536" y="44" width="14" height="14" rx="2" fill="#ffd27a"/>'
        '<rect x="536" y="26" width="14" height="14" rx="2" fill="#fff1c6"/>'
    )
    y = 96 if mobile else 54
    parts = [f'<text x="{pad}" y="{y}" font-family="{MONO}" font-size="{17 * s}" letter-spacing="{3 + s}" fill="{AMBER}">{esc(eyebrow)}</text>']
    title_size = 78 if mobile else 40
    y += 104 if mobile else 54
    for t in title_lines:
        parts.append(f'<text x="{pad - 3}" y="{y}" font-family="{SERIF}" font-size="{title_size}" font-weight="700" fill="{INK}">{esc(t)}</text>')
        y += 82
    if line:
        y += -82 + 42
        parts.append(f'<text x="{pad}" y="{y}" font-family="{SANS}" font-size="20" fill="#c9d1d9">{esc(line)}</text>')
    chip_size = 32 if mobile else 15
    chip_h = 62 if mobile else 30
    chip_w = int(len(chip) * chip_size * 0.61) + (44 if mobile else 26)
    cy = h - (58 if mobile else 30) - chip_h
    parts.append(
        f'<rect x="{pad}" y="{cy}" width="{chip_w}" height="{chip_h}" rx="{chip_h / 2}" fill="#1c140a" stroke="#6a4a18"/>'
        f'<text x="{pad + (22 if mobile else 13)}" y="{cy + chip_h * 0.68:.1f}" font-family="{MONO}" font-size="{chip_size}" fill="{AMBER}">{esc(chip)}</text>'
    )
    r, sw = (28, 4) if mobile else (16, 2)
    label = f"{' '.join(title_lines)}: {line or eyebrow.lower()}. {chip}."
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">
  <rect x="{sw / 2}" y="{sw / 2}" width="{w - sw}" height="{h - sw}" rx="{r}" fill="#0b0f17" stroke="#262c38" stroke-width="{sw}"/>
  {icon}
  {''.join(parts)}
</svg>
"""


def write(name, svg, out=OUT):
    lines = (line.rstrip() for line in svg.splitlines())
    (out / name).write_text("\n".join(line for line in lines if line) + "\n")


# The koi swim across the pond as on the course page, each in its lane: `y` the height it
# keeps near, `dir` 1 to swim right and -1 left, `pass` the second of the cycle it passes
# the feeding spot. A handful of pellets is thrown from `hand` at `throw` seconds each cycle
# and lands around `at`; the koi that `feed` pass near it then and rush it after their
# `notice` delay, and once they have eaten it all, the cat's paw pats the spot and they
# scatter. The others pass the middle later, while the feeders are away. L and cruise are
# the course page's (128-180 long, 24-36 px/s); each banner scales them by its k like the
# page's opening screen, where the koi are 1.85 times that. The varieties and seeds start
# with the course page's shoal, so those markings match. colours: a KOI_COLOURS scheme.
# at_load: seconds into the cycle when the banner loads.
DESKTOP_K = 1.85
DESKTOP_FEED = {"at": (680, 160), "count": 18, "spread": 80, "hand": (760, 340), "throw": 0.6, "cycle": 32, "at_load": 0}
DESKTOP_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 150, "depth": 0.95, "cruise": 32, "colours": "course", "feeds": True, "notice": 0.1,
     "still_at": 4, "lane": {"y": 150, "dir": 1, "pass": 3.0}},
    {"variety": "sanke", "seed": 110, "L": 140, "depth": 0.75, "cruise": 32, "colours": "vermilion", "feeds": True, "notice": 0.2,
     "still_at": 4, "lane": {"y": 210, "dir": -1, "pass": 2.5}},
    {"variety": "tancho", "seed": 207, "L": 135, "depth": 0.55, "cruise": 30, "colours": "gold", "feeds": True, "notice": 0.4,
     "still_at": 4, "lane": {"y": 115, "dir": -1, "pass": 4.0}},
    {"variety": "kohaku", "seed": 304, "L": 145, "depth": 0.85, "cruise": 30, "colours": "sakura", "feeds": True, "notice": 0.3,
     "lane": {"y": 230, "dir": 1, "pass": 4.5}},
    {"variety": "sanke", "seed": 692, "L": 128, "depth": 0.45, "cruise": 30, "colours": "course",
     "lane": {"y": 175, "dir": -1, "pass": 17}},
    {"variety": "kohaku", "seed": 498, "L": 135, "depth": 0.65, "cruise": 30, "colours": "vermilion",
     "lane": {"y": 120, "dir": 1, "pass": 22}},
    {"variety": "sanke", "seed": 401, "L": 130, "depth": 0.6, "cruise": 28, "colours": "gold",
     "lane": {"y": 215, "dir": 1, "pass": 27}},
]
MOBILE_K = 2.0
MOBILE_FEED = {"at": (420, 420), "count": 14, "spread": 85, "hand": (480, 680), "throw": 0.6, "cycle": 32, "at_load": 0}
MOBILE_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 150, "depth": 0.95, "cruise": 32, "colours": "course", "feeds": True, "notice": 0.1,
     "still_at": 4, "lane": {"y": 390, "dir": 1, "pass": 3.0}},
    {"variety": "sanke", "seed": 110, "L": 140, "depth": 0.75, "cruise": 32, "colours": "vermilion", "feeds": True, "notice": 0.3,
     "still_at": 4, "lane": {"y": 470, "dir": -1, "pass": 2.5}},
    {"variety": "tancho", "seed": 207, "L": 135, "depth": 0.55, "cruise": 30, "colours": "gold", "feeds": True, "notice": 0.4,
     "still_at": 4, "lane": {"y": 330, "dir": -1, "pass": 4.0}},
    {"variety": "kohaku", "seed": 304, "L": 145, "depth": 0.85, "cruise": 30, "colours": "sakura", "feeds": True, "notice": 0.3,
     "lane": {"y": 520, "dir": 1, "pass": 4.5}},
    {"variety": "sanke", "seed": 401, "L": 130, "depth": 0.6, "cruise": 30, "colours": "gold",
     "lane": {"y": 300, "dir": 1, "pass": 18}},
    {"variety": "kohaku", "seed": 498, "L": 135, "depth": 0.65, "cruise": 30, "colours": "vermilion",
     "lane": {"y": 440, "dir": -1, "pass": 25}},
]


def banners(pond, out=OUT, koi=None):
    """The desktop banner and the narrow one GitHub shows up to 640 px wide."""
    write("song-of-hero.svg", banner(
        1200, 290, pond, cell=(8, 10), fish=DESKTOP_KOI, koi=koi, feed=DESKTOP_FEED, k=DESKTOP_K,
        title={"lines": [("Song of Hero", 0)], "font": "georgia", "size": 84, "squeeze": 0.8, "cell": (5, 6), "x": 44, "y": 30},
        subtitle={"lines": ["An AI explorer at the dawn of a magnificent age."], "size": 17, "x": 46, "ys": [150], "width": 520},
    ), out)
    write("song-of-hero-mobile.svg", banner(
        800, 600, pond, cell=(11, 14), fish=MOBILE_KOI, koi=koi, feed=MOBILE_FEED, k=MOBILE_K,
        title={"lines": [("Song of Hero", 0)], "font": "georgia", "size": 120, "squeeze": 0.8, "cell": (7, 9), "x": 40, "y": 40},
        subtitle={"lines": ["An AI explorer at the dawn", "of a magnificent age."], "size": 28, "x": 42, "ys": [212, 250], "width": 460},
    ), out)


def main():
    banners(POND)
    cards = {
        "seedance": ("AGENT SKILL", ["Seedance Director"], ["Seedance", "Director"],
                     "Brief to shot-by-shot QA for AI video", "2.2k★ awesome-seedance", "2.2k★ awesome-seedance"),
        "pipeline": ("RESEARCH TOOLING", ["Paper Pipeline"], ["Paper", "Pipeline"],
                     "Scores papers from 10 AI conferences", "23,197 collected → 5,720 kept", "23,197 → 5,720 kept"),
    }
    for key, (eyebrow, title, title_m, line, chip, chip_m) in cards.items():
        write(f"card-{key}.svg", card(600, 240, eyebrow, title, line, chip, mobile=False))
        write(f"card-{key}-mobile.svg", card(600, 480, eyebrow, title_m, None, chip_m, mobile=True))


if __name__ == "__main__":
    main()
