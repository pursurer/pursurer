"""Build the profile banner and project cards as SVG.

Run from the repository root: python3 assets/build.py

The banner is a koi pond seen from above, drawn in character cells like the
koi pond on my n8n course page. Each koi is a spine with a travelling body
wave. Every cell is sampled against the spine, classified as body, fin, eye,
ridge or barbel, coloured by the fish's markings and shaded by a light from
the upper left. An SVG image cannot run scripts, so each koi is drawn as a
loop of tail-beat poses that flip in place while the whole fish glides
across; the wake and the specks in the water are timed to match. Koi fade
under the title, a character-cell wordmark like "One Page" on the course
page (its font is rasterised with Pillow).
Once a loop a handful of pellets is thrown in ahead of the front koi: it
hurries over, slows down and eats them one by one. Reduced-motion users get
a still pond.
"""

from math import cos, floor, hypot, inf, pi, sin, sqrt
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

N = 10                      # spine nodes per koi
RAMP = " .:-=+*#%@"         # sparse glyphs on lit skin, dense ones in shadow
SUB = [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)]
POSES = 12                  # tail-beat poses per loop
FRAME = 0.09                # seconds per pose: a round number keeps every delay exact
BEAT = 0.6
BEAT_T = POSES * FRAME
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


def palette(name):
    p = PONDS[name]
    dark, water, light, black, accent = p["dark"], rgb(p["water"]), rgb(p["light"]), rgb(p["black"]), rgb(p["accent"])
    return {
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
    """(kind, across, rs, ra) or None. Kinds: 1 body, 2 fin, 4 ridge, 5 barbel; pose() places the eyes (3)."""
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


# ── one pose: the koi with its head at the origin, rasterised into cells ──

def pose(fish, phase, cw, ch, P):
    L, a, depth = fish["L"], fish["a"], fish["depth"]
    hx, hy, seg = cos(a), sin(a), fish["L"] / (N - 1)
    swim = 0.25 + 0.9 * BEAT
    spine = []
    for n in range(N):
        s = n / (N - 1)
        off = L * 0.045 * (0.05 + 0.95 * s ** 2.2) * swim * sin(phase - s * 4.6)
        spine.append((-hx * seg * n - hy * off, -hy * seg * n + hx * off))
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
    scull = 0.15 * (1 - BEAT) * sin(phase)
    flare_l, flare_r = 1 + scull, 1 - scull

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
                tile, t_a = P["fin"], (0.26 if P["dark"] else 0.3) * cover * alpha
                g_c, g_a = mul(P["fin"], 1.1 if P["dark"] else 0.62), (0.55 if P["dark"] else 0.42) * alpha
            else:
                nz = sqrt(max(0, 1 - across * across))
                lit = clamp(0.76 + 0.26 * nz + 0.2 * (-ty * side * across * lx + tx * side * across * ly), 0.62, 1.08)
                lit = round(lit / 0.04) * 0.04
                sk = None if kind == 3 else skin(fish["marks"], fish["seed"], s, v / L, across)
                base = P["eye"] if kind == 3 else P["red"] if sk == 1 else P["black"] if sk == 2 else P["white"]
                tile, t_a = mul(base, lit), (1 if cover >= 0.6 else cover * 1.4) * alpha
                if kind == 3:
                    g, g_c, g_a = "o", P["white"], 0.95 * alpha
                else:
                    idx = clamp(1 + round((1.08 - lit) / 0.46 * 6) + (2 if kind == 4 else 0), 1, len(RAMP) - 1)
                    g = RAMP[idx]
                    g_c = mul(base, (0.55 if sk == 0 else 1.35) if P["dark"] else 0.5)
                    g_a = 0.62 * alpha
                if cover >= 0.6:
                    shadow.add((c + sdc, r + sdr))
            cells[(c, r)] = (tile and (hexc(tile), round(t_a * 20) / 20), (g, hexc(g_c), round(g_a * 20) / 20))
    return cells, shadow, shade


def cell_path(cells, cw, ch, gap=0):
    """Cells as thick horizontal strokes, one per run of neighbours in a row.

    Drawn with stroke-width ch - gap and a dash of cw - gap, each run still
    shows separate tiles with a gap between them."""
    runs = []
    for c, r in sorted(cells, key=lambda k: (k[1], k[0])):
        if runs and runs[-1][1] == r and runs[-1][0] + runs[-1][2] == c:
            runs[-1][2] += 1
        else:
            runs.append([c, r, 1])
    out, end = [], None
    for c, r, n in runs:
        x, y, ln = c * cw + gap / 2, r * ch + ch / 2, n * cw - gap
        out.append(f"M{num(x)} {num(y)}" if end is None else f"m{num(x - end[0])} {num(y - end[1])}")
        out.append(f"h{num(ln)}")
        end = (x + ln, y)
    return "".join(out)


def pose_svg(cells, cw, ch, fs):
    """Tiles grouped into one path per colour, glyphs into one text per colour."""
    tiles, glyphs = {}, {}
    for (c, r), (tile, (g, g_c, g_a)) in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        if tile:
            tiles.setdefault(tile, []).append((c, r))
        if g != " ":
            glyphs.setdefault((g_c, g_a), []).append((c * cw + cw / 2, round(r * ch + ch / 2 + fs * 0.36, 1), g))
    out = [f'<path stroke="{col}" stroke-opacity="{num(a)}" d="{cell_path(d, cw, ch, 1)}"/>' for (col, a), d in tiles.items()]
    for (col, a), gs in glyphs.items():
        xs = " ".join(num(x) for x, _, _ in gs)
        ys = " ".join(num(y) for _, y, _ in gs)
        out.append(f'<text fill="{col}" fill-opacity="{num(a)}" x="{xs}" y="{ys}">{esc("".join(g for _, _, g in gs))}</text>')
    return "".join(out)


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


# ── how a koi crosses the banner, and the pellets thrown in ahead of one ──

FLIGHT = 6 * FRAME          # seconds a pellet is in the air
RING_LIFE = 12 * FRAME      # a landing or a gulp leaves a small ring for this long
THROW = 185                 # how far the koi's snout is from the food when the pellets are thrown


def ray_out(x, y, dx, dy, m, w, h):
    """How far from (x, y) along (dx, dy) the ray leaves the banner grown by m on every side."""
    t = inf
    if dx:
        t = min(t, ((w + m if dx > 0 else -m) - x) / dx)
    if dy:
        t = min(t, ((h + m if dy > 0 else -m) - y) / dy)
    return t


def glide(f, w, h):
    """The straight line a koi swims along, and when its snout is where.

    The line runs through (w / 2, y) at heading a, from where the whole koi is
    still out of sight to where its tail has left. A koi with a feed hurries
    once the pellets land, brakes as it reaches them and picks them off at
    under half speed."""
    L, a = f["L"], f["a"]
    back = ray_out(w / 2, f["y"], -cos(a), -sin(a), 0.12 * L, w, h)
    x0, y0 = w / 2 - cos(a) * back, f["y"] - sin(a) * back
    length = back + ray_out(w / 2, f["y"], cos(a), sin(a), 1.12 * L, w, h)
    feed = f.get("feed")
    s_food = (feed["x"] - x0) / cos(a) if feed else 0

    def pace(s):
        if not feed:
            return 1
        d = s - s_food
        return 1 + 0.6 * sstep(-175, -120, d) - 1.1 * sstep(-100, -25, d) + 0.5 * sstep(40, 140, d)

    ss, ts = [0.0], [0.0]
    while ss[-1] < length:
        s = min(length, ss[-1] + 2)
        ts.append(ts[-1] + (s - ss[-1]) / (f["speed"] * pace((s + ss[-1]) / 2)))
        ss.append(s)

    def t_at(s):
        k = clamp(int(s // 2), 0, len(ss) - 2)
        return lerp(ts[k], ts[k + 1], clamp((s - ss[k]) / ((ss[k + 1] - ss[k]) or 1), 0, 1))

    def s_at(t):
        lo, hi = 0, len(ts) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            lo, hi = (mid, hi) if ts[mid] <= t else (lo, mid)
        return lerp(ss[lo], ss[hi], clamp((t - ts[lo]) / ((ts[hi] - ts[lo]) or 1), 0, 1))

    marks = [0.0, length]
    if feed:
        marks[1:1] = [s_food + d for d in range(-200, 160, 10)]
    keys = [(t_at(s) / ts[-1] * 100, x0 + cos(a) * s, y0 + sin(a) * s) for s in marks]
    return {"x0": x0, "y0": y0, "length": length, "dur": ts[-1], "t_at": t_at, "s_at": s_at,
            "keys": keys, "food": (x0 + cos(a) * s_food, y0 + sin(a) * s_food), "s_food": s_food}


def ring(cx, cy, age, k, cw, ch):
    """A small ring spreading from (cx, cy), as in the course page: glyphs along it, fading as it grows."""
    R = (age * 34 + 4) * k
    out = []
    for r in range(floor((cy - R - ch) / ch), floor((cy + R + ch) / ch) + 1):
        for c in range(floor((cx - R - cw) / cw), floor((cx + R + cw) / cw) + 1):
            dx, dy = c * cw + cw / 2 - cx, r * ch + ch / 2 - cy
            if abs(hypot(dx, dy) - R) <= cw * 0.62:
                out.append((c, r, line_glyph(-dy, dx)))
    return out


def feeding(i, f, g, T0, w, h, cw, ch, fs, P):
    """Pellets thrown in from the near bank ahead of koi i; each one it reaches is gone with a gulp."""
    dur, a, feed = g["dur"], f["a"], f["feed"]
    fx, fy = g["food"]
    nx, ny = -sin(a), cos(a)
    k_ring = cw / 8
    food, food_g, shadow = hexc(P["food"]), hexc(mul(P["food"], 0.55)), hexc(P["shadow"])
    t_throw = g["t_at"](g["s_food"] - THROW) - FLIGHT
    hand = (fx + feed["hand"], h + 3 * ch)

    def delay(t):
        return num(-((T0 - t) % dur))

    def cxy(c, r):
        return f'x="{num(c * cw + cw / 2)}" y="{num(r * ch + ch / 2 + fs * 0.36)}"'

    css = [f"@keyframes e{i} {{ 0% {{ opacity: 1; }} {FRAME / dur * 100 + 0.001:.4f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
           f".e{i} {{ animation: e{i} {num(dur)}s step-end infinite; }}"]
    out, taken = [], set()
    n = feed["pellets"]
    pellets, tries = [], 0
    while len(pellets) < n:
        # Scattered over the koi's path and to either side of its snout, never two in touching cells.
        tries += 1
        d = lerp(-26, 40, h2(tries, 7))
        e = (h2(tries, 11) - 0.5) * 2 * feed["spread"]
        cell = (floor((fx + cos(a) * d + nx * e) / cw), floor((fy + sin(a) * d + ny * e) / ch))
        gap = 1 if tries < 400 else 0       # a crowded patch may put pellets side by side
        if all(max(abs(cell[0] - c), abs(cell[1] - r)) > gap for c, r in taken):
            taken.add(cell)
            pellets.append((d, cell))
    for j, (d, cell) in enumerate(pellets):
        px, py = cell[0] * cw + cw / 2, cell[1] * ch + ch / 2
        t_land = t_throw + 0.1 * round(h2(j, 3) * (n - 1)) + FLIGHT
        t_eat = g["t_at"](g["s_food"] + d)
        # In the air: high up it shows as "o", low as ".", with its shadow parting from it and closing in.
        for m in range(round(FLIGHT / FRAME)):
            u = (m + 0.5) / round(FLIGHT / FRAME)
            x, y, hh = lerp(hand[0], px, u), lerp(hand[1], py, u), 4 * u * (1 - u)
            c, r = floor(x / cw), floor(y / ch)
            if not 0 <= r * ch < h:
                continue
            sc, sr = round(hh * 3), round(hh * 2)
            out.append(f'<g class="e e{i}" style="animation-delay:{delay(t_land - FLIGHT + m * FRAME)}s">'
                       f'<rect x="{(c + sc) * cw}" y="{(r + sr) * ch}" width="{cw - 1}" height="{ch - 1}" fill="{shadow}" fill-opacity="0.25"/>'
                       f'<text fill="{food}" {cxy(c, r)}>{"o" if hh > 0.4 else "."}</text></g>')
        # Afloat until the koi gets there.
        css.append(f"@keyframes q{i}_{j} {{ 0% {{ opacity: 1; }} {(t_eat - t_land) / dur * 100:.4f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".q{i}_{j} {{ animation: q{i}_{j} {num(dur)}s step-end infinite; }}")
        out.append(f'<g class="e q{i}_{j}" style="animation-delay:{delay(t_land)}s">'
                   f'<rect x="{cell[0] * cw}" y="{cell[1] * ch}" width="{cw - 1}" height="{ch - 1}" fill="{food}"/>'
                   f'<text fill="{food_g}" {cxy(*cell)}>o</text></g>')
        # A faint ring where it lands, a clearer one where it is eaten. Rings pass under the pellets afloat.
        for t0, strength in ((t_land, 0.32), (t_eat, 0.6)):
            for m in range(round(RING_LIFE / FRAME)):
                age = (m + 0.5) * FRAME
                cells = [rc for rc in ring(px, py, age, k_ring, cw, ch) if rc[:2] not in taken]
                if not cells:
                    continue
                alpha = (1 - age / RING_LIFE) ** 1.5 * strength
                xs = " ".join(num(c * cw + cw / 2) for c, _, _ in cells)
                ys = " ".join(num(r * ch + ch / 2 + fs * 0.36) for _, r, _ in cells)
                out.append(f'<text class="e e{i}" style="animation-delay:{delay(t0 + m * FRAME)}s" fill-opacity="{num(alpha)}" '
                           f'x="{xs}" y="{ys}">{esc("".join(gl for _, _, gl in cells))}</text>')
    return css, out


def banner(w, h, pond, cell, fish, title, subtitle, avoid):
    P = palette(pond)
    cw, ch = cell
    fs = round(ch * 0.74)
    dot = hexc(P["dot"])
    css, shadows, bodies, wakes, feeds = [], [], [], [], []
    for i, f in enumerate(sorted(fish, key=lambda f: f["depth"])):
        f = dict(f, marks=markings(f["variety"], f["seed"]))
        L, a = f["L"], f["a"]
        g = glide(f, w, h)
        x0, y0, dur = g["x0"], g["y0"], g["dur"]
        # T0: where the koi is in its loop when the banner loads. A feeding koi starts a little before the throw.
        if "feed" in f:
            T0 = (g["t_at"](g["s_food"] - THROW) - FLIGHT - f["feed"]["after"]) % dur
            f_css, f_out = feeding(i, f, g, T0, w, h, cw, ch, fs, P)
            css += f_css
            feeds += f_out
        else:
            T0 = f["at"] * dur
        s0 = g["s_at"](T0)
        hx, hy = x0 + cos(a) * s0, y0 + sin(a) * s0
        keys = " ".join(f"{pct:.3f}% {{ transform: translate({num(x)}px, {num(y)}px); }}" for pct, x, y in g["keys"])
        css.append(f"@keyframes m{i} {{ {keys} }} "
                   f".m{i} {{ animation: m{i} {num(dur)}s {num(-T0)}s linear infinite; }}")
        move = f'<g class="m m{i}" transform="translate({num(hx)} {num(hy)})">'
        lag = round(f["beat_at"] * POSES)
        body_frames = []
        for j in range(POSES):
            cells, shade_cells, shade = pose(f, 2 * pi * j / POSES, cw, ch, P)
            delay = num(((j - lag) % POSES - POSES) * FRAME)
            cls = "p p0" if j == 0 else "p"
            body_frames.append(f'<g class="{cls}" style="animation-delay:{delay}s">{pose_svg(cells, cw, ch, fs)}</g>')
            if j == 0:
                shadows.append(f'{move}<path stroke="{hexc(P["shadow"])}" stroke-opacity="{num(shade)}" '
                               f'stroke-width="{ch}" d="{cell_path(shade_cells, cw, ch)}"/></g>')
        bodies.append(move + "".join(body_frames) + "</g>")
        # The wake: a speck in each column the tail tip crosses, timed to the fish's loop.
        hold, gone = 0.6 / dur * 100, 2.5 / dur * 100
        css.append(f"@keyframes w{i} {{ 0% {{ opacity: 0.42; }} {num(hold)}% {{ opacity: 0.42; }} {num(gone)}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }} "
                   f".w{i} {{ animation: w{i} {num(dur)}s linear infinite; }}")
        for c in range(i % 2, w // cw + 1, 2):
            s = (c * cw + cw / 2 + L * cos(a) - x0) / cos(a)
            ty = y0 + sin(a) * s - L * sin(a)
            if not 0 <= s <= g["length"] or not 0 <= ty < h:
                continue
            delay = num(-((T0 - g["t_at"](s)) % dur))
            wakes.append(f'<text class="w w{i}" style="animation-delay:{delay}s" x="{num(c * cw + cw / 2)}" '
                         f'y="{num(floor(ty / ch) * ch + ch / 2 + fs * 0.36)}">:</text>')
    specks = []
    for r in range(h // ch + 1):
        for c in range(w // cw + 1):
            k = h2(c, r)
            if k < 0.022:
                specks.append(f'<text class="tw" style="animation-delay:{num(-((k * 900) % (2 * pi)) / 0.9)}s" '
                              f'x="{num(c * cw + cw / 2)}" y="{num(r * ch + ch / 2 + fs * 0.36)}">·</text>')
    mark, mark_css, mark_box = wordmark(title, w, P)
    sub_x = w / 2 if title["align"] == "center" else title["x"]
    sub = "".join(f'<text x="{num(sub_x)}" y="{y}">{esc(line)}</text>' for line, y in zip(subtitle["lines"], subtitle["ys"]))
    avoid = avoid or [mark_box[:3] + (subtitle["ys"][-1] + subtitle["size"] // 2,)]
    veils = "".join(f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" rx="{cw * 3}"/>' for x0, y0, x1, y1 in avoid)
    glyph_font = f'font-family="{MONO}" font-weight="600" font-size="{fs}" text-anchor="middle"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Song of Hero. Haojie Song, an AI explorer at the dawn of a magnificent age.">
  <style>
    .p {{ opacity: 0; animation: pose {num(BEAT_T)}s step-end infinite; }}
    .p0 {{ opacity: 1; }}
    @keyframes pose {{ 0% {{ opacity: 1; }} {100 / POSES + 0.01:.2f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    {" ".join(css)}
    .w, .e {{ opacity: 0; }}
    .tw {{ opacity: 0.7; animation: twinkle 7s ease-in-out infinite; }}
    @keyframes twinkle {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
    {mark_css}
    @media (prefers-reduced-motion: reduce) {{ .p, .m, .w, .tw, .e, .tf {{ animation: none; }} .tn, .gl {{ display: none; }} }}
  </style>
  <defs>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="{14 if w > 1000 else 18}"/></clipPath>
    <filter id="soft" x="-20%" y="-60%" width="140%" height="220%" color-interpolation-filters="sRGB"><feGaussianBlur stdDeviation="{round(cw * 2.2)}"/></filter>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{hexc(P["water"])}"/>
    <g {glyph_font} fill="{dot}" fill-opacity="0.22">{"".join(specks)}</g>
    {"".join(shadows)}
    <g {glyph_font} fill="{dot}">{"".join(wakes)}</g>
    <g {glyph_font} fill="none" stroke-width="{ch - 1}" stroke-dasharray="{cw - 1} 1">{"".join(bodies)}</g>
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


# The shoal of the course page's pond band: six koi 128-180 long cruising at 24-36 px/s, varieties
# and seeds in its order so their markings match, tilted a little up or down as they wander.
# y: where the koi's line crosses the middle of the banner; a: heading in radians;
# at: where along its crossing the koi is when the banner loads.
# feed: pellets land around x on this koi's path, thrown from the bank below, `after` seconds after load.
DESKTOP_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 170, "a": -0.02, "y": 264, "speed": 30, "depth": 0.95, "beat_at": 0.0,
     "feed": {"x": 930, "pellets": 7, "spread": 24, "hand": 40, "after": 1.5}},
    {"variety": "sanke", "seed": 110, "L": 150, "a": pi + 0.2, "y": 150, "speed": 27, "depth": 0.6, "at": 0.1, "beat_at": 0.4},
    {"variety": "tancho", "seed": 207, "L": 140, "a": 0.24, "y": 120, "speed": 25, "depth": 0.45, "at": 0.8, "beat_at": 0.7},
    {"variety": "kohaku", "seed": 304, "L": 165, "a": pi - 0.1, "y": 70, "speed": 32, "depth": 0.8, "at": 0.15, "beat_at": 0.2},
    {"variety": "sanke", "seed": 401, "L": 135, "a": -0.28, "y": 190, "speed": 28, "depth": 0.5, "at": 0.85, "beat_at": 0.55},
    {"variety": "kohaku", "seed": 498, "L": 155, "a": pi + 0.06, "y": 40, "speed": 34, "depth": 0.7, "at": 0.35, "beat_at": 0.85},
]
MOBILE_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 225, "a": -0.03, "y": 540, "speed": 40, "depth": 0.95, "beat_at": 0.0,
     "feed": {"x": 560, "pellets": 7, "spread": 24, "hand": 50, "after": 1.5}},
    {"variety": "sanke", "seed": 110, "L": 200, "a": pi + 0.25, "y": 330, "speed": 36, "depth": 0.6, "at": 0.15, "beat_at": 0.4},
    {"variety": "tancho", "seed": 207, "L": 190, "a": 0.3, "y": 200, "speed": 34, "depth": 0.45, "at": 0.8, "beat_at": 0.7},
    {"variety": "kohaku", "seed": 304, "L": 210, "a": pi - 0.12, "y": 90, "speed": 38, "depth": 0.8, "at": 0.3, "beat_at": 0.2},
]


LAYOUT = "center"
FONT = "georgia"


def banners(pond, out=OUT, layout=LAYOUT, font=FONT):
    center = layout == "center"
    size = {"georgia": 160, "didot": 172}[font]
    write("song-of-hero.svg", banner(
        1200, 290, pond, cell=(8, 10), fish=DESKTOP_KOI,
        title={"lines": [("Song of Hero", 26)], "font": font, "size": size, "squeeze": 0.8, "cell": (8, 10),
               "align": layout, "x": 52},
        subtitle={"lines": ["An AI explorer at the dawn of a magnificent age."], "size": 22, "ys": [218]},
        avoid=None,
    ), out)
    write("song-of-hero-mobile.svg", banner(
        800, 600, pond, cell=(11, 14), fish=MOBILE_KOI,
        title={"lines": [("Song of", 18), ("Hero", 214)], "font": font, "size": size * 1.25, "squeeze": 0.85, "cell": (11, 14),
               "align": layout, "x": 40},
        subtitle={"lines": ["An AI explorer at the dawn", "of a magnificent age."], "size": 32, "ys": [408, 450]},
        avoid=None if center else [(20, 0, 640, 200), (20, 200, 560, 466)],
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
