#!/usr/bin/env node

import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";

function run(command, args, options = {}) {
  const environment = {
    ...process.env,
    PYTHONDONTWRITEBYTECODE: "1",
    ...options.env,
  };
  for (const key of Object.keys(environment)) {
    if (key.toLowerCase() === "npm_config_dry_run") {
      delete environment[key];
    }
  }
  environment.npm_config_dry_run = "false";

  const result = spawnSync(command, args, {
    cwd: options.cwd ?? ROOT,
    encoding: "utf8",
    env: environment,
  });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(
      command +
        " failed with exit " +
        result.status +
        "\n" +
        result.stdout +
        result.stderr,
    );
  }
  return result;
}

function createDeviceKit(root, version) {
  const required = [
    join("device-sim", "scripts", "create_esp32_project.py"),
    join(
      "device-sim",
      "sdk",
      "espressif-esp32s3",
      "2.3.0",
      "include",
      "tirtc",
      "tiRTC.h",
    ),
    join(
      "device-sim",
      "sdk",
      "espressif-esp32s3",
      "2.3.0",
      "lib",
      "libTiRTC.a",
    ),
    join(
      "device-sim",
      "sdk",
      "espressif-esp32s3",
      "2.3.0",
      "manifest",
      "build-contract.env",
    ),
  ];
  for (const relative of required) {
    const path = join(root, relative);
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, "test\n", "utf8");
  }
  writeFileSync(
    join(root, "manifest.json"),
    JSON.stringify({ kit_version: version }) + "\n",
    "utf8",
  );
}

const temporary = mkdtempSync(join(tmpdir(), "tirtc-packed-package-"));
try {
  const packed = run(npmCommand, [
    "pack",
    "--json",
    "--ignore-scripts",
    "--pack-destination",
    temporary,
  ]);
  const manifests = JSON.parse(packed.stdout);
  assert.equal(manifests.length, 1);

  const tarball = join(temporary, manifests[0].filename);
  const consumer = join(temporary, "consumer");
  mkdirSync(consumer, { recursive: true });
  run(
    npmCommand,
    [
      "install",
      "--prefix",
      consumer,
      tarball,
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--offline",
    ],
    { cwd: temporary },
  );

  const installedPackage = join(
    consumer,
    "node_modules",
    "tirtc-device-builder",
  );
  const cli = join(installedPackage, "bin", "tirtc-device-builder.js");
  const packageMetadata = JSON.parse(
    readFileSync(join(installedPackage, "package.json"), "utf8"),
  );
  const version = run(process.execPath, [cli, "--version"]);
  assert.equal(version.stdout.trim(), packageMetadata.version);

  const platforms = run(process.execPath, [cli, "list"]);
  assert.match(platforms.stdout, /esp32\s+tirtc-esp32-builder/);

  const skillsDir = join(temporary, "skills");
  run(process.execPath, [
    cli,
    "install",
    "esp32",
    "--skills-dir",
    skillsDir,
  ]);
  assert.equal(
    existsSync(join(skillsDir, "tirtc-esp32-builder", "SKILL.md")),
    true,
  );
  assert.equal(
    readFileSync(
      join(skillsDir, "tirtc-esp32-builder", "VERSION"),
      "utf8",
    ).trim(),
    packageMetadata.version,
  );

  const doctor = run(process.execPath, [cli, "doctor", "esp32", "--help"]);
  assert.match(doctor.stdout, /--expected-idf/);
  assert.match(doctor.stdout, /--thing-connect-root/);
  assert.match(doctor.stdout, /--expected-kit/);

  const registry = run(process.execPath, [
    cli,
    "boards",
    "esp32",
    "validate",
  ]);
  assert.match(registry.stdout, /valid board registry/);

  const setup = run(process.execPath, [cli, "setup", "esp32", "--help"]);
  assert.match(setup.stdout, /setup esp32 --install/);
  assert.equal(
    existsSync(join(installedPackage, "bin", "setup-esp32.js")),
    true,
  );
  assert.equal(
    existsSync(join(installedPackage, "bin", "install-esp32-kit.js")),
    true,
  );

  const managedRoot = join(temporary, "managed");
  const oldKit = join(managedRoot, "kits", "esp32s3", "1.0.0");
  const expectedKit = join(managedRoot, "kits", "esp32s3", "1.1.1");
  createDeviceKit(oldKit, "1.0.0");
  writeFileSync(
    join(managedRoot, "config.json"),
    JSON.stringify({
      device_kit_root: oldKit,
      device_kit_version: "1.1.1",
    }),
    "utf8",
  );
  const setupCheck = spawnSync(
    process.execPath,
    [
      cli,
      "setup",
      "esp32",
      "--root",
      managedRoot,
      "--skills-dir",
      skillsDir,
      "--idf-dir",
      join(temporary, "missing-idf"),
    ],
    {
      encoding: "utf8",
      env: { ...process.env, TIRTC_THING_CONNECT_ROOT: "" },
    },
  );
  assert.equal(setupCheck.status, 1, setupCheck.stderr);
  assert.match(setupCheck.stdout, /ignored stale Kit reference/);
  assert.match(
    setupCheck.stdout,
    new RegExp(expectedKit.replaceAll("\\", "\\\\")),
  );

  console.log(
    "Packed package smoke test passed (" + packageMetadata.version + ")",
  );
} finally {
  rmSync(temporary, { force: true, recursive: true });
}
