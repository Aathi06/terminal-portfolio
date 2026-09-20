"use strict";
// Vercel function: always serves the "stack-256" page.
const { serve } = require("../handler");
module.exports = (req, res) => serve(req, res, "stack-256");
