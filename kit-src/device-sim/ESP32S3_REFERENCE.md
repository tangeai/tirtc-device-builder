# ESP32-S3 设备参考实现需求基线

这份文档定义 ESP32-S3 独立移植工程的需求和架构基线。该工程借鉴 Linux `device-sim-c` 的协议顺序和会话设计，但不属于 `device-sim-c`，也不共用其构建系统或平台代码。ESP32-S3 的实现和验证结论不能用于描述 Linux C 参考实现。

## 1. 目标与范围

- 首个目标平台：ESP32-S3，推荐 16 MB Flash、8 MB PSRAM；默认 Demo 不依赖 TF 卡。
- 可扩展平台：ESP32-P4、其他 ESP-IDF 芯片、ARM/MIPS 嵌入式 Linux、君正 S10 等。
- 功能：H5 实时音频、AI 对讲、VoIP、设备互呼。
- ESP32-S3 从 Flash 媒体分区读取小型编码文件并循环发送，不在设备上转码。
- 不保存收到的音频。无喇叭时只输出限频帧日志；产品可接入播放模块。

## 2. 设备级媒体配置

一台设备只使用一份媒体配置，所有业务共享，不为每个业务或每个方向配置不同编码。

### 音频

- 默认：G.711 A-law（`alaw`）、8 kHz、单声道、40 ms/包。

### 视频

- ESP32-S3 不支持视频。
- `video.file` 为空，`uplink_enabled` 和 `downlink_enabled` 固定为 `false`。
- Flash 不打包视频素材，运行时不创建视频发送任务，也不订阅下行视频。

## 3. 各业务的媒体方向

| 业务 | 媒体 |
|---|---|
| H5 实时 | 双向音频 |
| AI 对讲 | 双向音频 |
| VoIP | 双向音频 |
| 设备互呼 | 双向音频 |

## 4. Flash 媒体与下行处理

参考 Demo 不依赖 TF 卡。小型测试素材制作成独立 Flash 文件系统镜像：

```text
/media/
├── media_profile.json
└── number.alaw_8khz
```

`media_profile.json` 是设备实际采用的唯一媒体配置，文件名用于让开发者直观看懂素材内容。
程序不通过解析文件名推断媒体参数，而是读取配置并校验素材：

```json
{
  "audio": {
    "file": "number.alaw_8khz",
    "codec": "alaw",
    "sample_rate_hz": 8000,
    "channels": 1,
    "packet_ms": 40,
    "duration_ms": 21840,
    "packet_count": 546
  },
  "video": {
    "file": "",
    "codec": "mjpeg",
    "width": 0,
    "height": 0,
    "camera_rotation": 0,
    "aspect_ratio": 1.3333333333,
    "hor_mirror": false,
    "vert_mirror": false,
    "fps": 0,
    "duration_ms": 0,
    "frame_count": 0,
    "uplink_enabled": false,
    "downlink_enabled": false
  }
}
```

字段说明：

| 字段 | 含义 |
|------|------|
| `audio.file` | Flash 媒体分区中的音频文件名，不允许包含目录 |
| `audio.codec` | 文件编码；默认 `alaw`，解析器兼容同义值 `g711a`，还支持 `amr-nb`、`amr-wb` 和 `opus` |
| `audio.sample_rate_hz`、`audio.channels` | 采样率和声道数；当前 TiRTC 适配要求单声道，采样率为 8 kHz 或 16 kHz |
| `audio.packet_ms` | 每个上行音频包覆盖的时长，单位毫秒 |
| `audio.duration_ms`、`audio.packet_count` | 整个素材的时长和包数；启动时和文件大小交叉校验 |
| `video.file`、`video.codec` | 视频素材文件名和编码；ESP32-S3 纯音频基线保留字段但不加载视频文件 |
| `video.width`、`video.height`、`video.fps` | 视频尺寸和帧率；纯音频基线固定为 `0` |
| `video.camera_rotation`、`video.aspect_ratio`、`video.hor_mirror`、`video.vert_mirror` | 设备上报给小程序的视频显示参数；纯音频基线使用默认值 |
| `video.down_video_rotation` | 可选的微信下行视频编码方向：`0` 不上传，`1` 输出正向画面，`2` 保留旋转画面；缺省为 `0` |
| `video.duration_ms`、`video.frame_count` | 视频素材时长和帧数；纯音频基线固定为 `0` |
| `video.uplink_enabled`、`video.downlink_enabled` | 是否启用设备视频上行和下行；ESP32-S3 目标必须同时为 `false` |

仓库中的可烧录配置见
[`media/media_profile.json`](device-sim-esp32/media/media_profile.json)，解析和目标能力校验见
[`media_runtime.c`](device-sim-esp32/components/media_runtime/src/media_runtime.c)。

- 音频素材到结尾后循环发送。
- 启动时校验配置与素材：文件必须存在，A-law 文件大小和音频包数必须与配置一致。
- `alaw` 使用 `number.alaw_8khz`，为 8 kHz 单声道、40 ms/包，共 174,720 字节、
  546 包、21.84 秒。
- `alaw` 8 kHz、40 ms 每包 320 字节。
- 收到音频时，有喇叭的产品投递到音频解码/播放任务；无喇叭时只记录帧元数据。
- 默认参考实现不保存下行音频。
- TiRTC 回调不得打印原始 payload，也不得每帧同步打印；只打印首批帧和周期统计。

## 5. Wi-Fi 配置

无 TF 卡的默认 Demo 使用串口或 SoftAP 网页首次配置 Wi-Fi，并保存到 NVS。

处理规则：

1. 启动时优先读取 NVS 中最后一次成功配置。
2. 没有配置时进入 SoftAP 配网页；已存网络连续 5 次失败后在继续重试（1/2/4/8/15/30 s 退避）的同时开启配网页，便于换网。
3. 配网页提供附近 Wi-Fi 扫描列表（`/api/scan`、`/api/networks`）与已保存网络历史，支持免密复用（`use_saved`）和手动输入；只接受 SoftAP 本地连接，写入请求校验 `Origin`。
4. 新配置连接成功后写入 NVS（版本化单键记录），成功联网写入网络历史；`wifi-change` 保留凭证重新打开配网页，`wifi-clear` 清除配置与历史。
5. 修改配置不需要改代码或重新编译固件。

Demo 可使用明文配置；正式产品应增加 NVS 加密或安全注入方案。

## 6. AI、呼叫和交互

### AI 对讲

- AI 使用按住保持会话（PTT）的交互。
- 按下：建立 AI 会话并持续发送音频。
- 松开：停止媒体、发送结束会话、断开连接，回到空闲态并等待 H5 重连。
- 文件模拟期间，音频文件按时间戳连续循环发送，直到松开。

### VoIP 与设备互呼

两种呼叫均支持：发起、主叫取消、接听、拒接、挂断、忙线、超时和异常断开。

- `cancel`：主叫尚未接通时取消。
- `reject`：被叫振铃时拒接。
- `hangup`：已经接通后结束。
- 无屏设备默认呼叫第一个联系人；无屏不等于只能使用 AI。

### 基础交互

串口命令是所有开发板必须支持的基础交互：

```text
status
ai-press
ai-release
voip-call
contacts
call
cancel
accept
reject
hangup
wifi-set <ssid> <password>
wifi-clear                                       # 清除 Wi-Fi 配置与历史
wifi-change                                      # 保留凭证，断开并重新打开配网页
tirtc-set <device_id> <device_key> [client_id]  # 仅预烧/联调
tirtc-clear                                     # 清除后重新验证码绑定
bind-retry                                      # 绑定失败/超时后无需重启的重试
```

产品可增加三键、LCD、LED、提示音或本地网页。GPIO 只在板级配置中定义，业务代码只接收抽象动作。

ESP32-S3 固件不设置 `TIRTC_OPT_SERVICE_ENDPOINT`，TiRTC SDK 使用内置默认入口；
`tirtc-srv` 仍由服务发现返回，但该字段供支持自定义入口的其他客户端使用。

## 7. 会话模型

单一 SessionManager 任务拥有所有会话状态，MQTT、TiRTC、按键、串口和定时器只向它投递事件。
TiRTC SDK 是进程级常驻资源。网络和凭证就绪后执行一次 `TiRtcInit`/`TiRtcStart`，H5、AI、VoIP
和设备互呼共用同一回调表。业务切换时只建立或断开对应的 TiRTC 连接，不通过
`TiRtcStop`/`TiRtcUninit` 更换业务。

只有启动提交失败时，才清理未成功启动的实例并重试。正常业务生命周期内不反复初始化和反初始化 SDK。

```text
OFFLINE
IDLE
H5_STREAMING
AI_CONNECTING
AI_ACTIVE
RINGING
CALLING
IN_CALL
RESTORING_H5
```

- 前台通话优先级高于振铃、AI 和 H5。
- VoIP 与设备互呼同级；已有通话时新来电返回忙线。
- AI 或已有通话占用媒体链路时，新来电按忙线处理；振铃态由用户决定接听或拒接。
- 前台会话结束后释放对应媒体链路，回到空闲态并接受 H5 重连。
- TiRTC 连接和业务会话分别使用 generation id。媒体源在换连接时从素材起点重新发送；迟到的
  连接结果、命令和 HTTP 响应必须按 generation 丢弃，不能作用于后续会话。
- `RINGING` 只表示业务信令已到达，不能因任意 TiRTC 入站连接直接进入 `IN_CALL`；接听后必须经过
  对应 P2P/WHIP 建连及业务确认。

## 8. 代码边界

```text
device-sim/
├── common/                 # 纯 C 公共模型、状态机、媒体读取和命令解析
├── device-sim-c/           # Linux 应用与 POSIX 适配
├── device-sim-esp32/       # ESP-IDF 应用与 FreeRTOS/Flash/NVS/Wi-Fi/HTTP/MQTT 适配
├── sdk/                    # 按平台和版本存放 TiRTC SDK
└── assets/                 # 测试媒体
```

公共代码不得直接依赖 pthread、FreeRTOS、POSIX、FatFS、ESP-IDF 或 TiRTC SDK 类型。TiRTC 公开类型只允许出现在
`tirtc_adapter` 内。Linux 与 ESP-IDF 的任务、锁、时钟、网络、存储和硬件驱动分别实现平台接口。

## 9. SDK 与构建

ESP32-S3 SDK 默认位置：

```text
sdk/espressif-esp32s3/2.5.0/
├── include/tirtc/
├── lib/libTiRTC.a
└── manifest/build-contract.env
```

SDK 路径必须可以通过 `TIRTC_SDK_DIR` 或构建参数覆盖，不把库复制到应用组件中。2.5.0 包要求 ESP-IDF
5.5.x、`CONFIG_FREERTOS_HZ=1000`，并关闭 FreeRTOS trace/stats 相关配置。旧工程中的 UNICORE 是旧版 SDK
问题的规避项，新 SDK 不直接继承，需通过双核实机压力测试决定。

嵌入式 Linux 使用目标 CPU/ABI/libc 匹配的 TiRTC SDK、交叉工具链和 sysroot；原有 x86_64 二进制不能复制到
ARM/MIPS 设备执行。

ESP32-S3 业务信令沿用 `device-sim-c` 的服务发现、HMAC-SHA256 设备登录、业务 HTTP、永久 MQTT、
ACK 和心跳协议；`platform_client` 负责这些平台通信，`tirtc_adapter` 只负责媒体连接、命令和帧。
首次启动沿用 `device-sim-c` 的验证码绑定：设备上报 MAC，显示验证码，通过临时 MQTT 等待
`auth_grant`，ACK 后将 `device_id/device_key` 保存到 NVS。后续启动直接读取凭证；收到解绑
通知或登录返回 6006 时保留本地身份，先核对服务端绑定状态，确认后用旧密钥签名重绑，
重绑返回的身份与本地不一致时拒绝写入。

## 10. 验证范围与产品扩展

参考工程提供以下内容：

- ESP-IDF 工程、SDK 外部链接和构建契约验证。
- 公共设备配置、媒体读取和 SessionManager。
- Flash 媒体、NVS Wi-Fi、串口和 SoftAP 配置。
- `alaw` 文件源、校验和定时发送。
- 验证码绑定、凭证 NVS 持久化、解绑重绑和正式平台登录。
- H5、AI、VoIP、设备互呼和平台信令参考代码。

账号与音频链路仍需在 ESP32-S3 实机上联调。产品还需要接入真实 I2S、物理按键和扬声器播放模块。
