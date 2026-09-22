#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { ESP32_KIT, ESP32_KITS } from "./esp32-kit-metadata.js";

const REQUIRED_FILES_BY_TARGET = {
  esp32s3: [
    "manifest.json",
    "device-sim/scripts/create_esp32_project.py",
    "device-sim/templates/esp32-h5-ai/CMakeLists.txt",
    "device-sim/templates/esp32-h5-ai/platform-media-contract.json",
    "device-sim/templates/esp32-h5-ai/tirtc-runtime-contract.json",
  ],
  esp32p4: [
    "manifest.json",
    "device-sim/scripts/create_esp32_project.py",
    "device-sim/device-sim-p4/CMakeLists.txt",
    "device-sim/device-sim-p4/sdkconfig.defaults",
    "device-sim/device-sim-p4/dependencies.lock",
    "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
  ],
};

const SDK_VERSION_PATTERN_BY_TARGET = {
  esp32s3: /^(?:2\.3\.0|2\.5\.0)$/,
  esp32p4: /^2\.5\.0$/,
};

function hashFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function runTar(args) {
  const result = spawnSync("tar", args, { encoding: "utf8" });
  if (result.error) {
    throw new Error(`could not run tar: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(
      `tar exited with status ${result.status}: ${result.stderr.trim()}`,
    );
  }
  return result.stdout;
}

function assertArchivePaths(archive, archiveRoot) {
  const entries = runTar(["-tzf", archive])
    .split(/\r?\n/)
    .filter(Boolean);
  if (entries.length === 0) {
    throw new Error("Device Kit archive is empty");
  }
  for (const entry of entries) {
    if (
      entry.startsWith("/") ||
      entry.split("/").includes("..") ||
      !(entry === archiveRoot || entry.startsWith(`${archiveRoot}/`))
    ) {
      throw new Error(`unsafe Device Kit archive path: ${entry}`);
    }
  }
}

function assertNoLinks(root, current = root) {
  for (const entry of readdirSync(current, { withFileTypes: true })) {
    const path = join(current, entry.name);
    const stat = lstatSync(path);
    if (stat.isSymbolicLink()) {
      throw new Error(`Device Kit contains a symbolic link: ${relative(root, path)}`);
    }
    if (stat.isDirectory()) {
      assertNoLinks(root, path);
    } else if (!stat.isFile()) {
      throw new Error(`Device Kit contains an unsupported entry: ${relative(root, path)}`);
    }
  }
}

function validateExtractedKit(root, metadata) {
  const requiredFiles = REQUIRED_FILES_BY_TARGET[metadata.target] ?? [];
  const missing = requiredFiles.filter((path) => !existsSync(join(root, path)));
  if (missing.length > 0) {
    throw new Error(`Device Kit is incomplete: ${missing.join(", ")}`);
  }
  assertNoLinks(root);
  let manifest;
  try {
    manifest = JSON.parse(readFileSync(join(root, "manifest.json"), "utf8"));
  } catch (error) {
    throw new Error(
      `Device Kit manifest is invalid: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
  if (manifest.kit_version !== metadata.version) {
    throw new Error(
      `Device Kit version mismatch: expected ${metadata.version}, got ${manifest.kit_version}`,
    );
  }
  const sdkPattern = SDK_VERSION_PATTERN_BY_TARGET[metadata.target];
  if (!sdkPattern ||
      manifest.target !== metadata.target ||
      manifest.platform !== metadata.platform ||
      !sdkPattern.test(manifest.tirtc_sdk_version) ||
      (metadata.sdkVersion && manifest.tirtc_sdk_version !== metadata.sdkVersion)) {
    throw new Error("Device Kit target or TiRTC SDK version is incompatible");
  }
  const sdkRoot = `device-sim/sdk/${metadata.platform}/${manifest.tirtc_sdk_version}`;
  const sdkFiles = [
    `${sdkRoot}/include/tirtc/tiRTC.h`,
    `${sdkRoot}/lib/libTiRTC.a`,
    `${sdkRoot}/manifest/build-contract.env`,
  ];
  const missingSdk = sdkFiles.filter((path) => !existsSync(join(root, path)));
  if (missingSdk.length > 0) {
    throw new Error(`Device Kit SDK is incomplete: ${missingSdk.join(", ")}`);
  }
  if (!manifest.files || typeof manifest.files !== "object") {
    throw new Error("Device Kit manifest has no file checksums");
  }
  for (const [path, expected] of Object.entries(manifest.files)) {
    if (
      typeof expected !== "string" ||
      path.startsWith("/") ||
      path.split("/").includes("..")
    ) {
      throw new Error(`Device Kit manifest contains an unsafe entry: ${path}`);
    }
    const file = join(root, path);
    if (!existsSync(file) || hashFile(file) !== expected) {
      throw new Error(`Device Kit file checksum mismatch: ${path}`);
    }
  }
}

export function installEsp32KitArchive(archive, target, metadata = ESP32_KIT) {
  const resolvedArchive = resolve(archive);
  const resolvedTarget = resolve(target);
  if (!existsSync(resolvedArchive)) {
    throw new Error(`Device Kit archive does not exist: ${resolvedArchive}`);
  }
  const actualHash = hashFile(resolvedArchive);
  if (actualHash !== metadata.sha256) {
    throw new Error(
      `Device Kit SHA-256 mismatch: expected ${metadata.sha256}, got ${actualHash}`,
    );
  }
  if (existsSync(resolvedTarget)) {
    throw new Error(`refusing to overwrite existing Device Kit: ${resolvedTarget}`);
  }
  mkdirSync(dirname(resolvedTarget), { recursive: true });
  const temporary = mkdtempSync(join(dirname(resolvedTarget), ".kit-install-"));
  try {
    assertArchivePaths(resolvedArchive, metadata.archiveRoot);
    runTar(["-xzf", resolvedArchive, "-C", temporary]);
    const extracted = join(temporary, metadata.archiveRoot);
    validateExtractedKit(extracted, metadata);
    renameSync(extracted, resolvedTarget);
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
  console.log(`Installed ESP32 Device Kit ${metadata.version} to ${resolvedTarget}`);
}

async function download(url, destination) {
  console.log(`GET   ${url}`);
  const response = await fetch(url, { redirect: "follow" });
  if (!response.ok) {
    throw new Error(`Device Kit download failed: HTTP ${response.status}`);
  }
  const content = Buffer.from(await response.arrayBuffer());
  writeFileSync(destination, content, { mode: 0o600 });
}

function parseArgs(args) {
  let archive = null;
  let target = null;
  let kit = "esp32s3";
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--archive" || argument === "--target" || argument === "--kit") {
      const value = args[index + 1];
      if (!value || value.startsWith("--")) {
        throw new Error(`${argument} requires a value`);
      }
      if (argument === "--archive") {
        archive = resolve(value);
      } else if (argument === "--target") {
        target = resolve(value);
      } else {
        kit = value;
      }
      index += 1;
      continue;
    }
    throw new Error(`unknown Device Kit installer option: ${argument}`);
  }
  if (!target) {
    throw new Error("--target is required");
  }
  if (!(kit in ESP32_KITS)) {
    throw new Error(`unknown Device Kit target selector: ${kit}`);
  }
  return { archive, target, metadata: ESP32_KITS[kit] };
}

async function main() {
  const options = parseArgs(process.argv.slice(2));
  const metadata = options.metadata;
  let archive = options.archive;
  let downloadDirectory = null;
  try {
    if (!archive) {
      if (!metadata.released) {
        throw new Error(
          `Device Kit ${metadata.target} metadata is not yet pinned to a release; pass --archive`,
        );
      }
      downloadDirectory = mkdtempSync(join(tmpdir(), "tirtc-kit-download-"));
      archive = join(downloadDirectory, metadata.archiveName);
      await download(metadata.url, archive);
    }
    installEsp32KitArchive(archive, options.target, metadata);
  } finally {
    if (downloadDirectory) {
      rmSync(downloadDirectory, { force: true, recursive: true });
    }
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`ERROR: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  });
}
