# device-sim-esp32

ESP32-S3 TiRTC 设备参考实现，目标硬件为 ESP32-S3 N16R8（16 MB Flash、8 MB
octal PSRAM），使用 ESP-IDF 5.5.x 和 TiRTC SDK 2.5.0。默认 Demo 不依赖 TF 卡，
H5 实时、AI 对讲、VoIP 和设备互呼均为纯音频，不保存下行音频。

这是基于 Linux C 参考实现的协议顺序和会话设计进行的**独立移植**。它不属于 `device-sim-c`，不与后者共用构建系统或平台代码；ESP32-S3 的能力、限制和测试结论不能反向代表 Linux C 参考实现。

只需要设备上线、H5 音视频和 AI 对讲的开发者，使用
[ESP32-S3 工程模板](../ESP32_STARTER.md)生成独立的最小工程。本目录保留完整参考实现，适合查阅全部协议和会话处理。

需求与跨芯片边界见 [ESP32S3_REFERENCE.md](../ESP32S3_REFERENCE.md)。

## 已实现

- TiRTC SDK 外部目录选择和构建契约校验。
- SPIFFS 媒体分区、`media_profile.json`、音频素材启动校验和按 PTS 循环发送。
- TiRTC 上行音频流 ID 为 10；入站连接等待对端订阅，外连等待业务确认后才开始发送。
- `alaw`（G.711 A-law）8 kHz 单声道固定包读取器。
- Wi-Fi NVS 持久化、串口修改、无配置/连接失败时带 captive portal 自动发现的
  SoftAP 配网页面。
- STA 关闭 Wi-Fi 省电模式，避免实时 KCP 音频因休眠产生排队和抖动。
- 首次验证码绑定、临时 MQTT `auth_grant`/ACK、设备凭证 NVS 持久化和解绑重绑。
- 服务发现、SNTP、HMAC-SHA256 设备登录、业务 HTTP、永久 MQTT、ACK 和心跳。
- H5 入站推流、AI PTT、VoIP、设备互呼的统一会话状态和串口交互。
- TiRTC SDK 启动后常驻，四类业务共用同一回调表；业务切换只切换连接，不反复停启 SDK。
- 会话和连接 generation 隔离迟到的连接结果、命令和 HTTP 响应。
- 下行音频不落盘：无喇叭时输出限频元数据日志，并保留产品接入 TODO。
- 纯音频能力由运行时代码强制校验；视频订阅固定拒绝，不打包视频素材，也不创建视频发送任务。

仓库提供主机单元测试和 ESP32-S3 纯音频固件构建验证。真实账号、MQTT 信令及
P2P/WHIP 音频互通仍须在 ESP32-S3 实机和对应服务环境中联调。

## 目录

```text
device-sim-esp32/
├── components/
│   ├── platform_client/   # 服务发现、签名登录、HTTP、MQTT
│   ├── session_runtime/   # H5/AI/VoIP/设备互呼状态与交互
│   ├── media_runtime/     # Flash 素材校验、定时读取和发送
│   ├── tirtc_adapter/     # 唯一允许直接依赖 TiRTC 类型的组件
│   ├── wifi_manager/      # NVS、STA、SoftAP 配网页面
│   ├── runtime_config/    # 设备凭证 NVS
│   └── device_console/    # 串口命令
├── media/                 # 默认纯音频配置和 alaw 素材
└── partitions.csv         # 4 MiB app + 1.5 MiB media
```

平台无关的配置、会话规则和文件拆帧代码位于 `../common/device_core`。

## SDK 位置

默认读取：

```text
../sdk/espressif-esp32s3/2.5.0/
├── include/tirtc/
├── lib/libTiRTC.a
└── manifest/build-contract.env
```

可指定其他 SDK 根目录：

```bash
idf.py -DTIRTC_SDK_DIR=/absolute/path/to/espressif-esp32s3/2.5.0 build
```

## 构建与烧录

默认配置使用 `number.alaw_8khz`：G.711 A-law（`alaw`）8 kHz 单声道数字语音，按 40 ms/包发送。
所有业务均为纯音频：

```bash
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyACM0 flash monitor
```

`flash` 会同时烧录应用和 `media.bin`。默认素材是：

```text
number.alaw_8khz
```

## 首次配置

设备没有 Wi-Fi 配置时会启动：

```text
SSID: TiRTC-XXXX
认证: 开放热点，无需密码
网页: http://192.168.6.1
```

设备通过通配 DNS 和 HTTP 重定向响应 Android、iOS、Windows 等客户端的 captive
portal 探测，连接热点后通常会自动显示配网页面；没有弹窗时手动打开上述 HTTP
地址。HTTPS 页面不能被透明重定向。
网页提交 SSID/密码后写入 NVS 并重启。也可使用串口：

```text
wifi-set "My WiFi" "12345678"
wifi-clear
```

Wi-Fi 连通后，如果 NVS 中没有设备凭证，设备会自动：

1. 上报 Wi-Fi STA MAC，获取验证码和临时 MQTT 凭证。
2. 在串口打印验证码和 [TiRTC 体验平台](https://xiaotai.chat) 地址，等待用户登录后进入设备绑定并输入验证码。
3. 接收临时 MQTT 的 `auth_grant`，发送 QoS1 ACK。
4. 将下发的 `device_id/device_key` 写入 NVS，随后启动正式 MQTT 和 TiRTC。

后续启动会直接读取 NVS，不再要求输入验证码。收到 `unbind` 或登录返回设备已解绑时，会重新进入绑定流程。
设备取得正式 MQTT token 后，会向 device-server 调用
[`POST /v1/device/profile`](../../api-reference.md#post-v1deviceprofile)，在 `profiles.voip`
中上报纯音频工作配置。Web 与微信小程序通过用户设备列表读取这份配置；联系人查询仍由
`GET /v1/voip/device/contacts` 单独完成。

`tirtc-set` 仅作为预烧凭证和底层联调入口，不是正常用户配置步骤；密钥不会打印到日志：

```text
tirtc-set <device_id> <device_key>
tirtc-set <device_id> <device_key> <client_id>
tirtc-clear  # 清除绑定凭证，重启后重新显示验证码
```

平台服务默认通过 `http://ep-open.tangeopen.com/services` 发现。ESP32-S3 不设置
`TIRTC_OPT_SERVICE_ENDPOINT`，TiRTC SDK 使用其内置默认入口。

## 串口交互

默认主控制台使用 ESP32-S3 原生 USB Serial/JTAG，对应 Linux/WSL 中的
`/dev/ttyACM*`。日志输出和 `tirtc>` 命令输入使用同一个端口。

```text
status          查看 Wi-Fi、平台、MQTT、TiRTC、会话和媒体配置
ai-press        模拟按住 AI 键，建连后持续循环发送音频
ai-release      模拟松开 AI 键，结束 AI 会话
voip-call       呼叫第一个授权 VoIP 联系人
contacts        查看设备互呼联系人
call            呼叫第一个设备联系人
accept          接听 VoIP 或设备来电
reject          拒接来电
cancel          取消尚未接通的外呼
hangup          挂断当前会话
restart         重启
```

底层联调命令 `voip-connect <service_description> <token>` 和
`call-direct <remote_device_id> <token>` 可绕过业务信令直接验证 SDK 连接。

串口命令是开发板的基础交互入口。产品使用三键、触摸屏或按键矩阵时，只需把动作映射到
`session_runtime_*()` 接口，无需修改会话业务代码。

## 媒体配置

一台设备只读取一份
[`media_profile.json`](media/media_profile.json)，所有业务共用同一音频配置。各字段含义见
[ESP32-S3 需求基线的媒体配置](../ESP32S3_REFERENCE.md#4-flash-媒体与下行处理)。

- `alaw`：默认素材为 `number.alaw_8khz`，8 kHz 单声道，40 ms 每包 320 字节，
  共 546 包、21.84 秒。
- `video.file` 为空，`uplink_enabled=false`，`downlink_enabled=false`。
- H5 实时、AI 对讲、VoIP、设备互呼都只发送和接收音频。

启动时会校验音频时长、包数和文件内容大小是否一致；校验不通过时不会启动媒体发送。

## 下行接入点

下行回调只统计并限频打印，不写入 Flash：

- 有喇叭：在
  [`tirtc_adapter.c`](components/tirtc_adapter/src/tirtc_adapter.c)
  的 `TODO(product-audio)` 后投递到独立播放任务。

不要在 TiRTC SDK 回调线程中同步解码、播放或逐帧打印。
