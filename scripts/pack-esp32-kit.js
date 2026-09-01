#!/usr/bin/env node

import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  copyFileSync,
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  renameSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { normalizeUstarArchive } from "./lib/normalize-ustar.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SOURCE_REPOSITORY =
  "https://github.com/tangeai/tirtc-server-example";
const TARGET = "esp32s3";
const IDF_VERSION = "5.5.x";
const SDK_VERSION = "2.3.0";
const VERSION_PATTERN = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$/;
const COMMIT_PATTERN = /^[0-9a-f]{40}$/i;

const COPY_ITEMS = [
  "device-sim/scripts/create_esp32_project.py",
  "device-sim/templates/esp32-h5-ai",
  "device-sim/device-sim-esp32/components/platform_client",
  "device-sim/device-sim-esp32/components/runtime_config",
  "device-sim/device-sim-esp32/components/wifi_manager",
  `device-sim/sdk/espressif-esp32s3/${SDK_VERSION}`,
  "device-integration.md",
  "device-h5-live.md",
  "device-ai.md",
  "device-session-model.md",
  "device-session-arbiter.md",
];

const REQUIRED_FILES = [
  "device-sim/scripts/create_esp32_project.py",
  "device-sim/templates/esp32-h5-ai/CMakeLists.txt",
  "device-sim/templates/esp32-h5-ai/sdkconfig.defaults",
  "device-sim/templates/esp32-h5-ai/platform-media-contract.json",
  "device-sim/templates/esp32-h5-ai/tirtc-runtime-contract.json",
  "device-sim/device-sim-esp32/components/platform_client/CMakeLists.txt",
  "device-sim/device-sim-esp32/components/runtime_config/CMakeLists.txt",
  "device-sim/device-sim-esp32/components/wifi_manager/CMakeLists.txt",
  "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
  "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_captive_dns.c",
  "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_captive_dns.h",
  `device-sim/sdk/espressif-esp32s3/${SDK_VERSION}/include/tirtc/tiRTC.h`,
  `device-sim/sdk/espressif-esp32s3/${SDK_VERSION}/lib/libTiRTC.a`,
  `device-sim/sdk/espressif-esp32s3/${SDK_VERSION}/manifest/build-contract.env`,
  "device-integration.md",
  "device-h5-live.md",
  "device-ai.md",
  "device-session-model.md",
  "device-session-arbiter.md",
];

const KIT_NOTICE = `TiRTC ESP32-S3 Device Kit
Copyright 2026 探鸽智能 (TangeAI)

This kit contains the TiRTC ESP32-S3 SDK 2.3.0, including libTiRTC.a,
redistributed by TangeAI for TiRTC device development. It also contains a
focused selection of MIT-licensed ThingConnect example sources and protocol
documentation. ESP-IDF, board BSPs, credentials, and captured media are not
included and remain subject to their own licenses and terms.
`;

function printHelp() {
  console.log(`Usage:
  npm run pack:esp32-kit -- --source <thing-connect-or-repository> --kit-version <version>

Options:
  --source <path>         ThingConnect repository root or thing-connect directory
  --kit-version <semver>  Device Kit version, for example 1.0.0
  --output <path>         Output directory (default: ./dist)
  --source-commit <sha>   Override the detected 40-character source commit
  -h, --help              Show this help

The source paths used by the Kit must be clean in Git unless --source-commit
is supplied for an isolated packaging fixture.`);
}

function takeValue(args, index, option) {
  const value = args[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`${option} requires a value`);
  }
  return value;
}

function parseOptions(args) {
  const options = {
    help: false,
    kitVersion: null,
    output: join(ROOT, "dist"),
    source: null,
    sourceCommit: null,
  };
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    if (
      argument === "--source" ||
      argument === "--kit-version" ||
      argument === "--output" ||
      argument === "--source-commit"
    ) {
      const value = takeValue(args, index, argument);
      if (argument === "--source") {
        options.source = resolve(value);
      } else if (argument === "--kit-version") {
        options.kitVersion = value;
      } else if (argument === "--output") {
        options.output = resolve(value);
      } else {
        options.sourceCommit = value;
      }
      index += 1;
      continue;
    }
    throw new Error(`unknown option: ${argument}`);
  }
  if (options.help) {
    return options;
  }
  if (!options.source) {
    throw new Error("--source is required");
  }
  if (!options.kitVersion || !VERSION_PATTERN.test(options.kitVersion)) {
    throw new Error("--kit-version must be a semantic version such as 1.0.0");
  }
  if (options.sourceCommit && !COMMIT_PATTERN.test(options.sourceCommit)) {
    throw new Error("--source-commit must be a 40-character Git commit");
  }
  return options;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    encoding: "utf8",
    env: options.environment ?? process.env,
  });
  if (result.error) {
    throw new Error(`could not run ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    const detail = `${result.stdout || ""}${result.stderr || ""}`.trim();
    throw new Error(
      `${command} exited with status ${result.status}${detail ? `: ${detail}` : ""}`,
    );
  }
  return result.stdout.trim();
}

function normalizeThingConnectRoot(source) {
  for (const candidate of [source, join(source, "thing-connect")]) {
    if (existsSync(join(candidate, "device-sim", "scripts", "create_esp32_project.py"))) {
      return candidate;
    }
  }
  throw new Error(
    `--source does not contain thing-connect/device-sim resources: ${source}`,
  );
}

function repositoryRoot(thingConnectRoot) {
  try {
    return resolve(run("git", ["-C", thingConnectRoot, "rev-parse", "--show-toplevel"]));
  } catch {
    return dirname(thingConnectRoot);
  }
}

function sourceCommit(thingConnectRoot, override) {
  if (override) {
    return override.toLowerCase();
  }
  const commit = run("git", ["-C", thingConnectRoot, "rev-parse", "HEAD"]);
  if (!COMMIT_PATTERN.test(commit)) {
    throw new Error(`could not determine a full source commit: ${commit}`);
  }
  return commit.toLowerCase();
}

function assertSelectedSourceIsClean(thingConnectRoot, override) {
  if (override) {
    return;
  }
  const repository = repositoryRoot(thingConnectRoot);
  const selected = COPY_ITEMS.map((item) =>
    relative(repository, join(thingConnectRoot, item)),
  );
  const status = run("git", [
    "-C",
    repository,
    "status",
    "--porcelain",
    "--",
    ...selected,
  ]);
  if (status) {
    throw new Error(
      `selected Kit sources contain uncommitted changes:\n${status}`,
    );
  }
}

function copyFilter(source) {
  const name = basename(source);
  return !(
    name === ".git" ||
    name === "__pycache__" ||
    name === "build" ||
    name === "sdkconfig" ||
    name === "sdkconfig.old" ||
    name.endsWith(".pyc") ||
    name.endsWith(".pyo")
  );
}

function hashFile(path) {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function listFiles(root, current = root) {
  const files = [];
  const entries = readdirSync(current, { withFileTypes: true }).sort((left, right) =>
    left.name.localeCompare(right.name),
  );
  for (const entry of entries) {
    const path = join(current, entry.name);
    if (entry.isDirectory()) {
      files.push(...listFiles(root, path));
    } else if (entry.isFile()) {
      files.push(relative(root, path).split("\\").join("/"));
    } else {
      throw new Error(`Kit contains unsupported filesystem entry: ${path}`);
    }
  }
  return files;
}

function writeAtomic(path, content) {
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, content);
  renameSync(temporary, path);
}

function copyAtomic(source, destination) {
  const temporary = `${destination}.tmp-${process.pid}`;
  copyFileSync(source, temporary);
  renameSync(temporary, destination);
}

function copyLicense(thingConnectRoot, destination) {
  const candidates = [
    join(repositoryRoot(thingConnectRoot), "LICENSE"),
    join(thingConnectRoot, "LICENSE"),
    join(ROOT, "LICENSE"),
  ];
  const license = candidates.find((candidate) => existsSync(candidate));
  if (!license) {
    throw new Error("no LICENSE file is available for the Device Kit");
  }
  copyFileSync(license, destination);
}

function assertRequiredFiles(root) {
  const missing = REQUIRED_FILES.filter((path) => !existsSync(join(root, path)));
  if (missing.length > 0) {
    throw new Error(`Device Kit source is incomplete:\n${missing.join("\n")}`);
  }
  const library = join(
    root,
    `device-sim/sdk/espressif-esp32s3/${SDK_VERSION}/lib/libTiRTC.a`,
  );
  if (statSync(library).size === 0) {
    throw new Error("TiRTC static library is empty");
  }
}

function assertContains(content, fragment, label) {
  if (!content.includes(fragment)) {
    throw new Error(`SoftAP contract is missing ${label}: ${fragment}`);
  }
}

function assertOmits(content, fragment, label) {
  if (content.includes(fragment)) {
    throw new Error(`SoftAP contract still contains ${label}: ${fragment}`);
  }
}

function assertSoftApContract(root) {
  const sourcePath = join(
    root,
    "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
  );
  const dnsPath = join(
    root,
    "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_captive_dns.c",
  );
  const cmakePath = join(
    root,
    "device-sim/device-sim-esp32/components/wifi_manager/CMakeLists.txt",
  );
  const readmePath = join(root, "device-sim/templates/esp32-h5-ai/README.md");
  if (
    !existsSync(sourcePath) ||
    !existsSync(dnsPath) ||
    !existsSync(cmakePath) ||
    !existsSync(readmePath)
  ) {
    throw new Error("SoftAP contract sources are missing from the Device Kit");
  }

  const source = readFileSync(sourcePath, "utf8");
  assertContains(source, '"TiRTC-%02X%02X"', "SSID prefix");
  assertContains(source, "ap.ap.authmode = WIFI_AUTH_OPEN", "open authentication");
  assertContains(source, "#define WIFI_SETUP_IP_A 192", "IPv4 first octet");
  assertContains(source, "#define WIFI_SETUP_IP_B 168", "IPv4 second octet");
  assertContains(source, "#define WIFI_SETUP_IP_C 6", "IPv4 third octet");
  assertContains(source, "#define WIFI_SETUP_IP_D 1", "IPv4 fourth octet");
  assertContains(source, '"http://192.168.6.1"', "provisioning URL");
  assertContains(source, "wifi_captive_dns_start", "wildcard DNS startup");
  assertContains(source, "httpd_register_err_handler", "HTTP fallback redirect");
  assertOmits(
    source,
    "ESP_NETIF_CAPTIVEPORTAL_URI",
    "an invalid DHCP option 114 HTML endpoint",
  );
  assertOmits(source, "WIFI_SETUP_PASSWORD", "a SoftAP password");
  assertOmits(source, "TiRTC-Setup-", "the legacy SSID prefix");
  assertOmits(source, "192.168.4.1", "the legacy provisioning address");

  const dns = readFileSync(dnsPath, "utf8");
  assertContains(dns, "DNS_FLAG_RESPONSE", "DNS response handling");
  assertContains(dns, "wildcard DNS listening", "DNS server startup");

  const cmake = readFileSync(cmakePath, "utf8");
  assertContains(cmake, '"src/wifi_captive_dns.c"', "DNS component source");
  assertContains(cmake, "lwip", "DNS socket dependency");

  const readme = readFileSync(readmePath, "utf8");
  assertContains(readme, "TiRTC-XXXX", "documented SSID prefix");
  assertContains(readme, "无需密码", "documented open authentication");
  assertContains(readme, "http://192.168.6.1", "documented provisioning URL");
  assertContains(readme, "captive portal", "documented automatic portal discovery");
  assertOmits(readme, "192.168.4.1", "the legacy documented address");
}

function createArchive(staging, kitName, temporary) {
  const tarPath = join(temporary, `${kitName}.tar`);
  const environment = { ...process.env, LC_ALL: "C" };
  run(
    "tar",
    [
      "--sort=name",
      "--mtime=UTC 1970-01-01",
      "--owner=0",
      "--group=0",
      "--numeric-owner",
      "--format=ustar",
      "-cf",
      tarPath,
      "-C",
      staging,
      kitName,
    ],
    { environment },
  );
  normalizeUstarArchive(tarPath);
  run("gzip", ["-n", "-f", tarPath], { environment });
  return `${tarPath}.gz`;
}

function build(options) {
  const thingConnectRoot = normalizeThingConnectRoot(options.source);
  assertSelectedSourceIsClean(thingConnectRoot, options.sourceCommit);
  const commit = sourceCommit(thingConnectRoot, options.sourceCommit);
  const kitName = `tirtc-esp32s3-kit-${options.kitVersion}`;
  const temporary = mkdtempSync(join(tmpdir(), "tirtc-esp32-kit-"));
  try {
    const staging = join(temporary, "staging");
    const kitRoot = join(staging, kitName);
    mkdirSync(kitRoot, { recursive: true });

    for (const item of COPY_ITEMS) {
      const source = join(thingConnectRoot, item);
      if (!existsSync(source)) {
        throw new Error(`required Kit source is missing: ${source}`);
      }
      const destination = join(kitRoot, item);
      mkdirSync(dirname(destination), { recursive: true });
      cpSync(source, destination, {
        dereference: true,
        filter: copyFilter,
        recursive: statSync(source).isDirectory(),
      });
    }

    copyLicense(thingConnectRoot, join(kitRoot, "LICENSE"));
    writeFileSync(join(kitRoot, "NOTICE"), KIT_NOTICE, "utf8");
    assertRequiredFiles(kitRoot);
    assertSoftApContract(kitRoot);

    const files = Object.fromEntries(
      listFiles(kitRoot).map((path) => [path, hashFile(join(kitRoot, path))]),
    );
    const manifest = {
      schema_version: 1,
      kit_version: options.kitVersion,
      platform: "espressif-esp32s3",
      target: TARGET,
      idf_version: IDF_VERSION,
      tirtc_sdk_version: SDK_VERSION,
      generator: "device-sim/scripts/create_esp32_project.py",
      source_repository: SOURCE_REPOSITORY,
      source_commit: commit,
      files,
    };
    writeFileSync(
      join(kitRoot, "manifest.json"),
      `${JSON.stringify(manifest, null, 2)}\n`,
      "utf8",
    );

    const archive = createArchive(staging, kitName, temporary);
    mkdirSync(options.output, { recursive: true });
    const destination = join(options.output, `${kitName}.tar.gz`);
    copyAtomic(archive, destination);
    const checksum = hashFile(destination);
    const checksumPath = `${destination}.sha256`;
    writeAtomic(checksumPath, `${checksum}  ${basename(destination)}\n`);

    console.log(`Created ${destination}`);
    console.log(`Created ${checksumPath}`);
    console.log(`SHA256  ${checksum}`);
    console.log(`Source  ${SOURCE_REPOSITORY}@${commit}`);
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
}

try {
  const options = parseOptions(process.argv.slice(2));
  if (options.help) {
    printHelp();
  } else {
    build(options);
  }
} catch (error) {
  console.error(`ERROR: ${error instanceof Error ? error.message : String(error)}`);
  process.exitCode = 1;
}
