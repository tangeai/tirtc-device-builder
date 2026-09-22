export const ESP32_KIT = Object.freeze({
  target: "esp32s3",
  platform: "espressif-esp32s3",
  archiveName: "tirtc-esp32s3-kit-1.1.7.tar.gz",
  archiveRoot: "tirtc-esp32s3-kit-1.1.7",
  releaseTag: "kit-esp32s3-v1.1.7",
  sha256: "61be93e5b3648c067a581195d2146ac57f748c2f356e9b681a0926f301cf6a8b",
  sdkVersion: "2.5.0",
  sourceCommit: "50be0b4b6ad83ca376e010ebb7256db4fb6debcd",
  url: "https://github.com/tangeai/tirtc-device-builder/releases/download/kit-esp32s3-v1.1.7/tirtc-esp32s3-kit-1.1.7.tar.gz",
  version: "1.1.7",
  released: true,
});

/*
 * The ESP32-P4 Device Kit is pinned by its first release. Until the release
 * workflow publishes and pins it, sha256/sourceCommit/url stay null and the
 * publish-p4 job fails any premature kit-esp32p4-v* tag. Nothing is fabricated.
 */
export const ESP32_P4_KIT = Object.freeze({
  target: "esp32p4",
  platform: "espressif-esp32p4",
  archiveName: "tirtc-esp32p4-kit-1.0.0.tar.gz",
  archiveRoot: "tirtc-esp32p4-kit-1.0.0",
  releaseTag: "kit-esp32p4-v1.0.0",
  sha256: null,
  sdkVersion: "2.5.0",
  sourceCommit: null,
  url: null,
  version: "1.0.0",
  released: false,
});

export const ESP32_KITS = Object.freeze({
  esp32s3: ESP32_KIT,
  esp32p4: ESP32_P4_KIT,
});
