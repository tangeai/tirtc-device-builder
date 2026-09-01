import assert from "node:assert/strict";
import { createHash } from "node:crypto";
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
import test from "node:test";
import { fileURLToPath } from "node:url";
import { installEsp32KitArchive } from "../bin/install-esp32-kit.js";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const SCRIPT = join(ROOT, "scripts", "pack-esp32-kit.js");
const COMMIT = "a".repeat(40);

function writeFixture(root, relative, content = "fixture\n") {
  const path = join(root, relative);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, content);
}

function createSource(root) {
  const thingConnect = join(root, "thing-connect");
  const files = [
    "device-sim/scripts/create_esp32_project.py",
    "device-sim/templates/esp32-h5-ai/CMakeLists.txt",
    "device-sim/templates/esp32-h5-ai/sdkconfig.defaults",
    "device-sim/templates/esp32-h5-ai/platform-media-contract.json",
    "device-sim/templates/esp32-h5-ai/tirtc-runtime-contract.json",
    "device-sim/templates/esp32-h5-ai/README.md",
    "device-sim/device-sim-esp32/components/platform_client/CMakeLists.txt",
    "device-sim/device-sim-esp32/components/runtime_config/CMakeLists.txt",
    "device-sim/device-sim-esp32/components/wifi_manager/CMakeLists.txt",
    "device-sim/sdk/espressif-esp32s3/2.3.0/include/tirtc/tiRTC.h",
    "device-sim/sdk/espressif-esp32s3/2.3.0/lib/libTiRTC.a",
    "device-sim/sdk/espressif-esp32s3/2.3.0/manifest/build-contract.env",
    "device-integration.md",
    "device-h5-live.md",
    "device-ai.md",
    "device-session-model.md",
    "device-session-arbiter.md",
  ];
  for (const file of files) {
    writeFixture(thingConnect, file);
  }
  writeFixture(
    thingConnect,
    "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
    `#define WIFI_SETUP_URL "http://192.168.6.1"
#define WIFI_SETUP_IP_A 192
#define WIFI_SETUP_IP_B 168
#define WIFI_SETUP_IP_C 6
#define WIFI_SETUP_IP_D 1
const char *ssid_format = "TiRTC-%02X%02X";
void configure(void) { ap.ap.authmode = WIFI_AUTH_OPEN; }
`,
  );
  writeFixture(
    thingConnect,
    "device-sim/templates/esp32-h5-ai/README.md",
    "设备启动 TiRTC-XXXX 开放 SoftAP，无需密码；打开 http://192.168.6.1 配网。\n",
  );
  writeFixture(root, "LICENSE", "fixture license\n");
  return thingConnect;
}

test("pack:esp32-kit creates a versioned, checksummed minimal Kit", () => {
  const temporary = mkdtempSync(join(tmpdir(), "tirtc-kit-test-"));
  try {
    const source = createSource(join(temporary, "source"));
    const output = join(temporary, "dist");
    const result = spawnSync(
      process.execPath,
      [
        SCRIPT,
        "--source",
        source,
        "--kit-version",
        "1.0.0",
        "--source-commit",
        COMMIT,
        "--output",
        output,
      ],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 0, result.stderr);

    const archive = join(output, "tirtc-esp32s3-kit-1.0.0.tar.gz");
    const checksumPath = `${archive}.sha256`;
    assert.equal(existsSync(archive), true);
    assert.equal(existsSync(checksumPath), true);
    const actual = createHash("sha256")
      .update(readFileSync(archive))
      .digest("hex");
    assert.match(readFileSync(checksumPath, "utf8"), new RegExp(`^${actual}  `));

    const secondOutput = join(temporary, "dist-second");
    const second = spawnSync(
      process.execPath,
      [
        SCRIPT,
        "--source",
        source,
        "--kit-version",
        "1.0.0",
        "--source-commit",
        COMMIT,
        "--output",
        secondOutput,
      ],
      { encoding: "utf8" },
    );
    assert.equal(second.status, 0, second.stderr);
    assert.deepEqual(
      readFileSync(join(secondOutput, "tirtc-esp32s3-kit-1.0.0.tar.gz")),
      readFileSync(archive),
    );

    const extracted = join(temporary, "extracted");
    mkdirSync(extracted);
    const unpack = spawnSync("tar", ["-xzf", archive, "-C", extracted], {
      encoding: "utf8",
    });
    assert.equal(unpack.status, 0, unpack.stderr);
    const kit = join(extracted, "tirtc-esp32s3-kit-1.0.0");
    const manifest = JSON.parse(readFileSync(join(kit, "manifest.json"), "utf8"));
    assert.equal(manifest.kit_version, "1.0.0");
    assert.equal(manifest.tirtc_sdk_version, "2.3.0");
    assert.equal(manifest.source_commit, COMMIT);
    assert.equal(
      existsSync(
        join(kit, "device-sim/templates/esp32-h5-ai/platform-media-contract.json"),
      ),
      true,
    );
    assert.equal(
      existsSync(
        join(kit, "device-sim/templates/esp32-h5-ai/tirtc-runtime-contract.json"),
      ),
      true,
    );
    assert.equal(
      existsSync(
        join(
          kit,
          "device-sim/sdk/espressif-esp32s3/2.3.0/lib/libTiRTC.a",
        ),
      ),
      true,
    );
    assert.ok(Object.keys(manifest.files).length >= 16);

    const installed = join(temporary, "installed-kit");
    installEsp32KitArchive(archive, installed, {
      archiveName: "tirtc-esp32s3-kit-1.0.0.tar.gz",
      archiveRoot: "tirtc-esp32s3-kit-1.0.0",
      releaseTag: "test",
      sha256: actual,
      url: "https://example.invalid/test.tar.gz",
      version: "1.0.0",
    });
    assert.equal(
      existsSync(
        join(
          installed,
          "device-sim/sdk/espressif-esp32s3/2.3.0/lib/libTiRTC.a",
        ),
      ),
      true,
    );
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
});

test("pack:esp32-kit rejects incomplete sources", () => {
  const temporary = mkdtempSync(join(tmpdir(), "tirtc-kit-test-"));
  try {
    const source = join(temporary, "thing-connect");
    writeFixture(source, "device-sim/scripts/create_esp32_project.py");
    const result = spawnSync(
      process.execPath,
      [
        SCRIPT,
        "--source",
        source,
        "--kit-version",
        "1.0.0",
        "--source-commit",
        COMMIT,
        "--output",
        join(temporary, "dist"),
      ],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 1);
    assert.match(result.stderr, /required Kit source is missing/);
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
});

test("pack:esp32-kit rejects the legacy SoftAP contract", () => {
  const temporary = mkdtempSync(join(tmpdir(), "tirtc-kit-test-"));
  try {
    const source = createSource(join(temporary, "source"));
    writeFixture(
      source,
      "device-sim/device-sim-esp32/components/wifi_manager/src/wifi_manager.c",
      `#define WIFI_SETUP_URL "http://192.168.4.1"
#define WIFI_SETUP_PASSWORD "tirtc1234"
const char *ssid_format = "TiRTC-Setup-%02X%02X";
`,
    );
    const result = spawnSync(
      process.execPath,
      [
        SCRIPT,
        "--source",
        source,
        "--kit-version",
        "1.0.0",
        "--source-commit",
        COMMIT,
        "--output",
        join(temporary, "dist"),
      ],
      { encoding: "utf8" },
    );
    assert.equal(result.status, 1);
    assert.match(result.stderr, /SoftAP contract/);
  } finally {
    rmSync(temporary, { force: true, recursive: true });
  }
});
