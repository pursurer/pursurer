"""Build the profile banner and project cards as SVG.

Run from the repository root: python3 assets/build.py

The banner is a koi pond seen from above, drawn in character cells like the
koi pond on my n8n course page. Each koi is a spine with a travelling body
wave. Every cell is sampled against the spine, classified as body, fin, eye,
ridge or barbel, coloured by the fish's markings and shaded by a light from
the upper left. An SVG image cannot run scripts, so each koi is drawn as a
loop of tail-beat poses that flip in place while the whole fish glides
across; the wake and the specks in the water are timed to match. Koi fade
under the title. Reduced-motion users get a still pond.
"""

from math import cos, floor, hypot, inf, pi, sin, sqrt, tan
from pathlib import Path

OUT = Path(__file__).resolve().parent

SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

INK = "#f7f1e3"
AMBER = "#e9a23b"

# "normal" is the course page's own pond; "lake" is lake water with the page's dark-mode koi.
PONDS = {
    "normal": {"water": "#d6cebf", "accent": "#9e3214", "light": "#f7f2e8", "black": "#2b2723",
               "ink": "#1c1a17", "dark": False},
    "lake": {"water": "#2d6a68", "accent": "#e8784f", "light": "#ece6da", "black": "#3a3632",
             "ink": "#f3efe4", "dark": True},
}
# Shadow on the pond floor: colour as a share of the water, and its strength.
SHADOW = {"normal": (0.55, 0.22), "lake": (0.35, 0.36)}
POND = "lake"

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


def banner(w, h, pond, cell, fish, title, subtitle, title_size, sub_size, title_xy, sub_lines_y, avoid):
    P = palette(pond)
    cw, ch = cell
    fs = round(ch * 0.74)
    dot = hexc(P["dot"])
    css, shadows, bodies, wakes = [], [], [], []
    for i, f in enumerate(sorted(fish, key=lambda f: f["depth"])):
        f = dict(f, marks=markings(f["variety"], f["seed"]))
        L, a = f["L"], f["a"]
        right = cos(a) > 0
        x0 = -0.12 * L if right else w + 0.12 * L
        x1 = w + 1.12 * L if right else -1.12 * L
        y0 = f["y"]
        y1 = y0 + (x1 - x0) * tan(a)
        dur = hypot(x1 - x0, y1 - y0) / f["speed"]
        at = f["at"]
        hx, hy = lerp(x0, x1, at), lerp(y0, y1, at)
        css.append(f"@keyframes m{i} {{ from {{ transform: translate({num(x0)}px, {num(y0)}px); }} "
                   f"to {{ transform: translate({num(x1)}px, {num(y1)}px); }} }} "
                   f".m{i} {{ animation: m{i} {num(dur)}s {num(-at * dur)}s linear infinite; }}")
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
            u = (c * cw + cw / 2 + L * cos(a) - x0) / (x1 - x0)
            ty = lerp(y0, y1, u) - L * sin(a)
            if not 0 <= u <= 1 or not 0 <= ty < h:
                continue
            delay = num(((u - at) * dur) % dur - dur)
            wakes.append(f'<text class="w w{i}" style="animation-delay:{delay}s" x="{num(c * cw + cw / 2)}" '
                         f'y="{num(floor(ty / ch) * ch + ch / 2 + fs * 0.36)}">:</text>')
    specks = []
    for r in range(h // ch + 1):
        for c in range(w // cw + 1):
            k = h2(c, r)
            if k < 0.022:
                specks.append(f'<text class="tw" style="animation-delay:{num(-((k * 900) % (2 * pi)) / 0.9)}s" '
                              f'x="{num(c * cw + cw / 2)}" y="{num(r * ch + ch / 2 + fs * 0.36)}">·</text>')
    sub = "".join(
        f'<text x="{title_xy[0] + 4}" y="{y}" font-family="{SERIF}" font-size="{sub_size}" '
        f'font-style="italic" fill="{P["ink"]}" fill-opacity="0.8">{esc(line)}</text>'
        for line, y in zip(subtitle, sub_lines_y)
    )
    ax0, ay0, ax1, ay1 = avoid
    glyph_font = f'font-family="{MONO}" font-weight="600" font-size="{fs}" text-anchor="middle"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Song of Hero. Haojie Song, an AI explorer at the dawn of a magnificent age.">
  <style>
    .p {{ opacity: 0; animation: pose {num(BEAT_T)}s step-end infinite; }}
    .p0 {{ opacity: 1; }}
    @keyframes pose {{ 0% {{ opacity: 1; }} {100 / POSES + 0.01:.2f}% {{ opacity: 0; }} 100% {{ opacity: 0; }} }}
    {" ".join(css)}
    .w {{ opacity: 0; }}
    .tw {{ opacity: 0.7; animation: twinkle 7s ease-in-out infinite; }}
    @keyframes twinkle {{ 0%, 100% {{ opacity: 0.45; }} 50% {{ opacity: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{ .p, .m, .w, .tw {{ animation: none; }} }}
  </style>
  <defs>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="{14 if w > 1000 else 18}"/></clipPath>
    <filter id="soft" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="{round(cw * 2.2)}"/></filter>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="{hexc(P["water"])}"/>
    <g {glyph_font} fill="{dot}" fill-opacity="0.22">{"".join(specks)}</g>
    {"".join(shadows)}
    <g {glyph_font} fill="{dot}">{"".join(wakes)}</g>
    <g {glyph_font} fill="none" stroke-width="{ch - 1}" stroke-dasharray="{cw - 1} 1">{"".join(bodies)}</g>
    <rect x="{ax0}" y="{ay0}" width="{ax1 - ax0}" height="{ay1 - ay0}" rx="{cw * 3}" fill="{hexc(P["water"])}" fill-opacity="0.88" filter="url(#soft)"/>
  </g>
  <text x="{title_xy[0]}" y="{title_xy[1]}" font-family="{SERIF}" font-size="{title_size}" font-weight="700" fill="{P["ink"]}">{esc(title)}</text>
  {sub}
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


# Varieties and seeds are the first four koi of the course page, so their markings match.
# a: heading in radians; at: where along its crossing the koi is when the banner loads.
DESKTOP_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 270, "a": -0.03, "y": 205, "speed": 46, "depth": 0.95, "at": 0.68, "beat_at": 0.0},
    {"variety": "sanke", "seed": 110, "L": 240, "a": pi + 0.03, "y": 100, "speed": 38, "depth": 0.6, "at": 0.3, "beat_at": 0.4},
    {"variety": "tancho", "seed": 207, "L": 215, "a": 0.035, "y": 60, "speed": 33, "depth": 0.4, "at": 0.3, "beat_at": 0.7},
    {"variety": "kohaku", "seed": 304, "L": 245, "a": pi - 0.02, "y": 240, "speed": 41, "depth": 0.8, "at": 0.62, "beat_at": 0.2},
]
MOBILE_KOI = [
    {"variety": "kohaku", "seed": 13, "L": 380, "a": -0.03, "y": 432, "speed": 46, "depth": 0.95, "at": 0.52, "beat_at": 0.0},
    {"variety": "sanke", "seed": 110, "L": 330, "a": pi + 0.03, "y": 330, "speed": 38, "depth": 0.6, "at": 0.2, "beat_at": 0.4},
    {"variety": "tancho", "seed": 207, "L": 300, "a": 0.03, "y": 175, "speed": 33, "depth": 0.4, "at": 0.35, "beat_at": 0.7},
]


def banners(pond, out=OUT):
    write("song-of-hero.svg", banner(
        1200, 290, pond, cell=(8, 10), fish=DESKTOP_KOI,
        title="Song of Hero", subtitle=["An AI explorer at the dawn of a magnificent age."], title_size=80, sub_size=26,
        title_xy=(60, 146), sub_lines_y=[192], avoid=(40, 70, 680, 205),
    ), out)
    write("song-of-hero-mobile.svg", banner(
        800, 500, pond, cell=(11, 14), fish=MOBILE_KOI,
        title="Song of Hero", subtitle=["An AI explorer at the dawn", "of a magnificent age."],
        title_size=100, sub_size=40, title_xy=(48, 150), sub_lines_y=[220, 270], avoid=(30, 60, 780, 285),
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
