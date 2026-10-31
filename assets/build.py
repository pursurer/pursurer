"""Build the profile banner and project cards as SVG.

Run from the repository root: python3 assets/build.py

The banner is a koi pond seen from above, drawn in character cells like the
koi pond on my n8n course page, with its koi at the size of that page's
opening screen. Each koi is stepped the way the page steps it: the head
wanders and steers, a chain of spine nodes trails it, so the body curves
through every turn, and a body wave runs down it. Every cell is sampled
against the spine, classified as body, fin, eye, ridge or barbel, coloured by
the fish's markings and shaded by a light from the upper left. An SVG image
cannot run scripts, so each koi's pass through the pond is drawn as frames
that show one after another; a tile and its glyph are one cell-sized pattern,
so a frame is a few paths. Once a loop a handful of pellets is thrown in and
a group of koi rush it from different sides. Koi fade under the title, a
character-cell wordmark like "One Page" on the course page (its font is
rasterised with Pillow). Reduced-motion users get a still pond. The live,
click-to-feed pond is pond/index.html.
"""

from math import atan2, cos, floor, hypot, inf, pi, sin, sqrt
from pathlib import Path

OUT = Path(__file__).resolve().parent

SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
# The title's font is rasterised at build time; the course page used Noto Serif Display, then Didot.
TITLE_FONTS = {"georgia": ("/System/Library/Fonts/Supplemental/Georgia Bold.ttf", 0),
               "didot": ("/System/Library/Fonts/Supplemental/Didot.ttc", 2)}
NOISE = "/\\|=+*%#@"
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
FRAME = 0.15                # seconds per drawn frame: koi, pellets, rings and the title's flicker
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


# ── a koi's pass through the pond, stepped like the course page ──

def wrap(a):
    return (a + pi) % (2 * pi) - pi


def swim(group, w, h, feed=None):
    """Passes of koi swimming at the same time, stepped like the course page's pond.

    Each koi enters at its `enter` (x, y, heading) `delay` seconds in, wanders,
    and steers for each point of its `via` in turn, the last one outside the
    banner. The head leads and the chain trails it, no joint bending more than
    BEND, so the body curves through every turn. Once the pellets land, every
    koi goes for them after its own `notice` delay: it darts over, slows down
    near them, and the koi pick the pellets off between them, each taking the
    one nearest its snout. Fed, they head for their last point and leave.
    Returns each koi's frames, one every FRAME while it is in view, as
    (time, spine, flare_l, flare_r), and when each pellet was eaten."""
    left = dict(enumerate(feed["pellets"])) if feed else {}
    koi = []
    for f in group:
        x, y, a = f["enter"]
        seg = f["L"] / (N - 1)
        koi.append({"f": f, "x": x, "y": y, "a": a, "turn": 0.0, "phase": h2(f["seed"], 5) * 2 * pi,
                    "nodes": [(x - cos(a) * seg * j, y - sin(a) * seg * j) for j in range(N)],
                    "via": list(f["via"]), "seen": False, "fed": False, "done": False, "frames": []})
    eaten, step = {}, 0
    while not all(k["done"] for k in koi):
        t = step * SIM_DT
        step += 1
        for k in koi:
            f = k["f"]
            if k["done"] or t < f.get("delay", 0):
                continue
            L, seed, x, y, a = f["L"], f["seed"], k["x"], k["y"], k["a"]
            beat = 0.5 + 0.5 * sin(t * 0.45 + seed)
            target = sin(t * 0.29 + seed) * 0.32 + sin(t * 0.11 + seed * 1.7) * 0.22
            hurry, goal = 1.0, None
            if left and t >= feed["land"] + f.get("notice", 0):
                j, (gx, gy) = min(left.items(), key=lambda kv: hypot(kv[1][0] - x, kv[1][1] - y))
                dist = hypot(gx - x, gy - y)
                if dist < L * 0.09:
                    eaten[j] = t
                    del left[j]
                goal, hurry, k["fed"] = (gx, gy), lerp(0.5, 1.9, sstep(L * 0.15, L * 0.7, dist)), True
            elif k["via"]:
                if k["fed"]:
                    k["via"], k["fed"] = k["via"][-1:], False     # fed: straight for the way out
                if hypot(k["via"][0][0] - x, k["via"][0][1] - y) < L * 0.4:
                    k["via"].pop(0)
                goal = k["via"][0] if k["via"] else None
            if goal:
                d = wrap(atan2(goal[1] - y, goal[0] - x) - a)
                target = target * 0.4 + clamp(d * (2.6 if hurry != 1 else 1.4), -2.4, 2.4)
            elif not left:
                target = 0                  # past its last point: straight on out of the pond
            k["turn"] = lerp(k["turn"], target, min(1, SIM_DT * (3 if hurry != 1 else 2)))
            a += k["turn"] * SIM_DT
            speed = f["cruise"] * (0.65 + 0.7 * beat) * hurry
            x, y = x + cos(a) * speed * SIM_DT, y + sin(a) * speed * SIM_DT
            k["x"], k["y"], k["a"] = x, y, a
            nodes, seg = k["nodes"], L / (N - 1)
            nodes[0] = (x, y)
            bx, by = -cos(a), -sin(a)
            for j in range(1, N):
                px, py = nodes[j - 1]
                vx, vy = nodes[j][0] - px, nodes[j][1] - py
                d = hypot(vx, vy) or 1
                vx, vy = vx / d, vy / d
                bend = atan2(bx * vy - by * vx, bx * vx + by * vy)
                if abs(bend) > BEND:
                    r = BEND if bend > 0 else -BEND
                    vx, vy = bx * cos(r) - by * sin(r), bx * sin(r) + by * cos(r)
                nodes[j] = (px + vx * seg, py + vy * seg)
                bx, by = vx, vy
            k["phase"] += SIM_DT * (2.6 + 5 * beat)
            reach = L * 0.27
            xs, ys = [n[0] for n in nodes], [n[1] for n in nodes]
            seen = max(xs) + reach > 0 and min(xs) - reach < w and max(ys) + reach > 0 and min(ys) - reach < h
            k["seen"] = k["seen"] or seen
            if k["seen"] and not seen and len(k["via"]) <= 1 and (not left or t > feed["land"] + 20):
                k["done"] = True
            elif seen and step % 8 == 0:
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
                k["frames"].append((step * SIM_DT, spine, 1 + scull - bank, 1 - scull + bank))
    return [k["frames"] for k in koi], eaten


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


def frame_svg(cells, shadow, shade, cls, P):
    """One frame of a koi in cells, from its top-left cell: its shadow, then one path per paint.
    A paint is a cell-sized pattern holding the tile and its glyph, so a frame names each paint
    once and writes no glyphs of its own."""
    c0 = min(c for c, _ in list(cells) + list(shadow))
    r0 = min(r for _, r in list(cells) + list(shadow))
    runs = {}
    for (c, r), paint in cells.items():
        runs.setdefault(paint, []).append((c - c0, r - r0))
    out = [f'<path class="{cls("s", hexc(P["shadow"]), shade)}" d="{cell_path((c - c0, r - r0) for c, r in shadow)}"/>'] if shadow else []
    out += [f'<path class="{cls("p", paint)}" d="{cell_path(d)}"/>' for paint, d in runs.items()]
    return c0, r0, "".join(out)


def wordmark(title, w, P):
    """The title drawn like "One Page" on the course page: the letters are
    sampled from the font outline into character cells, and each cell gets a
    glyph by how much of it the letter covers, white fading to grey across the
    word. On load the cells flicker through random glyphs and settle into the
    word; afterwards a thin accent glint crosses it now and then."""
    from PIL import Image, ImageDraw, ImageFont
    cw, ch = title["cell"]
    ss = 4
    path, index = TITLE_FONTS[title["font"]]
    font = ImageFont.truetype(path, round(title["size"] * ss), index=index)
    cells = []
    for line, (text, top) in enumerate(title["lines"]):
        left, upper, right, lower = font.getbbox(text)
        img = Image.new("L", (right - left, lower - upper), 0)
        ImageDraw.Draw(img).text((-left, -upper), text, font=font, fill=255)
        img = img.resize((round(img.width * title["squeeze"]), img.height), Image.LANCZOS)
        cols, rows = -(-img.width // (cw * ss)), -(-img.height // (ch * ss))
        pad = Image.new("L", (cols * cw * ss, rows * ch * ss), 0)
        pad.paste(img, (0, 0))
        cover = pad.resize((cols, rows), Image.BOX).load()
        x0 = round((w - cols * cw) / 2) if title["align"] == "center" else title["x"]
        for r in range(rows):
            for c in range(cols):
                v = cover[c, r] / 255
                if v >= 0.12:
                    cells.append((x0 + c * cw + cw / 2, top + r * ch + ch / 2, v, h2(c + 1000 * line, r)))
    fs = round(ch * 0.8)
    x_lo, x_hi = min(x for x, *_ in cells), max(x for x, *_ in cells)

    def text(cls, style, group):
        xs = " ".join(num(x) for x, _, _ in group)
        ys = " ".join(num(y + fs * 0.36) for _, y, _ in group)
        return f'<text class="{cls}" style="{style}" x="{xs}" y="{ys}">{esc("".join(g for _, _, g in group))}</text>'

    final, settle, glint = {}, {}, {}
    for x, y, v, k in cells:
        g = ("#" if k < 0.5 else "@") if v > 0.82 else "%" if v > 0.55 else "+" if v > 0.32 else ":"
        at = round(0.15 + k * 0.95, 1)
        final.setdefault(at, []).append((x, y, g))
        settle.setdefault(at, []).append((x, y))
        glint.setdefault(x, []).append((x, y, g))
    out = [text("tf", f"animation-delay:{num(at)}s", group) for at, group in sorted(final.items())]
    # Before it settles each cell flips between two random glyphs, brightening as it goes.
    for at, group in sorted(settle.items()):
        flips = "".join(
            text("nf", f"animation-delay:{num(m * FRAME)}s",
                 [(x, y, NOISE[int(h2(round(x) * 7 + m, round(y) * 13) * len(NOISE))]) for x, y in group])
            for m in range(2))
        out.append(f'<g class="tn" style="animation: rise {num(at)}s linear both, gone 0.01s {num(at)}s forwards">{flips}</g>')
    # The glint: a band about a twentieth of the word wide, crossing it every GLINT_PERIOD seconds.
    gl = []
    for x, group in sorted(glint.items()):
        u = (x - x_lo) / ((x_hi - x_lo) or 1)
        gl.append(text("gl", f"animation-delay:{num((u - GLINT_HALF + 0.45) / GLINT_SPEED)}s", group))
    css = (f".tf {{ animation: settle 0.12s ease-out both; }} "
           f"@keyframes settle {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }} "
           f".nf {{ opacity: 0; animation: flick {num(2 * FRAME)}s step-end infinite; }} "
           f"@keyframes flick {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
           f"@keyframes rise {{ from {{ opacity: 0.25; }} to {{ opacity: 0.75; }} }} "
           f"@keyframes gone {{ to {{ opacity: 0; }} }} "
           f".gl {{ opacity: 0; animation: glint {num(GLINT_PERIOD)}s step-end infinite; }} "
           f"@keyframes glint {{ 0% {{ opacity: 1; }} {2 * GLINT_HALF / GLINT_SPEED / GLINT_PERIOD * 100:.3f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}")
    svg = (f'<defs><linearGradient id="tg" gradientUnits="userSpaceOnUse" x1="{num(x_lo)}" y1="0" x2="{num(x_hi)}" y2="0">'
           f'<stop stop-color="{hexc(P["title"][0])}"/><stop offset="1" stop-color="{hexc(P["title"][1])}"/></linearGradient></defs>'
           f'<g font-family="{MONO}" font-weight="600" font-size="{fs}" text-anchor="middle">'
           f'<g fill="url(#tg)">{"".join(out)}</g><g fill="{hexc(P["glint"])}">{"".join(gl)}</g></g>')
    box = (min(x for x, *_ in cells) - cw, min(y for _, y, *_ in cells) - ch, x_hi + cw, max(y for _, y, *_ in cells) + ch)
    return svg, css, box


# ── the koi on screen: each one's pass as frames, and the pellets thrown to one of them ──

FLIGHT = 4 * FRAME          # seconds a pellet is in the air
RING_LIFE = 9 * FRAME       # a landing or a gulp leaves a small ring for this long


SPLASH_LIFE = 2.6          # the handful hitting the water leaves a wide double ring this long, like the paw on the course page


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


def feeding(i, feed, spots, eaten, cycle, T0, cw, ch, gy, P):
    """The pellets: thrown in from the near bank, a splash where the handful lands, then each one
    afloat until a koi eats it, with a ring where it lands and where it goes."""
    food, food_g, shadow = hexc(P["food"]), hexc(mul(P["food"], 0.55)), hexc(P["shadow"])
    hx, hy = feed["hand"]

    def delay(t):
        return num(-((T0 - t) % cycle))

    def at(c, r):
        return f'x="{c * cw + cw // 2}" y="{r * ch + gy}"'

    css, out = [], []
    # The handful hitting the water: a wide ring of glyphs, a fainter ring of dots behind it.
    cx, cy = feed["at"]
    for m in range(round(SPLASH_LIFE / FRAME)):
        age = (m + 0.5) * FRAME
        for lag, glyphs, strength in ((0, None, 0.62), (0.38, "·", 0.32)):
            if age <= lag:
                continue
            cells = [rc for rc in ring(cx, cy, ((age - lag) * 74 + 26) * feed["k"], cw, ch) if rc[:2] not in spots]
            if not cells:
                continue
            alpha = (1 - age / SPLASH_LIFE) ** 1.5 * strength
            xs = " ".join(str(c * cw + cw // 2) for c, _, _ in cells)
            ys = " ".join(str(r * ch + gy) for _, r, _ in cells)
            text = "".join(glyphs or gl for _, _, gl in cells)
            out.append(f'<text class="e e{i}" style="animation-delay:{delay(feed["land"] + m * FRAME)}s" fill-opacity="{num(alpha)}" '
                       f'x="{xs}" y="{ys}">{esc(text)}</text>')
    for j, (c0, r0) in enumerate(spots):
        px, py = c0 * cw + cw / 2, r0 * ch + ch / 2
        t_land, t_eat = feed["lands"][j], eaten[j]
        # In the air: high up it shows as "o", low as ".", with its shadow parting from it and closing in.
        for m in range(round(FLIGHT / FRAME)):
            u = (m + 0.5) / round(FLIGHT / FRAME)
            x, y, hh = lerp(hx, px, u), lerp(hy, py, u), 4 * u * (1 - u)
            c, r = floor(x / cw), floor(y / ch)
            sc, sr = round(hh * 3), round(hh * 2)
            out.append(f'<g class="e e{i}" style="animation-delay:{delay(t_land - FLIGHT + m * FRAME)}s">'
                       f'<rect x="{(c + sc) * cw}" y="{(r + sr) * ch}" width="{cw - 1}" height="{ch - 1}" fill="{shadow}" fill-opacity="0.25"/>'
                       f'<text fill="{food}" {at(c, r)}>{"o" if hh > 0.4 else "."}</text></g>')
        # Afloat until the koi gets there.
        css.append(f"@keyframes q{i}_{j} {{ 0% {{ opacity: 1; }} {(t_eat - t_land) / cycle * 100:.4f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".q{i}_{j} {{ animation: q{i}_{j} {num(cycle)}s step-end infinite; }}")
        out.append(f'<g class="e q{i}_{j}" style="animation-delay:{delay(t_land)}s">'
                   f'<rect x="{c0 * cw}" y="{r0 * ch}" width="{cw - 1}" height="{ch - 1}" fill="{food}"/>'
                   f'<text fill="{food_g}" {at(c0, r0)}>o</text></g>')
        # A faint ring where it lands, a clearer one where it is eaten. Rings pass under the pellets afloat.
        for t0, strength in ((t_land, 0.32), (t_eat, 0.6)):
            for m in range(round(RING_LIFE / FRAME)):
                age = (m + 0.5) * FRAME
                cells = [rc for rc in ring(px, py, (age * 34 + 4) * feed["k"], cw, ch) if rc[:2] not in spots]
                if not cells:
                    continue
                alpha = (1 - age / RING_LIFE) ** 1.5 * strength
                xs = " ".join(str(c * cw + cw // 2) for c, _, _ in cells)
                ys = " ".join(str(r * ch + gy) for _, r, _ in cells)
                out.append(f'<text class="e e{i}" style="animation-delay:{delay(t0 + m * FRAME)}s" fill-opacity="{num(alpha)}" '
                           f'x="{xs}" y="{ys}">{esc("".join(gl for _, _, gl in cells))}</text>')
    return css, out


def sized(fish, k):
    """The koi at scale k: longer, and faster in proportion, as on the course page."""
    return [dict(f, L=f["L"] * k, cruise=f["cruise"] * k) for f in fish]


def banner(w, h, pond, cell, fish, title, subtitle, avoid, koi=None, feed=None, k=1):
    P = palette(pond, koi)
    cw, ch = cell
    fs = round(ch * 0.74)
    gy = round(ch / 2 + fs * 0.36)
    dot = hexc(P["dot"])
    names = {}

    def cls(kind, *key):
        return names.setdefault((kind,) + key, f"{kind}{len(names)}")

    css, koi, wakes, feeds = [], [], [], []
    # The koi with "feeds" swim as one group on the feed's cycle and share its pellets; the rest swim alone.
    fish = sized(fish, k)
    runs = {}
    group = [f for f in fish if f.get("feeds")]
    if feed:
        spots = scatter(feed, cw, ch)
        lands = [feed["throw"] + FLIGHT + FRAME * round(h2(j, 3) * (len(spots) - 1) / 2) for j in range(len(spots))]
        feed = dict(feed, k=k, lands=lands, land=min(lands), pellets=[(c * cw + cw / 2, r * ch + ch / 2) for c, r in spots])
        passes, eaten = swim(group, w, h, feed)
        assert len(eaten) == len(spots), "some pellets were never eaten"
        for f, frames in zip(group, passes):
            runs[id(f)] = (frames, feed["cycle"], feed["at_load"])
    for f in fish:
        if not f.get("feeds"):
            runs[id(f)] = (swim([f], w, h)[0][0], f["cycle"], f["at"])
    for i, f in enumerate(sorted(fish, key=lambda f: f["depth"])):
        frames, cycle, T0 = runs[id(f)]
        assert frames[-1][0] < cycle - 1, f"koi {f['seed']} needs a longer cycle than {cycle}s"
        f = dict(f, marks=markings(f["variety"], f["seed"]))
        skin = palette(pond, f.get("colours", koi))     # a koi may carry its own colour scheme

        def delay(t):
            return num(-((T0 - t) % cycle))

        # Each frame shows for one FRAME of the koi's cycle; the rest of the cycle it is out of sight.
        css.append(f"@keyframes k{i} {{ 0% {{ opacity: 1; }} {FRAME / cycle * 100 + 0.001:.4f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".f{i} {{ opacity: 0; animation: k{i} {num(cycle)}s step-end infinite; }}")
        still = round(f.get("still", 0.5) * (len(frames) - 1))
        tail = None
        for k, (t, spine, fl, fr) in enumerate(frames):
            cells, shadow, shade = rasterise(f, spine, fl, fr, cw, ch, skin)
            c0, r0, body = frame_svg(cells, shadow, shade, cls, P)
            koi.append(f'<g class="f{i}{" st" if k == still else ""}" style="animation-delay:{delay(t)}s" '
                       f'transform="matrix({cw} 0 0 {ch} {c0 * cw} {r0 * ch + ch / 2:g})">{body}</g>')
            # The wake: a speck in each cell the tail tip moves into, fading behind it.
            tc = (floor(spine[-1][0] / cw), floor(spine[-1][1] / ch))
            if tc != tail and 0 <= tc[0] * cw < w and 0 <= tc[1] * ch < h:
                wakes.append(f'<text class="w w{i}" style="animation-delay:{delay(t)}s" x="{tc[0] * cw + cw // 2}" y="{tc[1] * ch + gy}">:</text>')
            tail = tc
        hold, gone = 0.6 / cycle * 100, 2.5 / cycle * 100
        css.append(f"@keyframes w{i} {{ 0% {{ opacity: 0.42; }} {num(hold)}% {{ opacity: 0.42; }} {num(gone)}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".w{i} {{ animation: w{i} {num(cycle)}s linear infinite; }}")
    if feed:
        cycle = feed["cycle"]
        css.append(f"@keyframes ex {{ 0% {{ opacity: 1; }} {FRAME / cycle * 100 + 0.001:.4f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".ex {{ animation: ex {num(cycle)}s step-end infinite; }}")
        f_css, f_out = feeding("x", feed, spots, eaten, cycle, feed["at_load"], cw, ch, gy, P)
        css += f_css
        feeds += f_out
    # Paints: a tile and its glyph in one cell-sized pattern, drawn in the frames' cell units.
    # Patterns start half a cell up because the frames' paths run along the middle of each row.
    paints, colours = [], []
    for key, n in names.items():
        if key[0] == "s":
            colours.append(f".{n} {{ stroke: {key[1]}; stroke-opacity: {num(key[2])}; stroke-width: 1px; stroke-dasharray: none; }}")
            continue
        tile, (g, g_c, g_a) = key[1]
        rect = f'<rect width="1" height="1" fill="{tile[0]}" fill-opacity="{num(tile[1])}"/>' if tile else ""
        glyph = (f'<text transform="scale({1 / cw:.5g} {1 / ch:.5g})" x="{cw / 2:g}" y="{gy}" fill="{g_c}" fill-opacity="{num(g_a)}">'
                 f'{esc(g)}</text>') if g != " " else ""
        paints.append(f'<pattern id="{n}" width="1" height="1" y="-.5" patternUnits="userSpaceOnUse">{rect}{glyph}</pattern>')
        colours.append(f".{n} {{ stroke: url(#{n}); }}")
    colours = " ".join(colours)
    frames_off = ", ".join(f".f{i}" for i in range(len(fish)))
    specks = []
    for r in range(h // ch + 1):
        for c in range(w // cw + 1):
            k = h2(c, r)
            if k < 0.022:
                specks.append(f'<text class="tw" style="animation-delay:{num(-((k * 900) % (2 * pi)) / 0.9)}s" '
                              f'x="{c * cw + cw // 2}" y="{r * ch + gy}">·</text>')
    mark, mark_css, mark_box = wordmark(title, w, P)
    sub_x = w / 2 if title["align"] == "center" else title["x"]
    sub = "".join(f'<text x="{num(sub_x)}" y="{y}">{esc(line)}</text>' for line, y in zip(subtitle["lines"], subtitle["ys"]))
    avoid = avoid or [mark_box[:3] + (subtitle["ys"][-1] + subtitle["size"] // 2,)]
    veils = "".join(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{cw * 3}"/>' for x0, y0, x1, y1 in avoid)
    glyph_font = f'font-family="{MONO}" font-weight="600" font-size="{fs}" text-anchor="middle"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Song of Hero. Haojie Song, an AI explorer at the dawn of a magnificent age.">
  <style>
    {colours}
    {" ".join(css)}
    .st {{ opacity: 1; }}
    .w, .e {{ opacity: 0; }}
    .tw {{ opacity: 0.7; animation: twinkle 7s ease-in-out infinite; }}
    @keyframes twinkle {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
    {mark_css}
    @media (prefers-reduced-motion: reduce) {{ {frames_off}, .w, .tw, .e, .tf {{ animation: none; }} .tn, .gl {{ display: none; }} }}
  </style>
  <defs>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="{14 if w > 1000 else 18}"/></clipPath>
    <filter id="soft" x="-20%" y="-60%" width="140%" height="220%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="{round(cw * 2.2)}"/></filter>
    <g {glyph_font}>{"".join(paints)}</g>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{hexc(P["water"])}"/>
    <g {glyph_font} fill="{dot}" fill-opacity="0.22">{"".join(specks)}</g>
    <g {glyph_font} fill="{dot}">{"".join(wakes)}</g>
    <g {glyph_font} fill="none" stroke-width="{(ch - 1) / ch:.5g}" stroke-dasharray="{(cw - 1) / cw:.5g} {1 / cw:.5g}">{"".join(koi)}</g>
    <g {glyph_font} fill="{dot}">{"".join(feeds)}</g>
    <g fill="{hexc(P["water"])}" fill-opacity="0.88" filter="url(#soft)">{veils}</g>
  </g>
  {mark}
  <g font-family="{MONO}" font-size="{subtitle["size"]}" font-weight="500" letter-spacing="0.02em" fill="{P["ink"]}"{' text-anchor="middle"' if title["align"] == "center" else ""}>{sub}</g>
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


# Each koi makes one pass through the pond per cycle: it enters at `enter` (x, y, heading),
# steers for each point of `via` in turn while it wanders, and is out of sight for the rest
# of its cycle. at: seconds into its cycle when the banner loads (picked so open water is
# never empty). L and cruise are the course page's (128-180 long, 24-36 px/s); each banner
# scales them by its k like the page's opening screen, where the koi are 1.85 times that,
# so they cross the pond on the slant, as there. Varieties and seeds start with the course
# page's shoal, so those markings match. colours: a KOI_COLOURS scheme.
# Koi with "feeds" swim on the feed's cycle instead: a handful of pellets is thrown from
# `hand` at `throw` seconds, lands around `at`, and they all rush it from different sides,
# each after its `notice` delay.
DESKTOP_K = 1.85
DESKTOP_FEED = {"at": (1050, 245), "count": 11, "spread": 50, "hand": (1110, 340), "throw": 0.8, "cycle": 26, "at_load": 0}
DESKTOP_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 150, "depth": 0.95, "cruise": 32, "colours": "course", "feeds": True,
     "enter": (1330, 330, -2.6), "via": [(640, -330)], "still": 0.35},
    {"variety": "sanke", "seed": 110, "L": 140, "depth": 0.7, "cruise": 32, "colours": "vermilion", "feeds": True,
     "enter": (820, 560, -1.0), "via": [(1500, -200)], "delay": 0.3, "notice": 0.3},
    {"variety": "tancho", "seed": 207, "L": 135, "depth": 0.5, "cruise": 30, "colours": "gold", "feeds": True,
     "enter": (1200, -260, 1.95), "via": [(880, 600)], "delay": 0.2, "notice": 0.5},
    {"variety": "kohaku", "seed": 304, "L": 145, "depth": 0.8, "cruise": 30, "cycle": 24, "at": 9, "colours": "sakura",
     "enter": (90, -270, 1.25), "via": [(260, 560)]},
    {"variety": "kohaku", "seed": 498, "L": 135, "depth": 0.65, "cruise": 30, "cycle": 27, "at": 21, "colours": "vermilion",
     "enter": (-280, 330, -0.75), "via": [(420, -260)]},
    {"variety": "sanke", "seed": 401, "L": 130, "depth": 0.55, "cruise": 28, "cycle": 25, "at": 6, "colours": "gold",
     "enter": (720, 570, -1.95), "via": [(380, -280)]},
    {"variety": "tancho", "seed": 595, "L": 140, "depth": 0.6, "cruise": 30, "cycle": 28, "at": 22, "colours": "course",
     "enter": (1000, -260, 2.25), "via": [(520, 570)]},
    {"variety": "sanke", "seed": 692, "L": 128, "depth": 0.4, "cruise": 28, "cycle": 29, "at": 16, "colours": "sakura",
     "enter": (-270, 20, 0.55), "via": [(560, 580)]},
]
MOBILE_K = 2.0
MOBILE_FEED = {"at": (560, 540), "count": 11, "spread": 60, "hand": (620, 680), "throw": 0.8, "cycle": 28, "at_load": 0}
MOBILE_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 150, "depth": 0.95, "cruise": 32, "colours": "course", "feeds": True,
     "enter": (1080, 470, pi + 0.15), "via": [(-400, 640)], "still": 0.35},
    {"variety": "sanke", "seed": 110, "L": 140, "depth": 0.7, "cruise": 32, "colours": "vermilion", "feeds": True,
     "enter": (-300, 520, 0.1), "via": [(1150, 400)], "delay": 0.3, "notice": 0.3},
    {"variety": "tancho", "seed": 207, "L": 135, "depth": 0.5, "cruise": 30, "colours": "gold", "feeds": True,
     "enter": (450, 900, -1.3), "via": [(200, 950)], "delay": 0.2, "notice": 0.5},
    {"variety": "kohaku", "seed": 304, "L": 145, "depth": 0.8, "cruise": 30, "cycle": 30, "at": 25, "colours": "sakura",
     "enter": (1100, 260, 2.6), "via": [(-350, 700)]},
    {"variety": "sanke", "seed": 401, "L": 130, "depth": 0.6, "cruise": 30, "cycle": 24, "at": 5, "colours": "gold",
     "enter": (-300, 380, 0.45), "via": [(900, 900)]},
]


LAYOUT = "center"
FONT = "georgia"


def banners(pond, out=OUT, layout=LAYOUT, font=FONT, koi=None):
    center = layout == "center"
    size = {"georgia": 160, "didot": 172}[font]
    write("song-of-hero.svg", banner(
        1200, 290, pond, cell=(8, 10), fish=DESKTOP_KOI,
        title={"lines": [("Song of Hero", 26)], "font": font, "size": size, "squeeze": 0.8, "cell": (8, 10),
               "align": layout, "x": 52},
        subtitle={"lines": ["An AI explorer at the dawn of a magnificent age."], "size": 22, "ys": [218]},
        avoid=None, koi=koi, feed=DESKTOP_FEED, k=DESKTOP_K,
    ), out)
    write("song-of-hero-mobile.svg", banner(
        800, 600, pond, cell=(11, 14), fish=MOBILE_KOI,
        title={"lines": [("Song of", 18), ("Hero", 214)], "font": font, "size": size * 1.25, "squeeze": 0.85, "cell": (11, 14),
               "align": layout, "x": 40},
        subtitle={"lines": ["An AI explorer at the dawn", "of a magnificent age."], "size": 32, "ys": [408, 450]},
        avoid=None if center else [(20, 0, 640, 200), (20, 200, 560, 466)], koi=koi, feed=MOBILE_FEED, k=MOBILE_K,
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
