#!/usr/bin/env python3
"""
layout.py  (stage 2)

Builds the whole page: framed box, Yuta on the left, portfolio text on the right.
Runs once at build time and writes static .ans files into dist/ for the server.

    python layout.py                       # print the wide truecolor page
    python layout.py --layout stack        # compact page for 80-column terminals
    python layout.py --build-all           # write all 4 variants to dist/

Alignment rule: every piece is measured from its PLAIN text first (escape codes have
zero width), and every row is padded to the same visible width before it is framed.
"""
import argparse
import json
import os
import sys
import textwrap

from renderer import RESET, THEMES, render, sgr

# ============================ edit your content here ===========================
DOMAIN = "yourdomain.dev"          # shown in the footer hints; set to your real domain

# (command shown after "$ ", [items])   item kinds: "name", "text", "kv"
SECTIONS = [
    ("whoami", [
        ("name", "Aathi Krishnan M"),
        ("text", "3rd-year B.E. CSE at Government College of Engineering, Tirunelveli. Graduating May 2028."),
        ("text", "Looking for product-based SDE roles in the 2027 campus placements."),
    ]),
    ("ls ~/stack", [
        ("kv", "langs", "C++ (primary), Python, JavaScript"),
        ("kv", "web", "MongoDB, Express, React, Node.js"),
        ("kv", "env", "Fedora Linux, Git"),
    ]),
    ("tail -f now.log", [
        ("kv", "building", "HTTP server from scratch in raw C++ sockets (multi-client support next)"),
        ("kv", "practice", "390+ LeetCode problems in C++, longest streak 51 days"),
    ]),
    ("ls ~/projects", [
        ("kv", "notes-app", "MERN notes app with JWT auth; live on Vercel + Render + Atlas"),
        ("kv", "deadlock-sim", "Deadlock analysis simulator (Python, Tkinter, NetworkX)"),
        ("kv", "url-shortener", "URL shortener"),
    ]),
    ("cat contact.txt", [
        ("kv", "github", "github.com/Aathi06"),
        ("kv", "linkedin", "linkedin.com/in/aathi-krishnan-9534ba329"),
        ("kv", "email", "aathi8012@gmail.com"),
    ]),
]
HOST = "aathi@krishnan"
# ==============================================================================

TEXT, DIM, GREEN = (205, 214, 244), (105, 110, 140), (158, 206, 106)

# layout name -> (image width in columns, content column width in columns)
LAYOUTS = {"side": (44, 53), "stack": (36, 74)}


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


class Painter:
    """Turns (text, colour) into escape-wrapped strings while tracking visible width."""

    def __init__(self, colors):
        self.colors = colors

    def seg(self, *parts):
        """parts: (text, rgb, bold). Returns (visible_width, painted_string)."""
        n = sum(len(t) for t, _, _ in parts)
        out = "".join(
            f"\x1b[{'1;' if bold else ''}{sgr(rgb, 38, self.colors)}m{t}{RESET}"
            for t, rgb, bold in parts)
        return n, out


def wrap(text, width):
    return textwrap.wrap(text, width, break_long_words=False, break_on_hyphens=False) or [""]


def content_lines(R, P, accent_a, accent_b):
    """Right-hand text as a list of (visible_width, painted) rows, each <= R wide."""
    rows = []
    for cmd, items in SECTIONS:
        # key column is sized per section so short keys don't waste room for long values
        KEY_W = max([len(it[1]) for it in items if it[0] == "kv"] or [0]) + 2
        rows.append(P.seg(("$ ", GREEN, True), (cmd, accent_a, True)))
        for it in items:
            if it[0] == "name":
                rows.append(P.seg(("  " + it[1], TEXT, True)))
            elif it[0] == "text":
                for w in wrap(it[1], R - 2):
                    rows.append(P.seg(("  " + w, TEXT, False)))
            elif it[0] == "kv":
                lines = wrap(it[2], R - 2 - KEY_W)
                rows.append(P.seg(("  " + it[1].ljust(KEY_W), accent_b, True), (lines[0], TEXT, False)))
                for w in lines[1:]:
                    rows.append(P.seg(("  " + " " * KEY_W + w, TEXT, False)))
        rows.append((0, ""))
    rows.pop()                                            # no blank line after the last section
    return rows


def pad(row, width):
    n, s = row
    assert n <= width, f"row is {n} columns wide but only {width} fit: shorten the text"
    return s + " " * (width - n)


def build(layout="side", colors="truecolor", theme="violet", image="assets/yuta.jpg"):
    img_w, R = LAYOUTS[layout]
    a, b = THEMES[theme]
    P = Painter(colors)
    border_rgb = mix(a, b, 0.5)
    border_rgb = tuple(v * 0.55 for v in border_rgb)      # frame is quieter than the content
    B = lambda ch: P.seg((ch, border_rgb, False))[1]

    art = [(img_w, line) for line in render(image, img_w, "braille", "chalk", colors, theme=theme)]
    text = content_lines(R, P, a, b)

    if layout == "side":
        inner = 1 + img_w + 3 + R + 1                     # space | image | " | " | text | space
        h = max(len(art), len(text))
        top_pad = (h - len(art)) // 2
        art = [(img_w, " " * img_w)] * top_pad + art
        art += [(img_w, " " * img_w)] * (h - len(art))
        text += [(0, "")] * (h - len(text))
        body = [f"{B('│')} {pad(x, img_w)} {B('│')} {pad(t, R)} {B('│')}" for x, t in zip(art, text)]
    else:                                                 # stack: image on top, text below
        inner = 1 + R + 1
        left = (R - img_w) // 2
        body = [f"{B('│')} {' ' * left}{pad(x, img_w)}{' ' * (R - img_w - left)} {B('│')}" for x in art]
        body.append(B("├") + B("─" * inner) + B("┤"))
        body += [f"{B('│')} {pad(t, R)} {B('│')}" for t in text]

    title = f" {HOST}: ~ "
    top = B("╭─") + P.seg((title, mix(a, b, 0.5), True))[1] + B("─" * (inner - 1 - len(title)) + "╮")
    # Accept a pasted URL ("https://name.vercel.app/") and wrap the tip if the domain is long,
    # so a long domain can never overflow the frame.
    domain = DOMAIN.replace("https://", "").replace("http://", "").strip("/")
    hints = wrap(f"tip: curl {domain}/256 (256 colours) or /compact (80 columns)", inner - 2)
    foot = [B("├") + B("─" * inner) + B("┤")]
    foot += [f"{B('│')} {pad(P.seg((h, DIM, False)), inner - 2)} {B('│')}" for h in hints]
    foot.append(B("╰") + B("─" * inner) + B("╯"))
    return "\n".join([top] + body + foot) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Compose the terminal portfolio page.")
    ap.add_argument("--layout", choices=list(LAYOUTS), default="side")
    ap.add_argument("--colors", choices=["truecolor", "256"], default="truecolor")
    ap.add_argument("--theme", choices=list(THEMES), default="violet")
    ap.add_argument("--image", default="assets/yuta.jpg")
    ap.add_argument("--build-all", action="store_true", help="write all variants into dist/")
    ap.add_argument("--out-dir", default="dist")
    a = ap.parse_args()

    if a.build_all:
        os.makedirs(a.out_dir, exist_ok=True)
        pages = {}
        for layout in LAYOUTS:
            for colors in ("truecolor", "256"):
                key = f"{layout}-{colors}"
                pages[key] = build(layout, colors, a.theme, a.image)
                with open(os.path.join(a.out_dir, f"portfolio-{key}.ans"), "w", encoding="utf-8", newline="\n") as f:
                    f.write(pages[key])
                print(f"wrote portfolio-{key}.ans: {len(pages[key])} bytes", file=sys.stderr)
        # One JSON file the Node server can require(): no filesystem reads at runtime,
        # so the same code works on any host (including serverless ones).
        with open(os.path.join(a.out_dir, "pages.json"), "w", encoding="utf-8", newline="\n") as f:
            json.dump(pages, f, ensure_ascii=False)
        print("wrote pages.json", file=sys.stderr)
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(build(a.layout, a.colors, a.theme, a.image))


if __name__ == "__main__":
    main()
