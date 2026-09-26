#!/usr/bin/env python3
"""
renderer.py  (stage 1)

Turns an image into lines of ANSI-coloured text a terminal can display.

Used by the next stages as:
    render(path, width=44, mode="braille", style="chalk", colors="truecolor") -> list[str]

Every returned line is exactly `width` character cells wide and ends with a
reset code, so the layout stage can put text next to it without misalignment.
"""
import argparse
import sys

from PIL import Image, ImageFilter, ImageOps

RESET = "\x1b[0m"

# The source panel is black-and-white, so ALL colour here is a choice, not something
# recovered from the image. A theme is either:
#   (top, bottom)                       -- one blend, top to bottom (the original style)
#   (top_left, top_right, bot_left, bot_right) -- a 4-corner blend, varying left/right too
# Ink strength always still controls brightness on top of whatever colour this picks.
THEMES = {
    "violet":  ((122, 162, 247), (187, 154, 247)),   # blue -> violet
    "ice":     ((137, 220, 235), (205, 214, 244)),   # cyan -> soft white
    "ember":   ((255, 158, 100), (247, 118, 142)),   # orange -> rose
    "matrix":  ((120, 220, 120), (190, 240, 150)),   # green
    "mono":    ((170, 170, 178), (235, 235, 240)),   # plain grey, closest to the original
    # 4-corner themes: genuinely multicoloured, blending across both axes.
    "aurora":  ((110, 231, 183), (99, 179, 237), (168, 129, 244), (247, 118, 142)),   # teal / blue / violet / rose
    "sunset":  ((255, 190, 110), (247, 118, 142), (187, 134, 252), (99, 122, 247)),   # amber / rose / violet / indigo
    "citrus":  ((240, 230, 120), (150, 220, 130), (255, 160, 90),  (240, 90, 120)),   # yellow / green / orange / red
}


def corners(tint):
    """Normalize a theme to 4 corners: (top_left, top_right, bot_left, bot_right)."""
    if len(tint) == 2:
        top, bottom = tint
        return top, top, bottom, bottom
    return tint
# "paper" style colours (dark ink on a light card, like the original panel).
PAPER, INK = (236, 236, 242), (26, 27, 38)

# Braille dot bit values, indexed [row][col] inside one 2x4 cell.
BRAILLE_BITS = ((0x01, 0x08), (0x02, 0x10), (0x04, 0x20), (0x40, 0x80))


# ---------------------------------------------------------------- colour ---
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def to_256(rgb):
    """Nearest xterm-256 palette index (fallback for terminals without true-colour)."""
    r, g, b = (int(round(v)) for v in rgb)
    if max(r, g, b) - min(r, g, b) < 10:              # greys: use the 24-step grey ramp
        grey = round((r + g + b) / 3)
        if grey < 8:
            return 16
        if grey > 248:
            return 231
        return 232 + round((grey - 8) / 247 * 23)
    cube = lambda v: round(v / 255 * 5)               # 6x6x6 colour cube
    return 16 + 36 * cube(r) + 6 * cube(g) + cube(b)


def sgr(rgb, layer, colors):
    """SGR parameters for a foreground (38) or background (48). None = terminal default."""
    if rgb is None:
        return "39" if layer == 38 else "49"
    if colors == "256":
        return f"{layer};5;{to_256(rgb)}"
    r, g, b = (int(round(v)) for v in rgb)
    return f"{layer};2;{r};{g};{b}"


def emit_row(cells, colors):
    """cells: list of (char, fg, bg). fg None = keep current, bg None = default background.
    Only emits an escape when the colour actually changes, which keeps the output small."""
    out, pfg, pbg = [], "39", "49"                    # state right after a reset
    for ch, fg, bg in cells:
        f = pfg if fg is None else sgr(fg, 38, colors)
        b = sgr(bg, 48, colors)
        changed = [c for c, p in ((f, pfg), (b, pbg)) if c != p]
        if changed:
            out.append("\x1b[" + ";".join(changed) + "m")
        out.append(ch)
        pfg, pbg = f, b
    out.append(RESET)                                 # never leave colours on for the next line
    return "".join(out)


# ----------------------------------------------------------------- image ---
def load_image(path, crop=True):
    img = Image.open(path)
    # Some editors (Windows Photos among them) flip/rotate by writing an EXIF
    # orientation tag rather than actually transposing the pixels. Without this,
    # we'd read the untouched pixel data and the flip would silently do nothing.
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")
    if crop:                                          # trim empty white margins
        bbox = img.point(lambda v: 255 if v < 200 else 0).getbbox()
        if bbox:
            m = 6
            x0, y0, x1, y1 = bbox
            img = img.crop((max(0, x0 - m), max(0, y0 - m),
                            min(img.width, x1 + m), min(img.height, y1 + m)))
    return img


def ink_grid(img, w, h, thicken):
    """Shrink to w x h and return an accessor giving ink strength 0..1 (1 = solid black).
    Thin pen lines vanish when averaged down, so we first erode the white (MinFilter)
    a little, in proportion to how much we are shrinking."""
    k = int((img.width / w) * thicken) | 1
    if k >= 3:
        img = img.filter(ImageFilter.MinFilter(min(k, 9)))
    small = img.resize((w, h), Image.Resampling.BOX)
    px = small.load()

    def strength(x, y):
        s = 1 - px[x, y] / 255
        s = max(0.0, min(1.0, (s - 0.04) / 0.70))     # stretch contrast
        return s ** 0.8
    return strength


def ink_color(s, x_frac, y_frac, tint):
    tl, tr, bl, br = corners(tint)
    top = lerp(tl, tr, x_frac)
    bottom = lerp(bl, br, x_frac)
    base = lerp(top, bottom, y_frac)
    k = 0.35 + 0.65 * s                               # stronger ink -> brighter
    return tuple(min(255, v * k) for v in base)


# ------------------------------------------------------------- renderers ---
def render_half(img, width, style, colors, thicken=0.15, tint=THEMES["violet"]):
    """Half-block mode: '▀' = top pixel in the foreground, bottom pixel in the background.
    A cell is ~1:2 (w:h), so two vertical pixels per cell makes pixels roughly square."""
    ph = round(width * img.height / img.width)
    ph += ph % 2
    strength = ink_grid(img, width, ph, thicken)

    def pixel(x, y):
        s = strength(x, y)
        if style == "paper":
            return lerp(PAPER, INK, s)
        return None if s < 0.10 else ink_color(s, x / width, y / ph, tint)    # chalk: paper is transparent

    rows = []
    for y in range(0, ph, 2):
        cells = []
        for x in range(width):
            top, bot = pixel(x, y), pixel(x, y + 1)
            if top is None and bot is None:
                cells.append((" ", None, None))
            elif bot is None:
                cells.append(("▀", top, None))
            elif top is None:
                cells.append(("▄", bot, None))
            else:
                cells.append(("▀", top, bot))
        rows.append(emit_row(cells, colors))
    return rows


def render_braille(img, width, colors, thicken=0.10, threshold=0.33, tint=THEMES["violet"]):
    """Braille mode: each cell is a 2x4 dot grid (one colour per cell). Twice the
    resolution of half-block in both directions, so it suits pen-and-ink line art."""
    dw = width * 2
    dh = round(dw * img.height / img.width)
    dh += (-dh) % 4
    strength = ink_grid(img, dw, dh, thicken)

    rows = []
    for cy in range(0, dh, 4):
        cells = []
        for cx in range(0, dw, 2):
            mask, total, n = 0, 0.0, 0
            for r in range(4):
                for c in range(2):
                    s = strength(cx + c, cy + r)
                    if s >= threshold:
                        mask |= BRAILLE_BITS[r][c]
                        total += s
                        n += 1
            if mask == 0:
                cells.append((" ", None, None))
            else:
                cells.append((chr(0x2800 + mask), ink_color(total / n, cx / dw, cy / dh, tint), None))
        rows.append(emit_row(cells, colors))
    return rows


def render(path, width=44, mode="braille", style="chalk", colors="truecolor", crop=True,
           thicken=None, threshold=None, theme="violet"):
    img = load_image(path, crop)
    tint = THEMES[theme]
    if mode == "braille":
        return render_braille(img, width, colors,
                              0.10 if thicken is None else thicken,
                              0.33 if threshold is None else threshold, tint)
    return render_half(img, width, style, colors, 0.15 if thicken is None else thicken, tint)


# ------------------------------------------------------------------- CLI ---
def main():
    ap = argparse.ArgumentParser(description="Render an image as ANSI-coloured terminal text.")
    ap.add_argument("image")
    ap.add_argument("--width", type=int, default=44, help="width in terminal columns")
    ap.add_argument("--mode", choices=["half", "braille"], default="braille",
                    help="braille: sharpest for line art; half: blockier but works in fonts without braille glyphs")
    ap.add_argument("--style", choices=["chalk", "paper"], default="chalk",
                    help="chalk: light ink on your terminal background; paper: dark ink on a light card (half mode only)")
    ap.add_argument("--colors", choices=["truecolor", "256"], default="truecolor")
    ap.add_argument("--theme", choices=list(THEMES), default="violet", help="colour tint (the image itself is black and white)")
    ap.add_argument("--no-crop", action="store_true")
    ap.add_argument("--thicken", type=float, help="line thickening before shrinking (try 0.05-0.3)")
    ap.add_argument("--threshold", type=float, help="braille only: ink strength needed to set a dot (try 0.2-0.5)")
    ap.add_argument("-o", "--out", help="write UTF-8 to this file instead of printing")
    a = ap.parse_args()

    lines = render(a.image, a.width, a.mode, a.style, a.colors, not a.no_crop, a.thicken, a.threshold, a.theme)
    text = "\n".join(lines) + "\n"
    print(f"{a.width} columns x {len(lines)} rows, {len(text)} bytes", file=sys.stderr)

    if a.out:                                         # write UTF-8 ourselves: PowerShell's ">" would make UTF-16
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        sys.stdout.reconfigure(encoding="utf-8")      # Windows consoles default to a legacy codepage
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
