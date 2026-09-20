"use strict";
// Vercel function: always serves the "stack-truecolor" page.
const { serve } = require("../handler");
module.exports = (req, res) => serve(req, res, "stack-truecolor");
