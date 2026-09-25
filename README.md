# terminal-portfolio

A portfolio you read with `curl`. Run one command and my portfolio renders right in your terminal: a colored braille-art image on the left, my details on the right.

```bash
curl https://aathi-cli.vercel.app
```

> On Windows use `curl.exe`, and run `chcp 65001` first if the box and braille characters look garbled.
> The page is 104 columns wide, so use a wide terminal window.

## How it works

```
image ──> renderer.py ──> layout.py ──> dist/pages.json ──> handler.js ──> curl
          (Pillow)         (frame +       (prebuilt          (plain-text
                            text)          pages)             HTTP response)
```

1. **`renderer.py`** turns an image into ANSI-colored text. It maps the picture onto Unicode braille characters (a 2x4 dot grid per terminal cell), which keeps thin pen lines readable at only 44 columns wide. It also has a half-block mode, five color themes, and a 256-color fallback for terminals without 24-bit color.
2. **`layout.py`** builds the page: a rounded frame, the art on the left, and prompt-style sections (`$ whoami`, `$ ls ~/projects`) on the right. It measures every row's visible width before adding color codes, so alignment is exact, and it refuses to build if any row overflows. It writes four variants (wide or compact, truecolor or 256-color) into `dist/`.
3. **`handler.js`** is a dependency-free Node.js handler that looks up a prebuilt page and returns it as `text/plain`. It never returns HTML, and a browser visitor gets a short plain-text hint to use a terminal instead.

The pages are built ahead of time, so the server does no image processing and reads no files at runtime. That keeps it cheap and fast on free hosting.

## Run it locally

Requires Python 3 and Node.js 18+.

```bash
pip install pillow
python layout.py --build-all      # writes dist/pages.json (needs your image at assets/yuta.jpg)
node server.js                    # http://localhost:3000
curl -s localhost:3000
```

Try the other variants and themes:

```bash
python layout.py                          # print the wide page directly
python layout.py --layout stack           # compact 80-column page
python layout.py --colors 256             # 256-color fallback
python layout.py --theme ice              # violet (default), ice, ember, matrix, mono
python renderer.py assets/yuta.jpg        # just the image renderer
```

## Customize

- **Content:** edit the `SECTIONS` block at the top of `layout.py`.
- **Domain shown in the footer tip:** set `DOMAIN` in `layout.py`.
- **Colors:** pick a theme with `--theme`, or edit the `THEMES` dictionary in `renderer.py`.
- After any change, run `python layout.py --build-all` and commit `dist/`.

## Project structure

```
renderer.py      image -> ANSI art (braille / half-block, themes, 256-color fallback)
layout.py        page layout, content, build script
handler.js       request handling logic (no dependencies)
server.js        runs the handler as a normal Node server
api/             one small Vercel function per route
vercel.json      maps URLs to those functions
dist/            prebuilt pages (pages.json is what the server serves)
```

## Deployment

Deployed on Vercel's free plan from this repo.

- `dist/pages.json` must be committed, because the server serves it directly.
- Don't add a plain `build` script to `package.json`: Vercel would run it automatically, and its build machine has no Pillow. The Python build is `npm run build:pages`, run locally.
- Keep Deployment Protection on **Standard Protection** so the production domain is public and `curl` doesn't receive a login page.

## Known issues

- The alternate routes (`/256`, `/compact`, `/compact-256`) are not working reliably on the Vercel deployment yet. They work locally with `node server.js`. The likely cause is how Vercel routes requests to the functions, and I'm still investigating.
- Until that's fixed, the compact 80-column layout isn't available to visitors, so narrow terminals will wrap the main page.

## Credits and AI assistance

I built this project with help from **Claude**, Anthropic's AI assistant, in a long working session. Claude helped design the architecture and wrote much of the code (the renderer, the layout, the server, and the deployment setup) and helped debug it. I came up with the idea, chose the content, ran and tested it, and deployed it.

Character art: Yuta Okkotsu from *Jujutsu Kaisen* by Gege Akutami. This is unofficial fan work, not affiliated with or endorsed by the creator or publisher. The source panel is not included in this repository.

Made by [Aathi Krishnan M](https://github.com/Aathi06).
