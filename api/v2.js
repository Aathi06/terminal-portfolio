"use strict";
/**
 * api/v2.js — TEMPORARY DEBUG VERSION (no routing logic at all right now).
 *
 * If a request to /256 or /compact reaches this function, you'll see plain text
 * below proving it. If instead you still get a 404, this function never ran at
 * all for that request — meaning vercel.json's rewrite for that path isn't
 * matching, and the problem is entirely in Vercel's routing config, not our code.
 */
module.exports = (req, res) => {
  const u = new URL(req.url, "http://x");
  const body =
    "THIS FUNCTION RAN. If you're seeing this for /256 or /compact, the rewrite works\n" +
    "and the bug is in our routing code, not Vercel config.\n\n" +
    "req.url (raw):\n  " + JSON.stringify(req.url) + "\n\n" +
    "'path' query param:\n  " + JSON.stringify(u.searchParams.get("path")) + "\n\n" +
    "all query params:\n  " + JSON.stringify(Object.fromEntries(u.searchParams)) + "\n";
  res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
  res.end(body);
};