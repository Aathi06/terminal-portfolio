"use strict";

const { handle } = require("../handler");

module.exports = (req, res) => {

  console.log("===== ROUTE HIT =====");
    console.log("method:", req.method);
    console.log("url:", req.url);
    console.log("query:", req.query);
    console.log("headers:", req.headers);
    
  return handle(req, res);
};