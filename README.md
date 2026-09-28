# terminal-portfolio

A portfolio you read with `curl`. One command prints a boot sequence, then reveals a
card line by line in your terminal: braille-dot ink art on the left, my details on
the right.

```bash
curl https://aathi06-cli.vercel.app
```

> On Windows use `curl.exe`, and run `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`
> first if characters look garbled. Add `?plain=1` to skip the animation and get the
> full page instantly (useful for scripts).

## How it works

```
image ──> renderer.py ──> layout.py ──> dist/page.json ──> handler.js ──> curl
         (Pillow, ink        (frame +      (one prebuilt      (streams it:
          detection,          content)      page, JSON)        boot lines,
          braille dots,                                        then the card,
          colour themes)                                       line by line)
```

**Build time (Python, run on my machine):** `renderer.py` turns a black-and-white
line-art image into Unicode braille characters — each character cell holds a 2x4
grid of dots, which is what makes it possible to keep pen lines readable at only
44 columns wide. Ink strength (how dark a pen stroke is) controls dot placement
and brightness; colour comes from a theme (a gradient blended across the image,
since the source art has no colour of its own) or from hardcoded regions, which
override the gradient inside specific coordinate boxes (e.g. "this box is always
blue") for images where a single part should stand out.

`layout.py` builds the whole page around that art: a rounded frame, my info as
shell-prompt-style sections (`$ whoami`, `$ ls ~/projects`), and a footer. It
measures every line's *visible* width before adding colour codes and refuses to
build if anything would overflow the frame, so the border always lines up exactly.
`--build` writes the result to `dist/page.ans` and `dist/page.json` — the only
files the server actually reads.

**Request time (Node.js):** `handler.js` streams the response in pieces —
a short boot sequence (`connecting...`, `authenticating...`), then the card
itself, one row at a time — using HTTP chunked transfer (no `Content-Length`
header, so each `write()` reaches the client as soon as it's sent rather than
being buffered until the end). That's what makes it visibly build up in your
terminal instead of appearing all at once. Nothing is generated per-request;
it's the same prebuilt string from `dist/page.json` either way, just delivered
gradually.

## Run it locally

Requires Python 3 and Node.js 18+.

```bash
pip install pillow
python layout.py --build      # writes dist/page.ans + dist/page.json
node server.js                # http://localhost:3000
curl -s localhost:3000
```

Try variations:

```bash
python layout.py --theme ice --build      # violet (default), ice, ember, matrix,
                                           # mono, aurora, sunset, citrus
python layout.py --image assets/other.jpg --build
python renderer.py assets/yuta.jpg        # preview just the art, no build needed
curl -s "localhost:3000/?plain=1"         # instant, no streaming
```

## Customize

- **Content:** edit `SECTIONS` at the top of `layout.py`.
- **Footer:** edit the `FOOTER` string in the same file.
- **Colours:** pick a theme with `--theme`, or add your own to the `THEMES` dict in
  `renderer.py` — either two colours (a top-to-bottom blend) or four (blended
  across both axes, for a genuinely multicoloured look).
- **Region colours:** `renderer.render_braille(..., regions=[((x0,y0,x1,y1), (r,g,b)), ...])`
  lets specific coordinate boxes (as fractions of the image, 0 to 1) override the
  theme gradient with a fixed colour — useful for e.g. always making hair blue
  regardless of theme. Boxes are hand-picked per image, not automatic.
- **Boot sequence / animation timing:** `BOOT_SEQUENCE` and `LINE_DELAY_MS` in
  `handler.js`.

After any change: `python layout.py --build`, then commit `dist/`, since that's
the file the live server actually serves.

## Project structure

```
renderer.py      image -> braille ANSI art (ink detection, themes, region colours)
layout.py        page layout, content (SECTIONS/FOOTER), build script
handler.js       request handling: streaming boot sequence + typewriter reveal
server.js        runs the handler as a normal Node server (local dev)
dist/            prebuilt output (page.json is what the server serves)
```

## Deployment

Deployed on Vercel (free plan) at `aathi06-cli.vercel.app`, built from this repo.

- `dist/page.json` must be committed — the server reads it directly and does no
  image processing at request time, so there's no Python dependency in
  production.
- `package.json`'s Python build step is named `build:pages`, deliberately not
  `build` — Vercel auto-runs a script literally named `build`, and its build
  machine has no Pillow installed.

## Credits and AI assistance

Built with help from **Claude** (Anthropic), across a long working session —
architecture, the renderer, the streaming server, and a lot of debugging
(including tracking down a Vercel routing/caching issue that took several
rounds to isolate). I came up with the concept, picked the content and image,
and tested and deployed it.

Made by [Aathi Krishnan M](https://github.com/Aathi06).