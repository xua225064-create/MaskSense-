const fs = require("fs");
const path = require("path");

const apiBaseUrl = (process.env.MARKSENSE_API_BASE_URL || "").trim().replace(/\/+$/, "");
const target = path.join(__dirname, "..", "frontend-config.js");

fs.writeFileSync(
  target,
  `window.MARKSENSE_API_BASE_URL = ${JSON.stringify(apiBaseUrl)};\n`,
  "utf8"
);

console.log(`Wrote frontend-config.js with MARKSENSE_API_BASE_URL=${apiBaseUrl || "(empty)"}`);
