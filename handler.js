"use strict";
/**
 * handler.js
 *
 * One route now: "/" streams a short boot sequence, then reveals the pre-built
 * page (dist/page.json, from `python layout.py --build`) one line at a time.
 *
 * Why streaming works at all: res.write() called repeatedly, with no
 * Content-Length header set, makes Node send the response using HTTP chunked
 * transfer -- each chunk reaches the client as soon as it's flushed, not
 * buffered until res.end(). curl prints bytes as they arrive, so this shows
 * up as a genuine build-up in the terminal, not a trick on our end.
 *
 * ?plain=1 (or header X-Plain: 1) skips all delays and sends the full page in
 * one write -- useful for scripts, tools, or anyone who just wants the content.
 */
const { page } = require("./dist/page.json"); // built by: python layout.py --build

const RESET = "\x1b[0m";
const dim = (s) => `\x1b[38;5;60m${s}${RESET}`;
const green = (s) => `\x1b[38;5;114m${s}${RESET}`;

// [text, pause-after-this-line in ms]
const BOOT_SEQUENCE = [
  [dim("connecting to aathi@krishnan..."), 260],
  [dim("authenticating with public key... ") + green("ok"), 220],
  [dim("loading profile..."), 200],
  [dim("rendering terminal art..."), 260],
  ["", 160], // blank line as a beat before the card
];
const LINE_DELAY_MS = 18;   // base delay between each row of the card
const LINE_JITTER_MS = 10;  // +0..jitter random wobble so it doesn't feel mechanical

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const TEXT_HEADERS = {
  "Content-Type": "text/plain; charset=utf-8", // never HTML: curl prints it as-is
  "X-Content-Type-Options": "nosniff",
  "Cache-Control": "no-store", // a stream can't be meaningfully cached, and shouldn't be
};

function hostOf(req) {
  const h = String(req.headers["x-forwarded-host"] || req.headers.host || "");
  return /^[a-z0-9.-]+(:\d+)?$/i.test(h) ? h : "<this-host>";
}

function sendPlain(req, res, status, body, extra = {}) {
  const buf = Buffer.from(body, "utf8");
  res.writeHead(status, { ...TEXT_HEADERS, "Content-Length": buf.length, ...extra });
  res.end(req.method === "HEAD" ? undefined : buf);
}

async function streamCard(req, res) {
  res.writeHead(200, TEXT_HEADERS); // no Content-Length: this is what makes it chunked/streamed
  let closed = false;
  req.on("close", () => { closed = true; }); // stop writing if the visitor Ctrl-C's or disconnects

  for (const [line, pause] of BOOT_SEQUENCE) {
    if (closed) return;
    res.write(line + "\n");
    await sleep(pause);
  }
  for (const line of page.replace(/\n+$/, "").split("\n")) {
    if (closed) return;
    res.write(line + "\n");
    await sleep(LINE_DELAY_MS + Math.random() * LINE_JITTER_MS);
  }
  if (!closed) res.end();
}

async function handle(req, res) {
  try {
    if (req.method !== "GET" && req.method !== "HEAD") {
      return sendPlain(req, res, 405, "Method not allowed. Use GET.\n", { Allow: "GET, HEAD" });
    }

    const url = new URL(req.url, "http://localhost");
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (path === "/healthz") return sendPlain(req, res, 200, "ok\n");

    if (path !== "/") {
      return sendPlain(req, res, 404, `Not found. Try:\n  curl ${hostOf(req)}\n`);
    }

    // A browser gets a plain hint, not raw escape codes or a stream it can't render right.
    const accept = String(req.headers.accept || "");
    const ua = String(req.headers["user-agent"] || "");
    if (accept.includes("text/html") && !/curl|wget|httpie/i.test(ua)) {
      return sendPlain(
        req, res, 200,
        `This portfolio is made for terminals.\n\nOpen a terminal and run:\n\n  curl ${hostOf(req)}\n\n(On Windows use curl.exe)\n`,
        { Vary: "Accept" }
      );
    }

    const plain = url.searchParams.get("plain") === "1" || req.headers["x-plain"] === "1";
    if (req.method === "HEAD" || plain) {
      return sendPlain(req, res, 200, page, { Vary: "Accept" });
    }

    return streamCard(req, res);
  } catch (err) {
    console.error(err);
    if (!res.headersSent) sendPlain(req, res, 500, "Something went wrong.\n");
    else res.end(); // mid-stream failure: close cleanly rather than hang the connection
  }
}

module.exports = { handle };
