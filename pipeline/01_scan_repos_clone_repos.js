#!/usr/bin/env node
/**
 * codeup-clone: Batch clone repositories from Codeup JSON export files.
 *
 * Usage:
 *   node clone_repos.js [JSON_FILES...] [--dir TARGET_DIR] [--dry-run]
 *
 * If no JSON files are specified, auto-discovers groups_and_projects*.json
 * in the current directory.
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

function convertHttpsToSsh(httpsUrl) {
  const withoutProtocol = httpsUrl.replace("https://", "");
  const slashIndex = withoutProtocol.indexOf("/");
  if (slashIndex === -1) {
    throw new Error(`Invalid URL format: ${httpsUrl}`);
  }
  const domain = withoutProtocol.slice(0, slashIndex);
  const repoPath = withoutProtocol.slice(slashIndex + 1);
  return `git@${domain}:${repoPath}.git`;
}

function extractProjects(jsonFiles) {
  const projects = [];
  const seenUrls = new Set();

  for (const filepath of jsonFiles) {
    console.log(`Reading: ${filepath}`);
    const raw = fs.readFileSync(filepath, "utf-8");
    const data = JSON.parse(raw);

    for (const entry of data) {
      if (entry.type !== "Project") continue;
      const project = entry.project;
      if (!project) continue;
      const webUrl = project.web_url;
      if (!webUrl || seenUrls.has(webUrl)) continue;
      seenUrls.add(webUrl);
      projects.push({
        name: project.name || "unknown",
        web_url: webUrl,
        source_file: filepath,
      });
    }
  }

  return projects;
}

function cloneRepo(sshUrl, targetDir, dryRun = false) {
  const repoName = path.basename(sshUrl).replace(".git", "");
  const dest = path.join(targetDir, repoName);

  if (dryRun) {
    return `[DRY-RUN] Would clone: ${sshUrl} → ${dest}`;
  }

  if (fs.existsSync(dest)) {
    return `[SKIP] Already exists: ${dest}`;
  }

  try {
    execSync(`git clone "${sshUrl}" "${dest}"`, {
      stdio: "pipe",
      timeout: 300000,
    });
    return `[OK] Cloned: ${repoName}`;
  } catch (err) {
    const stderr = err.stderr ? err.stderr.toString().trim() : "";
    if (err.signal === "SIGTERM" || (err.code && err.code === "ETIMEDOUT")) {
      return `[FAIL] ${repoName}: Clone timed out (5min)`;
    }
    return `[FAIL] ${repoName}: ${stderr || err.message}`;
  }
}

function parseArgs(argv) {
  const args = { jsonFiles: [], dir: ".", dryRun: false };
  let i = 0;
  while (i < argv.length) {
    if (argv[i] === "--dir" && i + 1 < argv.length) {
      args.dir = argv[++i];
    } else if (argv[i] === "--dry-run") {
      args.dryRun = true;
    } else {
      args.jsonFiles.push(argv[i]);
    }
    i++;
  }
  return args;
}

function main() {
  const rawArgs = process.argv.slice(2);
  const args = parseArgs(rawArgs);

  // Auto-discover JSON files if none specified
  if (args.jsonFiles.length === 0) {
    const files = fs.readdirSync(".")
      .filter((f) => /^groups_and_projects.*\.json$/.test(f))
      .sort();
    args.jsonFiles = files;
    if (args.jsonFiles.length === 0) {
      console.error(
        "Error: No JSON files specified and none found matching 'groups_and_projects*.json'"
      );
      process.exit(1);
    }
    console.log(`Auto-discovered: ${args.jsonFiles.join(", ")}`);
  }

  // Validate files exist
  for (const filepath of args.jsonFiles) {
    if (!fs.existsSync(filepath)) {
      console.error(`Error: File not found: ${filepath}`);
      process.exit(1);
    }
  }

  // Extract and deduplicate projects
  console.log(`\nExtracting projects from ${args.jsonFiles.length} file(s)...`);
  const projects = extractProjects(args.jsonFiles);

  if (projects.length === 0) {
    console.log("No Project entries found in the specified JSON files.");
    process.exit(0);
  }

  console.log(`Found ${projects.length} unique project(s).\n`);

  // Convert URLs
  const repos = [];
  for (const proj of projects) {
    const sshUrl = convertHttpsToSsh(proj.web_url);
    repos.push(sshUrl);
    if (args.dryRun) {
      console.log(`  ${proj.name} → ${sshUrl}`);
    }
  }

  if (args.dryRun) {
    console.log(`\n[DRY-RUN] Total: ${repos.length} repo(s) would be cloned.`);
    return;
  }

  // Create target directory if needed
  if (args.dir !== ".") {
    fs.mkdirSync(args.dir, { recursive: true });
    console.log(`Target directory: ${args.dir}\n`);
  }

  // Clone each repo
  console.log(`Cloning ${repos.length} repo(s) to ${args.dir}...\n`);
  const results = [];
  for (const sshUrl of repos) {
    const msg = cloneRepo(sshUrl, args.dir);
    console.log(`  ${msg}`);
    results.push(msg);
  }

  // Summary
  const ok = results.filter((r) => r.startsWith("[OK]")).length;
  const skip = results.filter((r) => r.startsWith("[SKIP]")).length;
  const fail = results.filter((r) => r.startsWith("[FAIL]")).length;

  console.log(`\n${"=".repeat(50)}`);
  console.log(
    `Summary: ${ok} cloned, ${skip} skipped, ${fail} failed (total: ${repos.length})`
  );
  if (fail > 0) {
    console.log("\nFailed repos:");
    for (const r of results) {
      if (r.startsWith("[FAIL]")) {
        console.log(`  ${r}`);
      }
    }
  }
  console.log("=".repeat(50));
}

main();
