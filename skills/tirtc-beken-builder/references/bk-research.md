# BK7258/BK7259 硬件能力探测调研

> 调研日期：2026-09-25
> 范围：Beken 官方文档与官方 GitHub 源码；重点核对可运行的硬件探测能力，而不是仅复述开发板文档。

## 结论摘要

可以为本工程做一个与 ESP32 builder skill 对等的 BK skill，但应把“硬件诊断”定义成**板级清单约束下的主动探测与功能自检**，而不是承诺从一份完全未知的 BK7258/BK7259 PCB 上无条件枚举所有器件。

最可靠的实现是四层证据：

1. **E3：主动识别**——读取 Flash JEDEC ID、触控芯片 product ID、可读回的 LCD/codec ID；
2. **E2：主动功能自检**——内存压力/读写测试、LCD test pattern、麦克风录音统计、扬声器到麦克风的声学回环、全双工与 AEC 评估；
3. **E1：固件/BSP 声明**——已编译进固件的 panel、GPIO、I2C 地址、音频通路与分辨率；
4. **E0：文档声明**——原理图、BOM、开发板说明，仅作为候选输入。

最终 capability manifest 必须逐字段记录 `value`、`evidence_level`、`probe`、`raw`、`confidence` 和 `reason`。业务功能只能消费 E2/E3，或显式允许降级到 E1；E0 不应直接打开“小钛”的 UI、音视频或 AEC 功能。

## SDK 基线与 BK7259 资料边界

Beken 官方 `bk_idk` README 要求使用 release 分支/tag，而不是随意跟随开发分支；公开的 `bk_idk release/v2.0.1` 明确列出 BK7258。[官方 README（固定提交）](https://github.com/bekencorp/bk_idk/blob/650e754e12fe1e43c37ce2316a973668b033fd48/README.md)

本次直接核对了：

- BK7258：`bk_avdk_smp release/v3.1.1`，提交 `993df5647f084551a677a2bc741b200cfd75d5f2`；
- BK7259：`bk_avdk_smp release/v4.0.1`，提交 `584b947920c414230f9909375f008e7d6a2c6c6b`，该提交包含 `bk7259_ap` SoC/BSP、BK7259 音频库、显示与触控实现，可作为公开可复现基线。[BK7259 defconfig](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/middleware/soc/bk7259_ap/bk7259_ap.defconfig) [BK7259 音频能力头](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/include/soc/bk7259/aud_cap.h)

因此建议 skill 把 SDK baseline 固定为 tag/commit，并为 BK7258 v3.1.1 与 BK7259 v4.0.1 分设 adapter。不要假定两个版本的目录和显示 API 完全相同：v4 已把 panel 注册进一步改为 linker-section 模式。

## 已确认的可探测能力

### Flash：可读 JEDEC ID，但容量是“ID 查表结果”

官方 API 暴露 `bk_flash_get_id()` 和 `bk_flash_get_current_total_size()`。[BK7258 API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/flash.h#L62-L68) [BK7259/v4 API](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/include/driver/flash.h#L62-L68)

驱动初始化实际读取 Flash ID，再在静态 `flash_config[]` 中匹配容量；若未识别，会打印错误并选默认配置。因此 `total_size` 不能脱离 `id_known` 使用。[BK7258 ID/容量表与 fallback](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/middleware/driver/flash/flash_driver.c#L69-L79) [BK7258 匹配逻辑](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/middleware/driver/flash/flash_driver.c#L232-L249) [BK7258 size getter](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/middleware/driver/flash/flash_driver.c#L1005-L1013)；v4 也保留相同公共接口，并提供 CLI 同时打印 ID 与总容量。[BK7259/v4 CLI](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/middleware/driver/flash/cli_flash_api.c#L64-L76)

建议探针：输出 `jedec_id`、`recognized`、`mapped_size`、分区表最大结束地址，并检查 `mapped_size >= partition_end`。不要做破坏性“写到容量边界”试探；仅在专用 scratch 分区执行擦写校验。

### SRAM/PSRAM：区分物理/映射容量与可用 heap

官方 RTOS API 可查询 internal heap 和 PSRAM heap 的 total/free/minimum-ever-free；官方 `memshow` CLI 正是这样实现。[API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/os/os.h#L1171-L1208) [CLI 实现](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_cli/cli_mem.c#L25-L40) [FreeRTOS SMP 实现](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_rtos/freertos/v10/rtos_pub_smp.c#L1496-L1524)

这些数值是**分配器管理区**，不是完整芯片 SRAM 物理容量。manifest 应分别报告 `internal_heap_total/free/min_ever`、`psram_heap_total/free/min_ever`，并从 linker/ram regions 记录 `declared_sram_regions`（E1），不可混成一个“内存大小”。

BK7258 IDK 的 PSRAM 驱动会读取实际 PSRAM ID，`actual_id == 0` 时初始化失败，并可缓存识别结果；这是 presence probe 的依据，但它不是公开的“返回容量”API。[PSRAM 自动识别实现](https://github.com/bekencorp/bk_idk/blob/650e754e12fe1e43c37ce2316a973668b033fd48/middleware/driver/psram/psram_driver.c#L161-L202) [PSRAM init/actual ID](https://github.com/bekencorp/bk_idk/blob/650e754e12fe1e43c37ce2316a973668b033fd48/middleware/driver/psram/psram_driver.c#L205-L253)

建议在 `bk_psram_init()` 成功后做非破坏性的 walking-bit、地址别名和分块压力测试，测试范围只限 SDK 已映射/分配的 PSRAM。容量以 `psram_heap_total + reserved_regions` 的构建清单为 E1，读写与无别名结果为 E2；不要越界扫描总线。

### 触控：官方已有真正的自动识别链路

`bk_tp_driver_init()` 的文档明确说明会自动探测触控传感器，成功后 `bk_tp_get_device()` 返回当前设备。[BK7258 API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/tp.h#L43-L55) [当前设备 API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/tp.h#L81-L90)

实现会遍历 linker-section 中注册的 detect 函数（或兼容设备表），逐一执行探测。[BK7258 探测循环](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/middleware/driver/tp/tp_driver.c#L83-L105) 注册宏也明确说明是为了自动发现探测函数。[注册宏](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/tp_types.h#L179-L195)

以 GT911 为例，探针通过 I2C 读取 product ID 并比对，再返回包含默认分辨率、触点数和读取函数的描述符。[GT911 product-ID 探测](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_peripheral/src/tp/tp_gt911.c#L121-L145) [GT911 描述符](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_peripheral/src/tp/tp_gt911.c#L604-L631)。BK7259/v4 同样保留该模式，并增加更多 controller。[v4 TP 驱动](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/components/bk_peripheral/src/tp/tp_driver.c#L78-L108)

这可直接形成 E3：`touch.present=true` 只在 product ID 匹配后成立；再采集若干真实触点事件形成 E2。注意 SoC 自带 capacitive-touch channel 与 LCD 上的 I2C touch controller 是两类硬件，不应混淆。

### LCD：BK7258 多为清单选择，BK7259 v4 的 MIPI 支持读 ID

BK7258 v3.1.1 将 Kconfig 选中的 `lcd_device_t` 放入数组并调用 `bk_lcd_set_devices_list()`；描述符内的 width/height 是驱动声明值。[设备表](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_peripheral/src/lcd/lcd_panel_devices.c#L20-L145) [LCD 选择 API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/lcd.h#L35-L50) [GC9D01 160×160 描述符](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_peripheral/src/lcd/spi/lcd_spi_gc9d01.c#L81-L91)

所以对 BK7258，`get_lcd_device_by_id/name/ppi()` 只是从已编译列表取元数据，不等于发现了物理面板。[查询 API](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/driver/lcd.h#L319-L347) QSPI 驱动虽支持读寄存器，但必须已知候选面板的命令和 dummy-cycle；RGB panel 通常没有读回通道。[QSPI read API 实现](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/middleware/driver/lcd/lcd_qspi_driver.c#L249-L268)

BK7259/v4 的 MIPI panel 描述符已经包含 `read_id_regs/read_id_bytes`，官方接入说明要求 `bk_lcd_panel_read_id()` 与 `panel.id` 一致，可作为 E3。[官方 MIPI panel 接入说明](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/components/bk_peripheral/src/lcd/how_to_add_mipi_panel.md#L576-L588) [实际 1024×600 panel 的 ID 寄存器配置](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/components/bk_peripheral/src/lcd/dsi/lcd_mipi_ek79007ad_1024x600.c#L71-L90)

建议流程：先由 board profile 限定 bus/pins/reset/候选 panel；对支持读 ID 的 SPI/QSPI/DSI panel 逐个以低速、安全 reset 时序读 ID；匹配后才采用驱动声明的像素 width/height，并显示 RGB/棋盘/渐变测试图做 E2。裸 RGB panel 无可靠 ID 时只能是 E1+E2。“屏幕大小”应拆成 `pixel_width/height` 与 `physical_mm/diagonal`；后者在无 EDID/EEPROM 时程序无法推导，必须来自板级清单。

### 麦克风、喇叭和音频格式：初始化成功不等于器件存在

官方高层录音/播放配置都显式包含 `nChans`、`sampRate`、`bitsPerSample`；默认是 mono/8 kHz/16 bit。[record config](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/audio_record/include/audio_record.h#L44-L65) [play config](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/audio_play/include/audio_play.h#L49-L70)

板载实现把 mono/stereo 映射到 ADC/DAC L/LR，并把采样率传给 `bk_aud_adc_init()` / `bk_aud_dac_init()`。[麦克风 ADC 配置](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/audio_record/src/onboard_mic_record.c#L519-L554) [喇叭 DAC 配置](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/audio_play/src/onboard_speaker_play.c#L499-L534) I2S 控制器支持的格式集合还包括 8/16/24/32 bit 和多档采样率，但这只是控制器能力，不代表板上 codec/transducer 支持。[I2S 类型](https://github.com/bekencorp/bk_idk/blob/650e754e12fe1e43c37ce2316a973668b033fd48/include/driver/i2s_types.h#L159-L180)

因此音频探测必须分三步：

1. profile 指定 internal ADC/DAC、DMIC、I2S codec 或 UAC 的候选通路；外部 codec 若有 I2C ID/状态寄存器先做 E3；
2. 对白名单格式逐项 open + DMA，录制 0.5~2 秒并计算 DC、RMS、峰值、饱和率、非零率和噪声底，排除全 0/固定码/浮空噪声；
3. 低音量播放 chirp/PRBS，同时录音做互相关，只有检测到已知延迟与足够 SNR 才把 speaker+mic+full-duplex 记为 E2。没有麦克风、回采 ADC、功放 fault/status 或人工确认时，程序不能独立证明“有喇叭”。

`bitsPerSample` 在上述高层实现中主要保存在配置，底层 DMA 对 mono/stereo 固定使用 16/32-bit 搬运；因此不能仅以 create/open 成功宣布任意 bit depth 可用，必须把格式 sweep 的实际数据结果写入 manifest。

### AEC：属于业务就绪验证，不是静态硬件规格

官方 AEC 支持 hardware mode（ADC L 为 mic、R 为 speaker reference）与 software mode（mic 走 ADC，播放数据写入 reference ringbuffer），且该版本 AEC 采样率限定为 8 kHz 或 16 kHz。[AEC 模式与配置](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/include/components/bk_audio/audio_algorithms/aec_algorithm.h#L27-L100)

实现按 20 ms、16-bit frame 工作，hardware mode 拆分 L/R，software mode 从第二输入取 reference，然后调用 `aec_proc(ref, mic, out)`。[AEC 数据路径](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_audio/audio_algorithms/aec_algorithm/aec_algorithm.c#L259-L313) [frame 约束](https://github.com/bekencorp/bk_avdk_smp/blob/993df5647f084551a677a2bc741b200cfd75d5f2/ap/components/bk_audio/audio_algorithms/aec_algorithm/aec_algorithm.c#L350-L383) BK7259/v4 仍明确标注 8/16 kHz，并提供 AEC v3 adapter。[v4 AEC v3 header](https://github.com/bekencorp/bk_avdk_smp/blob/584b947920c414230f9909375f008e7d6a2c6c6b/ap/include/components/bk_audio/audio_algorithms/aec_v3_algorithm.h#L76-L116)

skill 应用 far-end chirp 做双工录制，比较 AEC 前后 ERLE、残余回声与 near-end 语音失真；仅“库可链接/初始化成功”是 E1，实际达到阈值才是 `aec.ready=true`（E2）。delay、ref scale、音量和结构声学都依赖具体机壳，不能跨板复用一个常量。

## 建议的诊断程序与 skill 工作流

诊断固件建议提供 JSONL 串口协议：

```text
probe identity
probe flash
probe memory --stress=bounded
probe display --profile=<id> --pattern
probe touch --profile=<id> --events=5s
probe audio-capture --matrix=safe
probe audio-loopback --volume=-30dbfs
probe duplex-aec --seconds=10
report --json
```

skill 流程：识别 SDK/tag 与 target → 导入/生成 board profile → 构建最小 probe firmware → 烧录并采集串口 JSONL → 必要时做一次人工观察（屏幕颜色、是否听到声音、触摸五点）→ 生成 `hardware-capabilities.json` → 由 capability gate 选择“小钛”组件并构建业务固件 → 运行 HIL smoke/长稳测试。

业务 gate 建议：

- 无 display：纯语音/指示灯模式；
- display E2、touch 不存在：只允许被动状态 UI，交互改为明确存在的按键/语音，不自动假设按键合适；
- touch E3+事件 E2：启用点击 UI，并校验触控坐标与 panel 旋转；
- mic E2：才启用唤醒/ASR；speaker E2：才启用 TTS/提示音；
- full-duplex 与 AEC E2：才启用免提 RTC；只有产品合同明确允许时才可提供
  半双工 push-to-talk，不能用它把“小钛”AI/呼叫能力判为通过；
- PSRAM/heap 不足：关闭高分辨率 framebuffer、摄像头、多路音频缓存或本地 AI，并给出具体预算差额。

## 风险与安全边界

- 总线盲扫可能误写寄存器、触发 reset 或与其他器件冲突；只读已知 ID 寄存器，并由 profile 限定 bus/address/pins。
- 显示器 reset/init、背光和电源 rail 有顺序要求；未知板不得穷举 GPIO。
- 声学探测必须限制音量、时长和频段，默认先静音初始化，再渐升；结果允许 `unknown`，不能把“没有检测到”一律解释成“没有硬件”。
- Flash/PSRAM 测试不得覆盖固件、校准、OTA、密钥或用户分区；写测试仅限显式 scratch 区域。
- 报告必须保留原始 ID、返回码、测试矩阵和 SDK commit，便于“文档声明 vs 程序实测”追溯。

## 推荐落地顺序

1. 首版支持两条固定基线：BK7258 `v3.1.1.x`、BK7259 `v4.0.1.x`；
2. 先实现 Flash/heap/PSRAM/touch 与 manifest，因这些已有明确官方 API；
3. 再实现 profile 驱动的 LCD ID/readback + test pattern；
4. 实现 audio format sweep、录音统计与安全声学回环；
5. 最后将 AEC、RTC、“小钛”UI/语音能力接到统一 capability gate；
6. 每新增一块开发板，沉淀 profile、原始探测报告、通过阈值和已验证 SDK commit，而不是仅增加一页板卡文档。
