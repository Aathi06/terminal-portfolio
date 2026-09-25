"use strict";
/**
 * handler.js
 *
 * Plain (req, res) functions with no dependencies. They only look up a page that
 * layout.py already built, so a request costs almost nothing.
 *
 *  - handle(req, res)      picks the page from the URL path   -> used by `node server.js`
 *  - serve(req, res, key)  serves one fixed page              -> used by the Vercel functions in api/
 *
 * On Vercel each route is its own small function file, so nothing depends on how
 * the platform rewrites the request URL.
 */
const pages = require("./dist/pages.json"); // built by: python layout.py --build-all

// URL path -> key in pages.json (used by handle() when running locally)
const ROUTES = {
  "/": "side-truecolor",           // wide layout, 24-bit colour
  "/256": "side-256",              // wide layout, 256-colour fallback
  "/compact": "stack-truecolor",   // 80-column layout
  "/compact-256": "stack-256",     // 80-column layout, 256-colour fallback
};

const TEXT_HEADERS = {
  "Content-Type": "text/plain; charset=utf-8", // plain text, never HTML: curl prints it as-is
  "X-Content-Type-Options": "nosniff",
};

function send(req, res, status, body, extra = {}) {
  const buf = Buffer.from(body, "utf8");
  res.writeHead(status, { ...TEXT_HEADERS, "Content-Length": buf.length, ...extra });
  res.end(req.method === "HEAD" ? undefined : buf); // HEAD: same headers, no body
}

// The Host header is client-controlled, so only echo it back if it looks like a hostname.
function hostOf(req) {
  const h = String(req.headers["x-forwarded-host"] || req.headers.host || "");
  return /^[a-z0-9.-]+(:\d+)?$/i.test(h) ? h : "<this-host>";
}

function methodAllowed(req, res) {
  if (req.method === "GET" || req.method === "HEAD") return true;
  send(req, res, 405, "Method not allowed. Use GET.\n", { Allow: "GET, HEAD" });
  return false;
}

function notFound(req, res) {
  if (!methodAllowed(req, res)) return;
  send(req, res, 404, `Not found. Try:\n  curl ${hostOf(req)}\n`, { "Cache-Control": "no-store" });
}

function health(req, res) {
  if (!methodAllowed(req, res)) return;
  send(req, res, 200, "ok\n", { "Cache-Control": "no-store" });
}

function serve(req, res, key) {
  try {
    if (!methodAllowed(req, res)) return;

    // A browser would show raw escape codes as garbage, so tell it what to do (still plain text).
    const accept = String(req.headers.accept || "");
    const ua = String(req.headers["user-agent"] || "");
    if (accept.includes("text/html") && !/curl|wget|httpie/i.test(ua)) {
      return send(
        req, res, 200,
        `This portfolio is made for terminals.\n\nOpen a terminal and run:\n\n  curl ${hostOf(req)}\n\n(On Windows use curl.exe)\n`,
        { Vary: "Accept", "Cache-Control": "no-store" }
      );
    }

    return send(req, res, 200, pages[key], {
      Vary: "Accept",
      // No caching while we're actively debugging routing: a cached response can outlive
      // the deploy that was supposed to replace it, which is exactly what happened here.
      "Cache-Control": "no-store",
    });
  } catch (err) {
    console.error(err);
    return send(req, res, 500, "Something went wrong.\n", { "Cache-Control": "no-store" });
  }
}

// Path-based router for the local / long-running server.
function handle(req, res) {
  const path = new URL(req.url, "http://localhost").pathname.replace(/\/+$/, "") || "/";
  if (path === "/healthz") return health(req, res);
  const key = ROUTES[path];
  return key ? serve(req, res, key) : notFound(req, res);
}

module.exports = { handle, serve, health, notFound };
