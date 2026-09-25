"use strict";
/**
 * api/v2.js — real routing logic, under a name Vercel/its CDN has never seen before.
 * (The old api/route.js is deleted — its URL was getting served from cache even
 * after redeploys, so a fresh path sidesteps that entirely rather than fighting it.)
 *
 * vercel.json rewrites every request here and passes the original path explicitly
 * as a query string, e.g. /256 becomes /api/v2?path=/256. We read that back out
 * ourselves rather than relying on req.url surviving the rewrite untouched, then
 * hand it to the same handle() that server.js uses locally.
 */
const { handle } = require("../handler");

module.exports = (req, res) => {
  const u = new URL(req.url, "http://x");
  req.url = u.searchParams.get("path") || "/"; // handle() reads the path straight off req.url
  return handle(req, res);
};
