# TiRTC ESP32 开发板接入提示词

不用先把所有硬件参数查齐。你只要说明是哪块板、资料放在哪里、想实现什么，以及工程输出到哪里。其余内容由 Skill 从原理图、BSP、Device Kit 和数据手册中提取；确实不知道的地方写“未知”。

## 精简模板

```text
$tirtc-esp32-builder

请为下面这块开发板完成 ThingConnect TiRTC ESP32 接入。

开发板：
- 厂商、完整型号、PCB/硬件版本：<填写>
- 资料与手中实物是否对应：<是/否/未知>

资料：
- <原理图、BSP/厂商示例、数据手册、产品页等本地绝对路径或固定链接；一行一个>

目标：
- <例如：H5 实时视频和声音、H5 语音对讲、AI 双向语音对讲>
- 视频选择：<MJPEG/H264/H265/根据合同和硬件证据选择>
- 双工或 AEC 的硬要求：<无，初版可半双工/必须全双工或 AEC/未知>

接入方式：
- Wi-Fi：<选择一种，或写“根据 BSP 选择”>
- 设备绑定：<选择一种，或写“根据平台合同选择”>

工程：
- 输出目录或现有工程：<绝对路径>

执行要求：
1. 先运行 Device Kit Doctor，读完全部资料，再生成 Hardware IR v2。没有证据的器件、GPIO 和媒体能力保持未知。
2. 把每个未知项标为 source_resolvable、implementation_resolvable、build_resolvable、hil_resolvable 或 user_blocked。先通过资料和固定版本源码解决 source_resolvable；只有 user_blocked 会阻止开始 adapter 开发。
3. READY_TO_PORT 表示硬件身份、连接、媒体合同和资源设计已经有证据，足以开始实现；它不要求最终 ELF 或实机数据。可通过实现或构建解决的项目必须继续生成 compile-safe adapter、锁定依赖、运行门禁并编译。
4. 移植前核对媒体合同、板级资源、静态内存预算、配网和绑定状态。构建后只把源代码、锁定依赖、编译或 post-link 门禁实际证明的事实升级为 build_verified。
5. 记录 BIN/ELF 路径、大小和 SHA-256，运行 build 阶段评估并输出 TIRTC_PORTING_REPORT.md。编译结果必须与 L2-L7 实机验收分开。
6. 本轮不访问串口、不烧录、不擦除 NVS；因此缺少启动、浏览器、实体声音和运行时资源数据时，把相应 L2-L7 标为 SKIP，不得阻止 L0/L1。
7. Wi-Fi 密码、设备密钥、token、私钥和用户音视频不能写入工程或报告。
```

## 只有已知时才补充

这些信息如果手头已有，也可以附上；没有就交给 Skill 查资料：

- 主控/模组完整型号、Flash 和 PSRAM 容量及总线模式；
- BSP 的 commit、tag 或 release，以及已验证的摄像头、录音和播放示例；
- H5/AI 媒体合同链接、选定 profile、stream ID 和帧或 access unit 边界；
- 凭证保存与重配方式、已有绑定处理和独立清除入口；
- 已知资料矛盾、实机 PID、串口日志或已知良好固件 SHA-256；
- 非默认 ESP-IDF、TiRTC SDK、Device Kit、服务发现地址或 HTTP/HTTPS 分阶段要求。
- 若用于 clean-room 验证，明确允许的资料根目录，并列出不得读取的历史工程或旧 artifact。

直接把它们追加在提示词末尾即可，不必逐项填表。
