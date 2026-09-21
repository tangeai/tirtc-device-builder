## 本仓库内的 SDK 出处

本组件的静态库与配套头文件来自 tirtc-device-builder 的版本化 kit SDK 树：

```text
device-sim/sdk/espressif-esp32p4/2.5.0/{include,lib,manifest}
```

- 库：`lib/libTiRTC.a`，sha256 `9b4e35c7a2cb203fc463417739199429057c8b036936faa11f844c726455301f`（TiRTC 2.5.0 P4 vendor 基线，与 ESP32-S3 包不可互换）。
- 构建契约：`manifest/build-contract.env`（IDF 5.5.4、1000 Hz ticks、trace/stats 关闭、`CONFIG_LWIP_MAX_SOCKETS=10`、`StaticSemaphore_t=84`）。
- CMake 解析顺序：`TIRTC_SDK_DIR`（CMake 变量或环境变量）→ `third_party/tirtc`（生成工程）→ `../../../sdk/espressif-esp32p4/2.5.0`（kit 树）。

本工程不再随附批补丁、VERSION.md 或 SHA256SUMS；一切以 kit SDK 树为准。

---

# TiRTC ESP32 SDK 接入配置说明

TiRTC ESP32 SDK 是预编译静态库。接入工程的 ESP-IDF / FreeRTOS 关键配置需要和 SDK 包保持一致，否则可能出现连接异常、线程异常或运行时崩溃。

## 默认配置

| 配置项 | 默认值 |
|---|---:|
| 目标芯片 | ESP32-S3 / ESP32-P4 对应包 |
| ESP-IDF | 5.5.x |
| P2P | KCP / noSCTP |
| `CONFIG_FREERTOS_HZ` | `1000` |
| `CONFIG_FREERTOS_USE_TRACE_FACILITY` | `n` |
| `CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS` | `n` |
| `CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS` | `n` |
| `StaticSemaphore_t` | `84 bytes` |

SDK 包内会附带实际编译配置：

```text
manifest/build-contract.env
```

接入时请以该文件为准。

## 为什么需要对齐

`CONFIG_FREERTOS_HZ` 会影响 SDK 内部超时、等待和调度节奏。
`CONFIG_FREERTOS_USE_TRACE_FACILITY` 会影响 FreeRTOS 静态对象布局，例如 `StaticSemaphore_t` 尺寸。

当前默认包按 trace 关闭编译，`StaticSemaphore_t = 84 bytes`。如果接入工程打开 trace，尺寸可能变为 `92 bytes`，会导致预编译 SDK 和运行工程的对象布局不一致，存在内存覆盖和线程异常风险。

## 推荐配置

在工程 `sdkconfig` 中保持：

```text
CONFIG_FREERTOS_HZ=1000
# CONFIG_FREERTOS_USE_TRACE_FACILITY is not set
# CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS is not set
# CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS is not set
```

配置完成后建议重新生成并编译：

```bash
idf.py fullclean
idf.py reconfigure
idf.py build
```

## 如何检查

Linux / WSL：

```bash
grep -E "CONFIG_FREERTOS_HZ|CONFIG_FREERTOS_USE_TRACE_FACILITY|CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS|CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS" sdkconfig build/config/sdkconfig.h
```

Windows PowerShell：

```powershell
Select-String -Path .\sdkconfig,.\build\config\sdkconfig.h -Pattern "CONFIG_FREERTOS_HZ|CONFIG_FREERTOS_USE_TRACE_FACILITY|CONFIG_FREERTOS_USE_STATS_FORMATTING_FUNCTIONS|CONFIG_FREERTOS_GENERATE_RUN_TIME_STATS"
```

## 使用不同配置时

如果工程必须使用不同的 tick、trace 或 stats 配置，请提供：

- 目标芯片型号
- ESP-IDF 版本
- 工具链版本
- `sdkconfig`
- `build/config/sdkconfig.h`

我们会基于该配置重新生成匹配的 SDK 包。

## 注意事项

- ESP32-S3 和 ESP32-P4 的 `libTiRTC.a` 不能混用。
- `libwebrtc_nosctp.a` 已按目标芯片打入 `libTiRTC.a`，无需额外链接。
- 如果修改了 FreeRTOS 关键配置，应重新获取匹配 SDK 包，不建议直接复用旧静态库。
