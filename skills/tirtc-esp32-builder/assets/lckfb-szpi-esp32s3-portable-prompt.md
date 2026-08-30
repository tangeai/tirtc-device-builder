$tirtc-esp32-builder

请在当前工作区完成一次立创·实战派 ESP32-S3 的 ThingConnect TiRTC clean-room L-1/L0/L1 接入验证。

这是 Skill、提示词和开发板资料的独立有效性测试。允许访问外网。

前置条件（必须由开发者在启动本次 Codex 会话前完成，不属于本提示词内的操作）：

```bash
npx --yes tirtc-device-builder@0.7.3 setup esp32 --install --force-skill
```

该命令只允许在当前用户目录安装固定版本的 Skill、managed ESP32 Device Kit、ESP-IDF 和工具链；禁止 sudo、系统级包变更和修改 shell profile。安装完成后，开发者必须关闭原 Codex 会话，再从本 clean-room 工作区启动一个新会话，然后粘贴本提示词。

本轮第一步先只读运行：

```bash
npx --yes tirtc-device-builder@0.7.3 --version
npx --yes tirtc-device-builder@0.7.3 setup esp32
```

必须根据命令的实际输出和本机文件确认：npm 包为 0.7.3、已安装 Skill 的 `VERSION` 为 0.7.3、所选 Device Kit 的 `manifest.json` 中 `kit_version` 为 1.1.1，并且 Doctor 对 `--expected-kit 1.1.1` 输出 `OVERALL: PASS`。Plugin manifest 不属于这种 npm 安装方式的运行时前置条件，不得把不可访问的 Plugin 版本当作阻塞项。如果版本不一致、Skill 是在当前会话启动后才安装，或环境检查未通过，停止并报告前置条件不成立；不要在当前会话中替换 Skill 后继续生成工程。

工作区与 clean-room 边界：
- 将启动 Codex 时的当前目录定义为 `WORKSPACE_ROOT`。
- 所有工程输入和输出必须位于 `WORKSPACE_ROOT`。
- 不得读取 `WORKSPACE_ROOT` 之外的项目、兄弟目录、父目录项目、备份、旧构建、日志、报告或 artifact。
- 如果目标输出目录已经存在，停止并报告 clean-room 条件不成立；不要读取、覆盖或删除该目录。

允许的证据：
- `WORKSPACE_ROOT/docs/` 中实际存在的全部资料。
- 开发板厂商官方网站：https://wiki.lckfb.com/zh-hans/szpi-esp32s3/
- 芯片、组件和 ESP-IDF 厂商官方资料。
- managed Device Kit 内的 manifest、协议资料、生成器、锁定组件源码和 codec driver table。
- 本提示词中的板型、实物观察和产品要求属于用户输入，但提示词本身不得作为 clock、GPIO、I2S、TDM、DMA、camera 调度或内存参数的技术证据。

禁止：
- 不读取任何 `.bak`、旧项目、旧报告、旧 `build/`、日志或历史 artifact。
- 不使用社区博客、论坛代码或来源不明的示例替代官方证据。
- 不记录或生成真实 Wi-Fi、设备、MQTT、WHIP 或 AI 凭证。
- 不访问串口、不烧录、不 monitor、不擦除 NVS。
- 不为了通过编译而猜测硬件参数、伪造来源或静默关闭请求的功能。

开发板：
- 立创·实战派 ESP32-S3，PCB V1.0.1。
- ESP32-S3-WROOM-1-N16R8，16 MB Flash、8 MB Octal PSRAM。
- `docs/立创实战派ESP32-S3开发板原理图.pdf` 对应手中实物。
- 厂商页面可能标称 GC0308，但手中实物观测到 PID `0x2145`，对应 GC2145；必须保留该矛盾。
- 只能接受资料或锁定驱动明确支持的 PID；必须拒绝未知 PID。

媒体合同：
- ThingConnect 平台和 Web 播放端支持 MJPEG、H.264、H.265；这属于平台能力。
- 本开发板初版只选择 MJPEG；这是板级输出选择，不得错误写成平台只支持 MJPEG。
- H5 MJPEG 实时视频和声音、H5 双向语音对讲、AI 双向语音对讲。
- 每次视频调用必须发送一张完整 JPEG，禁止截断帧或裸分片。
- 音频 G.711 A-law、8 kHz、mono。
- stream：H5 上行 10、视频 11、H5 下行 14、AI 1。
- 初版允许半双工；不得声明未经实机验证的全双工或 AEC。

接入要求：
- SoftAP 配网，凭证保存 NVS。
- 验证码绑定，并复用已有绑定。
- 分别实现 `wifi-clear` 和 `tirtc-clear`。
- 平台发现本轮先使用 HTTP；HTTPS 留待独立验收。

输出目录：
- `WORKSPACE_ROOT/lckfb-szpi-esp32s3-tirtc/`

必须完成：
1. 运行 Device Kit Doctor，记录实际使用的 npm 包、Skill、ESP32 Device Kit、源模板 commit、ESP-IDF、TiRTC SDK、生成器和所有关键组件版本。
2. 审查 `docs/` 的实际内容，建立“需求—硬件事实—来源—验证等级”证据矩阵。每个来源只能使用一个可解析定位符；不得把提示词、多个文件或绝对机器路径拼成伪来源。
3. 生成 Hardware IR v2。每个影响功能的 GPIO、clock、I2S controller/mode、codec slot、camera PID、DMA、task/core、frame buffer、内存和 backpressure 参数必须有精确来源。
4. 对无法从允许证据确认的事实分类为 `source_resolvable`、`implementation_resolvable`、`build_resolvable`、`hil_resolvable` 或 `user_blocked`。只有真正的 `user_blocked` 才停止安全实现；不得用历史工程补证据。
5. 生成板级 media adapter 和可独立构建的 ESP-IDF 工程。板级常量只进入项目 Hardware IR、合同或 adapter，不得写入通用 Skill。
6. 音频生成 `board-audio-contract.json`。在 `idf.py reconfigure` 后，直接检查锁定 codec driver table，证明所选 sample rate、MCLK、I2S 模式和 slot 组合受相关 codec 支持；不得使用注释中的典型值代替驱动能力证明。
7. 视频生成 `board-video-contract.json`，并引用项目内 `platform-media-contract.json`。门禁必须同时证明平台 stream 11 接受 MJPEG/H.264/H.265，以及本板只选择 MJPEG；还要核验锁定 camera 组件支持允许 PID、完整 JPEG 边界、TiRTC JPEG media type、camera/Wi-Fi 调度、frame buffer、最大 JPEG、send buffer、backpressure、PSRAM 和内部 DMA 内存关系。
8. 生成并验证 `tirtc-runtime-contract.json`，证明发现得到的 `tirtc-srv` 实际传入 SDK、SDK callback 内不直接执行 disconnect/stop/uninit、H5 下行严格过滤 stream 14 与 A-law/8 kHz、AI `start_session` 严格验证 `session_id` 和输入输出格式、远端 `end_session` 能停止会话。
9. 用 Skill 的 gate installer 把 runtime、audio、video 三个语义检查接入每次普通 `idf.py build`；合同必须和 adapter 源码及最终 `sdkconfig` 核对。任一适用门禁缺失或失败时，只能报告 `COMPILE_PASS / CAPABILITY_BLOCKED`，不得报告 `BUILD_VERIFIED`。
10. 执行 `idf.py reconfigure`、全部语义门禁和完整 `idf.py build`。
11. 将最终 BIN/ELF 复制到项目内 `artifacts/`，记录项目相对路径、实际大小和完整 SHA-256；用同一 SHA-256 执行 build-phase Hardware IR assessment。评估器必须重新读取 artifact 并核对大小和哈希。
12. build assessment 通过后删除机器绑定的 `build/`，不要再次构建；对源码与 `artifacts/` 交付物运行 `project_portability.py --export`。交付物不得包含旧 `build/` 或本机绝对依赖。
13. 生成 `TIRTC_PORTING_REPORT.md`，逐项记录 L-1、L0、L1 的 PASS/FAIL/SKIP、完整命令和证据。L2-L7 必须记为 SKIP，不得把编译通过描述成已有实机图像、声音、网络连接或稳定性证据。

报告必须包含“根因归属”章节：
- 必要硬件事实不在允许资料中：归类为“板卡资料不足”，列出缺失事实和所需官方证据。
- 资料充分但 Skill 没有读取、校验或正确生成：归类为“Skill 缺陷”。
- 要求存在歧义、冲突或错误约束：归类为“提示词缺陷”。
- 只是缺少串口、设备、账号或实机运行证据：归类为“本轮 L2-L7 未执行”，不得错误归责给前三者。
- 每项结论必须附具体文件、页码、URL、源码位置或命令结果，不能只给主观判断。

即使构建失败，也不要引用历史工程修复。保留失败现场，报告最小阻塞点及下一步所需证据。
