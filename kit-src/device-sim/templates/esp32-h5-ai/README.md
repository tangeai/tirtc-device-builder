# @PROJECT_NAME@

这是一个面向 ESP32-S3 N16R8 的 ThingConnect 起步工程，使用 ESP-IDF 5.5.x 和 TiRTC SDK 2.5.0。工程只保留三条基础路径：设备配网/绑定上线、H5 实时画面与双向语音、AI 对讲。

模板不内置媒体文件，也不自动生成音视频帧。没有接入板级媒体适配器时，工程可以完成配网、绑定、MQTT、TiRTC、H5 和 AI 会话流程，但不会向 H5/AI 发送媒体，也不会从物理扬声器或屏幕输出收到的媒体。

`platform-media-contract.json` 固定平台/Web 支持的 stream、媒体类型和发送边界；
板级 `board-video-contract.json` 必须从其中选择一个视频 profile。平台支持某种编码
不等于开发板能生成该编码。

## 构建和烧录

准备 ESP-IDF 5.5.x 环境后执行：

```bash
idf.py set-target esp32s3
idf.py build
idf.py -p <SERIAL_PORT> flash monitor
```

工程默认使用 16 MB Flash、8 MB Octal PSRAM 和 USB Serial/JTAG 控制台。其他硬件规格需要同步调整 `sdkconfig.defaults`、`partitions.csv` 和板级驱动。

## 首次启动

1. 设备没有 Wi-Fi 配置时启动 `TiRTC-XXXX` 开放 SoftAP，无需密码。设备通过通配 DNS 和 HTTP 重定向响应 Android、iOS、Windows 等客户端的 captive portal 探测，连接后通常会自动显示配网页面；没有弹窗时打开 `http://192.168.6.1`。HTTPS 页面不能被透明重定向。
2. 设备联网后在串口打印绑定验证码和体验平台地址。
3. 在 H5 完成设备绑定。凭证保存到 NVS，设备随后完成服务发现、MQTT 登录和 TiRTC 启动。
4. 串口输入 `status` 查看平台、MQTT、TiRTC、会话和媒体计数。

也可以使用以下联调命令预置或清理配置：

```text
wifi-set <ssid> <password>
wifi-clear
tirtc-set <device_id> <device_secret> [client_id]
tirtc-clear
restart
```

`tirtc-set` 只用于受控联调环境。不要在日志、脚本或版本库中保存真实设备密钥。

## H5 画面与对讲

设备处于 `waiting` 时接受一个 H5 连接。接入板级媒体适配器后：

- 音频上行使用 stream `10`，格式为 G.711 A-law、8 kHz、单声道；
- 视频上行使用 stream `11`；平台/Web 支持 MJPEG、H.264、H.265，本工程必须
  根据板级合同固定选择一种。MJPEG 每次发送完整 JPEG，H.264/H.265 每次发送
  完整 Annex-B access unit；
- H5 下行语音使用 stream `14`，SDK 回调复制到固定队列后由媒体任务消费；
- H5 请求关键帧时，`starter_media_request_key_frame()` 通知产品编码器产生 IDR。

默认接收任务把下行语音安全地移出 SDK 回调后丢弃。接入扬声器的 TODO 位于 `components/starter_media/src/starter_media.c`；接入视频显示的 TODO 位于 `components/starter_tirtc/src/starter_tirtc.c`。

## AI 对讲

串口执行：

```text
ai-start
ai-stop
```

`ai-start` 依次完成 AI token 请求、WHIP 建连和 `start_session`。只有服务端确认 `start_session` 后，运行时才允许板级媒体适配器发送音频。AI 返回的 stream `1` 音频进入与 H5 对讲相同的下行队列。`ai-stop` 发送 `end_session`、停止媒体并重新等待 H5 连接。

## 代码边界

```text
main/                         组合根、首次绑定和启动顺序
components/starter_runtime/   H5/AI 单一会话状态任务
components/starter_tirtc/     TiRTC SDK 类型和回调适配
components/starter_media/     空媒体适配器与板级媒体 seam
components/starter_console/   最小串口命令
components/platform_client/   服务发现、设备 HTTP/MQTT
components/wifi_manager/      Wi-Fi 与 SoftAP 配置
components/runtime_config/    NVS 设备凭证
third_party/tirtc/             TiRTC SDK 2.5.0
```

会话状态只在 `starter_runtime` 任务中改变。TiRTC 回调只投递有长度上限的事件或把音频复制到固定队列；回调中不执行 HTTP、阻塞等待、SDK Stop 或 Uninit。

## 建议阅读顺序

代码中的模块头部和公开头文件说明了职责、调用顺序、线程归属和数据生命周期。首次接入建议按以下顺序阅读：

1. `main/app_main.c`：查看启动、绑定和模块组装顺序；
2. `components/starter_media/include/starter_media.h`：先了解产品媒体接入契约；
3. `components/starter_media/src/starter_media.c`：实现采集、播放和关键帧 TODO；
4. `components/starter_runtime/include/starter_runtime.h`：了解产品控制入口和公开状态；
5. `components/starter_runtime/src/starter_runtime.c`：需要排查会话问题时再阅读状态机；
6. `components/starter_tirtc/`：只在核对 SDK stream、回调或连接生命周期时阅读。

`platform_client`、`wifi_manager` 和 `runtime_config` 隐藏平台接入细节。普通板级音视频移植不需要修改这些模块。

## 产品化 TODO

代码中的 `TODO(product-...)` 是预留的产品适配点：

- `TODO(product-media-capture)`：启动/停止麦克风、摄像头和编码任务，并提交 G.711A 与板级合同选定的视频帧；
- `TODO(product-media-keyframe)`：把 H5 关键帧请求转成编码器 IDR 请求；
- `TODO(product-media-playback)`：把下行 A-law 解码成 PCM 并写入 I2S 扬声器；
- `TODO(product-media-display)`：有屏设备增加非阻塞视频接收、解码和显示适配；
- `TODO(product-control)`：把实体按键的按下/松开映射到 AI 开始/停止；
- `TODO(product-security)`：使用加密 NVS 或安全芯片保护设备凭证。

可以随时执行以下命令检查未完成的产品适配点：

```bash
rg -n 'TODO\(product-' main components
```

这些 TODO 都位于板级媒体、控制和凭证边界。接入真实硬件时不需要改动 H5/AI 协议状态机。

## 验收顺序

1. `idf.py build` 成功，启动日志显示 TiRTC SDK 版本与 build info。
2. 首次配网和验证码绑定成功，`status` 显示 platform、MQTT、TiRTC 就绪。
3. 未接媒体适配器时，H5 连接可以建立，但发送计数保持为零。
4. 接入摄像头和麦克风后，H5 持续显示视频，音频/视频发送计数增长，下行语音接收计数增长。
5. 执行 `ai-start` 后状态从 `ai-connecting` 进入 `ai-active`；接入麦克风和扬声器后音频计数增长。
6. 执行 `ai-stop` 后状态回到 `waiting`，H5 可以重新连接。

这是协议接入模板，不是量产固件。产品还需要完成硬件驱动、弱网策略、看门狗、凭证保护、长期稳定性和实机音视频验收。
