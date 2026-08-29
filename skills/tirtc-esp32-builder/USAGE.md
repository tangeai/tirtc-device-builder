# TiRTC ESP32 Builder 使用说明

## 一键准备

```bash
npx tirtc-device-builder@latest setup esp32
npx tirtc-device-builder@latest setup esp32 --install
```

第一条命令只检查；第二条命令自动安装用户目录内缺失的 Skill、带校验的 ESP32 Device Kit、ESP-IDF 5.5.4 和 ESP32-S3 工具链，最后复跑 Doctor。它不执行 `sudo`，也不修改 shell 配置。安装完成后新开 Codex 会话即可调用 Skill。

安装后可在 Codex 中显式调用：

```text
$tirtc-esp32-builder

开发板：<厂商、完整型号、PCB 版本>
资料与实物对应：<是/否/未知>

资料：
- <原理图、BSP/厂商示例、数据手册和产品页；一行一个>

目标：<H5 实时音视频、H5 对讲、AI 双向语音等>
视频：<MJPEG/H264/H265/根据证据选择>
Wi-Fi 与设备绑定：<指定方案/根据 BSP 和平台合同选择>
工程：<输出目录或现有工程的绝对路径>

先运行 Doctor，再生成 Hardware IR v2。READY_TO_PORT 只表示资料足以设计板级适配；随后完成适配和编译，以精确 artifact SHA-256 运行 build 阶段评估并输出 TIRTC_PORTING_REPORT.md。
本轮不访问串口、不烧录、不擦除 NVS，也不把凭证写入源码或报告。
```

可直接复制的版本见[开发板接入提示词](assets/developer-intake-prompt.md)。SoftAP 只是可选方案；没有 AP 配网时，Skill 会根据 BSP 和产品要求评估其他可重配路径。生产 SSID 和密码不能进入源码或报告。

## ESP32 Device Kit

一键安装会下载固定版本的最小资源包并校验 SHA-256，不需要克隆 ThingConnect 服务端仓库。安装路径由下面的文件记录：

```bash
source ~/.tirtc-device-builder/env.sh
printf '%s\n' "$TIRTC_THING_CONNECT_ROOT"
```

已有完整 ThingConnect 工作区仍可通过 `--thing-connect-root` 显式复用，主要用于维护模板或协议时的开发场景。

## 常见输入方式

只有板卡型号：

```text
$tirtc-esp32-builder 分析 <厂商> <型号> <硬件版本>，目标是 H5 实时视频、talkback 和 AI 对讲。先输出缺失资料与能力结论。
```

提供本地资料：

```text
$tirtc-esp32-builder 使用原理图 /path/board.pdf、BSP /path/vendor-project 和一键安装的 Device Kit，为该板生成 TiRTC H5/AI ESP-IDF 工程并编译。
```

完整实机流程：

```text
$tirtc-esp32-builder 使用 /path/hardware-ir.json 生成工程，编译后烧录到 /dev/ttyACM0，验证绑定、H5 和 AI，并生成 TIRTC_PORTING_REPORT.md。
```

## ESP-IDF 环境检查

将 `<skill-dir>` 替换为安装后的 Skill 路径，例如 `~/.codex/skills/tirtc-esp32-builder`。

生成工程前检查工作区和开发环境：

```bash
python3 <skill-dir>/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root ~/.tirtc-device-builder/kits/esp32s3/1.1.1 \
  --require-workspace
```

工程生成后检查其内置 SDK 和配置契约：

```bash
python3 <skill-dir>/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project /absolute/path/my-tirtc-device
```

如果 `idf.py` 缺失，Skill 默认只报告安装计划。只有明确授权安装版本、目录和环境修改后，才按照 Espressif 官方步骤安装并重新运行检查。

## Hardware IR 工具

```bash
python3 <skill-dir>/scripts/hardware_ir.py init /tmp/hardware-ir.json
python3 <skill-dir>/scripts/hardware_ir.py validate /tmp/hardware-ir.json
python3 <skill-dir>/scripts/hardware_ir.py assess --phase intake --strict /tmp/hardware-ir.json
python3 <skill-dir>/scripts/hardware_ir.py assess --phase build \
  --artifact-sha256 <64-character-sha256> --strict /tmp/hardware-ir.json
python3 <skill-dir>/scripts/hardware_ir.py assess --phase hil \
  --artifact-sha256 <64-character-sha256> --strict /tmp/hardware-ir.json
```

`init` 默认创建 schema v2；v1 仅用于兼容已有 H.264 IR。`BLOCKED` 表示资料已确认硬件/合同/资源或凭证策略不满足；`NEEDS_CONFIRMATION` 表示当前阶段仍有未知项或证据不足；`READY_TO_PORT` 表示可以生成并实现板级适配；`BUILD_VERIFIED` 表示精确 artifact 已通过源码、编译和 post-link 门禁；`HIL_VERIFIED` 还要求同一 SHA-256 的 L5/L6 运行证据。

## 当前边界

ThingConnect 仓库提供 ESP32-S3 H5/AI 模板和生成器，但默认媒体适配器不包含特定开发板的摄像头、麦克风、选定视频路径、Wi-Fi 凭证方法和扬声器驱动。模板生成和编译成功只证明工程与协议骨架可用，不代表 Web 已经出图或 AI 音频已经通过实机验收。
