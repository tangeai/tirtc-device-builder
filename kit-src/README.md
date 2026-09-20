# ESP32 Kit 源码

本目录是 `tirtc-device-builder` 的 ESP32-S3 Device Kit 源码。生成器、模板、独立参考工程、共用组件和匹配的 TiRTC ESP32-S3 SDK 由本仓库维护；`scripts/pack-esp32-kit.js` 从这里生成发布包，不读取 `tirtc-server-example` 的 ESP32 路径。

初始设备源码取自 `tirtc-server-example` 提交 `6b8076c` 的父提交；协议文档快照取自提交 `6b8076c`。这些来源只用于追溯，不代表后续修改要写回服务端仓库。服务端协议变化时，应按固定提交更新这里的文档快照和对应测试。

默认使用 `device-sim/sdk/espressif-esp32s3/2.5.0` 中的 ESP32-S3 专用静态库、配套头文件和构建合同。不要将其他平台的同版本 SDK 库用于 ESP32 固件。
`2.3.0` 目录仅保留供旧版 Kit 与已有项目核对；生成器、参考工程和新 Kit 打包均选用 `2.5.0`。
