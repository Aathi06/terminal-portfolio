"use strict";

const { handle } = require("../handler");

module.exports = (req, res) => {
  const debug = JSON.stringify(req.query);

  res.setHeader("Content-Type", "text/plain; charset=utf-8");
  return res.end(
    `URL: ${req.url}\nQUERY: ${debug}\nPATH: ${req.query?.path}\n`
  );
};