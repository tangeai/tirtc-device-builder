import assert from "node:assert/strict";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const CLI = join(ROOT, "bin", "tirtc-device-builder.js");
const PACKAGE = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));

function run(args, environment = {}) {
  return spawnSync(process.execPath, [CLI, ...args], {
    encoding: "utf8",
    env: { ...process.env, ...environment },
  });
}

async function withTemporaryDirectory(callback) {
  const directory = await mkdtemp(join(tmpdir(), "tirtc-device-builder-"));
  try {
    await callback(directory);
  } finally {
    await rm(directory, { force: true, recursive: true });
  }
}

test("--version reports package version", () => {
  const result = run(["--version"]);
  assert.equal(result.status, 0);
  assert.equal(result.stdout.trim(), PACKAGE.version);
});

test("list exposes the ESP32 skill", () => {
  const result = run(["list"]);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /esp32\s+tirtc-esp32-builder/);
});

test("install copies a complete skill to an explicit skills directory", async () => {
  await withTemporaryDirectory(async (directory) => {
    const skillsDir = join(directory, "skills");
    const result = run(["install", "esp32", "--skills-dir", skillsDir]);
    const target = join(skillsDir, "tirtc-esp32-builder");

    assert.equal(result.status, 0, result.stderr);
    assert.equal(existsSync(join(target, "SKILL.md")), true);
    assert.equal(existsSync(join(target, "scripts", "doctor.py")), true);
    assert.match(result.stdout, /Installed tirtc-esp32-builder/);
  });
});

test("install respects CODEX_HOME", async () => {
  await withTemporaryDirectory(async (directory) => {
    const result = run(["install", "esp32"], { CODEX_HOME: directory });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(
      existsSync(join(directory, "skills", "tirtc-esp32-builder", "SKILL.md")),
      true,
    );
  });
});

test("install preserves an existing skill unless --force is supplied", async () => {
  await withTemporaryDirectory(async (directory) => {
    const skillsDir = join(directory, "skills");
    const target = join(skillsDir, "tirtc-esp32-builder");

    assert.equal(
      run(["install", "esp32", "--skills-dir", skillsDir]).status,
      0,
    );
    const marker = join(target, "local-change.txt");
    writeFileSync(marker, "keep me", "utf8");

    const blocked = run(["install", "esp32", "--skills-dir", skillsDir]);
    assert.equal(blocked.status, 1);
    assert.match(blocked.stderr, /already exists/);
    assert.equal(readFileSync(marker, "utf8"), "keep me");

    const replaced = run([
      "install",
      "esp32",
      "--skills-dir",
      skillsDir,
      "--force",
    ]);
    assert.equal(replaced.status, 0, replaced.stderr);
    assert.equal(existsSync(marker), false);
    assert.equal(existsSync(join(target, "SKILL.md")), true);
  });
});

test("unknown platforms fail without creating an installation", async () => {
  await withTemporaryDirectory(async (directory) => {
    const result = run([
      "install",
      "unknown-board",
      "--skills-dir",
      directory,
    ]);
    assert.equal(result.status, 1);
    assert.match(result.stderr, /unsupported platform/);
  });
});

test("doctor delegates to the packaged Python helper", () => {
  const result = run(["doctor", "esp32", "--help"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /--expected-idf/);
  assert.match(result.stdout, /--thing-connect-root/);
});
