# ESP32-P4 参考固件（小钛 P4 1.4.0）

本目录 `device-sim-p4/` 是 `tirtc-esp32p4-kit` 随包分发的 ESP32-P4 参考固件，
与 S3 的 `device-sim-esp32/` 对等。它是生成器 `create_esp32_project.py
--target esp32p4` 的复制源（P4 生成 = 复制本工程 + 物化共享组件 + 拷贝 SDK）。

## 出处

- 源工程：`xiaotai-esp32/waveshare-esp32p4-xiaotai`（产品 1.4.0）
- 源提交：`f33b7d2dea298f3f7f3f76051298dd34c937e7c2`
- 导入方式：源仓库 `git ls-files` 的完整跟踪文件集（确定性地排除
  `build/`、`sdkconfig`、`managed_components/` 等未跟踪产物）
- 许可证：工程自身 MIT（`LICENSE`）；vendored Espressif 组件（esp_hosted、
  esp_lvgl_port、esp_codec_dev、esp_h264、esp_video、esp_lcd）为 Apache-2.0
  且随树保留 LICENSE/NOTICE；第三方资产见 `THIRD_PARTY.md`

## 相对产品应用的改动清单（有意为之，移植时按此差异对齐）

1. **共享组件单一源**：`components/{platform_client,runtime_config,wifi_manager}/`
   删除，改由根 `CMakeLists.txt` 中带存在守卫的 `EXTRA_COMPONENT_DIRS` 指向
   `../device-sim-esp32/components/`。三个组件与 S3 参考共用一份源码
   （wifi_manager 使用直接 nvs 而非 nvs_store 异步 worker；NVS 命名空间与
   键完全一致，已存凭证可无缝迁移）。
2. **TiRTC SDK 走 kit 树**：`components/tirtc_sdk/` 不再捆绑 `lib/`、
   `manifest/`、批补丁与审计文件；库/头/契约统一来自
   `../sdk/espressif-esp32p4/2.5.0/`，钉扎 sha256 更新为供应商基线
   `9b4e35c7a2cb203fc463417739199429057c8b036936faa11f844c726455301f`
   （产品实机验证过的 feedback-stack 批 `7cf1569e…` 不含在 kit 中；
   如需切换，仅需更新本工程 `components/tirtc_sdk/CMakeLists.txt` 的钉扎）。
3. **`CONFIG_LWIP_MAX_SOCKETS` 16 → 10**：与权威 SDK 构建契约一致
   （doctor 对 esp32p4 校验该键）。
4. 其余源码、UI、板级组件、工具与文档按源工程原样保留。

## 构建要点

- ESP-IDF **恰好 5.5.4**（组件门禁强制）+ riscv32-esp-elf 工具链
  （`install.sh esp32p4`）
- 首次构建需联网解析 `dependencies.lock` 中的组件注册表依赖
- 共享组件与 SDK 的解析顺序见根 `CMakeLists.txt` 与
  `components/tirtc_sdk/README.md`；生成工程在 `third_party/tirtc` 下物化 SDK
