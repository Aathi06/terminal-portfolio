"use strict";

const { handle } = require("../handler");

module.exports = (req, res) => {
  req.url = req.query.path || "/";
  return handle(req, res);
};