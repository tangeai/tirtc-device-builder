$tirtc-esp32-builder

请在一台全新电脑上完成立创·实战派 ESP32-S3 的 ThingConnect TiRTC clean-room L-1/L0/L1 接入。允许访问外网，并允许 `npx tirtc-device-builder@latest setup esp32 --install` 在当前用户目录安装固定版本的 Device Kit、ESP-IDF 和 Skill；禁止 sudo、系统级包变更和修改 shell profile。无需重复询问该用户目录安装权限。

工作区：
- 将本提示词所在资料包目录作为 `WORKSPACE_ROOT`。
- 所有本地输入和输出均相对 `WORKSPACE_ROOT` 解析；报告中再记录规范化绝对路径。

证据边界：
- 只使用 `docs/`、其中的厂商示例、厂商官方资料和 managed Device Kit。
- 不读取工作区外的历史工程、日志或 artifact。
- 不使用任何真实 Wi-Fi、设备、MQTT、WHIP 或 AI 凭证。

开发板：
- 立创·实战派 ESP32-S3，PCB V1.0.1。
- ESP32-S3-WROOM-1-N16R8，16 MB Flash、8 MB Octal PSRAM。
- `docs/立创实战派ESP32-S3开发板原理图.pdf` 对应手中实物。
- 厂商标称 GC0308，实物 PID `0x2145`/GC2145；保留矛盾，只允许有精确证据的 PID，拒绝未知 PID。

资料：
- `docs/立创实战派ESP32-S3开发板原理图.pdf`
- `docs/02-芯片手册/`
- `docs/szpi-s3-esp/`
- https://wiki.lckfb.com/zh-hans/szpi-esp32s3/

目标：
- H5 MJPEG 实时视频和声音、H5 双向语音、AI 双向语音。
- 每次视频发送一张完整 JPEG。
- 音频 G.711 A-law、8 kHz、mono。
- stream：H5 上行 10、视频 11、下行 14、AI 1。
- 初版允许半双工；不声明未实测的全双工或 AEC。

接入：
- SoftAP 配网，凭证保存 NVS。
- 验证码绑定，复用已有绑定。
- 分别提供 `wifi-clear` 和 `tirtc-clear`。
- 平台发现先用 HTTP；HTTPS 后续独立验收。

输出：
- `lckfb-szpi-esp32s3-tirtc/`

强制门禁：
1. 运行 Device Kit Doctor并固定 ESP-IDF、Kit、TiRTC SDK、生成器和组件版本。
2. 从不存在的输出目录开始生成 Hardware IR v2 和工程；不得读取或复制任何既有 adapter、历史工程、`build/`、日志或 artifact。所有具体 clock、I2S mode/controller、TDM slot、物理信号、shared-GPIO handoff、camera task/core、frame buffer 和 memory/backpressure 值都要引用来源。
3. 音频必须生成项目内 `board-audio-contract.json`。`idf.py reconfigure` 后，使用 Skill 的 `audio_contract.py` 直接查询锁定 codec driver table；所选 `(MCLK, sample rate)` 必须被所有相关 codec 支持。
4. 视频必须生成项目内 `board-video-contract.json` 并使用 `video_contract.py` 核对锁定组件、CPU 隔离、完整 JPEG、PID 白名单、frame buffers、TiRTC send buffer 和 backpressure。此板初版合同必须包含 camera event CPU1、Wi-Fi CPU0、两个 PSRAM frame buffers、256 KiB max send buffer、192 KiB backpressure、stream 11 和 `TIRTC_VIDEO_JPEG`；esp32-camera 固定官方 2.1.7 legacy-I2C 配置。
5. 音频和视频合同都必须和 adapter 源码核对，并分别通过 `install_audio_gate.py`、`install_video_gate.py` 接入每次 `idf.py build`。任何缺失或失败都只能记为 `COMPILE_PASS / CAPABILITY_BLOCKED`，不得写 `BUILD_VERIFIED`。
6. build assessment 必须提供 `--project` 和当前 artifact SHA-256，并重新运行两个语义合同；任一 requested feature 阻塞时，project gate 也必须阻塞。
7. 输出 Hardware IR、两个合同、依赖锁、可独立构建工程、门禁证据、BIN/ELF 大小与 SHA-256，以及 `TIRTC_PORTING_REPORT.md`。
8. 对源码交付物运行 `project_portability.py --export`；不得携带旧 `build/`，CMake 中的 shell 门禁必须显式通过 `bash` 调用。
9. 本轮不访问串口、不烧录、不 monitor、不擦除 NVS；L2-L7 记为 SKIP，不得把 L1 编译表述为实机已有图像或声音。
