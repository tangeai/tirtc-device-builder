# TiRTC ESP32 Builder 使用说明

安装后可在 Codex 中显式调用：

```text
$tirtc-esp32-builder

在“厂商 + 完整开发板型号 + PCB 版本”上实现：
- H5 实时视频和声音
- H5 按住说话
- AI 双向对讲

资料：
- 产品页或资料链接：...
- 原理图：/absolute/path/board-schematic.pdf
- BSP 或示例工程：/absolute/path/vendor-bsp
- ThingConnect：/absolute/path/tirtc-server-example/thing-connect
- 输出目录：/absolute/path/my-tirtc-device

先完成能力分析；具备条件后生成并编译。只有我明确指定串口时才烧录。
```

## ThingConnect 工作区

这个 Skill 不复制 ThingConnect 源码和 TiRTC 静态库。首次使用可以准备公开仓库：

```bash
git clone https://github.com/tangeai/tirtc-server-example.git \
  /absolute/path/tirtc-server-example

export TIRTC_THING_CONNECT_ROOT=\
/absolute/path/tirtc-server-example/thing-connect
```

也可以在调用 Skill 时直接给出 ThingConnect 绝对路径，不需要设置持久环境变量。

## 常见输入方式

只有板卡型号：

```text
$tirtc-esp32-builder 分析 <厂商> <型号> <硬件版本>，目标是 H5 实时视频、talkback 和 AI 对讲。先输出缺失资料与能力结论。
```

提供本地资料：

```text
$tirtc-esp32-builder 使用原理图 /path/board.pdf、BSP /path/vendor-project 和 ThingConnect /path/tirtc-server-example/thing-connect，为该板生成 TiRTC H5/AI ESP-IDF 工程并编译。
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
  --thing-connect-root /absolute/path/tirtc-server-example/thing-connect \
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
python3 <skill-dir>/scripts/hardware_ir.py assess --strict /tmp/hardware-ir.json
```

`BLOCKED` 表示资料已确认硬件不满足；`NEEDS_CONFIRMATION` 表示仍有未知项或只有单一来源；`READY_TO_PORT` 表示可以生成并实现板级适配；`HIL_VERIFIED` 表示端到端实机验收通过。

## 当前边界

ThingConnect 仓库提供 ESP32-S3 H5/AI 模板和生成器，但默认媒体适配器不包含特定开发板的摄像头、麦克风、H.264 编码和扬声器驱动。模板生成和编译成功只证明工程与协议骨架可用，不代表 Web 已经出图或 AI 音频已经通过实机验收。
