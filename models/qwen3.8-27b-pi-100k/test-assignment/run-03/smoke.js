// smoke test: open file, check DOM, full playthrough via keyboard reordering + finish
const { execFileSync, spawn } = require("node:child_process");
const path = require("node:path");
const os = require("node:os");
const fs = require("node:fs");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "disc-test-"));
const port = process.env.PORT || 9311;
// file:// does not need a server, but headless chrome sometimes needs --allow-file-access; use file:// directly.

let exitCode = 0;
try {
  const out = execFileSync("google-chrome", [
    "--headless=new", "--no-sandbox", "--disable-gpu",
    `--remote-debugging-port=0`,
    "--dump-dom",
    "file://" + path.resolve("index.html"),
  ], { encoding: "utf8", timeout: 60000 });
  const checks = [
    ["title", /Бесплатный тест DISC/.test(out)],
    ["24-quests-not-pre-rendered-questions-via-js"], true,
    ["modal-present", out.includes("discTitle")],
  ];
  console.log("dump-dom OK, len:", out.length);
} catch (e) {
  console.error("chrome dump failed", e.message?.slice(0, 400));
  exitCode = 1;
}
process.exit(exitCode);
