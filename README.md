# TiRTC Device Builder

TiRTC Device Builder 帮助设备开发者把一块 ESP32-S3 开发板接入 TiRTC。你可以只给出开发板型号，也可以提供原理图、BSP、引脚表和外设示例。安装后的 Codex Skill 会检查开发环境，整理硬件事实，生成独立的 ESP-IDF 工程，完成板级移植和编译，并在获得明确授权后烧录、验证 H5 实时查看、H5 对讲和 AI 对讲。

当前仓库提供一个 Skill：

| Skill | 平台 | 主要用途 |
|---|---|---|
| `tirtc-esp32-builder` | ESP32-S3、ESP-IDF 5.5.x | 环境检查、Hardware IR、工程生成、板级媒体移植、编译、烧录和分层验收 |

普通使用者不需要克隆 `tirtc-server-example`，也不需要登录 npm。生成工程需要的模板、协议文档和 TiRTC SDK 已放进独立的 ESP32 Device Kit，由安装命令自动下载并校验。

- npm 包：[tirtc-device-builder](https://www.npmjs.com/package/tirtc-device-builder)
- GitHub 仓库：[tangeai/tirtc-device-builder](https://github.com/tangeai/tirtc-device-builder)
- ESP32 Device Kit：[kit-esp32s3-v1.0.0](https://github.com/tangeai/tirtc-device-builder/releases/tag/kit-esp32s3-v1.0.0)

文档导航：

- [新用户 5 分钟开始](#先看结果新用户这样开始)
- [准备板卡资料](#准备板卡资料)
- [依赖和支持范围](#依赖和支持范围)
- [安装方式和默认目录](#安装方式和目录)
- [检查、生成和编译](#常用检查和开发命令)
- [烧录和实机验收](#烧录和验收)
- [常见问题](#常见问题)

## 先看结果：新用户这样开始

### 1. 确认 Node.js

安装命令依赖 Node.js 18 或更高版本：

```bash
node --version
npm --version
```

`node --version` 应输出 `v18.x` 或更高版本。如果终端提示找不到 `node` 或 `npm`，先从 [Node.js 官方下载页](https://nodejs.org/en/download) 安装受支持版本，再打开一个新终端。

### 2. 一条命令准备开发环境

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

这条命令会：

- 把 `tirtc-esp32-builder` 安装到 Codex Skill 目录；
- 下载 ESP32 Device Kit 并校验 SHA-256；
- 复用当前可用的 ESP-IDF 5.5.x，找不到时安装 ESP-IDF 5.5.4；
- 安装 Espressif 管理的 ESP32-S3 工具链；
- 写入只包含本地路径的 `config.json` 和 `env.sh`；
- 激活托管环境并运行 Doctor。

安装器只写当前用户有权限的目录，不执行 `sudo`，也不修改 `.bashrc`、`.zshrc` 等 shell 配置。缺少系统软件时，它会停下来并给出处理方法；补齐后重复同一条命令即可继续。

安装成功时，输出末尾应包含：

```text
OVERALL: PASS
SETUP: READY
Start a new Codex session and invoke $tirtc-esp32-builder.
```

如果看到 `OVERALL: NEEDS_SETUP`、`MISS` 或 `FAIL`，先看[常见问题](#常见问题)。

### 3. 重新打开 Codex

Skill 在 Codex 会话启动时被发现。安装完成后，关闭当前 Codex 会话，再打开一个新会话。

### 4. 把板卡和目标告诉 Codex

有完整板卡资料时，复制下面的提示词并替换尖括号内容。路径使用绝对路径；未知项写“未知”，不要让 Skill 猜。完整版本见 [通用开发者接入提示词](skills/tirtc-esp32-builder/assets/developer-intake-prompt.md)。

```text
请使用 $tirtc-esp32-builder 完成这块开发板的 TiRTC 移植。

板卡：
- 厂商：<厂商>
- 完整型号：<型号>
- 模组：<例如 ESP32-S3-WROOM-1-N16R8>
- PCB 丝印/硬件版本：<版本>
- Flash/PSRAM：<容量和总线模式>

资料：
- 资料目录：/absolute/path/board-materials
- 原理图或网表：/absolute/path/board-materials/schematic/<file>
- BSP 或厂商示例：/absolute/path/vendor-bsp
- 摄像头、Codec、功放数据手册：/absolute/path/board-materials/datasheets
- BSP 版本：<commit/tag/release>

目标：
- H5 实时视频和声音
- H5 下行语音对讲
- AI 双向语音对讲

媒体合同：
- H5 支持的视频格式：<MJPEG/H264/H265及合同链接>
- 本设备选择：<选择一种>
- 视频提交单位/stream：<完整JPEG或Annex-B access unit/stream ID>
- 音频格式和stream：<codec、采样率、位宽、声道、ID>

配网与绑定：
- 板卡/BSP支持：<SoftAP/BLE/SmartConfig/工厂NVS/其他/未知>
- 本工程选择：<方法或根据证据选择>
- 凭证注入/保存：<NVS/安全工厂工具/不跟踪的开发配置>
- 设备绑定支持/选择：<验证码/工厂预绑定/开发凭证/custom>
- 重配、已有绑定处理与绑定清除方式：<方式或未知>

输出：
- 新工程：/absolute/path/my-esp32-device
- 报告：/absolute/path/my-esp32-device/TIRTC_PORTING_REPORT.md

先运行环境检查，再分析全部资料并生成 Hardware IR v2。
达到 READY_TO_PORT 后生成工程、完成板级适配并编译。
Skill 保持开发板无关；具体器件、GPIO、时钟、槽位和配网方法只进入该板的 IR/adapter。
本轮不烧录；不要把 Wi-Fi 密码、设备密钥或用户音视频写入源码、IR和报告。
```

手头只有型号也可以开始：

```text
$tirtc-esp32-builder

分析 <厂商> <完整型号> <PCB 版本>，目标是 H5 实时音视频、
H5 对讲和 AI 双向对讲。
先给出板卡资料清单、Hardware IR、能力结论和最小缺失项；
本轮不生成工程、不烧录。
```

只有型号时，Skill 可以调查和列出缺失资料，但不会猜测 GPIO、器件或媒体能力。要进入可靠的代码移植，通常还需要准确的板卡版本、原理图和可工作的 BSP 或外设示例。

## 这个 Skill 能做什么

它处理的是一条完整的设备开发路径：

```text
开发板型号、原理图、BSP、数据手册
                  │
                  ▼
      Hardware IR：硬件事实、来源和未知项
                  │
                  ▼
       能力门禁：能否支持 H5 / AI
                  │
                  ▼
      独立 ESP-IDF 工程与板级媒体适配
                  │
                  ▼
       编译 → 授权烧录 → 分层实机验收
                  │
                  ▼
            TIRTC_PORTING_REPORT.md
```

具体包括：

- 检查 Node.js 之外的 ESP-IDF、编译器、TiRTC SDK、工程配置和串口；
- 从原理图、BSP、数据手册和实测示例中提取有来源的硬件事实；
- 生成并校验 `hardware-ir.json`，把冲突和未知项留在报告里；
- 判断视频、上行音频、下行播放和 AI 会话是否具备移植条件；
- 生成带 TiRTC SDK 的独立 ESP-IDF 工程；
- 把摄像头、所选 MJPEG/H.264/H.265 路径、麦克风、Codec、I2S、功放和按键接到板级 adapter；
- 运行测试和 `idf.py build`，记录固件路径、版本和 SHA-256；
- 在用户明确给出芯片、工程和串口后烧录；
- 分别验证启动、上线、本地媒体、H5、AI 和稳定性；
- 输出 `TIRTC_PORTING_REPORT.md`，每一层都标成 `PASS`、`FAIL` 或 `SKIP`。

### 它不会替你猜硬件

模板工程包含配网、绑定、MQTT、TiRTC、H5 和 AI 会话骨架，不包含所有开发板的产品驱动。开发板仍需具备并正确接入：

- 摄像头和所选 MJPEG/H.264/H.265 完整媒体路径；
- 麦克风采集路径；
- Codec、I2S、功放和扬声器播放路径；
- 板级电源、时钟、复位和使能控制；
- 需要用于 AI 会话的实体按键或其他触发方式。

工程编译成功只说明构建层通过。没有浏览器画面、实体扬声器声音和双向 AI 音频的实测证据，就不能写成“Web 已出图”或“AI 对讲已完成”。

## 准备板卡资料

资料是否准确，直接决定移植能走多远。建议为每块板、每个 PCB 版本单独建目录，不要把相似型号的文档混在一起。

一个便于检查的目录可以这样组织：

```text
board-materials/
├── BOARD.md
├── schematic/
│   └── board-rev-a.pdf
├── bom/
│   └── board-rev-a.xlsx
├── bsp/
│   └── README.md
├── datasheets/
│   ├── camera-sensor.pdf
│   ├── audio-codec.pdf
│   └── amplifier.pdf
└── examples/
    ├── camera/
    ├── audio-record/
    └── audio-playback/
```

`BOARD.md` 至少记录：

```markdown
# 板卡身份

- 厂商：
- 完整销售型号：
- 模组型号：
- PCB 丝印：
- 硬件版本：
- Flash / PSRAM：

# 资料来源

- 产品页：
- 原理图名称和版本：
- BSP 仓库、commit 或 tag：
- 已在实物上验证的示例：

# 开发目标

- H5 实时视频：
- H5 实时音频：
- H5 下行对讲：
- AI 双向对讲：

# 媒体与接入合同

- H5 支持/选定的视频 profile：
- 音频格式与 stream ID：
- 板卡/BSP 支持的 Wi-Fi 凭证方法：
- 本工程选择的凭证方法和重配入口：
- ThingConnect 绑定、已绑定跳过和清除方式：
```

不同能力需要的证据不一样：

| 资料 | 用来确认什么 | 重要程度 |
|---|---|---|
| 板卡身份 | 厂商、完整型号、模组、PCB 丝印和硬件版本 | 必需 |
| 原理图或网表 | GPIO、电源、复位、时钟、I2C、I2S、SPI、摄像头和音频链路 | 必需 |
| BSP 或厂商示例 | 实际初始化顺序、驱动版本、ESP-IDF 版本和可工作的管脚定义 | 必需 |
| 摄像头和编码资料 | Sensor、输入接口、所选 MJPEG/H.264/H.265 输出边界与刷新/关键帧控制 | H5 视频必需 |
| 音频资料 | 麦克风类型、Codec/ADC/DAC、采样率、位宽、声道、MCLK/BCLK/LRCK、功放使能 | 对讲必需 |
| 配网/绑定资料 | 可用 Wi-Fi 凭证方法、凭证存储/重配、可用绑定方法、已有绑定状态和清除入口 | 上线必需 |
| 数据手册 | 器件寄存器、时序、电气限制和版本差异 | 推荐 |
| 实测小工程 | 证明摄像头、录音、播放或编码确实在该 PCB 版本工作 | 强烈推荐 |

给 BSP 时，请同时提供可复现的 commit、tag 或压缩包版本，以及它使用的 ESP-IDF 版本。只给一个会持续变化的仓库首页，后续很难解释代码为什么和实物不一致。

不要放进资料包的内容包括 Wi-Fi 密码、设备密钥、MQTT/WHIP token、证书、生产配置和真实用户音视频。

## 依赖和支持范围

### 当前版本基线

| 项目 | 当前要求 |
|---|---|
| 芯片 | ESP32-S3 |
| 参考模组 | ESP32-S3-WROOM-1-N16R8，或资源和配置经过确认的兼容板 |
| ESP-IDF | 5.5.x |
| 自动安装版本 | ESP-IDF v5.5.4 |
| TiRTC SDK | `espressif-esp32s3/2.3.0` |
| ESP32 Device Kit | 1.0.0 |
| Node.js | 18 或更高版本 |
| 支持自动安装的系统 | Linux、WSL、macOS |
| 原生 Windows | 使用 Espressif 官方安装器准备 ESP-IDF，再重新运行检查 |

当前生成器只支持 ESP32-S3。Flash 或 PSRAM 不是 16 MB / 8 MB 时，需要重新评估 `sdkconfig.defaults`、分区表、DMA 和媒体缓存预算。Skill 不会因为芯片名称接近，就把其他目标当成 ESP32-S3 处理。

### 本机软件

`setup esp32 --install` 会检查以下基础命令：

| 命令 | 用途 |
|---|---|
| `python3` | ESP-IDF、工程生成器和检查脚本 |
| `git` | 获取固定版本的 ESP-IDF |
| `bash` | 激活和安装 ESP-IDF |
| `tar` | 解包并验证 Device Kit |

Doctor 还会检查 `cmake`、`ninja`、`idf.py` 和 `xtensa-esp32s3-elf-gcc`。安装器不会调用系统包管理器；缺少基础命令时，需要开发者按当前操作系统安装。

Ubuntu、Debian 或 WSL 可以参考：

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv bash tar
```

### 网络和业务环境

首次安装通常需要访问：

- npm 官方 Registry，用于取得 `tirtc-device-builder`；
- GitHub Release，用于下载 ESP32 Device Kit；
- Espressif 的 GitHub 仓库和工具下载地址，用于安装 ESP-IDF 与工具链。

完成 H5 和 AI 端到端验收时，还需要可访问的 ThingConnect 服务、可用账号、设备绑定条件、浏览器和外网。缺少其中一项时，工程仍可生成和编译，但对应验收层必须记录为 `SKIP`。

### 媒体约束

H5 视频必须先从当前前端/服务合同选择一种 profile。MJPEG 需要完整 JPEG 帧；H.264/H.265 需要合同规定的 Annex-B access unit、参数集和刷新/关键帧控制。板上只有摄像头 Sensor，不代表浏览器一定能出图。

当前音频基线使用 G.711 A-law、8 kHz、单声道。对讲还要有可靠的下行队列、A-law 解码、Codec/I2S/功放播放和会话停止清理。没有可用的全双工和 AEC 证据时，应按半双工设计 AI 对讲。

## 安装方式和目录

### 推荐：用 npx 一次检查并安装

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

`npx` 会临时取得最新 CLI 并运行，不要求全局安装。它适合这种低频的安装和诊断工具，也避免用户机器里长期保留旧版本命令。

### 也可以全局安装

```bash
npm install --global tirtc-device-builder@latest
tirtc-device-builder setup esp32 --install
```

正确的 npm 命令是 `npm install`，没有 `npm --install` 这种写法。

仅执行 `npm install --global tirtc-device-builder` 只会安装 CLI。随后仍需显式运行 `setup esp32 --install`，因为后者会写 Codex Skill 目录、下载 Device Kit，并可能安装 ESP-IDF。npm 包没有 `preinstall`、`install` 或 `postinstall` 生命周期脚本，不会在用户没有看到目标路径时悄悄改动开发环境。

普通用户不用执行 `npm login`。`npm login` 只和包维护者发布新版本有关。

### 只安装 Skill

如果 ESP-IDF 和 Device Kit 已经由团队统一准备，可以只复制 Codex Skill：

```bash
npx --yes tirtc-device-builder@latest install esp32
```

这条命令不安装 ESP-IDF，也不下载 Device Kit。完整的新用户环境仍建议使用 `setup esp32 --install`。

### 默认目录

| 内容 | 默认位置 |
|---|---|
| Codex Skill | `${CODEX_HOME:-~/.codex}/skills/tirtc-esp32-builder` |
| 托管根目录 | `~/.tirtc-device-builder` |
| Device Kit | `~/.tirtc-device-builder/kits/esp32s3/1.0.0` |
| ESP-IDF | `~/.tirtc-device-builder/esp-idf-v5.5.4` |
| Espressif 工具 | `~/.tirtc-device-builder/espressif` |
| 安装记录 | `~/.tirtc-device-builder/config.json` |
| 环境入口 | `~/.tirtc-device-builder/env.sh` |

每个新终端可以这样激活托管环境：

```bash
source ~/.tirtc-device-builder/env.sh
idf.py --version
printf '%s\n' "$TIRTC_THING_CONNECT_ROOT"
```

`env.sh` 只设置 ESP-IDF、工具链和 Device Kit 路径，不包含设备凭证。

### 自定义目录或复用已有环境

把所有托管文件放到指定目录：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --root /absolute/path/tirtc-dev
```

自定义根目录后，环境入口也随之变为 `/absolute/path/tirtc-dev/env.sh`。

复用已有 ESP-IDF 5.5.x：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --idf-dir /absolute/path/esp-idf
```

复用已经解包的 Device Kit，或维护者本地的完整 ThingConnect 工作区：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --thing-connect-root /absolute/path/to/device-kit-or-thing-connect
```

从本地 Device Kit 压缩包安装，适合内网或离线转交：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --kit-archive /absolute/path/tirtc-esp32s3-kit-1.0.0.tar.gz
```

安装器仍会核对固定的 SHA-256、目录结构、清单和每个资源文件，不接受未经验证的同名压缩包。

### 更新已安装的 Skill

普通安装会保护已经存在的 Skill，避免覆盖本地修改。确认不需要保留本地改动后，可用最新 npm 包替换：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install --force-skill
```

这只替换 Skill；已验证的同版本 Device Kit 和 ESP-IDF 会被复用。替换前如有自己的脚本或规则，请先备份。

## 常用检查和开发命令

### 查看当前状态

```bash
npx --yes tirtc-device-builder@latest setup esp32
```

`setup esp32` 的检查逻辑不会安装开发组件、修改 shell 配置、生成工程或烧录。第一次运行 `npx` 时，npm 可能会把 CLI 下载到自己的缓存。

环境完整时，它会运行 Doctor 并输出 `SETUP: READY`。环境不完整时，它输出 `OVERALL: NEEDS_SETUP` 和下一条建议命令。

查看 CLI 和当前平台：

```bash
npx --yes tirtc-device-builder@latest --help
npx --yes tirtc-device-builder@latest list
npx --yes tirtc-device-builder@latest setup esp32 --help
```

### 生成工程前运行 Doctor

```bash
source ~/.tirtc-device-builder/env.sh

npx --yes tirtc-device-builder@latest doctor esp32 \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root "$TIRTC_THING_CONNECT_ROOT" \
  --require-workspace
```

生成前应看到：

| 检查项 | 合格结果 |
|---|---|
| Python、Git | `PASS` |
| `idf.py` | `PASS`，版本为 5.5.x |
| target compiler | `PASS`，找到 ESP32-S3 编译器 |
| ESP32 Device Kit | `PASS` |
| TiRTC SDK | `PASS` |
| serial discovery | 未接板时允许 `WARN` |
| OVERALL | `PASS` |

已经安装 Skill 时，也能直接调用同一份脚本：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root "$TIRTC_THING_CONNECT_ROOT" \
  --require-workspace
```

### 检查 Hardware IR

一般由 Codex 运行下面的工具，开发者可以手工复核：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py init \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py validate \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess --strict \
  /absolute/path/hardware-ir.json
```

能力门禁有四种状态：

| 状态 | 含义 | 怎么处理 |
|---|---|---|
| `NEEDS_CONFIRMATION` | 关键事实未知、冲突或只有单一来源 | 补原理图、BSP、数据手册或实测证据 |
| `BLOCKED` | 现有硬件或 SDK 已确认不满足 | 更换硬件，补编码/播放路径，或取得匹配 SDK |
| `READY_TO_PORT` | 资料足以开始生成和板级实现 | 进入工程生成与编译 |
| `HIL_VERIFIED` | 已完成端到端实机验证 | 固定版本并保存证据 |

`assess --strict` 在条件不足时返回非零，这是门禁在阻止过早生成，不代表脚本损坏。

Hardware IR v2 只有在运行证据绑定到同一固件 SHA-256 时才会给出 `HIL_VERIFIED`：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess \
  /absolute/path/hardware-ir.json \
  --artifact-sha256 <64-character-sha256> --strict
```

### 生成和编译

推荐直接让 Skill 生成、实现并编译。需要人工复现时，先激活环境，并确保输出目录还不存在：

```bash
source ~/.tirtc-device-builder/env.sh

python3 "$TIRTC_THING_CONNECT_ROOT/device-sim/scripts/create_esp32_project.py" \
  /absolute/path/my-esp32-device \
  --name my_esp32_device
```

`--name` 只能包含小写字母、数字和下划线。生成器不会覆盖已有目录。

工程生成后再做项目级检查：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project /absolute/path/my-esp32-device
```

`TiRTC build contract` 为 `PASS` 后编译：

```bash
cd /absolute/path/my-esp32-device
idf.py set-target esp32s3
idf.py build
```

生成器会把 TiRTC SDK 复制到工程的 `third_party/tirtc/`，生成后的工程可以脱离 `tirtc-server-example` 使用。换一台机器编译时，仍需准备兼容的 ESP-IDF 5.5.x 工具链。

检查尚未完成的产品适配点：

```bash
rg -n 'TODO\(product-' main components
```

常见适配内容包括麦克风采集、G.711 A-law 编码、所选视频 profile 输出与刷新请求、下行音频播放、实体按键和会话停止后的资源清理。

## 烧录和验收

### 烧录前确认串口

Linux 常见串口是 `/dev/ttyACM0` 或 `/dev/ttyUSB0`：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

把实际端口交给 Doctor：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project /absolute/path/my-esp32-device \
  --serial-port /dev/ttyACM0
```

`serial port` 为 `PASS` 后，再单独向 Skill 授权：

```text
$tirtc-esp32-builder

我确认目标芯片是 ESP32-S3，工程是 /absolute/path/my-esp32-device，
串口是 /dev/ttyACM0。授权本轮烧录该设备并打开串口监视。
不要擦除其他串口设备，不要在日志中输出 Wi-Fi 密码或设备密钥。
烧录后执行 L2 Boot 检查并更新 TIRTC_PORTING_REPORT.md。
```

也可以人工烧录：

```bash
cd /absolute/path/my-esp32-device
idf.py -p /dev/ttyACM0 flash monitor
```

使用 `Ctrl+]` 退出 ESP-IDF Monitor。多个串口同时存在时，需要通过 USB 拔插、设备标识或芯片探测确认目标，不能默认烧录第一个端口。

### Wi-Fi 凭证和设备绑定

Skill 不假设每块板都支持 SoftAP，也不要求开发者把 SSID/密码写死。Hardware IR 应从 BSP 和产品要求中选择一条可用路径：SoftAP、BLE、SmartConfig、安全工厂/NVS 注入、不纳入版本控制的开发配置，或有文档的自定义方案。

选中的方法必须满足：凭证不进入 Git/源码/报告；存在清除或重配入口；该 PCB/BSP 有证据支持。没有 SoftAP 但支持工厂 NVS 的设备仍可接入。把明文密码提交到工程会被 v2 门禁判为 `BLOCKED`。

Wi-Fi 和 ThingConnect 绑定是两个独立状态机。绑定可选择验证码、工厂预绑定、开发凭证或平台合同允许的 custom 流程，应分别验证：

1. 无 Wi-Fi 凭证时进入所选配网/注入流程。
2. 已联网但无设备绑定时，进入所选绑定流程；选择验证码时才显示验证码。
3. NVS 已有绑定时，明确记录复用/跳过初始绑定，而不是误判为绑定流程缺失。
4. 分别验证只清设备绑定和只清 Wi-Fi 凭证的入口。
5. `status` 确认 platform、MQTT、TiRTC 和 runtime 状态。

具体命令和 UI 由生成工程及所选方法定义，不能从另一块板复制。生产凭证、设备 secret 和 token 不能写进源码、脚本、Hardware IR、报告或 Git。

### 验证 H5 实时查看和对讲

1. 串口 `status` 显示 runtime 为 `waiting`。
2. 在体验平台打开该设备的实时查看入口。
3. 确认所选 MJPEG/H.264/H.265 视频持续显示，音频和视频发送计数持续增长。
4. 发起 H5 对讲，确认 stream 14 下行计数增长，实体扬声器可以听到声音。
5. 触发浏览器重连或刷新请求，确认 MJPEG 提交下一张完整 JPEG，或 H.264/H.265 产生合同要求的刷新/关键帧，画面能够恢复。

视频、声音和重连分别保留证据。浏览器偶尔显示一帧，不等于持续实时查看已经通过。

### 验证 AI 对讲

1. 先确认 H5 或其他会话没有占用媒体资源。
2. 串口输入 `ai-start`，观察状态从 `ai-connecting` 进入 `ai-active`。
3. 确认 `start_session` 成功后，设备才开始发送麦克风音频。
4. 确认上行语音被 AI 接收，下行 AI 音频能从实体扬声器播放。
5. 输入 `ai-stop`，确认发送 `end_session`，媒体任务停止，状态回到 `waiting`。
6. 再次打开 H5，确认实时音视频可以重新连接。

如果产品使用实体按键启动 AI，会话状态和验收条件相同，只是触发方式从串口命令换成板级按键。

### 分层验收

每一层都需要独立证据。缺少硬件、账号、浏览器、服务或网络时，写 `SKIP` 并说明补测条件。

| 层级 | 通过条件 |
|---|---|
| L-1 Environment | Doctor 必需项和项目构建契约通过 |
| L0 Generate | 新工程和 Hardware IR 存在，没有覆盖旧目录 |
| L1 Build | `idf.py build` 成功，固件和 SHA-256 已记录 |
| L2 Boot | 指定串口烧录成功，无 panic 或反复重启 |
| L3 Online | 所选 Wi-Fi 凭证和设备绑定流程、MQTT 与 TiRTC 就绪 |
| L4 Media | 摄像头、麦克风、扬声器的本地路径和计数正常 |
| L5 H5 | 浏览器持续收到声明的音视频，下行对讲到达实体扬声器 |
| L6 AI | token、WHIP、`start_session`、双向音频、停止和 H5 恢复正常 |
| L7 Stability | 按需求完成反复会话、弱网、资源和长稳测试 |

一份完整交付通常包含：

- 生成工程的绝对路径；
- `hardware-ir.json` 和关键事实来源；
- 能力评估与剩余阻塞项；
- 固件文件、构建命令、版本和 SHA-256；
- 明确到芯片和串口的烧录记录；
- 脱敏后的构建、启动和验收日志；
- `TIRTC_PORTING_REPORT.md`；
- L-1 到 L7 的 `PASS`、`FAIL` 或 `SKIP`。

任务只做到生成和编译时，报告应明确停在 L1。

## 常见问题

### 找不到 `node`、`npm` 或 `npx`

安装 Node.js 18 或更高版本，重新打开终端，再检查：

```bash
node --version
npm --version
npx --version
```

### npm 使用了镜像源，提示 404 或找不到包

查看当前 Registry：

```bash
npm config get registry
```

如果不是 `https://registry.npmjs.org/`，切回官方源后重试：

```bash
npm config set registry https://registry.npmjs.org/
npm view tirtc-device-builder version
```

### `npm login` 提示无法打开浏览器

普通使用者不需要登录 npm。直接执行：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

`npm login` 只供维护者发布包，与安装公开包无关。

### 输出 `OVERALL: NEEDS_SETUP`

这是只读检查在提示环境不完整。按输出给出的下一条命令安装：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

### 提示缺少 `python3`、`git`、`bash` 或 `tar`

安装器不会运行 `sudo`。用当前系统的包管理器补齐这些命令，再重复 `setup esp32 --install`。安装过程可以续跑，已完成的项目会被复用。

### `idf.py not found`

当前终端没有激活 ESP-IDF。使用一键环境时执行：

```bash
source ~/.tirtc-device-builder/env.sh
idf.py --version
```

使用已有 ESP-IDF 时执行它自己的 `export.sh`：

```bash
source /absolute/path/esp-idf/export.sh
```

### ESP-IDF 版本不是 5.5.x

不要用错误版本继续编译预编译 SDK。让安装器使用新的托管目录，或明确传入正确版本：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --idf-dir /absolute/path/esp-idf-v5.5.4
```

如果指定目录已存在但内容不完整或版本错误，安装器会拒绝覆盖。换一个空的新路径，或先人工备份原目录。

### 安装完成后 Codex 找不到 Skill

关闭当前 Codex 会话并重新打开。再检查默认文件是否存在：

```bash
ls -l ~/.codex/skills/tirtc-esp32-builder/SKILL.md
```

设置过 `CODEX_HOME` 或 `--skills-dir` 时，要检查对应目录。不要同时把 Skill 安装到多个位置。

### 已有 Skill，安装器拒绝覆盖

这是对本地修改的保护。确认可以替换后执行：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install --force-skill
```

如果只使用 `install esp32` 子命令，对应选项是 `--force`。

### Device Kit 下载失败

确认能访问 npm 和 GitHub Release。受限网络中，可以在另一台机器下载公开 Release 附件，再传到开发机：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --kit-archive /absolute/path/tirtc-esp32s3-kit-1.0.0.tar.gz
```

安装器会做 SHA-256 和内部文件清单校验。出现校验不一致时不要绕过，应重新取得官方 Release 附件。

### 提示 `refusing to overwrite incomplete directory`

目标路径已经存在，但不是完整的 Device Kit 或 ESP-IDF。安装器不会删除或覆盖它。先检查并备份该目录，再改用新的 `--root` 或 `--idf-dir` 路径。

### Doctor 报 `no sdkconfig or sdkconfig.defaults`

典型输出是：

```text
FAIL TiRTC build contract [required]: no sdkconfig or sdkconfig.defaults in ...
```

`--project` 指向的目录还不是已生成的 ESP-IDF 工程，或者路径写错了。生成前不要传 `--project`；生成后确认工程中存在 `sdkconfig.defaults`，再运行项目级 Doctor。

### `WARN serial discovery: no serial device detected`

没有连接开发板时，这是正常警告，不影响生成和编译。烧录前必须让串口检查变成 `PASS`。

设备已连接但没有权限时，按操作系统规范把当前用户加入串口用户组并重新登录。Ubuntu 常见用户组是 `dialout`。不要长期把串口权限放宽给所有用户。

WSL 默认不一定能看到 USB 设备。按 [Microsoft WSL USB 连接说明](https://learn.microsoft.com/windows/wsl/connect-usb) 将设备附加到当前 WSL 实例，再运行 Doctor。

### Hardware IR 一直是 `NEEDS_CONFIRMATION`

查看每个未知项的来源要求。最常缺的是准确 PCB 版本、摄像头数据格式、所选视频 profile 的完整输出路径、Codec 时钟、功放使能脚、配网方法和可工作的厂商示例。补资料比从相似开发板复制管脚更可靠。

### 工程能编译，浏览器没有画面

重点检查摄像头输出是否真正进入所选视频路径。MJPEG 必须逐次提交完整 JPEG；H.264/H.265 必须符合合同规定的 Annex-B、参数集和刷新帧行为。还要确认持续发送计数、丢弃和队列水位。Sensor 的 JPEG、RGB 或裸 YUV 能力本身不等于完整 H5 路径。

### 工程能编译，但 H5 或 AI 没有声音

分别检查上行和下行，不要把它们当成同一条链路：

- 上行：麦克风、采样率、声道、G.711 A-law 编码、发送时机；
- 下行：stream 14、队列边界、A-law 解码、I2S/Codec、功放使能、扬声器；
- AI：`start_session` 成功后才发送音频，停止时清理旧 generation 数据；
- 全双工：没有 AEC 和硬件证据时先验证半双工。

### 原生 Windows 无法自动安装 ESP-IDF

自动安装当前支持 Linux、WSL 和 macOS。原生 Windows 请使用 Espressif 官方安装器准备 ESP-IDF 5.5.x 和 ESP32-S3 工具链，再运行：

```powershell
npx --yes tirtc-device-builder@latest setup esp32
```

也可以在 WSL 中完成整个流程，但烧录前要先把 USB 设备连接到 WSL。

## 常见疑问

### 必须克隆 `tirtc-server-example` 吗？

不需要。普通开发所需的生成器、模板、协议文档、TiRTC 头文件和 `libTiRTC.a` 都在版本化的 ESP32 Device Kit 中。一键安装会下载公开 Release，并把路径写进 `env.sh`。

`--thing-connect-root` 主要用于维护模板、协议或 Device Kit 的开发者复用完整源码工作区。

### 为什么推荐 `npx`，不是安装一个 npm 包就结束？

`npx` 适合运行一次性的安装器和诊断命令，每次都能明确选择 `@latest`。全局 `npm install` 同样可用，但它只负责安装 CLI。

Skill、Device Kit 和 ESP-IDF 会写到 npm 包目录之外，还可能占用较多磁盘和下载时间，所以必须由 `setup esp32 --install` 这一条显式命令完成。这样用户能先看到安装计划、目标目录和失败原因，卸载或升级 CLI 也不会意外删除开发环境。

### 只给开发板型号能不能自动完成全部代码？

可以先开始分析，不能保证直接完成硬件移植。型号足以定位候选资料，但 GPIO、器件版本、所选视频 profile、音频时钟和配网能力必须有可信来源。资料不足时，Skill 会给出最小补充清单，不会用相似板型填空。

### 能接入已有 ESP-IDF 工程吗？

可以。把现有工程路径、目标芯片、ESP-IDF 版本、BSP 和已验证外设示例交给 Skill。它会先检查组件、配置、SDK 构建契约和媒体 seam，再决定复用哪些板级代码。

### 生成的工程可以移走吗？

可以。TiRTC SDK 会复制到工程的 `third_party/tirtc/`。移动后仍需在新机器上激活兼容的 ESP-IDF 5.5.x，并重新运行项目级 Doctor 和构建。

### 能支持 ESP32 之外的芯片吗？

仓库结构允许每个平台拥有独立 Skill，但当前公开版本只实现 ESP32-S3。泰芯或其他平台应作为新的 `skills/<platform-skill>/` 加入，分别维护 SDK、工具链、板级 adapter 和验收约束。

## 给仓库维护者

普通开发者不需要执行本节命令。

### 本地验证

```bash
npm ci --ignore-scripts
npm test
npm pack --dry-run
```

`npm pack --dry-run` 用于核对公开 tarball。包内不应出现 Device Kit 二进制、设备凭证、板卡私有资料、构建产物或用户媒体。

本机安装了 Codex 系统校验器时，还可以运行：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  skills/tirtc-esp32-builder

python3 ~/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

### 打包 ESP32 Device Kit

```bash
npm run pack:esp32-kit -- \
  --source /absolute/path/tirtc-server-example/thing-connect \
  --kit-version 1.0.0
```

输出位于 `dist/`：

```text
tirtc-esp32s3-kit-1.0.0.tar.gz
tirtc-esp32s3-kit-1.0.0.tar.gz.sha256
```

校验后使用独立的 `kit-esp32s3-v<version>` 标签发布 GitHub Release：

```bash
gh --version
gh release --help

cd dist
sha256sum -c tirtc-esp32s3-kit-1.0.0.tar.gz.sha256
cd ..

git tag -a kit-esp32s3-v1.0.0 -m "TiRTC ESP32-S3 Device Kit 1.0.0"
git push origin kit-esp32s3-v1.0.0

gh release create kit-esp32s3-v1.0.0 \
  dist/tirtc-esp32s3-kit-1.0.0.tar.gz \
  dist/tirtc-esp32s3-kit-1.0.0.tar.gz.sha256 \
  --repo tangeai/tirtc-device-builder \
  --verify-tag \
  --latest=false \
  --title "TiRTC ESP32-S3 Device Kit 1.0.0" \
  --notes "ESP-IDF 5.5.x；TiRTC SDK 2.3.0；包含 H5/AI 工程生成资源。"
```

`gh release --help` 如果提示 `No such command 'release'`，当前系统安装的不是 GitHub 官方 CLI。先按 [GitHub CLI 官方安装说明](https://github.com/cli/cli/blob/trunk/docs/install_linux.md) 安装或替换，再登录并发布 Release。

### 发布 npm

`package.json` 版本与 Git 标签必须一致。推送 `v<package-version>` 标签后，`.github/workflows/publish.yml` 通过 npm Trusted Publishing 发布：

```bash
npm test
git tag -a v0.3.0 -m "v0.3.0"
git push origin v0.3.0
```

不要重复发布已经存在的 npm 版本。版本变化同步更新 `package.json`、`.codex-plugin/plugin.json` 和发布说明。

### 增加新平台

每个平台放在独立的 `skills/<platform-skill>/` 目录，并明确：

- 芯片、SDK、工具链和不适用范围；
- Hardware IR 需要的事实和来源；
- 板级媒体 adapter 与公共会话逻辑的边界；
- 编译、启动、上线、媒体、业务和稳定性验收；
- 下载、工具链安装、串口烧录和凭证写入的授权边界。

只有两个以上平台出现相同不变量时再抽取共享逻辑，避免形成只转发参数的公共层。

## 安全与许可证

不要在 Issue、日志或报告中提交设备密钥、Wi-Fi 密码、MQTT/WHIP token、证书、生产配置或用户音视频。安全问题按 [SECURITY.md](SECURITY.md) 私下报告。

本仓库源码使用 [MIT License](LICENSE)。ThingConnect、TiRTC SDK、ESP-IDF、厂商 BSP、芯片资料和其他第三方内容使用各自的许可证，本仓库许可证不会替代它们。版本差异见 [CHANGELOG.md](CHANGELOG.md)。
