"use strict";
// Vercel function: always serves the "side-truecolor" page.
const { serve } = require("../handler");
module.exports = (req, res) => serve(req, res, "side-truecolor");
