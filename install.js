#!/usr/bin/env node

const fs = require("fs");
const path = require("path");
const https = require("https");
const os = require("os");
const { execSync } = require("child_process");

const REPO_URL = "https://raw.githubusercontent.com/nicobailon/gemini-multimodal/main";
const SKILL_DIR = path.join(os.homedir(), ".claude", "skills", "gemini");

const FILES = [
  "SKILL.md",
  "README.md",
  "requirements.txt",
  "webapi",
  "webapi.py"
];

function download(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      if (res.statusCode === 301 || res.statusCode === 302) {
        return download(res.headers.location).then(resolve).catch(reject);
      }
      if (res.statusCode !== 200) {
        return reject(new Error(`Failed to download ${url}: ${res.statusCode}`));
      }
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => resolve(data));
      res.on("error", reject);
    }).on("error", reject);
  });
}

function run(cmd, opts = {}) {
  console.log(`  $ ${cmd}`);
  try {
    execSync(cmd, { stdio: "inherit", ...opts });
    return true;
  } catch (err) {
    return false;
  }
}

async function main() {
  console.log("Installing gemini-multimodal skill...\n");

  // Create skill directory
  console.log(`Creating directory: ${SKILL_DIR}`);
  fs.mkdirSync(SKILL_DIR, { recursive: true });

  // Download skill files
  console.log("\nDownloading files...");
  for (const file of FILES) {
    console.log(`  ${file}`);
    const content = await download(`${REPO_URL}/${file}`);
    fs.writeFileSync(path.join(SKILL_DIR, file), content);
  }

  // Make webapi executable
  const webapiPath = path.join(SKILL_DIR, "webapi");
  fs.chmodSync(webapiPath, "755");

  // Set up Python venv
  console.log("\nSetting up Python virtual environment...");
  const venvPath = path.join(SKILL_DIR, ".venv");

  if (!run(`python3 -m venv "${venvPath}"`, { cwd: SKILL_DIR })) {
    console.error("\nFailed to create venv. Make sure Python 3.10+ is installed.");
    process.exit(1);
  }

  // Install dependencies
  console.log("\nInstalling Python dependencies...");
  const pip = path.join(venvPath, "bin", "pip");
  const requirements = path.join(SKILL_DIR, "requirements.txt");

  if (!run(`"${pip}" install -r "${requirements}"`, { cwd: SKILL_DIR })) {
    console.error("\nFailed to install dependencies.");
    process.exit(1);
  }

  console.log("\n" + "=".repeat(50));
  console.log("Installation complete!");
  console.log("=".repeat(50));
  console.log("\nThe skill is now available at:");
  console.log(`  ${SKILL_DIR}/webapi`);
  console.log("\nClaude Code will auto-discover the skill via SKILL.md.");
  console.log("\nUsage:");
  console.log('  ~/.claude/skills/gemini/webapi "Your prompt here"');
  console.log("\nPrerequisites:");
  console.log("  - Be logged into gemini.google.com in Chrome");
  console.log("  - On macOS, allow Keychain access when prompted (first run)");
}

main().catch((err) => {
  console.error(`\nInstallation failed: ${err.message}`);
  process.exit(1);
});
