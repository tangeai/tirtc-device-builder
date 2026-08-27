#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  renameSync,
  rmSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const PACKAGE = JSON.parse(
  readFileSync(join(PACKAGE_ROOT, "package.json"), "utf8"),
);

const PLATFORMS = new Map([
  [
    "esp32",
    {
      aliases: new Set(["esp32", "esp32s3", "tirtc-esp32-builder"]),
      skill: "tirtc-esp32-builder",
      summary: "ESP32-S3 / ESP-IDF 5.5.x",
    },
  ],
]);

function printHelp() {
  console.log(`TiRTC Device Builder ${PACKAGE.version}

Usage:
  tirtc-device-builder list
  tirtc-device-builder install <platform> [--skills-dir <path>] [--force]
  tirtc-device-builder doctor <platform> [doctor options]
  tirtc-device-builder --version

Platforms:
  esp32       ESP32-S3 / ESP-IDF 5.5.x

Examples:
  npx tirtc-device-builder install esp32
  npx tirtc-device-builder install esp32 --skills-dir /absolute/path/skills
  npx tirtc-device-builder doctor esp32 --project /absolute/path/project

Install defaults to ${"$"}{CODEX_HOME:-~/.codex}/skills. Existing skills are
preserved unless --force is explicitly supplied.`);
}

function fail(message) {
  console.error(`ERROR: ${message}`);
  return 1;
}

function resolvePlatform(identifier) {
  for (const [name, platform] of PLATFORMS) {
    if (platform.aliases.has(identifier)) {
      return { name, ...platform };
    }
  }
  return null;
}

function defaultSkillsDir() {
  const codexHome = process.env.CODEX_HOME
    ? resolve(process.env.CODEX_HOME)
    : join(homedir(), ".codex");
  return join(codexHome, "skills");
}

function parseInstallOptions(args) {
  const options = {
    force: false,
    skillsDir: defaultSkillsDir(),
  };

  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--force") {
      options.force = true;
      continue;
    }
    if (argument === "--skills-dir") {
      const value = args[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error("--skills-dir requires a path");
      }
      options.skillsDir = resolve(value);
      index += 1;
      continue;
    }
    throw new Error(`unknown install option: ${argument}`);
  }

  return options;
}

function installSkill(platform, options) {
  const source = join(PACKAGE_ROOT, "skills", platform.skill);
  const skillsDir = options.skillsDir;
  const target = join(skillsDir, platform.skill);
  const nonce = `${process.pid}-${Date.now()}`;
  const staged = join(skillsDir, `.${platform.skill}.install-${nonce}`);
  const backup = join(skillsDir, `.${platform.skill}.backup-${nonce}`);

  if (!existsSync(join(source, "SKILL.md"))) {
    throw new Error(`package is missing ${platform.skill}/SKILL.md`);
  }
  if (existsSync(target) && !options.force) {
    throw new Error(
      `${target} already exists; rerun with --force only when replacement is intended`,
    );
  }

  mkdirSync(skillsDir, { recursive: true });
  let movedExisting = false;
  try {
    cpSync(source, staged, {
      errorOnExist: true,
      force: false,
      recursive: true,
    });
    if (!existsSync(join(staged, "SKILL.md"))) {
      throw new Error("staged skill failed validation");
    }
    if (existsSync(target)) {
      renameSync(target, backup);
      movedExisting = true;
    }
    renameSync(staged, target);
  } catch (error) {
    if (existsSync(staged)) {
      rmSync(staged, { force: true, recursive: true });
    }
    if (movedExisting && !existsSync(target) && existsSync(backup)) {
      renameSync(backup, target);
    }
    throw error;
  }

  if (movedExisting && existsSync(backup)) {
    rmSync(backup, { force: true, recursive: true });
  }
  console.log(`Installed ${platform.skill} ${PACKAGE.version} to ${target}`);
  console.log(`Start a new Codex session, then invoke $${platform.skill}.`);
}

function runDoctor(platform, args) {
  const script = join(
    PACKAGE_ROOT,
    "skills",
    platform.skill,
    "scripts",
    "doctor.py",
  );
  if (!existsSync(script)) {
    return fail(`package is missing doctor script for ${platform.name}`);
  }

  const python = process.env.PYTHON || "python3";
  const result = spawnSync(python, [script, ...args], {
    stdio: "inherit",
  });
  if (result.error) {
    return fail(`could not run ${python}: ${result.error.message}`);
  }
  return Number.isInteger(result.status) ? result.status : 1;
}

function main(args) {
  if (args.length === 0 || args[0] === "--help" || args[0] === "-h") {
    printHelp();
    return 0;
  }
  if (args[0] === "--version" || args[0] === "-v") {
    console.log(PACKAGE.version);
    return 0;
  }
  if (args[0] === "list") {
    for (const [name, platform] of PLATFORMS) {
      console.log(`${name}\t${platform.skill}\t${platform.summary}`);
    }
    return 0;
  }

  const [command, identifier, ...rest] = args;
  if (command !== "install" && command !== "doctor") {
    return fail(`unknown command: ${command}; run with --help`);
  }
  if (!identifier) {
    return fail(`${command} requires a platform; run "list" to see options`);
  }
  const platform = resolvePlatform(identifier);
  if (!platform) {
    return fail(`unsupported platform: ${identifier}; run "list" to see options`);
  }

  if (command === "doctor") {
    return runDoctor(platform, rest);
  }

  try {
    const options = parseInstallOptions(rest);
    installSkill(platform, options);
    return 0;
  } catch (error) {
    return fail(error instanceof Error ? error.message : String(error));
  }
}

process.exitCode = main(process.argv.slice(2));
