"use strict";
/**
 * api/route.js — the ONLY Vercel function in this project.
 *
 * vercel.json rewrites every request here and passes the original path explicitly
 * as a query string, e.g. /256 becomes /api/route?path=/256. We don't rely on
 * Vercel preserving req.url through the rewrite (that's what broke last time) —
 * we read the exact path back out of the query string ourselves, then hand it to
 * the same handle() that server.js uses locally, so routing logic exists in one place.
 */
const { handle } = require("../handler");

module.exports = (req, res) => {
  const u = new URL(req.url, "http://x");
  const originalPath = u.searchParams.get("path") || "/";
  req.url = originalPath; // handle() reads the path straight off req.url
  return handle(req, res);
};
