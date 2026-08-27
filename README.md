# TiRTC Device Builder

TiRTC Device Builder 是一个面向设备开发者的 Codex Plugin 仓库。它把不同芯片平台的开发流程拆成独立 Skill，根据开发板型号、原理图、BSP、引脚表和外设示例生成、移植、编译和验证 TiRTC 设备工程。

仓库当前包含：

| Skill | 平台 | 能力 |
|---|---|---|
| `tirtc-esp32-builder` | ESP32-S3 / ESP-IDF 5.5.x | 环境诊断、Hardware IR、H5 实时查看/对讲、AI 对讲工程生成、编译、烧录和分层验收 |

后续平台以新的同级 Skill 加入，例如 `skills/tirtc-taixin-builder/`。每个平台独立维护 SDK、构建工具、板级适配和验收约束。

## 能力边界

ESP32 Skill 使用公开的 [ThingConnect 示例仓库](https://github.com/tangeai/tirtc-server-example)作为协议、模板、生成器和 TiRTC ESP32 SDK 的事实源。这个仓库不复制服务端源码、预编译 TiRTC SDK、设备凭证或媒体样本。

模板工程提供配网、绑定、MQTT、TiRTC、H5 和 AI 会话骨架。具体开发板仍需接入摄像头、H.264 编码器、麦克风、扬声器、Codec、I2S 和按键。工程编译成功不等于 Web 已经出图或 AI 对讲已通过实机验收。

## npm 安装（推荐）

查看当前支持的平台：

```bash
npx tirtc-device-builder@latest list
```

安装 ESP32 Skill：

```bash
npx tirtc-device-builder@latest install esp32
```

默认安装到 `${CODEX_HOME:-~/.codex}/skills/tirtc-esp32-builder`。安装器不会使用
`postinstall` 修改用户目录；只有显式执行 `install` 才会写入。目标已经存在时默认退出，
需要确认丢弃本地改动后才能使用：

```bash
npx tirtc-device-builder@latest install esp32 --force
```

自定义 Skill 根目录：

```bash
npx tirtc-device-builder@latest install esp32 \
  --skills-dir /absolute/path/to/skills
```

安装完成后启动新的 Codex 会话，Skill 调用名为：

```text
$tirtc-esp32-builder
```

也可以不安装，直接运行打包在 npm 中的 ESP-IDF 环境诊断：

```bash
npx tirtc-device-builder@latest doctor esp32 \
  --thing-connect-root /absolute/path/tirtc-server-example/thing-connect \
  --require-workspace
```

## 从 GitHub 安装

在 Codex 对话中使用内置安装器：

```text
$skill-installer

安装：
https://github.com/tangeai/tirtc-device-builder/tree/v0.2.0/skills/tirtc-esp32-builder
```

Linux/macOS 也可以使用安装器脚本：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo tangeai/tirtc-device-builder \
  --ref v0.2.0 \
  --path skills/tirtc-esp32-builder
```

仓库根目录同时包含 `.codex-plugin/plugin.json`，可以作为 skills-only Plugin 提交到 ChatGPT/Codex Plugin Directory。GitHub 直接安装不依赖 Plugin Directory 审核。

## 准备 ThingConnect

```bash
git clone https://github.com/tangeai/tirtc-server-example.git \
  /absolute/path/tirtc-server-example
```

调用 Skill 时提供：

```text
ThingConnect 根目录：/absolute/path/tirtc-server-example/thing-connect
```

也可以只为当前终端设置：

```bash
export TIRTC_THING_CONNECT_ROOT=\
/absolute/path/tirtc-server-example/thing-connect
```

## 最小使用示例

```text
$tirtc-esp32-builder

使用 ThingConnect /absolute/path/tirtc-server-example/thing-connect，
检查 ESP-IDF 环境，并为 ESP32-S3 N16R8 生成 TiRTC H5/AI 工程到
/absolute/path/my-esp32-device。先编译并生成 TIRTC_PORTING_REPORT.md，
本轮不烧录。
```

新板卡资料输入示例：

```text
$tirtc-esp32-builder

开发板：<厂商> <完整型号> <PCB 版本>
原理图：/absolute/path/board.pdf
BSP：/absolute/path/vendor-bsp
目标：H5 实时视频、H5 对讲、AI 双向对讲

先生成 Hardware IR 和能力结论。资料不足时列出最小缺失项，
能力达到 READY_TO_PORT 后再生成和编译工程。不要自动烧录。
```

## 手动运行环境诊断

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root /absolute/path/tirtc-server-example/thing-connect \
  --require-workspace
```

生成工程后：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project /absolute/path/my-esp32-device
```

`doctor.py` 检查 Python、Git、CMake、Ninja、`idf.py`、目标工具链、ThingConnect 工作区、TiRTC SDK 构建契约和串口权限。检查本身不安装软件、不修改 shell 配置，也不烧录设备。

npm CLI 的 `doctor esp32` 调用同一个脚本，参数和退出码保持一致。

## 开发与验证

```bash
npm ci --ignore-scripts
npm test
npm pack --dry-run
```

`npm pack --dry-run` 展示实际进入公开 tarball 的文件；发布前必须确认其中没有
SDK 二进制、凭证、板卡私有资料、构建产物或用户媒体。

本地安装了 Codex 系统校验器时，还可以运行：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/tirtc-esp32-builder

python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

## 增加新平台

每个平台使用 `skills/<platform-skill>/` 独立目录。新 Skill 需要：

- 明确芯片、SDK、工具链和不适用范围；
- 使用来源可追溯的硬件事实，不从相似型号静默推断；
- 把平台驱动隔离在板级 adapter，不复制 H5/AI 会话状态机；
- 区分编译、烧录启动、设备上线、媒体链路和端到端业务验收；
- 对下载、工具链安装、串口烧录和凭证写入保留明确授权边界。

共享逻辑只在两个以上平台出现相同不变量后抽取，避免形成只转发参数的公共层。

## 安全与许可证

不要在 Issue、日志或报告中提交设备密钥、Wi-Fi 密码、MQTT/WHIP token、证书或用户音视频。安全问题按 [SECURITY.md](SECURITY.md) 私下报告。

本仓库源码使用 MIT License，见 [LICENSE](LICENSE)。ThingConnect、TiRTC SDK、ESP-IDF、厂商 BSP、芯片资料和其他第三方内容使用各自的许可证；本仓库许可证不会替代它们。
