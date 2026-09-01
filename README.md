# TiRTC Device Builder

TiRTC Device Builder 用于把 ESP32-S3/ESP32-P4 开发板接入 TiRTC。输入可以只有开发板型号，也可以包含原理图、BSP、引脚表和外设示例。安装后的 Agent Skill 会先检查环境、整理有依据的硬件事实，再生成或移植独立的 ESP-IDF 工程并完成板级适配和编译。烧录和实机验证只有在开发者明确给出目标串口并授权后才会执行。

当前仓库提供一个 Skill：

| Skill | 平台 | 主要用途 |
|---|---|---|
| `tirtc-esp32-builder` | ESP32-S3 / ESP32-P4、ESP-IDF 5.5.x | 板型识别、Hardware IR、工程生成/移植、H5/AI/设备互呼/微信 VoIP、AEC 门禁、编译烧录和分层验收 |

H5/AI 的 ESP32-S3 托管模板、协议文档和 TiRTC SDK 已打包在独立的 ESP32 Device Kit 中，安装时会自动下载并校验。设备互呼或微信 VoIP 的模拟/移植若超出当前 Kit 内容，则需要在用户授权后使用固定 commit 的 `tirtc-server-example` 完整仓库。ESP32-P4 必须使用匹配的 P4 SDK、BSP 与网络方案，不能复用 S3 预编译库。

- npm 包：[tirtc-device-builder](https://www.npmjs.com/package/tirtc-device-builder)
- GitHub 仓库：[tangeai/tirtc-device-builder](https://github.com/tangeai/tirtc-device-builder)
- ESP32 Device Kit：[kit-esp32s3-v1.1.1](https://github.com/tangeai/tirtc-device-builder/releases/tag/kit-esp32s3-v1.1.1)

文档导航：

- [新用户快速开始](#新用户快速开始)
- [准备板卡资料](#准备板卡资料)
- [依赖和支持范围](#依赖和支持范围)
- [安装方式和默认目录](#安装方式和目录)
- [检查、生成和编译](#常用检查和开发命令)
- [烧录和实机验收](#烧录和验收)
- [常见问题](#常见问题)

## 新用户快速开始

### 1. 确认 Node.js

安装命令依赖 Node.js 18 或更高版本：

```bash
node --version
npm --version
```

`node --version` 应输出 `v18.x` 或更高版本。如果终端提示找不到 `node` 或 `npm`，先从 [Node.js 官方下载页](https://nodejs.org/en/download) 安装受支持版本，再打开一个新终端。

### 2. 安装并检查开发环境

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

默认安装到 Codex。使用其他客户端时增加 `--client`，例如：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install --client qwen-code
```

这条命令会：

- 把 `tirtc-esp32-builder` 安装到所选 Agent 客户端的 Skill 目录；
- 下载 ESP32 Device Kit 并校验 SHA-256；
- 复用当前可用的 ESP-IDF 5.5.x，找不到时安装 ESP-IDF 5.5.4；
- 安装 Espressif 管理的 ESP32-S3 工具链；
- 写入只包含本地路径的 `config.json` 和 `env.sh`；
- 激活托管环境并运行 Doctor。

安装器只写入当前用户有权限的目录，不执行 `sudo`，也不修改 `.bashrc`、`.zshrc` 等 shell 配置。如果缺少系统软件，它会停下来说明缺少什么；补齐后重新执行同一条命令即可继续。

安装成功时，输出末尾应包含：

```text
OVERALL: PASS
SETUP: READY
Start a new Codex session, then ask it to use tirtc-esp32-builder.
```

如果看到 `OVERALL: NEEDS_SETUP`、`MISS` 或 `FAIL`，先看[常见问题](#常见问题)。

### 3. 重新打开 Agent 客户端

Skill 通常在 Agent 会话启动时被发现。安装完成后，关闭当前会话，再打开一个新会话。

### 4. 把板卡和目标告诉 Agent

把你已经掌握的信息填进下面的提示词即可，不用先查齐所有硬件参数。先指定工作区根目录，本地路径尽量相对工作区填写；不确定的内容写“未知”。可直接复制的版本见[开发板接入提示词](skills/tirtc-esp32-builder/assets/developer-intake-prompt.md)。

```text
请使用 tirtc-esp32-builder Skill 完成这块开发板的 TiRTC 移植。

开发板：
- 厂商、完整型号、PCB/硬件版本：<填写>
- 资料与手中实物是否对应：<是/否/未知>

工作区：<本机目录；以下本地路径均相对此目录>

资料：
- <原理图、BSP/厂商示例、数据手册或产品页；一行一个>

目标：
- 功能：<例如 H5 实时音视频/对讲、AI 对讲、设备呼设备、微信 VoIP>
- 平台/Web 视频：MJPEG、H264、H265
- 板级视频选择：<MJPEG/H264/H265/根据硬件证据选择一种>
- Wi-Fi：<指定方案/根据 BSP 选择>
- 设备绑定：<指定方案/根据平台合同选择>
- AEC：AI 对讲、设备呼设备、微信 VoIP 必须全双工并启用 AEC

工程：<输出目录或现有工程的工作区相对路径>

请先运行 Doctor，分析全部资料并生成 Hardware IR v2。把未知项区分为可由资料、实现、构建或 HIL 解决，以及必须由用户补充的阻塞项。READY_TO_PORT 表示资料足以开始设计，不要求最终 ELF；随后生成、适配和编译，运行项目内 runtime、音频和视频语义门禁，把项目内 artifacts/ 的真实大小与 SHA-256 写入 build_evidence 后执行 build 阶段评估，并输出 TIRTC_PORTING_REPORT.md。
本轮不访问串口、不烧录、不擦除 NVS；缺少串口只让 L2-L7 记为 SKIP，不得阻止 L0/L1。不要把任何凭证写入源码或报告。
```

手头只有型号也可以开始：

```text
$tirtc-esp32-builder

分析 <厂商> <完整型号> <PCB 版本>，目标是 H5 实时音视频、
H5 对讲和 AI 双向对讲。
先给出板卡资料清单、Hardware IR、能力结论和最小缺失项；
本轮不生成工程、不烧录。
```

只有型号时，Skill 会先调查公开资料并列出缺口，不会猜测 GPIO、器件或媒体能力。要进入代码移植，通常还需要准确的板卡版本、原理图，以及能在实物上运行的 BSP 或外设示例。

### 示例对话

新板卡、先做资料评审：

```text
用户：$tirtc-esp32-builder
      这是 XX 厂商 ESP32-S3 Camera Board Rev.B，资料在 boards/xx-revb/。
      目标是 H5 音视频、AI 对讲、设备互呼和微信 VoIP；后三项必须 AEC。
      先识别板型、生成 Hardware IR 并告诉我还缺什么，不烧录。

Codex：我会先运行 Doctor，读取原理图/BSP/数据手册，生成 board identity，
       查询已验证板型注册表；无法从 SoC 判断的 PCB 引脚仍保持未知。
       随后分别评估四类业务能力，并对 AI/CALL/VOIP 强制检查全双工、
       回采参考和 AEC，不满足时返回 BLOCKED，不自动降级半双工。
```

同板型复用并完成真机验证：

```text
用户：$tirtc-esp32-builder
      使用 boards/identity.json 匹配已验证板型，工程输出到 ports/xx-revb。
      允许构建和烧录 /dev/ttyACM0，验证 call 另一台设备和 wxcall。

Codex：只有 exact identity 且 safe_registered_reuse=true 才复用板级包。
       我会重新运行 runtime/audio/video 门禁、构建并绑定新 artifact SHA，
       然后在该串口验证 AI、设备互呼、微信 VoIP 的 AEC/double-talk、
       会话切换和重连；旧固件的 HIL 结果不会继承给新固件。
```

## 工作范围

整个流程从板卡资料核对开始，以分层验收报告结束：

```text
开发板型号、原理图、BSP、数据手册
                  │
                  ▼
      Hardware IR：硬件事实、来源和未知项
                  │
                  ▼
       能力门禁：H5 / AI / CALL / VOIP / AEC
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

Skill 负责：

- 检查 Node.js 之外的 ESP-IDF、编译器、TiRTC SDK、工程配置和串口；
- 从原理图、BSP、数据手册和实测示例中提取有来源的硬件事实；
- 生成并校验 `hardware-ir.json`，把冲突和未知项留在报告里；
- 判断视频、上行音频、下行播放、AI、设备互呼、微信 VoIP 与 AEC 是否具备移植条件；
- 生成带 TiRTC SDK 的独立 ESP-IDF 工程；
- 核验发现地址、SDK callback 生命周期、下行格式过滤和 AI 会话响应等运行协议不变量；
- 把摄像头、所选 MJPEG/H.264/H.265 路径、麦克风、Codec、I2S、功放和按键接到板级 adapter；
- 运行测试和 `idf.py build`，记录固件路径、版本和 SHA-256；
- 在用户明确给出芯片、工程和串口后烧录；
- 分别验证启动、上线、本地媒体、H5、AI、设备互呼、微信 VoIP、AEC/double-talk 和稳定性；
- 输出 `TIRTC_PORTING_REPORT.md`，每一层都标成 `PASS`、`FAIL` 或 `SKIP`。

### Skill 不猜硬件

模板工程提供配网、绑定、MQTT、TiRTC、H5 和 AI 会话骨架，但不会内置所有开发板的产品驱动。每块开发板仍要根据自身资料接入：

- 摄像头和所选 MJPEG/H.264/H.265 完整媒体路径；
- 麦克风采集路径；
- Codec、I2S、功放和扬声器播放路径；
- 板级电源、时钟、复位和使能控制；
- 需要用于 AI 会话的实体按键或其他触发方式。

编译成功只代表构建层通过。只有拿到浏览器画面、实体扬声器声音和双向 AI 音频的实测证据，报告才能把对应能力标为 `PASS`。

## 准备板卡资料

板卡资料要和手上的实物版本对应。建议为每块板、每个 PCB 版本单独建目录，避免混入相似型号的文档。

建议按下面的结构整理：

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

提供 BSP 时，请同时注明可复现的 commit、tag 或压缩包版本，以及它使用的 ESP-IDF 版本。只有一个持续变化的仓库首页，后续很难追溯代码与实物不一致的原因。

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
| ESP32 Device Kit | 1.1.1 |
| Node.js | 18 或更高版本 |
| 支持自动安装的系统 | Linux、WSL、macOS |
| 原生 Windows | 使用 Espressif 官方安装器准备 ESP-IDF，再重新运行检查 |

当前托管自动生成器只提供 ESP32-S3 模板。ESP32-P4 可由 Skill 在已有、证据完整的 P4 BSP/工程上移植，但必须使用 `espressif-esp32p4` SDK、匹配的构建合同和明确的 ESP-Hosted 或以太网方案。Flash 或 PSRAM 容量变化时，需要重新评估 `sdkconfig.defaults`、分区表、DMA 和媒体缓存预算。

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

H5 和 AI 的端到端验收还需要可访问的 ThingConnect 服务、可用账号、设备绑定条件、浏览器和外网。缺少其中一项，不影响工程生成和编译，但对应验收层要记录为 `SKIP`。

### 媒体约束

ThingConnect 平台和 Web 播放端支持 MJPEG、H.264、H.265；具体开发板必须根据其有证据的媒体路径只选择一种输出 profile。MJPEG 提交完整 JPEG 帧；H.264/H.265 按合同提交 Annex-B access unit、参数集，并实现刷新或关键帧控制。某块板只能输出 MJPEG 不代表平台只支持 MJPEG。板上有摄像头 Sensor，只能证明图像有来源，不能证明浏览器一定能持续出图。

当前音频基线使用 G.711 A-law、8 kHz、单声道。对讲还要有可靠的下行队列、A-law 解码、Codec/I2S/功放播放和会话停止清理。AI 对讲、设备互呼和微信 VoIP 强制要求全双工、真实播放参考和 AEC；没有证据时必须标记为 `BLOCKED`，不能自动降级为半双工。只有单独请求的 H5 talkback 可在产品合同明确允许时采用半双工。

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

安装命令是 `npm install`，不要写成 `npm --install`。

只执行 `npm install --global tirtc-device-builder` 会安装 CLI，不会准备完整开发环境。随后还要运行 `setup esp32 --install`，由它安装 Agent Skill、下载 Device Kit，并在需要时安装 ESP-IDF。npm 包没有 `preinstall`、`install` 或 `postinstall` 生命周期脚本，因此不会在安装 CLI 时改动这些目录。

安装公开包不需要执行 `npm login`；这个命令只和维护者发布新版本有关。

### 只安装 Skill

如果 ESP-IDF 和 Device Kit 已经由团队统一准备，可以只复制 Agent Skill：

```bash
npx --yes tirtc-device-builder@latest install esp32
npx --yes tirtc-device-builder@latest install esp32 --client gemini
```

这条命令不安装 ESP-IDF，也不下载 Device Kit。完整的新用户环境仍建议使用 `setup esp32 --install`。

### 支持的 Agent 客户端

同一个 `tirtc-esp32-builder` Skill 会完整复制到所选客户端的原生目录，不维护客户端专用的内容副本。先用下面的命令查看当前机器解析出的目录：

```bash
npx --yes tirtc-device-builder@latest clients
```

| `--client` | 客户端 | 默认 Skill 根目录 |
|---|---|---|
| `codex` | Codex（默认） | `${CODEX_HOME:-~/.codex}/skills` |
| `claude-code` | Claude Code | `~/.claude/skills` |
| `opencode` | OpenCode | `${XDG_CONFIG_HOME:-~/.config}/opencode/skills` |
| `gemini` | Gemini CLI | `~/.gemini/skills` |
| `copilot` | GitHub Copilot | `~/.copilot/skills` |
| `qwen-code` | Qwen Code | `~/.qwen/skills` |
| `windsurf` | Windsurf Cascade | `~/.codeium/windsurf/skills` |
| `cline` | Cline | `~/.cline/skills` |
| `kiro` | Kiro | `~/.kiro/skills` |

也可以使用 `claude`、`gemini-cli`、`github-copilot`、`qwen`、`cascade`、`kiro-cli` 等别名。`--skills-dir` 的优先级高于默认目录，适合项目级安装或客户端使用非默认配置目录的情况。

`--client` 只选择 Skill 的安装目录和提示文案，不绑定模型服务。DeepSeek、Qwen、GLM、Kimi、OpenAI 或 Claude 等模型仍在对应客户端中配置；只要客户端能发现 Skill 并允许文件、终端等所需工具，就继续使用同一份工作流。

Cline 当前还需要在 `Settings → Features → Enable Skills` 中启用实验性 Skills 功能；安装器不会修改客户端自身的权限或功能开关。

### 默认目录

| 内容 | 默认位置 |
|---|---|
| Agent Skill | 上表中所选目录下的 `tirtc-esp32-builder` |
| 托管根目录 | `~/.tirtc-device-builder` |
| Device Kit | `~/.tirtc-device-builder/kits/esp32s3/1.1.1` |
| ESP-IDF | `~/.tirtc-device-builder/esp-idf-v5.5.4` |
| Espressif 工具 | `~/.tirtc-device-builder/espressif` |
| 安装记录 | `~/.tirtc-device-builder/config.json` |
| 环境入口 | `~/.tirtc-device-builder/env.sh` |

新开终端后，用下面的命令激活托管环境：

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
  --kit-archive /absolute/path/tirtc-esp32s3-kit-1.1.1.tar.gz
```

安装器仍会核对固定的 SHA-256、目录结构、清单和每个资源文件，不接受未经验证的同名压缩包。

### 更新已安装的 Skill

默认安装不会覆盖已有 Skill，以免丢失本地修改。确认这些修改不需要保留后，可用最新 npm 包替换：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install --force-skill
```

该命令只替换 Skill；同版本且已通过校验的 Device Kit 和 ESP-IDF 会继续复用。自定义脚本或规则请提前备份。

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
npx --yes tirtc-device-builder@latest clients
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

下面的工具通常由 Codex 调用，开发者也可以手工复核：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py init \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py validate \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess \
  --phase intake --strict \
  /absolute/path/hardware-ir.json
```

能力门禁有五种状态：

| 状态 | 含义 | 怎么处理 |
|---|---|---|
| `NEEDS_CONFIRMATION` | 当前阶段的关键事实未知、冲突或证据等级不足 | 按资料、实现、构建、HIL 或用户输入来源继续闭环 |
| `BLOCKED` | 现有硬件或 SDK 已确认不满足 | 更换硬件，补编码/播放路径，或取得匹配 SDK |
| `READY_TO_PORT` | 资料足以开始生成和板级实现 | 进入工程生成与编译 |
| `BUILD_VERIFIED` | 精确 artifact 通过 runtime、音频、视频、源码、编译和 post-link 门禁 | 记录项目内 BIN/ELF 的真实大小与 SHA-256；按授权进入实机验收 |
| `HIL_VERIFIED` | 已完成端到端实机验证 | 固定版本并保存证据 |

`assess --strict` 在条件不足时返回非零，这是门禁在阻止过早生成，不代表脚本损坏。

构建后运行 build 阶段；只有运行证据绑定到同一固件 SHA-256 时，hil 阶段才会给出 `HIL_VERIFIED`：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess \
  /absolute/path/hardware-ir.json \
  --phase build --project /absolute/path/generated-project \
  --artifact-sha256 <64-character-sha256> --strict

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess \
  /absolute/path/hardware-ir.json \
  --phase hil \
  --artifact-sha256 <64-character-sha256> --strict
```

### 生成和编译

建议让 Skill 完成生成、适配和编译。需要人工复现时，先激活环境，并确认输出目录尚不存在：

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

`TiRTC build contract` 为 `PASS` 后，先执行 `idf.py reconfigure` 锁定依赖。根据 [音频合同](skills/tirtc-esp32-builder/references/audio-contract.md) 和 [视频合同](skills/tirtc-esp32-builder/references/video-contract.md) 生成、核验并安装请求能力对应的项目内门禁，再编译：

```bash
cd /absolute/path/my-esp32-device
idf.py set-target esp32s3
idf.py reconfigure
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/install_audio_gate.py .
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/install_video_gate.py .
idf.py build
```

只安装实际请求能力的门禁。编译后先核对固件内嵌版本、应用 BIN
SHA-256 和完整 ELF SHA-256：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/firmware_identity.py \
  build/<app>.bin --elf build/<app>.elf --expect-version <expected-version>
```

随后按
[`firmware-delivery.md`](skills/tirtc-esp32-builder/references/firmware-delivery.md)
选择快速真机迭代或可移植证据包；该文档也规定从 `build/` 记录迁移到
`artifacts/` 时如何保持 Hardware IR 和报告一致。编译成功但语义门禁缺失
或失败时只能记录 `COMPILE_PASS / CAPABILITY_BLOCKED`。

生成器会把 TiRTC SDK 复制到工程的 `third_party/tirtc/`。此后工程不再依赖 `tirtc-server-example`，但换机编译仍需准备兼容的 ESP-IDF 5.5.x 工具链。

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

普通开发烧录优先使用这一条命令，让 ESP-IDF 从当前构建目录解析
bootloader、分区表和应用镜像；无需手工维护多条 `esptool.py` 地址参数。
使用 `Ctrl+]` 退出 ESP-IDF Monitor。多个串口同时存在时，需要通过 USB
拔插、设备标识或芯片探测确认目标，不能默认烧录第一个端口。

### Wi-Fi 凭证和设备绑定

SoftAP 是可选方案，不是接入前提。Hardware IR 要根据 BSP 的实际能力和产品要求，选择 SoftAP、BLE、SmartConfig、安全工厂/NVS 注入、不纳入版本控制的开发配置，或有文档的自定义方案。SSID 和密码不应写死在源码中。

无论选择哪种方法，都要有当前 PCB/BSP 的支持证据，凭证不能进入 Git、源码或报告，并且要保留清除或重配入口。没有 SoftAP、但支持工厂 NVS 注入的设备同样可以接入。只要工程提交了明文密码，Hardware IR v2 门禁就会判为 `BLOCKED`。

Wi-Fi 配网和 ThingConnect 设备绑定是两套独立流程。绑定可以选择验证码、工厂预绑定、开发凭证，或平台合同允许的 custom 方案。验收时要分开检查：

1. 没有 Wi-Fi 凭证时，设备进入选定的配网或注入流程。
2. 已联网但尚未绑定时，设备进入选定的绑定流程；只有验证码方案需要显示验证码。
3. NVS 已保存绑定时，日志应明确说明复用已有绑定并跳过首次绑定，不能据此判断“绑定流程缺失”。
4. 分别验证只清设备绑定和只清 Wi-Fi 凭证的入口。
5. `status` 确认 platform、MQTT、TiRTC 和 runtime 状态。

具体命令和 UI 由生成工程及所选方案决定，不能直接照搬另一块板。生产凭证、设备 secret 和 token 不得写入源码、脚本、Hardware IR、报告或 Git。

### 验证 H5 实时查看和对讲

1. 串口 `status` 显示 runtime 为 `waiting`。
2. 在体验平台打开该设备的实时查看入口。
3. 确认所选 MJPEG/H.264/H.265 视频持续显示，音频和视频发送计数持续增长。
4. 发起 H5 对讲，确认 stream 14 下行计数增长，实体扬声器可以听到声音。
5. 触发浏览器重连或刷新请求，确认 MJPEG 提交下一张完整 JPEG，或 H.264/H.265 产生合同要求的刷新/关键帧，画面能够恢复。

视频、声音和重连要分别保留证据。浏览器偶尔出现一帧，不能算作持续实时查看通过。

### 验证 AI 对讲

1. 先确认 H5 或其他会话没有占用媒体资源。
2. 串口输入 `ai-start`，观察状态从 `ai-connecting` 进入 `ai-active`。
3. 确认 `start_session` 成功后，设备才开始发送麦克风音频。
4. 确认上行语音被 AI 接收，下行 AI 音频能从实体扬声器播放。
5. 输入 `ai-stop`，确认发送 `end_session`，媒体任务停止，状态回到 `waiting`。
6. 再次打开 H5，确认实时音视频可以重新连接。

如果产品使用实体按键启动 AI，会话状态和验收条件相同，只是触发方式从串口命令换成板级按键。

### 分层验收

每一层都要有独立证据。缺少硬件、账号、浏览器、服务或网络时，写 `SKIP`，并注明后续补测条件。

| 层级 | 通过条件 |
|---|---|
| L-1 Environment | Doctor 必需项和项目构建契约通过 |
| L0 Generate | 新工程和 Hardware IR 存在，没有覆盖旧目录 |
| L1 Build | 请求能力的语义门禁与 `idf.py build` 均成功，固件和已登记 SHA-256 通过 build assessment |
| L2 Boot | 指定串口烧录成功，无 panic 或反复重启 |
| L3 Online | 所选 Wi-Fi 凭证和设备绑定流程、MQTT 与 TiRTC 就绪 |
| L4 Media | 摄像头、麦克风、扬声器的本地路径和计数正常 |
| L5 H5 | 浏览器持续收到声明的音视频，下行对讲到达实体扬声器 |
| L6 AI/CALL/VOIP/AEC | AI、设备互呼、微信 VoIP 的双向音频、AEC/double-talk、停止/超时和 H5 恢复分别通过 |
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

换机前先创建排除 `build/`、`managed_components/` 和 `.git` 的源码交付副本，再运行 `project_portability.py <source-only-export> --export`。只交付源码、依赖锁和工程内 TiRTC SDK，不携带包含原机器绝对路径的构建缓存。

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

这表示只读检查发现环境尚未准备完整。按输出提示执行安装：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install
```

### 提示缺少 `python3`、`git`、`bash` 或 `tar`

安装器不会运行 `sudo`。请用当前系统的包管理器补齐这些命令，再执行 `setup esp32 --install`。安装可以续跑，已经完成的部分会被复用。

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

### 安装完成后 Agent 客户端找不到 Skill

关闭当前 Agent 会话并重新打开。先查看客户端目录，再检查对应文件是否存在：

```bash
npx --yes tirtc-device-builder@latest clients
ls -l <skills-dir>/tirtc-esp32-builder/SKILL.md
```

确认安装和启动的是同一个客户端，例如 Qwen Code 要使用 `--client qwen-code`。设置过 `CODEX_HOME`、`XDG_CONFIG_HOME` 或 `--skills-dir` 时，要检查对应目录。项目级目录由客户端自身规则决定，可以用 `--skills-dir` 显式指定。

### 已有 Skill，安装器拒绝覆盖

安装器检测到本地已有 Skill，因此没有直接覆盖。确认可以替换后执行：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install --force-skill
```

如果只使用 `install esp32` 子命令，对应选项是 `--force`。

### Device Kit 下载失败

确认能访问 npm 和 GitHub Release。受限网络中，可以在另一台机器下载公开 Release 附件，再传到开发机：

```bash
npx --yes tirtc-device-builder@latest setup esp32 --install \
  --kit-archive /absolute/path/tirtc-esp32s3-kit-1.1.1.tar.gz
```

安装器会校验 SHA-256 和内部文件清单。如果校验不一致，请重新获取官方 Release 附件，不要跳过校验。

### 提示 `refusing to overwrite incomplete directory`

目标路径已经存在，但不是完整的 Device Kit 或 ESP-IDF。安装器不会删除或覆盖该目录。请先检查并备份，再改用新的 `--root` 或 `--idf-dir` 路径。

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

先确认当前运行的是 intake、build 还是 hil 阶段，再标记每个未知项的下一证据来源。资料/固定源码可解决的事实继续检查；adapter 或 ELF 可解决的事实进入对应实现/构建层；运行指标留到 HIL。只有准确 PCB 版本、关键连接、器件身份、产品合同或不可用 SDK 等无法安全推导的事实需要用户补充。不要从相似开发板复制管脚来填补这些信息。

### 工程能编译，浏览器没有画面

先确认摄像头输出是否真正进入选定的视频路径。MJPEG 要逐次提交完整 JPEG；H.264/H.265 要符合合同规定的 Annex-B、参数集和刷新帧行为。同时检查持续发送计数、丢帧和队列水位。Sensor 能输出 JPEG、RGB 或裸 YUV，不等于 H5 视频链路已经打通。

### 工程能编译，但 H5 或 AI 没有声音

分别检查上行和下行，不要把它们当成同一条链路：

- 上行：麦克风、采样率、声道、G.711 A-law 编码、发送时机；
- 下行：stream 14、队列边界、A-law 解码、I2S/Codec、功放使能、扬声器；
- AI：`start_session` 成功后才发送音频，停止时清理旧 generation 数据；
- 全双工：AI、设备互呼和微信 VoIP 缺少回采参考或 AEC 证据时直接阻塞；仅 H5 talkback 可按明确的产品合同验证半双工。

### 原生 Windows 无法自动安装 ESP-IDF

自动安装当前支持 Linux、WSL 和 macOS。原生 Windows 请使用 Espressif 官方安装器准备 ESP-IDF 5.5.x 和 ESP32-S3 工具链，再运行：

```powershell
npx --yes tirtc-device-builder@latest setup esp32
```

也可以在 WSL 中完成整个流程，但烧录前要先把 USB 设备连接到 WSL。

## 使用边界

### 必须克隆 `tirtc-server-example` 吗？

不需要。普通开发所需的生成器、模板、协议文档、TiRTC 头文件和 `libTiRTC.a` 都在版本化的 ESP32 Device Kit 中。一键安装会下载公开 Release，并把路径写进 `env.sh`。

`--thing-connect-root` 主要用于维护模板、协议或 Device Kit 的开发者复用完整源码工作区。

### 为什么推荐 `npx`，不是安装一个 npm 包就结束？

`npx` 适合运行低频的安装和诊断命令，也可以明确选择 `@latest`。全局 `npm install` 同样可用，但只负责安装 CLI。

Skill、Device Kit 和 ESP-IDF 会写到 npm 包目录之外，也可能占用较多磁盘和下载时间，因此统一由显式命令 `setup esp32 --install` 安装。开发者可以提前看到安装计划和目标目录；以后卸载或升级 CLI，也不会误删开发环境。

### 只给开发板型号能不能自动完成全部代码？

可以先分析，但不能保证直接完成硬件移植。型号足以定位候选资料；GPIO、器件版本、所选视频 profile、音频时钟和配网能力仍需可信来源。资料不足时，Skill 会给出最小补充清单，不会拿相似板型的数据填空。

### 能接入已有 ESP-IDF 工程吗？

可以。把现有工程路径、目标芯片、ESP-IDF 版本、BSP 和已验证的外设示例交给 Skill。它会先检查组件、配置、SDK 构建合同和媒体接入边界，再决定复用哪些板级代码。

### 生成的工程可以移走吗？

可以。TiRTC SDK 会复制到工程的 `third_party/tirtc/`。移动后仍需在新机器上激活兼容的 ESP-IDF 5.5.x，并重新运行项目级 Doctor 和构建。

### 能支持 ESP32 之外的芯片吗？

仓库允许每个平台使用独立 Skill。当前公开 Skill 覆盖 ESP32-S3，并支持在证据完整的已有工程上移植 ESP32-P4；托管一键生成仍是 S3。泰芯或其他平台需要新增 `skills/<platform-skill>/`，并分别维护 SDK、工具链、板级 adapter 和验收约束。

## 给仓库维护者

以下命令只供仓库维护者使用。

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
  --kit-version 1.1.1
```

输出位于 `dist/`：

```text
tirtc-esp32s3-kit-1.1.1.tar.gz
tirtc-esp32s3-kit-1.1.1.tar.gz.sha256
```

校验后推送独立的 `kit-esp32s3-v<version>` 标签。`publish-kit.yml` 会从 metadata 固定的上游 commit 重建压缩包、核对 SHA-256，并使用 GitHub Actions token 创建 Release：

```bash
cd dist
sha256sum -c tirtc-esp32s3-kit-1.1.1.tar.gz.sha256
cd ..

git tag -a kit-esp32s3-v1.1.1 -m "TiRTC ESP32-S3 Device Kit 1.1.1"
git push origin kit-esp32s3-v1.1.1
```

metadata 中的版本、标签、上游 commit 和期望 SHA-256 必须与本地可复现打包结果一致；工作流不会从浮动的 `main` 取发布内容。

### 发布 npm

`package.json` 版本与 Git 标签必须一致。推送 `v<package-version>` 标签后，`.github/workflows/publish.yml` 通过 npm Trusted Publishing 发布：

```bash
npm test
git tag -a v0.9.0 -m "v0.9.0"
git push origin v0.9.0
```

不要重复发布已经存在的 npm 版本。版本变化同步更新 `package.json`、`.codex-plugin/plugin.json` 和发布说明。

### 增加新平台

每个平台放在独立的 `skills/<platform-skill>/` 目录，并写清楚：

- 芯片、SDK、工具链和不适用范围；
- Hardware IR 需要的事实和来源；
- 板级媒体 adapter 与公共会话逻辑的边界；
- 编译、启动、上线、媒体、业务和稳定性验收；
- 下载、工具链安装、串口烧录和凭证写入的授权边界。

等两个以上平台出现相同且稳定的约束后，再提取共享逻辑，避免公共层只做参数转发。

## 安全与许可证

不要在 Issue、日志或报告中提交设备密钥、Wi-Fi 密码、MQTT/WHIP token、证书、生产配置或用户音视频。安全问题按 [SECURITY.md](SECURITY.md) 私下报告。

本仓库源码使用 [MIT License](LICENSE)。ThingConnect、TiRTC SDK、ESP-IDF、厂商 BSP、芯片资料和其他第三方内容使用各自的许可证，本仓库许可证不会替代它们。版本差异见 [CHANGELOG.md](CHANGELOG.md)。
