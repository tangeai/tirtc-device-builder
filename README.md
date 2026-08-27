# TiRTC Device Builder

TiRTC Device Builder 是一个面向设备开发者的 Codex Plugin 仓库。它把不同芯片平台的开发流程拆成独立 Skill，根据开发板型号、原理图、BSP、引脚表和外设示例生成、移植、编译和验证 TiRTC 设备工程。

仓库当前包含：

| Skill | 平台 | 能力 |
|---|---|---|
| `tirtc-esp32-builder` | ESP32-S3 / ESP-IDF 5.5.x | 环境诊断、Hardware IR、H5 实时查看/对讲、AI 对讲工程生成、编译、烧录和分层验收 |

后续平台以新的同级 Skill 加入，例如 `skills/tirtc-taixin-builder/`。每个平台独立维护 SDK、构建工具、板级适配和验收约束。

## 能力边界

ESP32 开发资源以独立、带版本和 SHA-256 的 Device Kit 发布。Kit 的事实源是公开的 [ThingConnect 示例仓库](https://github.com/tangeai/tirtc-server-example)，但普通开发者不需要克隆该服务端仓库。Device Kit 不包含设备凭证、板卡 BSP 或用户媒体。

## 维护者：发布最小 ESP32 资源包

最小资源包只包含工程生成器、`esp32-h5-ai` 模板、`platform_client`、`runtime_config`、`wifi_manager`、TiRTC ESP32-S3 SDK 2.3.0 和相关设备协议文档。打包命令会检查白名单资源、记录源码提交、生成确定性压缩包和 SHA-256：

```bash
cd /home/workspace/tirtc-device-builder

npm run pack:esp32-kit -- \
  --source /home/workspace/tirtc-server-example/thing-connect \
  --kit-version 1.0.0
```

输出文件位于 `dist/`：

```text
tirtc-esp32s3-kit-1.0.0.tar.gz
tirtc-esp32s3-kit-1.0.0.tar.gz.sha256
```

从 `dist/` 目录校验附件：

```bash
cd /home/workspace/tirtc-device-builder/dist
sha256sum -c tirtc-esp32s3-kit-1.0.0.tar.gz.sha256
```

发布前使用独立标签，并把两个文件作为 GitHub Release 附件上传：

```bash
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

模板工程提供配网、绑定、MQTT、TiRTC、H5 和 AI 会话骨架。具体开发板仍需接入摄像头、H.264 编码器、麦克风、扬声器、Codec、I2S 和按键。工程编译成功不等于 Web 已经出图或 AI 对讲已通过实机验收。

## 推荐：一键检查和安装

新人先执行一条只读命令：

```bash
npx tirtc-device-builder@latest setup esp32
```

环境完整时它直接运行 Doctor 并输出 `SETUP: READY`。存在缺失项时，它会显示具体状态和下一条命令：

```bash
npx tirtc-device-builder@latest setup esp32 --install
```

`--install` 自动完成：

- 安装 `tirtc-esp32-builder` 到 Codex Skill 目录；
- 下载并校验 ESP32 Device Kit 1.0.0，缓存后供多个工程复用；
- 复用已激活的 ESP-IDF 5.5.x，缺失时安装固定版本 ESP-IDF 5.5.4；
- 安装 Espressif 管理的 ESP32-S3 工具链；
- 生成只包含路径的 `config.json` 和 `env.sh`；
- 自动激活安装环境并重新运行 Doctor。

默认托管目录是 `~/.tirtc-device-builder`。自动安装不执行 `sudo`、不修改 `.bashrc` 或 `.zshrc`、不覆盖已有但内容不完整的目录。缺少 Git、Python 或其他系统依赖时，它会停止并给出可复制的系统安装命令；修复后重复同一条 `--install` 命令即可从断点继续。

需要自定义位置时：

```bash
npx tirtc-device-builder@latest setup esp32 --install \
  --root /absolute/path/tirtc-dev
```

安装完成后启动新的 Codex 会话，只需输入板卡和目标：

```text
$tirtc-esp32-builder

开发板：<厂商> <完整型号> <PCB 版本>
板卡资料：/absolute/path/board-materials
输出工程：/absolute/path/my-esp32-device
目标：H5 实时音视频、H5 对讲、AI 双向对讲

使用一键安装产生的托管环境。先分析资料并生成 Hardware IR，
达到 READY_TO_PORT 后生成和编译；本轮不烧录。
```

到这里，新人只需要“执行 `setup --install` → 重启 Codex → 输入板卡需求”。下面保留完整流程，供自定义目录、手动安装和故障排查使用。

## 完整手动流程和排障

推荐先跑通“安装 → 环境 → 板卡分析 → 生成 → 编译”，确认报告无误后再单独授权烧录和实机验收。整个过程使用同一份板卡事实，避免在代码生成阶段猜测引脚、器件或媒体能力。

```text
板卡型号/原理图/BSP
        ↓
Hardware IR（硬件事实与来源）
        ↓
能力门禁（READY_TO_PORT 才进入实现）
        ↓
独立 ESP-IDF 工程 + 板级媒体适配
        ↓
编译 → 授权烧录 → 配网绑定 → H5/AI 验收
        ↓
TIRTC_PORTING_REPORT.md
```

### 第 0 步：确认当前支持范围

当前可直接生成的基线是：

| 项目 | 当前基线 |
|---|---|
| 芯片 | ESP32-S3 |
| 模组 | ESP32-S3-WROOM-1-N16R8，或资源与配置经过确认的兼容板 |
| ESP-IDF | 5.5.x |
| TiRTC SDK | `espressif-esp32s3/2.3.0` |
| 业务 | H5 实时音视频、H5 对讲、AI 双向语音 |
| 工程生成 | 使用本地缓存的 ESP32 Device Kit 1.0.0 |
| 烧录 | 必须明确给出串口并授权 |

“板上有摄像头”不等于可以输出 H5 视频。H5 视频还需要可用的 H.264 Annex-B 编码输出、SPS/PPS、IDR 和关键帧请求控制；对讲还需要完整的麦克风采集、G.711 A-law 8 kHz 编码、下行解码、I2S/Codec/功放和扬声器路径。

当前生成器只支持 ESP32-S3，TiRTC SDK 也必须匹配 `espressif-esp32s3` 平台。Flash/PSRAM 不是 16 MB/8 MB 时，需要先调整 `sdkconfig.defaults`、分区表和板级资源预算并重新评估；Skill 不会把相似型号静默当作当前板卡。

### 第 1 步：固定工作路径

下面的命令以 Linux、Ubuntu 或 WSL 的 Bash 为例。先把所有路径改成自己的绝对路径；路径可以不同，但后续必须始终使用同一组值。

```bash
export TIRTC_WORKSPACE=/home/your-user/workspace
export TIRTC_BOARD_DOCS="$TIRTC_WORKSPACE/board-materials"
export TIRTC_PROJECT_DIR="$TIRTC_WORKSPACE/my-esp32-device"

source ~/.tirtc-device-builder/env.sh
```

逐项确认：

```bash
printf 'workspace: %s\n' "$TIRTC_WORKSPACE"
printf 'ESP32 Device Kit: %s\n' "$TIRTC_THING_CONNECT_ROOT"
printf 'board docs: %s\n' "$TIRTC_BOARD_DOCS"
printf 'output project: %s\n' "$TIRTC_PROJECT_DIR"
```

注意：

- `TIRTC_PROJECT_DIR` 是待生成的新目录，生成前不能已经存在；生成器不会覆盖旧工程。
- 板卡资料和输出工程使用不同目录。
- 不要把 Wi-Fi 密码、设备密钥、MQTT/WHIP token 或真实用户音视频放入板卡资料目录和 Git 仓库。
- 新开终端后需要重新设置这些变量，除非开发者自行把它们加入 shell 配置。

### 第 2 步：准备板卡资料包

创建资料目录，把原始资料按来源保存，不要先手工改写原理图或 BSP：

```bash
mkdir -p "$TIRTC_BOARD_DOCS"
```

最有利于一次完成的资料如下：

| 优先级 | 资料 | 需要明确的内容 |
|---|---|---|
| 必需 | 板卡身份 | 厂商、完整型号、模组型号、PCB 丝印和硬件版本 |
| 必需 | 原理图或网表 | 摄像头、麦克风、Codec、功放、I2S、I2C、SPI、时钟、复位、电源使能和 GPIO |
| 必需 | BSP 或厂商示例 | 可复现的 Git commit/tag、ESP-IDF 版本、能工作的外设初始化与管脚定义 |
| 视频必需 | 摄像头/编码资料 | Sensor 型号、输入接口、H.264 编码位置、Annex-B 输出、SPS/PPS、IDR 控制 |
| 对讲必需 | 音频资料 | 麦克风类型、Codec/ADC/DAC、采样率、位宽、声道、MCLK/BCLK/LRCK、功放使能 |
| 推荐 | 器件数据手册 | Sensor、Codec、功放、时钟和电源芯片的准确型号与版本 |
| 推荐 | 最小实测工程 | 已在该 PCB 版本运行的摄像头、录音、播放或编码示例及其构建命令 |

资料不完整也可以先调用 Skill。它会把未知事实写成 `null`，并列出进入下一步所需的最小补充项。不同 PCB 版本按不同板卡处理；不能只给“ESP32-S3”而省略载板型号和版本。

### 第 3 步：安装 Node.js 和 Skill

使用 npm 安装 Skill 只需要 Node.js 18 或更高版本。普通使用者不需要执行 `npm login`；登录只用于维护者发布 npm 包。

先检查版本和 npm 官方源：

```bash
node --version
npm --version
npm config get registry
```

预期：

- Node.js 输出 `v18.x` 或更高版本；
- npm registry 输出 `https://registry.npmjs.org/`。

如果 `node` 或 `npm` 不存在，先从 [Node.js 官方下载页](https://nodejs.org/en/download) 安装受支持版本，重新打开终端，再重复版本检查。

如果 registry 不是官方源，可为当前用户切换：

```bash
npm config set registry https://registry.npmjs.org/
```

确认 npm 包可访问并安装当前稳定版本：

```bash
npm view tirtc-device-builder version
npx tirtc-device-builder@latest list
npx tirtc-device-builder@latest install esp32
```

成功时最后会看到类似输出：

```text
Installed tirtc-esp32-builder <version> to /home/.../.codex/skills/tirtc-esp32-builder
Start a new Codex session, then invoke $tirtc-esp32-builder.
```

默认安装位置是 `${CODEX_HOME:-~/.codex}/skills/tirtc-esp32-builder`。安装完成后关闭当前 Codex 会话并启动一个新会话，让 Codex 重新发现 Skill。

如果目标目录已经存在，安装器会保护已有内容并退出。先确认目录中的本地修改是否需要保留；只有确定要替换时才执行：

```bash
npx tirtc-device-builder@latest install esp32 --force
```

自定义 Skill 根目录时使用绝对路径：

```bash
npx tirtc-device-builder@latest install esp32 \
  --skills-dir /absolute/path/to/skills
```

如果 npm 包尚未发布或当前网络无法访问 npm，可从 GitHub 安装固定版本。在 Codex 对话中输入：

```text
$skill-installer

安装：
https://github.com/tangeai/tirtc-device-builder/tree/v0.3.0/skills/tirtc-esp32-builder
```

Linux/macOS 也可以执行：

```bash
python3 ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo tangeai/tirtc-device-builder \
  --ref v0.3.0 \
  --path skills/tirtc-esp32-builder
```

仓库根目录还包含 `.codex-plugin/plugin.json`，可作为 skills-only Plugin 使用。直接从 npm 或 GitHub 安装不依赖 Plugin Directory 审核。

### 第 4 步：准备 ESP32 Device Kit

Device Kit 包含生成新工程需要的最小资源：

- ESP32-S3 H5/AI 工程生成器；
- 起步模板和平台公共组件；
- TiRTC ESP32-S3 SDK 头文件、静态库和构建契约；
- H5、AI、设备接入和会话协议文档。

一键安装会下载固定 Release、校验 SHA-256，并缓存到 `~/.tirtc-device-builder/kits/esp32s3/1.0.0/`。不需要克隆 `tirtc-server-example`：

```bash
npx tirtc-device-builder@latest setup esp32 --install
source ~/.tirtc-device-builder/env.sh
```

维护者刚生成 Release、附件还没有上传时，可以使用本地包完成同样的安装验证：

```bash
npx tirtc-device-builder@latest setup esp32 --install \
  --kit-archive /absolute/path/tirtc-esp32s3-kit-1.0.0.tar.gz
```

验证关键文件：

```bash
ls -l "$TIRTC_THING_CONNECT_ROOT/device-sim/scripts/create_esp32_project.py"
ls -l "$TIRTC_THING_CONNECT_ROOT/device-sim/sdk/espressif-esp32s3/2.3.0/include/tirtc/tiRTC.h"
ls -l "$TIRTC_THING_CONNECT_ROOT/device-sim/sdk/espressif-esp32s3/2.3.0/lib/libTiRTC.a"
ls -l "$TIRTC_THING_CONNECT_ROOT/device-sim/sdk/espressif-esp32s3/2.3.0/manifest/build-contract.env"
```

四条命令都应显示真实文件。资源来源版本记录在 Kit 清单中：

```bash
python3 -m json.tool "$TIRTC_THING_CONNECT_ROOT/manifest.json"
```

生成器会把必要模块和 TiRTC SDK 复制到新工程的 `third_party/tirtc/`，所以已生成的工程可以移动并独立编译。一个已校验的 Kit 缓存可以供多个工程使用。

### 第 5 步：检查或安装 ESP-IDF 5.5.x

先检查当前终端，不要因为环境未激活而重复安装：

```bash
command -v idf.py
idf.py --version
command -v xtensa-esp32s3-elf-gcc
```

如果 `idf.py --version` 输出 `ESP-IDF v5.5.x`，并且能找到 `xtensa-esp32s3-elf-gcc`，直接进入第 6 步。

如果 ESP-IDF 已安装但当前终端找不到 `idf.py`，执行该安装目录自带的 `export.sh`。例如：

```bash
source /absolute/path/to/esp-idf/export.sh
idf.py --version
command -v xtensa-esp32s3-elf-gcc
```

每个新终端都需要重新执行 `source .../export.sh`。Skill 的环境检查不会自动修改 `.bashrc`、`.zshrc` 等持久 shell 配置。

在 Ubuntu/Debian/WSL 中首次安装时，以下命令安装当前基线 `v5.5.4`。下载、系统包安装和磁盘写入应由开发者在确认目录后执行：

```bash
sudo apt-get update
sudo apt-get install -y git wget flex bison gperf python3 python3-pip \
  python3-venv cmake ninja-build ccache libffi-dev libssl-dev dfu-util \
  libusb-1.0-0

mkdir -p "$TIRTC_WORKSPACE/toolchains"
git clone -b v5.5.4 --recursive \
  https://github.com/espressif/esp-idf.git \
  "$TIRTC_WORKSPACE/toolchains/esp-idf-v5.5.4"

"$TIRTC_WORKSPACE/toolchains/esp-idf-v5.5.4/install.sh" esp32s3
source "$TIRTC_WORKSPACE/toolchains/esp-idf-v5.5.4/export.sh"

idf.py --version
command -v xtensa-esp32s3-elf-gcc
```

最后两条命令必须分别显示 ESP-IDF 5.5.x 和 ESP32-S3 编译器路径。macOS、原生 Windows 或依赖版本有变化时，以 [Espressif ESP-IDF 5.5.4 Get Started](https://docs.espressif.com/projects/esp-idf/en/v5.5.4/esp32s3/get-started/index.html) 为准。

### 第 6 步：生成工程前运行 Doctor

不安装 Skill 也可以通过 npm CLI 调用同一个检查脚本：

```bash
npx tirtc-device-builder@latest doctor esp32 \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root "$TIRTC_THING_CONNECT_ROOT" \
  --require-workspace
```

已经安装 Skill 时也可以直接执行：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --thing-connect-root "$TIRTC_THING_CONNECT_ROOT" \
  --require-workspace
```

生成前的合格结果应满足：

| 检查项 | 期望 |
|---|---|
| Python、Git | `PASS` |
| `idf.py` | `PASS`，版本为 5.5.x |
| target compiler | `PASS`，找到 ESP32-S3 编译器 |
| ESP32 Device Kit | `PASS` |
| TiRTC SDK | `PASS` |
| serial discovery | 还未接板时允许 `WARN` |
| OVERALL | `PASS` |

`doctor.py` 是只读检查：不安装软件、不修改 shell 配置、不生成工程，也不烧录设备。

常见检查失败：

- `idf.py not found`：当前终端没有激活 ESP-IDF，先执行 `source <idf-dir>/export.sh`。
- `target compiler ... not found`：ESP-IDF 环境未激活，或安装时没有包含 `esp32s3`。
- `ESP32 Device Kit ... not found`：先执行一键安装，或传入 Kit 根目录；兼容路径也可以是完整仓库根目录或其 `thing-connect/` 子目录。
- `TiRTC SDK ... missing`：检查仓库是否拉取完整，以及 SDK 的头文件、静态库和 `manifest/build-contract.env` 是否存在。
- `serial discovery: no serial device detected`：生成和编译阶段可以继续；烧录前必须解决。

不要在一个空目录上提前使用 `--project`。如果看到：

```text
FAIL TiRTC build contract [required]: no sdkconfig or sdkconfig.defaults in ...
```

表示传入目录还不是已生成的 ESP-IDF 工程，或者 `--project` 路径给错了。先让 Skill/生成器创建工程；生成后目录中应有 `sdkconfig.defaults`，再运行项目级 Doctor。

### 第 7 步：在新 Codex 会话中调用 Skill

只给出板卡型号也可以启动分析，但提供完整资料更容易一次进入开发。建议复制下面的提示词，逐项替换尖括号内容和绝对路径：

```text
请使用 $tirtc-esp32-builder 完成这块板的 TiRTC 移植。

板卡：
- 厂商：<厂商>
- 完整型号：<型号>
- 模组：<例如 ESP32-S3-WROOM-1-N16R8>
- PCB 丝印/硬件版本：<版本>

输入资料：
- 原理图或网表：/absolute/path/board-materials/<file>
- BOM：/absolute/path/board-materials/<file>
- BSP/厂商示例：/absolute/path/vendor-bsp
- 摄像头/Codec/功放数据手册：/absolute/path/board-materials/<files>
- Device Kit：使用 `setup esp32 --install` 生成的托管环境

目标：
- H5 实时视频和音频
- H5 下行语音对讲
- AI 双向语音对讲

输出：
- 新工程目录：/absolute/path/my-esp32-device
- Hardware IR：放在新工程同级或工程内的明确路径
- 报告：/absolute/path/my-esp32-device/TIRTC_PORTING_REPORT.md

执行要求：
1. 先运行环境 Doctor，并核对 ESP-IDF 5.5.x、esp32s3 工具链和 TiRTC SDK。
2. 完整分析我提供的每份资料，记录来源、版本、冲突和未知项。
3. 生成、校验并严格评估 Hardware IR；不要从相似板型猜测管脚或器件。
4. 每项能力达到 READY_TO_PORT 后，生成独立工程并把板级采集、编码、播放、按键放在 starter_media/板级 adapter。
5. 运行相关测试和 idf.py build，保留实际命令、结果、固件路径和 SHA-256。
6. 本轮不烧录、不写设备凭证；需要下载、安装或修改系统环境时先说明具体动作。
7. 最后生成 TIRTC_PORTING_REPORT.md，所有验收层级使用 PASS、FAIL 或 SKIP，不能用编译成功代替 H5/AI 实机通过。
```

如果只有型号和网页资料，可先用：

```text
$tirtc-esp32-builder

分析 <厂商> <完整型号> <PCB 版本>，目标是 H5 实时音视频、H5 对讲和 AI 双向对讲。
先输出板卡资料清单、Hardware IR、能力结论和最小缺失项；本轮不生成工程、不烧录。
```

Skill 会选择以下三条分支之一：

- 已支持板卡：校验已有 Hardware IR 和 adapter 后重新生成、编译和验收；
- 新板卡：逐份提取原理图/BSP/数据手册事实，建立 Hardware IR，再决定是否实现；
- 已有 ESP-IDF 工程：先检查目标、配置、组件、驱动和最小外设示例，再隔离可复用板级代码。

### 第 8 步：检查 Hardware IR 和能力门禁

默认 Hardware IR 工具位于：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py init \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py validate \
  /absolute/path/hardware-ir.json

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/hardware_ir.py assess --strict \
  /absolute/path/hardware-ir.json
```

通常由 Codex 执行这些命令，开发者只需检查结果：

| 状态 | 含义 | 下一步 |
|---|---|---|
| `NEEDS_CONFIRMATION` | 关键事实未知或只有单一来源 | 补原理图、BSP、数据手册或实测证据 |
| `BLOCKED` | 已确认当前硬件/SDK 不满足 | 换硬件、补编码/播放路径或取得匹配 SDK |
| `READY_TO_PORT` | 资料已足够，可以生成并实现板级适配 | 进入生成和编译 |
| `HIL_VERIFIED` | 该功能已完成端到端实机验证 | 保存证据和版本 |

`assess --strict` 返回非零不一定表示脚本坏了；当任一请求能力尚未达到 `READY_TO_PORT` 时，它会用退出码阻止过早生成。先处理输出中的具体原因。

### 第 9 步：生成、实现和编译

推荐让 Skill 自动执行。需要人工复现生成步骤时，确保 `TIRTC_PROJECT_DIR` 不存在，再运行：

```bash
python3 "$TIRTC_THING_CONNECT_ROOT/device-sim/scripts/create_esp32_project.py" \
  "$TIRTC_PROJECT_DIR" \
  --name my_esp32_device
```

`--name` 只能包含小写字母、数字和下划线。生成器拒绝覆盖已存在目录；需要重做时应先选择新的输出目录或人工备份旧工程。

进入工程，激活 ESP-IDF，再检查 SDK 构建契约。下面的 `source` 路径只适用于按第 5 步安装到示例目录的情况；已有安装应替换为其真实 `export.sh` 路径：

```bash
cd "$TIRTC_PROJECT_DIR"
source "$TIRTC_WORKSPACE/toolchains/esp-idf-v5.5.4/export.sh"

python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project "$TIRTC_PROJECT_DIR"
```

项目级 Doctor 的 `TiRTC build contract` 必须为 `PASS`。随后构建：

```bash
idf.py set-target esp32s3
idf.py build
```

构建成功只证明 L1 Build 通过。真正的板卡移植还要完成 `components/starter_media/` 中的产品适配点：

- 麦克风采集并提交 G.711 A-law、8 kHz、单声道帧；
- 摄像头采集并提交 H.264 Annex-B access unit；
- 收到关键帧请求时让编码器产生 IDR；
- 把下行 A-law 音频放入有界队列，解码后写入 Codec/I2S/功放；
- 把实体按键映射到 AI 开始/停止；
- 停止会话时有界停止采集/播放任务并清空旧 generation 数据。

检查仍未完成的产品适配点：

```bash
rg -n 'TODO\(product-' main components
```

编译产物位于 `build/`。报告至少记录 ESP-IDF、TiRTC SDK、BSP/adapter 版本，实际构建命令、返回码、固件文件和 SHA-256。

### 第 10 步：明确授权后烧录

先连接开发板并确定唯一串口。Linux 常见端口为 `/dev/ttyACM0` 或 `/dev/ttyUSB0`：

```bash
ls -l /dev/ttyACM* /dev/ttyUSB*
```

用实际端口运行 Doctor：

```bash
python3 ~/.codex/skills/tirtc-esp32-builder/scripts/doctor.py \
  --expected-idf 5.5 \
  --target esp32s3 \
  --project "$TIRTC_PROJECT_DIR" \
  --serial-port /dev/ttyACM0
```

`serial port` 必须为 `PASS`。如果设备存在但无权限，按系统规范配置串口用户组并重新登录；不要用长期放宽所有设备权限的方式绕过。

让 Skill 烧录时发起第二次、独立且明确的请求：

```text
$tirtc-esp32-builder

我确认目标芯片是 ESP32-S3，目标工程是 /absolute/path/my-esp32-device，
目标串口是 /dev/ttyACM0。授权本轮烧录该设备并打开串口监视；
不要擦除其他串口设备，不要在日志中输出 Wi-Fi 密码或设备密钥。
烧录后执行 L2 Boot 检查并更新 TIRTC_PORTING_REPORT.md。
```

也可以人工执行：

```bash
cd "$TIRTC_PROJECT_DIR"
idf.py -p /dev/ttyACM0 flash monitor
```

ESP-IDF Monitor 中使用 `Ctrl+]` 退出。多个串口同时存在时，必须根据 USB 拔插、设备标识或芯片探测结果确认目标，不能选择第一个端口直接写入。

WSL 不一定自动获得 USB 串口。Doctor 看不到端口时，先按 [Microsoft 的 WSL USB 连接说明](https://learn.microsoft.com/windows/wsl/connect-usb) 把目标设备附加到当前 WSL 实例，再重新运行串口检查。

### 第 11 步：首次配网和绑定

固件首次启动且没有 Wi-Fi 配置时：

1. 在手机或电脑连接 `TiRTC-Setup-XXXX`。
2. 输入默认密码 `tirtc1234`。
3. 打开 `http://192.168.4.1`，填写设备要连接的 Wi-Fi。
4. 设备重启并联网后，在串口查看绑定验证码和体验平台地址。
5. 登录体验平台，在设备绑定入口输入验证码。
6. 回到串口输入 `status`，确认 platform、MQTT、TiRTC 均已就绪，runtime 处于 `waiting`。

也可以在串口输入：

```text
wifi-set <ssid> <password>
wifi-clear
status
restart
```

`tirtc-set <device_id> <device_secret> [client_id]` 只用于受控底层联调。正常流程使用验证码绑定，真实凭证不能写入源码、脚本、报告或 Git。

### 第 12 步：按层验收 H5 和 AI

验收时不要跨级宣告成功。缺少账号、浏览器、服务、外网、板卡或仪器时，对应项记录为 `SKIP`，并写明补测条件。

| 层级 | 必须看到的证据 |
|---|---|
| L-1 Environment | Doctor 的必需项和项目构建契约通过 |
| L0 Generate | 新工程和 Hardware IR 存在，未覆盖旧目录 |
| L1 Build | `idf.py build` 成功并记录固件及 SHA-256 |
| L2 Boot | 指定串口烧录成功，无 panic/反复重启 |
| L3 Online | 配网、验证码绑定、MQTT、TiRTC 就绪 |
| L4 Media | 摄像头、麦克风、扬声器本地路径和计数正常 |
| L5 H5 | 浏览器持续收到声明的视频/音频，对讲到达设备扬声器 |
| L6 AI | token、WHIP、`start_session`、双向音频、停止和 H5 恢复正常 |
| L7 Stability | 按需求完成反复会话、弱网、资源和长稳测试 |

H5 验收：

1. 串口 `status` 显示 runtime 为 `waiting`。
2. 在体验平台打开该设备的实时查看入口。
3. 确认 H.264 视频持续显示，音频/视频发送计数持续增长。
4. 发起 H5 对讲，确认 stream 14 下行计数增长且实体扬声器可听。
5. 触发浏览器重连或关键帧请求，确认板端编码器产生新的 IDR，画面恢复。

AI 验收：

1. 确认 H5/其他会话没有占用媒体资源。
2. 串口输入 `ai-start`，观察状态从 `ai-connecting` 进入 `ai-active`。
3. 确认只有 `start_session` 成功后才开始发送麦克风音频。
4. 确认上行麦克风被 AI 接收，下行 AI 音频在扬声器播放。
5. 输入 `ai-stop`，确认发送 `end_session`、媒体任务停止，状态回到 `waiting`。
6. 再次打开 H5，确认 H5 可以重新连接并恢复音视频。

### 第 13 步：检查最终交付物

一次完整交付至少包含：

- 生成的 ESP-IDF 工程绝对路径；
- `hardware-ir.json` 及每条关键事实的来源；
- 能力评估结果和剩余阻塞项；
- `build/` 中的固件产物及 SHA-256；
- 明确到芯片和串口的烧录记录；
- 脱敏后的构建、启动和验收日志；
- `TIRTC_PORTING_REPORT.md`；
- L-1 到 L7 的 `PASS`、`FAIL` 或 `SKIP` 证据。

如果只完成生成和编译，报告应明确停在 L1；不能写成“Web 已出图”或“AI 对讲已完成”。

### 一次成功检查清单

开始下一阶段前逐项确认：

- [ ] 板卡厂商、完整型号、模组、PCB 版本一致。
- [ ] 原理图/BOM/BSP/数据手册路径均为绝对路径且可读。
- [ ] Node.js 版本不低于 18，Skill 已安装并重启 Codex。
- [ ] ESP32 Device Kit 的生成器、TiRTC 头文件、静态库和构建契约存在。
- [ ] 当前终端已激活 ESP-IDF 5.5.x 和 ESP32-S3 工具链。
- [ ] 生成前 Doctor 的 `OVERALL` 为 `PASS`。
- [ ] 所有请求能力均为 `READY_TO_PORT` 或 `HIL_VERIFIED`。
- [ ] 输出目录不存在，旧工程未被覆盖。
- [ ] 项目级 Doctor 的 `TiRTC build contract` 为 `PASS`。
- [ ] `idf.py build` 成功，但尚未把它当作实机功能通过。
- [ ] 烧录前已确认唯一串口并明确授权。
- [ ] 配网、绑定、H5、AI 分层验收均保留脱敏证据。
- [ ] 最终报告中的每个 `SKIP` 都有原因和最小下一步。

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
