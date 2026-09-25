"use strict";
/**
 * api/route.js — TEMPORARY DEBUG VERSION.
 *
 * Every request, no matter the path, gets back plain text showing exactly what
 * this function received: the raw req.url, and the "path" query param that
 * vercel.json's rewrite is supposed to set. No routing happens yet.
 *
 * Once we see this output for a few different URLs (/, /256, /compact), we'll
 * know whether the rewrite is firing at all, and restore the real routing logic.
 */
module.exports = (req, res) => {
  const u = new URL(req.url, "http://x");
  const body =
    "req.url (raw, as this function received it):\n  " + JSON.stringify(req.url) + "\n\n" +
    "req.method:\n  " + JSON.stringify(req.method) + "\n\n" +
    "'path' query param (what the rewrite should have set):\n  " + JSON.stringify(u.searchParams.get("path")) + "\n\n" +
    "all query params:\n  " + JSON.stringify(Object.fromEntries(u.searchParams)) + "\n";
  res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
  res.end(body);
};
