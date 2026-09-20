"use strict";
/**
 * handler.js  (stage 3)
 *
 * One plain (req, res) function with no dependencies. It only looks up a page that
 * layout.py already built, so a request costs almost nothing. It lives in its own
 * file so the same code can run under `node server.js` (Render, Fly, your laptop)
 * and as a serverless function (Vercel, see api/index.js).
 */
const pages = require("./dist/pages.json"); // built by: python layout.py --build-all

// URL path -> key in pages.json
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

function handle(req, res) {
  try {
    if (req.method !== "GET" && req.method !== "HEAD") {
      return send(req, res, 405, "Method not allowed. Use GET.\n", { Allow: "GET, HEAD" });
    }

    const path = new URL(req.url, "http://localhost").pathname.replace(/\/+$/, "") || "/";

    if (path === "/healthz") return send(req, res, 200, "ok\n", { "Cache-Control": "no-store" });

    const key = ROUTES[path];
    if (!key) {
      return send(req, res, 404, `Not found. Try:\n  curl ${hostOf(req)}\n`, { "Cache-Control": "no-store" });
    }

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
      // Let browsers cache 5 min and the host's CDN 1 h: fewer function runs, faster replies.
      "Cache-Control": "public, max-age=300, s-maxage=3600",
    });
  } catch (err) {
    console.error(err);
    return send(req, res, 500, "Something went wrong.\n", { "Cache-Control": "no-store" });
  }
}

module.exports = { handle };
