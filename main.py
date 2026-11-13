"""The Night Whale — a galaxy-filled whale swimming across a dusk sky,
raining tiny stars onto a quiet sea, watched by one small lighthouse.

Pure Python 3 standard library. Deterministic: no time, no randomness,
no network. Writes one PNG to $MAKEFUN_OUTPUT_DIR/entry.png (default /output).
"""

import os
import struct
import zlib
from math import cos, pi, sin, sqrt

W = H = 1024
HY = 800  # horizon line: sea below this


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def hash2(x, y):
    """Deterministic integer hash in [0, 1)."""
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


# ---- whale geometry (column profiles) -------------------------------------
WX0, WX1 = 150, 905  # whale spans these columns (tail stock at WX0, nose at WX1)


def whale_profiles():
    top = [None] * W
    bot = [None] * W
    for x in range(WX0, WX1):
        t = (x - WX0) / (WX1 - WX0)  # 0 at tail, 1 at nose
        cy = 372 - 46 * sin(pi * t)  # body arches gently upward mid-swim
        belly = sin(pi * (t ** 0.82)) ** 0.75
        half = 26 + 128 * belly
        if t > 0.80:  # round the nose off instead of a flat face
            s = (t - 0.80) / 0.20
            half *= 1 - 0.72 * s * s
        if t < 0.08:  # narrow the tail stock into the fluke
            half *= 0.45 + 0.55 * (t / 0.08)
        top[x] = cy - half
        bot[x] = cy + half * 0.82 + 10 * sin(pi * t)  # a gentle belly sag
    return top, bot


def in_rot_ellipse(x, y, cx, cy, rx, ry, ang):
    ca, sa = cos(ang), sin(ang)
    dx, dy = x - cx, y - cy
    u = (dx * ca + dy * sa) / rx
    v = (-dx * sa + dy * ca) / ry
    return u * u + v * v <= 1.0


# nebula blobs inside the whale: (cx, cy, radius, colour)
NEBULA = [
    (430, 330, 210, (150, 60, 170)),
    (620, 300, 170, (40, 150, 190)),
    (760, 380, 130, (240, 120, 150)),
    (300, 400, 130, (70, 90, 200)),
]

# falling-star drops under the whale: column -> (gap below belly, length)
def make_drops(bot):
    drops = {}
    for i in range(46):
        x = 200 + (i * 149) % 640
        if bot[x] is None:
            continue
        drops[x] = (6 + (i * 37) % 60, 26 + (i * 53) % 90)
    return drops


# ---- sky gradient (per row) ------------------------------------------------
def sky_row_color(y):
    t = y / HY
    if t < 0.55:
        return mix((7, 10, 36), (27, 18, 68), t / 0.55)
    if t < 0.85:
        return mix((27, 18, 68), (80, 34, 92), (t - 0.55) / 0.30)
    return mix((80, 34, 92), (232, 122, 92), (t - 0.85) / 0.15)


def sea_row_color(y):
    t = (y - HY) / (H - HY)
    return mix((38, 20, 58), (3, 5, 20), t)


def render():
    top, bot = whale_profiles()
    drops = make_drops(bot)
    rows = []
    for y in range(H):
        row = bytearray(W * 3)
        in_sea = y >= HY
        base_row = sea_row_color(y) if in_sea else sky_row_color(y)
        # cloud band curves for this row are tested per-pixel with these params
        for x in range(W):
            r, g, b = base_row

            if not in_sea:
                # --- stars in the open sky
                h = hash2(x >> 1, y >> 1)
                if h > 0.9965 and y < 640:
                    tw = (h - 0.9965) / 0.0035
                    r += 150 * tw; g += 150 * tw; b += 170 * tw
                # --- soft cloud bands
                for (by, thick, ph, dark) in ((150, 30, 0.0, 0.20), (560, 44, 2.1, 0.16), (668, 34, 4.0, 0.13)):
                    yc = by + 20 * sin(x * 0.004 + ph)
                    d = abs(y - yc)
                    if d < thick:
                        a = (1 - d / thick) * dark
                        r = r * (1 - a) + 16 * a; g = g * (1 - a) + 10 * a; b = b * (1 - a) + 40 * a

                # --- the whale
                in_whale = False
                if top[x] is not None and top[x] <= y <= bot[x]:
                    in_whale = True
                elif 55 <= x <= 240 and 235 <= y <= 510:
                    # tail fluke: two swept ellipses rooted at the tail stock (x=150)
                    if in_rot_ellipse(x, y, 148, 300, 80, 25, -0.42) or in_rot_ellipse(x, y, 148, 446, 80, 25, 0.42):
                        in_whale = True
                if in_whale:
                    t = (x - WX0) / (WX1 - WX0)
                    cr, cg, cb = mix((13, 16, 50), (30, 90, 130), t)
                    cr, cg, cb = mix((cr, cg, cb), (86, 40, 138), 0.5 + 0.5 * sin(x * 0.006 + y * 0.004))
                    for (cx, cy, rad, col) in NEBULA:
                        dx, dy = x - cx, y - cy
                        d2 = dx * dx + dy * dy
                        if d2 < rad * rad:
                            a = (1 - sqrt(d2) / rad) ** 2 * 0.55
                            cr = cr * (1 - a) + col[0] * a; cg = cg * (1 - a) + col[1] * a; cb = cb * (1 - a) + col[2] * a
                    hs = hash2(x, y)
                    if hs > 0.986:  # stars inside the galaxy body
                        tw = (hs - 0.986) / 0.014
                        cr += 210 * tw; cg += 200 * tw; cb += 190 * tw
                    if top[x] is not None and 0 <= y - top[x] < 9:  # warm rim light on the back
                        a = 1 - (y - top[x]) / 9
                        cr = cr * (1 - a * 0.7) + 255 * a * 0.7; cg = cg * (1 - a * 0.7) + 150 * a * 0.7; cb = cb * (1 - a * 0.7) + 130 * a * 0.7
                    r, g, b = cr, cg, cb
                    # pectoral fin: darker swept ellipse low on the body, mostly inside it
                    if in_rot_ellipse(x, y, 648, 428, 62, 16, 0.9):
                        r *= 0.45; g *= 0.45; b *= 0.55
                    # the eye: one small warm light
                    dx, dy = x - 806, y - 356
                    if dx * dx + dy * dy < 30:
                        r, g, b = 255, 214, 150
                else:
                    # --- falling stars under the belly
                    d = drops.get(x) or drops.get(x - 1)
                    if d is not None and bot[x] is not None:
                        start = bot[x] + d[0]
                        if start <= y <= start + d[1]:
                            fade = 1 - (y - start) / d[1]
                            r += 190 * fade; g += 130 * fade; b += 60 * fade
            else:
                # --- sea: a soft whale-glow on the water, broken into sparkles
                dxn = (x - 520) / 330.0
                env = max(0.0, 1 - dxn * dxn) ** 2
                fade = 1 - (y - HY) / (H - HY)
                glow = env * fade * (0.30 + 0.16 * sin(y * 0.22 + 1.7 * sin(x * 0.021)))
                r += 58 * glow; g += 26 * glow; b += 40 * glow
                if env > 0.05 and hash2(x // 6, y) > 0.90:  # short glittering dashes
                    tw = (hash2(x // 6, y) - 0.90) / 0.10 * env * fade
                    r += 120 * tw; g += 80 * tw; b += 90 * tw
                h = hash2(x >> 1, (y * 7) >> 1)
                if h > 0.9975:  # sparse star reflections
                    tw = (h - 0.9975) / 0.0025
                    r += 90 * tw; g += 85 * tw; b += 110 * tw
                if y - HY < 2:  # horizon glow line
                    r += 70; g += 34; b += 30

            # --- lighthouse (drawn over sky base / sea), lamp halo first
            ldx, ldy = x - 118, y - 672
            ld2 = ldx * ldx + ldy * ldy
            if ld2 < 3600:
                a = (1 - sqrt(ld2) / 60) * 0.5
                r = r * (1 - a) + 255 * a; g = g * (1 - a) + 196 * a; b = b * (1 - a) + 110 * a
            if 96 <= x <= 140 and 686 <= y <= HY:  # tower, trapezoid by rows
                half = 9 + (y - 686) * 0.075
                if abs(x - 118) <= half:
                    if ((y - 686) // 19) % 2 == 0:
                        r, g, b = 214, 62, 52
                    else:
                        r, g, b = 238, 232, 222
            if 104 <= x <= 132 and 664 <= y < 686:  # lamp room
                r, g, b = 24, 20, 30
                if ld2 < 42:
                    r, g, b = 255, 208, 120
            if in_sea and y <= 826:  # the rock it stands on
                if in_rot_ellipse(x, y, 118, 818, 78, 17, 0.0):
                    r, g, b = 10, 9, 20

            # --- vignette
            vx, vy = (x - 512) / 512.0, (y - 512) / 512.0
            q = vx * vx + vy * vy
            if q > 0.55:
                f = 1 - min(0.38, (q - 0.55) * 0.42)
                r *= f; g *= f; b *= f

            i = x * 3
            row[i] = 255 if r > 255 else (0 if r < 0 else int(r))
            row[i + 1] = 255 if g > 255 else (0 if g < 0 else int(g))
            row[i + 2] = 255 if b > 255 else (0 if b < 0 else int(b))
        rows.append(bytes(row))
    return rows


def write_png(path, rows):
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(kind, data):
        c = struct.pack(">I", len(data)) + kind + data
        return c + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    write_png(os.path.join(out_dir, "entry.png"), render())


if __name__ == "__main__":
    main()
