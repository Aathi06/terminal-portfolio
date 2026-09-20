"use strict";
/**
 * server.js: runs the handler as a normal long-lived Node server.
 * Use this locally and on hosts that run a process (Render, Fly, a VPS).
 * Hosts pass the port in the PORT environment variable, so we never hard-code it.
 */
const http = require("node:http");
const { handle } = require("./handler");

const PORT = Number(process.env.PORT) || 3000;

http.createServer(handle).listen(PORT, "0.0.0.0", () => {
  console.log(`terminal portfolio listening on http://localhost:${PORT}`);
});
