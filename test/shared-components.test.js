import assert from "node:assert/strict";
import {
  existsSync,
  readFileSync,
} from "node:fs";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

/*
 * The ESP32-S3 reference and the ESP32-P4 reference share ONE source for the
 * transport components (platform_client, runtime_config, wifi_manager). These
 * guards freeze that contract so neither reference can silently drift, and so
 * the on-flash NVS format stays upgrade-compatible for both targets.
 */

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const KIT_SRC = join(ROOT, "kit-src", "device-sim");
const SHARED = join(KIT_SRC, "device-sim-esp32", "components");
const P4 = join(KIT_SRC, "device-sim-p4");

test("P4 reference owns no transport component copies", () => {
  for (const component of ["platform_client", "runtime_config", "wifi_manager"]) {
    assert.equal(
      existsSync(join(P4, "components", component)),
      false,
      `device-sim-p4 must not bundle its own ${component}`,
    );
  }
});

test("P4 reference resolves shared components through a guarded EXTRA_COMPONENT_DIRS", () => {
  const cmake = readFileSync(join(P4, "CMakeLists.txt"), "utf8");
  assert.match(
    cmake,
    /EXTRA_COMPONENT_DIRS[\s\S]*platform_client[\s\S]*runtime_config[\s\S]*wifi_manager/,
  );
  assert.match(cmake, /if\(NOT EXISTS[\s\S]*wifi_manager\/CMakeLists\.txt/);
});

test("shared platform_client serves both the S3 starter and the P4 product", () => {
  const header = readFileSync(
    join(SHARED, "platform_client", "include", "platform_client.h"),
    "utf8",
  );
  assert.match(header, /platform_client_set_online_handler/);
  assert.match(header, /platform_client_tirtc_endpoint/);
  assert.match(header, /PLATFORM_SERVICE_DEVICE = 0/);
  assert.match(header, /PLATFORM_SERVICE_VOIP/);
  assert.match(header, /PLATFORM_SERVICE_CALL/);

  const p4Runtime = readFileSync(
    join(P4, "components", "starter_runtime", "src", "starter_runtime.c"),
    "utf8",
  );
  assert.match(p4Runtime, /platform_client_set_online_handler/);
});

test("shared wifi_manager freezes the on-flash credential format", () => {
  const source = readFileSync(
    join(SHARED, "wifi_manager", "src", "wifi_manager.c"),
    "utf8",
  );
  for (const fragment of [
    '"wifi_cfg"',
    '"ssid"',
    '"password"',
    '"credentials"',
    '"XiaoTai-%02X%02X"',
    "ap.ap.authmode = WIFI_AUTH_OPEN",
    '"http://192.168.6.1"',
  ]) {
    assert.ok(source.includes(fragment), `wifi_manager.c must contain ${fragment}`);
  }
  const history = readFileSync(
    join(SHARED, "wifi_manager", "src", "wifi_history.c"),
    "utf8",
  );
  assert.match(history, /WIFI_HISTORY_NAMESPACE "wifi_cfg"/);
  assert.match(history, /WIFI_HISTORY_KEY "known"/);
});

test("P4 tirtc_sdk wrapper pins the kit vendor baseline", () => {
  const cmake = readFileSync(
    join(P4, "components", "tirtc_sdk", "CMakeLists.txt"),
    "utf8",
  );
  assert.match(
    cmake,
    /9b4e35c7a2cb203fc463417739199429057c8b036936faa11f844c726455301f/,
  );
  assert.match(cmake, /third_party\/tirtc/);
  assert.match(cmake, /espressif-esp32p4\/2\.5\.0/);
  assert.match(cmake, /ESP-IDF 5\.5\.4/);
});
