"""Build the profile banner and project cards as SVG.

Run from the repository root: python3 assets/build.py

The banner is one pixel sunrise. The sun is drawn from contribution-graph
cells and rises one row at a time; its light spreads outward as an ordered
dither, ring by ring. After that only the sea below the horizon keeps
moving, one cell at a time, with a few slow stars. Reduced-motion users get
a still, finished frame.
"""

from math import hypot, sin
from pathlib import Path

OUT = Path(__file__).resolve().parent

SERIF = "Georgia, 'Iowan Old Style', 'Palatino Linotype', 'Times New Roman', serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"

INK = "#f7f1e3"
AMBER = "#e9a23b"
# Sun levels, edge to core: ember, orange, amber, gold, white-hot.
SUN = ["#8f4512", "#d8711f", "#f2a23a", "#ffd27a", "#fff1c6"]
HALO = "#d97a22"
WAVE = "#22324f"
# Sun light on the water, edge to centre: darker and more saturated than the sun itself.
GLINT = ["#9c4a16", "#dc7425", "#f6ad45"]
# Seconds per sway cycle for each sea row; unequal so the rows never move in lockstep.
SWAY = [2.4, 3.2, 2.0]
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]

# The sun climbs one row per step; each step waits longer than the last.
RISE_END = 78
EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)"


def esc(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rise_keyframes(rows, pitch):
    frames = []
    for i in range(rows + 1):
        pct = round(RISE_END * (i / rows) ** 1.5)
        frames.append(f"{pct}% {{ transform: translateY({(rows - i) * pitch}px); }}")
    frames.append("100% { transform: translateY(0); }")
    return "@keyframes rise { " + " ".join(frames) + " }"


def banner(w, h, horizon, sun_x, radius, halo, cell, gap, title, subtitle, title_size,
           sub_size, title_xy, sub_lines_y, stars, rows, reflect, avoid):
    pitch = cell + gap
    sun_y = horizon + pitch * 0.6
    core, rings = [], [[] for _ in range(3)]
    x0 = sun_x - radius - halo
    col0 = int(x0 // pitch)
    for col in range(col0, int((sun_x + radius + halo) // pitch) + 2):
        for row in range(int((horizon - radius - halo) // pitch) - 1, int(horizon // pitch) + rows + 1):
            x, y = col * pitch, row * pitch
            if y + cell > horizon + rows * pitch:
                continue
            d = hypot(x + cell / 2 - sun_x, y + cell / 2 - sun_y)
            if d <= radius:
                t = d / radius
                level = 4 if t < 0.42 else 3 if t < 0.66 else 2 if t < 0.84 else 1 if t < 0.95 else 0
                core.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{SUN[level]}"/>')
            elif d <= radius + halo and y + cell <= horizon:
                t = (d - radius) / halo
                light = (1 - t) ** 2
                if light * 16 > BAYER[row % 4][col % 4] + 0.5:
                    rings[min(2, int(t * 3))].append(
                        f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                        f'fill="{HALO}" fill-opacity="{0.16 + 0.42 * light:.2f}"/>'
                    )
    # Sea below the horizon: wave crests drawn as flat grid cells. Under the sun the crests
    # turn warm and dense, a glitter path. Each row sways one cell sideways in steps, out of
    # phase with its neighbours, so the water moves on the same grid the sun rises on.
    first = int(horizon // pitch) + 1
    bar = round(cell * 0.6)
    sea, sway_css = [], []
    for k in range(reflect):
        y = first * pitch + k * pitch + (cell - bar) // 2
        base, glint = [], []
        for col in range(-2, int(w // pitch) + 3):
            x = col * pitch
            warm = max(0.0, 1 - abs(x + cell / 2 - sun_x) / (radius * (1.0 + 0.3 * k)))
            if warm > 0 and warm ** 1.1 * 16 > BAYER[k % 4][col % 4] + 0.5:
                tone = GLINT[2] if warm > 0.7 else GLINT[1] if warm > 0.4 else GLINT[0]
                glint.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{bar}" rx="2" fill="{tone}" fill-opacity="{0.5 + 0.45 * warm - 0.08 * k:.2f}"/>')
            elif sin(col * 0.62 + k * 2.1) + 0.5 * sin(col * 0.23 - k) > 0.55:
                base.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{bar}" rx="2" fill="{WAVE}" fill-opacity="{0.4 + 0.12 * k:.2f}"/>')
        sea.append(f'<g class="w w{k}">{"".join(base)}<g class="glint">{"".join(glint)}</g></g>')
        shift = pitch if k % 2 == 0 else -pitch
        sway_css.append(
            f"@keyframes sway{k} {{ 0% {{ transform: translateX(0); }} 50% {{ transform: translateX({shift}px); }} }}"
            f" .w{k} {{ animation: sway{k} {SWAY[k % 3]}s {0.4 * k:.1f}s infinite; animation-timing-function: step-end; }}"
        )
    star_marks = []
    for i, (sx, sy, size, op) in enumerate(stars):
        if avoid[0] <= sx <= avoid[2] and avoid[1] <= sy <= avoid[3]:
            continue
        cls = f' class="tw tw{i % 3}"' if i % 6 == 0 else ""
        star_marks.append(f'<rect{cls} x="{sx}" y="{sy}" width="{size}" height="{size}" fill="#fff" fill-opacity="{op}"/>')
    glow_cy = sun_y / h
    halo_groups = "".join(f'<g class="ring r{i}">{"".join(cells)}</g>' for i, cells in enumerate(rings))
    sub = "".join(
        f'<text x="{title_xy[0] + 4}" y="{y}" font-family="{SERIF}" font-size="{sub_size}" '
        f'font-style="italic" fill="{INK}" fill-opacity="0.82">{esc(line)}</text>'
        for line, y in zip(subtitle, sub_lines_y)
    )
    land = 0.15 + 2.4 * RISE_END / 100
    ring_css = " ".join(
        f".r{i} {{ animation: light 0.01s {land + 0.18 * i:.2f}s both; }}" for i in range(3)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Song of Hero. Haojie Song, an AI explorer at the dawn of a magnificent age.">
  <style>
    .sun {{ animation: rise 2.4s 0.15s both; animation-timing-function: step-end; }}
    {rise_keyframes(rows, pitch)}
    @keyframes light {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
    {ring_css}
    .glow {{ animation: glow 2.8s 0.15s {EASE_OUT} both; }}
    .glint {{ animation: light 1.2s {land - 0.6:.2f}s {EASE_OUT} both; }}
    {' '.join(sway_css)}
    @keyframes glow {{ from {{ opacity: 0.15; }} to {{ opacity: 1; }} }}
    .tw {{ animation: twinkle 6s ease-in-out infinite; }}
    .tw1 {{ animation-duration: 7.5s; animation-delay: 1.5s; }}
    .tw2 {{ animation-duration: 9s; animation-delay: 3s; }}
    @keyframes twinkle {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
    @media (prefers-reduced-motion: reduce) {{ .sun, .ring, .glow, .glint, .w, .tw {{ animation: none; }} }}
  </style>
  <defs>
    <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#05080f"/><stop offset="{0.55 * horizon / h:.3f}" stop-color="#0a1020"/>
      <stop offset="{0.86 * horizon / h:.3f}" stop-color="#171226"/><stop offset="{horizon / h:.3f}" stop-color="#3a1b10"/>
    </linearGradient>
    <radialGradient id="glow" cx="{sun_x / w:.3f}" cy="{glow_cy:.3f}" r="0.5">
      <stop offset="0" stop-color="#ffb04a" stop-opacity="0.55"/><stop offset="0.45" stop-color="#c2571a" stop-opacity="0.16"/><stop offset="1" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#f5b94a" stop-opacity="0.08"/><stop offset="{sun_x / w:.3f}" stop-color="#ffd27a" stop-opacity="1"/><stop offset="1" stop-color="#f5b94a" stop-opacity="0.15"/>
    </linearGradient>
    <clipPath id="c"><rect width="{w}" height="{h}" rx="{14 if w > 1000 else 18}"/></clipPath>
  </defs>
  <g clip-path="url(#c)">
    <rect width="{w}" height="{h}" fill="url(#sky)"/>
    {''.join(star_marks)}
    <rect class="glow" width="{w}" height="{h}" fill="url(#glow)"/>
    {halo_groups}
    <g class="sun">{''.join(core)}</g>
    <rect x="0" y="{horizon}" width="{w}" height="{h - horizon}" fill="#05070c"/>
    {''.join(sea)}
    <rect x="0" y="{horizon - 0.5}" width="{w}" height="{1.5 if w > 1000 else 2}" fill="url(#line)"/>
  </g>
  <text x="{title_xy[0]}" y="{title_xy[1]}" font-family="{SERIF}" font-size="{title_size}" font-weight="700" fill="{INK}">{esc(title)}</text>
  {sub}
</svg>
"""


def scatter(w, top, bottom, n, seed):
    out, s = [], seed
    for i in range(n):
        s = (s * 1103515245 + 12345) % 2**31
        x = s % w
        s = (s * 1103515245 + 12345) % 2**31
        y = top + s % (bottom - top)
        size = 2 if i % 5 else 3
        op = [0.25, 0.4, 0.6, 0.85][i % 4]
        out.append((x, y, size, op))
    return out


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


def write(name, svg):
    lines = (line.rstrip() for line in svg.splitlines())
    (OUT / name).write_text("\n".join(line for line in lines if line) + "\n")


def main():
    subtitle = ["An AI explorer at the dawn of a magnificent age."]
    write("song-of-hero.svg", banner(
        1200, 290, horizon=236, sun_x=930, radius=124, halo=60, cell=13, gap=4,
        title="Song of Hero", subtitle=subtitle, title_size=80, sub_size=26,
        title_xy=(60, 146), sub_lines_y=[192], stars=scatter(1200, 10, 220, 46, 7), rows=6,
        reflect=3, avoid=(40, 70, 680, 205),
    ))
    write("song-of-hero-mobile.svg", banner(
        800, 500, horizon=420, sun_x=560, radius=150, halo=80, cell=15, gap=5,
        title="Song of Hero", subtitle=["An AI explorer at the dawn", "of a magnificent age."],
        title_size=100, sub_size=40, title_xy=(48, 150), sub_lines_y=[220, 270],
        stars=scatter(800, 12, 400, 40, 11), rows=6, reflect=3, avoid=(30, 60, 780, 285),
    ))
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
