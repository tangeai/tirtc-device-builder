import { spawnSync } from "node:child_process";
import {
  chmodSync,
  existsSync,
  mkdirSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import { homedir } from "node:os";
import { delimiter, dirname, join, resolve } from "node:path";
import { ESP32_KIT } from "./esp32-kit-metadata.js";

const EXPECTED_IDF_LINE = "5.5";
const PINNED_IDF_VERSION = "v5.5.4";
const TARGET = "esp32s3";
const TARGET_COMPILER = "xtensa-esp32s3-elf-gcc";
const ESP_IDF_REPOSITORY = "https://github.com/espressif/esp-idf.git";
const GENERATOR_PATH = join(
  "device-sim",
  "scripts",
  "create_esp32_project.py",
);
const SDK_PATH = join(
  "device-sim",
  "sdk",
  "espressif-esp32s3",
  "2.3.0",
);
const REQUIRED_SDK_FILES = [
  join("include", "tirtc", "tiRTC.h"),
  join("lib", "libTiRTC.a"),
  join("manifest", "build-contract.env"),
];

function setupRootFrom(environment) {
  return resolve(
    environment.TIRTC_DEVICE_BUILDER_ROOT ||
      join(homedir(), ".tirtc-device-builder"),
  );
}

function takeValue(args, index, option) {
  const value = args[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`${option} requires a path`);
  }
  return value;
}

export function parseSetupOptions(args, defaults = {}) {
  const environment = defaults.environment ?? process.env;
  const options = {
    forceSkill: false,
    help: false,
    idfDir: null,
    install: false,
    kitArchive: null,
    rootDir: setupRootFrom(environment),
    skillsDir: defaults.skillsDir,
    thingConnectRoot: null,
  };

  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    if (argument === "--install") {
      options.install = true;
      continue;
    }
    if (argument === "--force-skill") {
      options.forceSkill = true;
      continue;
    }
    if (
      argument === "--root" ||
      argument === "--skills-dir" ||
      argument === "--thing-connect-root" ||
      argument === "--kit-archive" ||
      argument === "--idf-dir"
    ) {
      const value = resolve(takeValue(args, index, argument));
      if (argument === "--root") {
        options.rootDir = value;
      } else if (argument === "--skills-dir") {
        options.skillsDir = value;
      } else if (argument === "--thing-connect-root") {
        options.thingConnectRoot = value;
      } else if (argument === "--kit-archive") {
        options.kitArchive = value;
      } else {
        options.idfDir = value;
      }
      index += 1;
      continue;
    }
    throw new Error(`unknown setup option: ${argument}`);
  }

  if (!options.skillsDir) {
    throw new Error("setup requires a default skills directory");
  }
  if (options.forceSkill && !options.install) {
    throw new Error("--force-skill requires --install");
  }
  if (options.kitArchive && !options.install) {
    throw new Error("--kit-archive requires --install");
  }
  return options;
}

export function printSetupHelp(version) {
  console.log(`TiRTC Device Builder ${version}

Usage:
  tirtc-device-builder setup esp32 [options]

Options:
  --install                    Install missing user-space components
  --root <path>                Managed files (default: ~/.tirtc-device-builder)
  --skills-dir <path>          Codex skills directory
  --thing-connect-root <path>  Reuse an existing Device Kit or legacy workspace
  --kit-archive <path>         Install from a local verified Kit archive
  --idf-dir <path>             Reuse or install ESP-IDF at this path
  --force-skill                Replace an existing Skill; requires --install
  -h, --help                   Show this help

Examples:
  npx tirtc-device-builder setup esp32
  npx tirtc-device-builder setup esp32 --install
  npx tirtc-device-builder setup esp32 --install --root /opt/tirtc-dev

Check mode is read-only. --install downloads the pinned ESP32 Device Kit,
may clone ESP-IDF v5.5.4, runs Espressif's user-space tool installer, and
installs the Codex Skill. It does not run sudo or edit shell profiles.`);
}

function printCheck(status, name, detail) {
  console.log(`${status.padEnd(5)} ${name}: ${detail}`);
}

function commandResult(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: options.cwd,
    encoding: "utf8",
    env: options.environment ?? process.env,
    stdio: options.stdio ?? "pipe",
  });
}

function commandAvailable(command, args = ["--version"], environment) {
  const result = commandResult(command, args, { environment });
  return !result.error && result.status === 0;
}

function runOrThrow(command, args, options = {}) {
  console.log(`RUN   ${command} ${args.join(" ")}`);
  const result = commandResult(command, args, {
    ...options,
    stdio: "inherit",
  });
  if (result.error) {
    throw new Error(`could not run ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(`${command} exited with status ${result.status ?? 1}`);
  }
}

function normalizeThingConnectRoot(candidate) {
  if (!candidate) {
    return null;
  }
  const absolute = resolve(candidate);
  for (const root of [absolute, join(absolute, "thing-connect")]) {
    if (existsSync(join(root, GENERATOR_PATH))) {
      return root;
    }
  }
  return null;
}

function discoverThingConnectRoot(start) {
  let candidate = resolve(start);
  for (;;) {
    const found = normalizeThingConnectRoot(candidate);
    if (found) {
      return found;
    }
    const parent = dirname(candidate);
    if (parent === candidate) {
      return null;
    }
    candidate = parent;
  }
}

function thingConnectReady(root) {
  if (!root || !existsSync(join(root, GENERATOR_PATH))) {
    return false;
  }
  const sdk = join(root, SDK_PATH);
  return REQUIRED_SDK_FILES.every((relative) =>
    existsSync(join(sdk, relative)),
  );
}

function readConfig(path) {
  if (!existsSync(path)) {
    return {};
  }
  try {
    const value = JSON.parse(readFileSync(path, "utf8"));
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

function findOnPath(name, environment) {
  const suffixes =
    process.platform === "win32" ? ["", ".exe", ".cmd", ".bat"] : [""];
  for (const entry of (environment.PATH || "").split(delimiter)) {
    if (!entry) {
      continue;
    }
    for (const suffix of suffixes) {
      const candidate = join(entry, name + suffix);
      if (existsSync(candidate)) {
        try {
          return realpathSync(candidate);
        } catch {
          return candidate;
        }
      }
    }
  }
  return null;
}

function versionMatches(output) {
  const match = output.match(/(?:ESP-IDF\s+)?v?(\d+)\.(\d+)/i);
  return Boolean(match && `${match[1]}.${match[2]}` === EXPECTED_IDF_LINE);
}

function currentIdf(environment) {
  const idfPath = findOnPath("idf.py", environment);
  const compilerPath = findOnPath(TARGET_COMPILER, environment);
  if (!idfPath) {
    return { ready: false, detail: "idf.py is not active", root: null };
  }
  const result = commandResult(idfPath, ["--version"], { environment });
  const output = `${result.stdout || ""}\n${result.stderr || ""}`.trim();
  let root = null;
  if (
    environment.IDF_PATH &&
    existsSync(join(environment.IDF_PATH, "export.sh"))
  ) {
    root = resolve(environment.IDF_PATH);
  } else if (dirname(idfPath).endsWith(join("tools"))) {
    root = dirname(dirname(idfPath));
  }
  if (result.status !== 0 || !versionMatches(output)) {
    return {
      ready: false,
      detail: `${output || "unknown ESP-IDF version"}; expected 5.5.x`,
      root,
    };
  }
  if (!compilerPath) {
    return {
      ready: false,
      detail: `${TARGET_COMPILER} is not active`,
      root,
    };
  }
  return { ready: true, detail: output, root };
}

function activatedResult(idfDir, toolsPath, command, args, options = {}) {
  const environment = { ...process.env, ...options.environment };
  if (toolsPath) {
    environment.IDF_TOOLS_PATH = toolsPath;
  }
  const script =
    'set -e\n. "$1/export.sh" >/dev/null\nshift\nexec "$@"';
  return commandResult(
    "bash",
    ["-c", script, "tirtc-device-builder", idfDir, command, ...args],
    {
      environment,
      stdio: options.stdio,
    },
  );
}

function idfAtDirectory(idfDir, toolsPath, environment) {
  if (!idfDir || !existsSync(join(idfDir, "export.sh"))) {
    return {
      ready: false,
      detail: `missing ${join(idfDir || "<unset>", "export.sh")}`,
    };
  }
  const version = activatedResult(idfDir, toolsPath, "idf.py", ["--version"], {
    environment,
  });
  const output = `${version.stdout || ""}\n${version.stderr || ""}`.trim();
  if (version.error || version.status !== 0) {
    return {
      ready: false,
      detail: output || version.error?.message || "ESP-IDF activation failed",
    };
  }
  if (!versionMatches(output)) {
    return {
      ready: false,
      detail: `${output}; expected 5.5.x`,
      wrongVersion: true,
    };
  }
  const compiler = activatedResult(
    idfDir,
    toolsPath,
    TARGET_COMPILER,
    ["--version"],
    { environment },
  );
  if (compiler.error || compiler.status !== 0) {
    return {
      ready: false,
      detail: `${TARGET_COMPILER} is not installed for this ESP-IDF`,
    };
  }
  return { ready: true, detail: output };
}

function shellQuote(value) {
  return `'${String(value).replaceAll("'", `'\\''`)}'`;
}

function writeAtomic(path, content, mode) {
  const temporary = `${path}.tmp-${process.pid}`;
  writeFileSync(temporary, content, { encoding: "utf8", mode });
  renameSync(temporary, path);
  chmodSync(path, mode);
}

function writeManagedEnvironment(context, packageVersion) {
  mkdirSync(context.rootDir, { recursive: true });
  const config = {
    schema_version: 1,
    platform: "esp32",
    package_version: packageVersion,
    idf_version: PINNED_IDF_VERSION,
    idf_dir: context.idfDir,
    idf_tools_path: context.idfToolsPath,
    device_kit_version: ESP32_KIT.version,
    device_kit_root: context.thingConnectRoot,
    thing_connect_root: context.thingConnectRoot,
    skills_dir: context.skillsDir,
  };
  writeAtomic(
    join(context.rootDir, "config.json"),
    JSON.stringify(config, null, 2) + "\n",
    0o600,
  );

  const lines = [
    "# Generated by tirtc-device-builder setup esp32.",
    "# Contains paths only; no device or network credentials.",
  ];
  if (context.idfToolsPath) {
    lines.push(
      `export IDF_TOOLS_PATH=${shellQuote(context.idfToolsPath)}`,
    );
  }
  if (context.idfDir && existsSync(join(context.idfDir, "export.sh"))) {
    lines.push(`. ${shellQuote(join(context.idfDir, "export.sh"))}`);
  }
  lines.push(
    `export TIRTC_THING_CONNECT_ROOT=${shellQuote(context.thingConnectRoot)}`,
  );
  writeAtomic(join(context.rootDir, "env.sh"), lines.join("\n") + "\n", 0o600);
}

function setupContext(options, runtime) {
  const environment = runtime.environment;
  const configPath = join(options.rootDir, "config.json");
  const config = readConfig(configPath);
  const managedThingConnect = join(
    options.rootDir,
    "kits",
    "esp32s3",
    ESP32_KIT.version,
  );

  let requestedThingConnect = null;
  let thingConnectSource = "managed Device Kit";
  if (options.thingConnectRoot) {
    requestedThingConnect = options.thingConnectRoot;
    thingConnectSource = "explicit --thing-connect-root";
  } else if (environment.TIRTC_THING_CONNECT_ROOT) {
    requestedThingConnect = environment.TIRTC_THING_CONNECT_ROOT;
    thingConnectSource = "TIRTC_THING_CONNECT_ROOT";
  } else {
    const discovered = discoverThingConnectRoot(runtime.cwd);
    if (discovered) {
      requestedThingConnect = discovered;
      thingConnectSource = "workspace discovery";
    } else if (config.device_kit_root || config.thing_connect_root) {
      requestedThingConnect = config.device_kit_root || config.thing_connect_root;
      thingConnectSource = "managed config";
    } else {
      requestedThingConnect = managedThingConnect;
    }
  }
  const normalizedThingConnect = normalizeThingConnectRoot(
    requestedThingConnect,
  );
  const thingConnectRoot =
    normalizedThingConnect || resolve(requestedThingConnect);

  const active = currentIdf(environment);
  let idfDir;
  let idfSource;
  if (options.idfDir) {
    idfDir = options.idfDir;
    idfSource = "explicit --idf-dir";
  } else if (active.ready && active.root) {
    idfDir = active.root;
    idfSource = "active ESP-IDF";
  } else if (
    environment.IDF_PATH &&
    existsSync(join(environment.IDF_PATH, "export.sh"))
  ) {
    idfDir = resolve(environment.IDF_PATH);
    idfSource = "IDF_PATH";
  } else if (config.idf_dir) {
    idfDir = resolve(config.idf_dir);
    idfSource = "managed config";
  } else {
    idfDir = join(options.rootDir, `esp-idf-${PINNED_IDF_VERSION}`);
    idfSource = "managed";
  }
  const idfToolsPath =
    environment.IDF_TOOLS_PATH ||
    config.idf_tools_path ||
    (idfSource === "managed" ? join(options.rootDir, "espressif") : null);
  const directoryIdf = idfAtDirectory(
    idfDir,
    idfToolsPath,
    environment,
  );
  const idf = idfSource === "active ESP-IDF" && active.ready
    ? { ...active, directoryReady: directoryIdf.ready }
    : { ...directoryIdf, root: idfDir, directoryReady: directoryIdf.ready };

  return {
    activeIdf: active,
    configPath,
    idf,
    idfDir,
    idfSource,
    idfToolsPath,
    managedThingConnect,
    rootDir: options.rootDir,
    skillTarget: join(options.skillsDir, runtime.platform.skill),
    skillsDir: options.skillsDir,
    thingConnectReady: thingConnectReady(thingConnectRoot),
    thingConnectRoot,
    thingConnectSource,
  };
}

function printState(context, runtime) {
  printCheck("INFO", "setup root", context.rootDir);
  printCheck(
    existsSync(join(context.skillTarget, "SKILL.md")) ? "PASS" : "MISS",
    "Codex Skill",
    context.skillTarget,
  );
  printCheck(
    context.thingConnectReady ? "PASS" : "MISS",
    "ESP32 Device Kit",
    `${context.thingConnectRoot} (${context.thingConnectSource})`,
  );
  printCheck(
    context.idf.ready ? "PASS" : "MISS",
    "ESP-IDF",
    `${context.idf.detail} (${context.idfSource}: ${context.idfDir})`,
  );
  for (const command of ["python3", "git", "bash", "tar"]) {
    printCheck(
      commandAvailable(command, ["--version"], runtime.environment)
        ? "PASS"
        : "MISS",
      command,
      findOnPath(command, runtime.environment) || "not found",
    );
  }
}

function prerequisites(runtime) {
  const checks = [
    ["python3", ["--version"]],
    ["git", ["--version"]],
    ["bash", ["--version"]],
    ["tar", ["--version"]],
  ];
  return checks
    .filter(
      ([command, args]) =>
        !commandAvailable(command, args, runtime.environment),
    )
    .map(([command]) => command);
}

function printSystemDependencyHelp(missing) {
  console.error(
    `BLOCKED: missing system prerequisite(s): ${missing.join(", ")}`,
  );
  console.error("Ubuntu/Debian/WSL example:");
  console.error(
    "  sudo apt-get update && sudo apt-get install -y git python3 python3-venv",
  );
  console.error(
    "Install system packages yourself, then rerun setup; this command never runs sudo.",
  );
}

function installSkill(options, context, runtime) {
  const present = existsSync(join(context.skillTarget, "SKILL.md"));
  if (present && !options.forceSkill) {
    console.log(`SKIP  Codex Skill already exists: ${context.skillTarget}`);
    return;
  }
  const args = [
    runtime.cliPath,
    "install",
    runtime.platform.name,
    "--skills-dir",
    options.skillsDir,
  ];
  if (options.forceSkill) {
    args.push("--force");
  }
  runOrThrow(process.execPath, args, {
    environment: runtime.environment,
  });
}

function installDeviceKit(options, context, runtime) {
  if (context.thingConnectReady) {
    console.log(
      `SKIP  ESP32 Device Kit already ready: ${context.thingConnectRoot}`,
    );
    return context.thingConnectRoot;
  }
  if (context.thingConnectSource !== "managed Device Kit") {
    throw new Error(
      `${context.thingConnectSource} does not contain a complete ESP32 Device Kit: ${context.thingConnectRoot}`,
    );
  }
  if (existsSync(context.managedThingConnect)) {
    throw new Error(
      `refusing to overwrite incomplete directory: ${context.managedThingConnect}`,
    );
  }
  const installer = join(runtime.packageRoot, "bin", "install-esp32-kit.js");
  const args = [installer, "--target", context.managedThingConnect];
  if (options.kitArchive) {
    args.push("--archive", options.kitArchive);
  }
  runOrThrow(process.execPath, args, { environment: runtime.environment });
  const root = normalizeThingConnectRoot(context.managedThingConnect);
  if (!thingConnectReady(root)) {
    throw new Error(
      `installed ESP32 Device Kit is missing its generator or TiRTC SDK: ${context.managedThingConnect}`,
    );
  }
  return root;
}

function installIdf(context, runtime) {
  if (context.idf.ready) {
    console.log(`SKIP  ESP-IDF already ready: ${context.idfDir}`);
    return;
  }
  if (process.platform === "win32") {
    throw new Error(
      "automatic ESP-IDF installation currently supports Linux, WSL, and macOS; use Espressif's Windows installer and rerun setup",
    );
  }
  if (context.idf.wrongVersion && existsSync(context.idfDir)) {
    throw new Error(
      `existing ESP-IDF at ${context.idfDir} does not match 5.5.x; select another --idf-dir`,
    );
  }
  if (!existsSync(join(context.idfDir, "export.sh"))) {
    if (existsSync(context.idfDir)) {
      throw new Error(
        `refusing to overwrite incomplete directory: ${context.idfDir}`,
      );
    }
    mkdirSync(dirname(context.idfDir), { recursive: true });
    runOrThrow(
      "git",
      [
        "clone",
        "--branch",
        PINNED_IDF_VERSION,
        "--depth",
        "1",
        "--recursive",
        "--shallow-submodules",
        ESP_IDF_REPOSITORY,
        context.idfDir,
      ],
      { environment: runtime.environment },
    );
  }
  const installEnvironment = { ...runtime.environment };
  if (context.idfToolsPath) {
    installEnvironment.IDF_TOOLS_PATH = context.idfToolsPath;
  }
  runOrThrow("bash", [join(context.idfDir, "install.sh"), TARGET], {
    environment: installEnvironment,
  });
  const ready = idfAtDirectory(
    context.idfDir,
    context.idfToolsPath,
    runtime.environment,
  );
  if (!ready.ready) {
    throw new Error(`ESP-IDF installation did not become ready: ${ready.detail}`);
  }
}

function runDoctor(context, runtime) {
  const doctor = join(
    runtime.packageRoot,
    "skills",
    runtime.platform.skill,
    "scripts",
    "doctor.py",
  );
  const args = [
    doctor,
    "--expected-idf",
    EXPECTED_IDF_LINE,
    "--target",
    TARGET,
    "--thing-connect-root",
    context.thingConnectRoot,
    "--require-workspace",
  ];
  let result;
  if (context.idfDir && existsSync(join(context.idfDir, "export.sh"))) {
    result = activatedResult(
      context.idfDir,
      context.idfToolsPath,
      runtime.environment.PYTHON || "python3",
      args,
      {
        environment: {
          ...runtime.environment,
          TIRTC_THING_CONNECT_ROOT: context.thingConnectRoot,
        },
        stdio: "inherit",
      },
    );
  } else {
    result = commandResult(runtime.environment.PYTHON || "python3", args, {
      environment: {
        ...runtime.environment,
        TIRTC_THING_CONNECT_ROOT: context.thingConnectRoot,
      },
      stdio: "inherit",
    });
  }
  if (result.error) {
    console.error(`ERROR: could not run Doctor: ${result.error.message}`);
    return 1;
  }
  return Number.isInteger(result.status) ? result.status : 1;
}

function isReady(context) {
  return (
    existsSync(join(context.skillTarget, "SKILL.md")) &&
    context.thingConnectReady &&
    context.idf.ready
  );
}

export function runEsp32Setup(args, input) {
  const runtime = {
    cliPath: input.cliPath,
    cwd: input.cwd ?? process.cwd(),
    environment: input.environment ?? process.env,
    packageRoot: input.packageRoot,
    packageVersion: input.packageVersion,
    platform: input.platform,
  };
  let options;
  try {
    options = parseSetupOptions(args, {
      environment: runtime.environment,
      skillsDir: input.defaultSkillsDir,
    });
  } catch (error) {
    console.error(
      `ERROR: ${error instanceof Error ? error.message : String(error)}`,
    );
    return 1;
  }
  if (options.help) {
    printSetupHelp(runtime.packageVersion);
    return 0;
  }

  let context = setupContext(options, runtime);
  printState(context, runtime);
  if (!options.install) {
    if (!isReady(context)) {
      console.log("OVERALL: NEEDS_SETUP");
      console.log(
        "NEXT: npx tirtc-device-builder@latest setup esp32 --install",
      );
      return 1;
    }
    const status = runDoctor(context, runtime);
    console.log(
      status === 0 ? "SETUP: READY" : "SETUP: Doctor reported a blocker",
    );
    return status;
  }

  const missing = prerequisites(runtime);
  if (missing.length > 0) {
    printSystemDependencyHelp(missing);
    return 1;
  }
  console.log("INSTALL PLAN:");
  console.log(`  Skill:        ${context.skillTarget}`);
  console.log(`  Device Kit:   ${context.thingConnectRoot} (${ESP32_KIT.version})`);
  console.log(`  ESP-IDF:      ${context.idfDir} (${PINNED_IDF_VERSION})`);
  console.log(`  IDF tools:    ${context.idfToolsPath || "existing default"}`);
  console.log("  System sudo:  never");
  console.log("  Shell profile: unchanged");

  try {
    installSkill(options, context, runtime);
    const thingConnectRoot = installDeviceKit(options, context, runtime);
    context = { ...context, thingConnectRoot, thingConnectReady: true };
    installIdf(context, runtime);
    context = setupContext(options, {
      ...runtime,
      environment: {
        ...runtime.environment,
        TIRTC_THING_CONNECT_ROOT: thingConnectRoot,
      },
    });
    if (!context.idf.ready) {
      const directoryIdf = idfAtDirectory(
        context.idfDir,
        context.idfToolsPath,
        runtime.environment,
      );
      context = { ...context, idf: directoryIdf };
    }
    writeManagedEnvironment(context, runtime.packageVersion);
  } catch (error) {
    console.error(
      `ERROR: ${error instanceof Error ? error.message : String(error)}`,
    );
    console.error(
      "The setup is resumable. Fix the reported item and rerun the same command.",
    );
    return 1;
  }

  const status = runDoctor(context, runtime);
  if (status !== 0) {
    console.error("SETUP: installation finished, but Doctor still reports a blocker");
    return status;
  }
  console.log("SETUP: READY");
  console.log(`Environment helper: ${join(context.rootDir, "env.sh")}`);
  console.log("Start a new Codex session and invoke $tirtc-esp32-builder.");
  return 0;
}
