#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
const result = spawnSync(
  npmCommand,
  ["pack", "--dry-run", "--json", "--ignore-scripts"],
  {
    cwd: ROOT,
    encoding: "utf8",
  },
);

if (result.error) {
  console.error("Tarball validation failed: " + result.error.message);
  process.exit(1);
}
if (result.status !== 0) {
  process.stderr.write(result.stderr);
  process.exit(result.status ?? 1);
}

let manifests;
try {
  manifests = JSON.parse(result.stdout);
} catch (error) {
  console.error("Tarball validation failed: npm pack did not return JSON");
  process.exit(1);
}

if (!Array.isArray(manifests) || manifests.length !== 1) {
  console.error("Tarball validation failed: expected exactly one package");
  process.exit(1);
}

const paths = manifests[0].files.map((file) => file.path);
const pathSet = new Set(paths);
const required = [
  ".codex-plugin/plugin.json",
  "LICENSE",
  "NOTICE",
  "README.md",
  "bin/tirtc-device-builder.js",
  "bin/esp32-kit-metadata.js",
  "bin/install-esp32-kit.js",
  "bin/setup-esp32.js",
  "package.json",
  "skills/tirtc-esp32-builder/SKILL.md",
  "skills/tirtc-esp32-builder/scripts/doctor.py",
];
const allowedTopLevel = new Set([
  ".codex-plugin",
  "CHANGELOG.md",
  "LICENSE",
  "NOTICE",
  "README.md",
  "SECURITY.md",
  "bin",
  "package.json",
  "skills",
]);
const forbiddenPatterns = [
  /(^|\/)__pycache__(\/|$)/,
  /\.py[co]$/i,
  /(^|\/)test_[^/]*\.py$/i,
  /\.(a|bin|der|elf|key|p12|pfx|pem)$/i,
];
const errors = [];

for (const requiredPath of required) {
  if (!pathSet.has(requiredPath)) {
    errors.push("missing required file: " + requiredPath);
  }
}
for (const path of paths) {
  const topLevel = path.split("/", 1)[0];
  if (!allowedTopLevel.has(topLevel)) {
    errors.push("unexpected top-level package path: " + path);
  }
  if (forbiddenPatterns.some((pattern) => pattern.test(path))) {
    errors.push("forbidden package file: " + path);
  }
}

if (errors.length > 0) {
  console.error("Tarball validation failed:");
  for (const error of errors) {
    console.error("- " + error);
  }
  process.exit(1);
}

console.log("Tarball validation passed (" + paths.length + " files)");
