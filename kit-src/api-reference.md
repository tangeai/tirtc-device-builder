# API Reference

> 面向开发者和二次开发的完整接口文档。业务流程和架构说明见 [ThingConnect 开发者文档](README.md)。

## 快速查找

| 要做什么 | 接口章节 | 操作与接入说明 |
|---|---|---|
| 获取服务地址 | [服务发现](#服务发现) | [设备上线](device-integration.md) |
| 设备上线、获取凭证、上报能力 | [device-server](#device-server) | [设备上线](device-integration.md) |
| 注册登录、绑定设备、用户配置 | [user-server](#user-server) | [开发者文档](README.md) |
| 查询官网开发板及固件资源 | [user-server](#user-server) | 官网 `/boards` 页面 |
| 微信 VoIP 呼叫与授权 | [voip-server](#voip-server) | [微信 VoIP](device-voip.md) |
| AI 对话、角色与知识库 | [ai-server](#ai-server) | [AI 接入](device-ai.md) |
| 设备互呼、联系人管理 | [call-server](#call-server) | [设备互呼](device-call.md) |
| 创建对讲房间、加入和续租 | [多人对讲](#多人对讲call-server) | [多人对讲接入](device-room.md) |
| 判断请求是否成功 | [响应约定](#约定)、[错误码汇总](#错误码汇总) | [错误响应规范](error-response-policy.md) |

“调用方”标明接口的接入用途：设备包括开发板和模拟器，Web 包括 H5 页面，小程序指微信小程序原生页面。共用接口列出多个调用方；小程序内嵌 Web 页面使用对应的 Web 接口。调用方标记不代替鉴权，仍须使用各接口指定的凭证。

接口列表中的 JWT 均通过 `Authorization: Bearer <token>` 传入；HMAC 使用签名请求头，内部密钥使用 `X-Internal-Key`。具体字段见[鉴权方式](#鉴权方式)及各接口详情。无需登录的接口仍可能要求邮箱验证码或人机验证。

Admin 接口见 [Admin API](admin/admin-server/API.md)。标记为内部服务的接口仅供服务间调用，不应暴露到公网。

<a id="service-discovery"></a>

## 服务发现

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [获取服务地址](#get-services) | 设备、Web、小程序 | GET | `/services` | 无需登录鉴权 |

<a id="get-services"></a>

### 获取服务地址

**接口**：`GET /services`

**调用方**：设备、Web、小程序。

**请求参数**：无。

设备启动时通过该接口获取各业务服务和 TiRTC 的入口地址，无需鉴权。自托管环境需要在 user-server 中启用 `discovery.enabled`，并配置设备可访问的公网地址。

向 `fetch_services()` 传入入口根地址后，Linux C 参考实现会请求根地址下的 `/services`。演示环境按接入协议提供两个入口：

| 接入方式 | 服务发现入口 |
|---|---|
| HTTP | `http://ep-open.tangeopen.com/services` |
| HTTPS | `https://ep-open.tangeopen.com/services` |

HTTPS 接入使用 HTTPS 入口，返回 HTTPS 业务服务地址和 MQTT TLS 地址。客户端应直接使用返回的完整地址，包括协议和端口，不要自行替换协议。

**成功响应示例**（HTTP 200）

以下分别展示演示环境两个入口的响应，实际接入时以接口返回为准。

**HTTP 入口响应**

```jsonc
{
  "device-srv": "http://srv-open.tangeopen.com", // device-server 根地址
  "user-srv": "http://srv-open.tangeopen.com", // user-server 根地址，供支持用户端入口发现的客户端使用
  "voip-srv": "http://srv-open.tangeopen.com", // voip-server 根地址
  "ai-srv": "http://srv-open.tangeopen.com", // ai-server 根地址
  "call-srv": "http://srv-open.tangeopen.com", // call-server 根地址
  "mqtt-srv": "mqtt://mqtt-open.tangeopen.com:8884", // MQTT 地址，格式 mqtt://host:port 或 mqtts://host:port
  "tirtc-srv": "http://ep-tirtc.tange365.com" // TiRTC SDK 服务入口；用于 TIRTC_OPT_SERVICE_ENDPOINT
}
```

**HTTPS 入口响应**

```jsonc
{
  "device-srv": "https://srv-open.tangeopen.com", // device-server 根地址
  "user-srv": "https://srv-open.tangeopen.com", // user-server 根地址，供支持用户端入口发现的客户端使用
  "voip-srv": "https://srv-open.tangeopen.com", // voip-server 根地址
  "ai-srv": "https://srv-open.tangeopen.com", // ai-server 根地址
  "call-srv": "https://srv-open.tangeopen.com", // call-server 根地址
  "mqtt-srv": "mqtts://mqtt-open.tangeopen.com:8883", // MQTT 地址，格式 mqtt://host:port 或 mqtts://host:port
  "tirtc-srv": "https://ep-tirtc.tange365.com" // TiRTC SDK 服务入口；用于 TIRTC_OPT_SERVICE_ENDPOINT
}
```

**成功响应**（HTTP 200），JSON 对象：

| 字段 | 必填 | 说明 |
|------|:--:|------|
| `device-srv` | ✅ | device-server 根地址 |
| `user-srv` | — | user-server 根地址，供支持用户端入口发现的客户端使用 |
| `voip-srv` | ✅ | voip-server 根地址 |
| `ai-srv` | ✅ | ai-server 根地址 |
| `call-srv` | ✅ | call-server 根地址 |
| `mqtt-srv` | ✅ | MQTT 地址，格式 `mqtt://host:port` 或 `mqtts://host:port` |
| `tirtc-srv` | ✅ | TiRTC SDK 服务入口；用于 `TIRTC_OPT_SERVICE_ENDPOINT` |

设备应使用服务发现返回的地址，不要将各业务服务地址或 `tirtc-srv` 固化在固件中。Linux C 参考实现见 [`fetch_services()`](device-sim/device-sim-c/src/device_flow.c)。

---

### 一对一通话与多人对讲

两类房间均由 `call-server` 管理，但接口、用途和生命周期不同，`room_id` 不能混用。

| 区别 | 一对一通话房间 | 多人对讲房间 |
|---|---|---|
| 用途 | 设备发起呼叫，对方接听后通话 | 多台设备加入同一房间进行对讲 |
| 创建方式 | [发起设备呼叫](#post-v1callrequest)，服务端为本次呼叫创建房间 | Web 或设备调用多人对讲 `create` 接口 |
| 设备查询 | `GET /v1/call/room` | `GET /v1/call/group/device/assignment` |
| Web 查询 | 本文不提供一对一通话房间的 Web 查询接口 | `GET /v1/call/group/web/device/:device_id` |
| 房间 ID | `d_roomid_` 开头，仅用于本次通话 | `group_room_` 开头；已有 `xiaotai_room_` ID 仍有效 |
| 加入方式 | 来电设备调用 `/v1/call/device/info` 接听 | 使用六位 `room_code` 加入，再领取连接凭证 |
| 结束或退出 | `/v1/call/cancel`、`reject`、`hangup`，按通话阶段调用 | 多人对讲 `leave` 接口；设备断线不等于退出房间关系 |

`room_code` 是多人对讲的六位房间号，不是 `room_id`。客户端应保存服务端返回的完整 `room_id`，按业务流程选择接口，不自行生成、截取或替换前缀。微信 VoIP 的 `wx_room_id` 属于微信呼叫流程，也不能与这两类 ID 混用。

## 约定

### 示例阅读说明

请求与响应示例使用 `jsonc` 展示完整字段，并用 `//` 注释说明含义。实际 HTTP 正文使用标准 JSON，发送前须移除注释；`Content-Type` 仍为 `application/json`。

- 字段表说明类型、必填性、范围和返回条件；示例值不代表默认值。可选字段按实际需要传入，只读字段只出现在响应中。
- 示例展开嵌套对象和数组元素的字段；数组仅列出代表性元素。`metadata`、`public_config`、`user_params` 等动态键值对象按提供方或业务配置取值，不存在固定的全部键列表。
- 有条件返回的字段在示例中展示其存在时的形态，实际响应仍可能省略；空对象、空数组、`null` 与字段省略按各接口说明区分。
- 凭证、密钥和上游生成的连接地址使用 `<说明>` 占位值，调用时使用实际返回值。不同服务类型和兼容请求形态分别展示，不将互斥配置混在同一个请求中。

### 响应格式

| 顶层字段 | 类型 | 返回条件与说明 |
|---|---|---|
| `code` | integer | 业务结果码，成功值按服务区分，见下表 |
| `msg` | string | 结果说明；成功为 `ok`，错误为可展示的提示，不能用于程序分支 |
| `data` | object / array / null | 接口业务数据，字段结构见各接口；普通操作接口无业务数据时省略；多人对讲 `presence` 成功和部分云端资源空结果会返回 `null`，具体见接口说明 |


| 服务 | 成功 `code` | 成功 `msg` | 错误 HTTP 状态 | 说明 |
|------|:--:|:--:|:--:|------|
| device-server | 200 | `"ok"` | 实际状态码 | 错误通过 HTTP 状态码 + body `code` 字段区分 |
| user-server | 200 | `"ok"` | 实际状态码 | 同上 |
| ai-server | 200 | `"ok"` | 通常为实际状态码 | `/v1/ai/token` 的上游错误例外使用 HTTP 200，见该接口错误表 |
| voip-server | 0 | `"ok"` | 200（鉴权 401 除外） | 错误通过 body `code` 字段区分 |
| call-server | 200 | `"ok"` | 200（鉴权 401 除外） | 成功码为 200；业务错误仍返回 HTTP 200，以 body `code` 判断 |

> 上表适用于使用统一业务响应体的接口。这些接口成功时都包含 `"msg":"ok"`；下文业务响应示例均保留该字段。
>
> 服务发现和微信回调使用各自的响应格式：`GET /services` 直接返回地址对象，`GET /v1/voip/notification/:wx_app_id` 返回纯文本，`POST /v1/voip/notification/:wx_app_id` 返回 `errcode/errmsg`。
>
> 客户端必须按数值 `code` 分支，不得比较 `msg` 文本；错误说明允许在不改变
> `code`、HTTP 状态和 JSON 字段的前提下优化。完整规则见
> [API 错误响应规范](error-response-policy.md)。

### 鉴权与业务错误

JWT 缺失、无效、过期或缺少必要 claim 时返回 HTTP 401 + `code=401`。JWT
鉴权通过后，各类业务错误按下表处理：

| 服务/场景 | 响应 | 客户端动作 |
|---|---|---|
| voip-server：微信登录状态无效/OpenID 不匹配 | HTTP 200 + `40203` | 重新完成微信登录 |
| voip-server：微信 VoIP 授权不存在或失效 | HTTP 200 + `40205` | 刷新授权列表并引导恢复授权 |
| voip-server：无权访问设备或资源 | HTTP 200 + `40300` | 停止当前资源操作 |
| voip-server：设备已解绑 | HTTP 200 + `6006` | 重新走设备绑定 |
| call-server：无权操作房间、设备或联系人 | HTTP 200 + `40300` | 停止当前资源操作 |
| voip/call-server：内部服务凭证无效 | HTTP 200 + `40301` | 检查共享 `X-Internal-Key` |
| ai-server：内部服务凭证无效 | HTTP 403 + `40301` | 检查共享 `X-Internal-Key` |

### 鉴权方式

| 调用方 | 鉴权方式 | Token 来源 |
|--------|---------|-----------|
| IoT 设备 | `Authorization: Bearer <mqtt_token>` | `POST /v1/device/token` 返回的 `mqtt_token` |
| 待绑定设备 TTS | `Authorization: Bearer <temp_token>` | 同一次 `POST /v1/device/report` 返回的 `temp_token` |
| H5、小程序用户 | `Authorization: Bearer <user_jwt>` | `POST /v1/user/register` 或 `/v1/user/login` 返回的 `token` |
| 微信服务器 | 签名校验（微信标准） | — |
| 内部服务 | `X-Internal-Key: <shared-key>` | 各服务共同配置的内部调用密钥 |
| 公开接口 | 无 | — |

**设备 JWT**: 正式 `mqtt_token` 的 `device_id` claim 是设备 ID；临时 `temp_token` 的 `device_id` claim 是 `temp_client_id`。两者都有 `exp`，由 device-server 签发；TTS 只接受与验证码记录匹配的临时 token。

**用户 JWT**: 包含 `user_id`、`auth_revision`、`iat` 和 `exp`。由 user-server 签发，user-server、
voip-server、ai-server 和 call-server 使用相同的 `jwt_secret` 验证。账号禁用、密码修改或认证版本递增后，只拒绝该用户的旧令牌；历史令牌缺少 `auth_revision` 时按版本 1 兼容。

### Content-Type

业务接口的 POST / PUT 请求默认使用 `Content-Type: application/json`。文件上传使用
`multipart/form-data`；微信 VoIP 通知回调的请求体是 XML，不适用上述 JSON 约定。GET
接口通常无需设置 `Content-Type`。

---

<a id="device-server"></a>

## 设备上线与能力

服务：`device-server`

面向 IoT 硬件设备，处理设备注册上线。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [获取设备绑定验证码](#post-v1devicereport) | 设备 | POST | `/v1/device/report` | 可选：设备 HMAC 签名 |
| [获取验证码语音](#get-v1devicetts) | 设备 | GET | `/v1/device/tts` | 必需：临时设备 JWT（temp_token） |
| [获取设备登录凭证](#post-v1devicetoken) | 设备 | POST | `/v1/device/token` | 必需：设备 HMAC 签名 |
| [上报设备能力](#post-v1deviceprofile) | 设备 | POST | `/v1/device/profile` | 必需：正式设备 JWT（mqtt_token） |

<a id="post-v1devicereport"></a>

### 获取设备绑定验证码

**接口**：`POST /v1/device/report`

**调用方**：设备。

上报设备 MAC，获取 6 位验证码和临时 MQTT 连接凭证。

**鉴权**： 无（可选 HMAC 签名）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |
| X-Device-Id | 签名上报时必填 | 设备 ID |
| X-Timestamp | 签名上报时必填 | Unix 秒级时间戳，与服务器偏差 ≤300s |
| X-Nonce | 签名上报时必填 | 随机串，建议使用 16 位十六进制；300 秒内不可重复，服务端不限定为 16 位 |
| X-Signature | 签名上报时必填 | `Base64(HMAC-SHA256(device_key, device_id + timestamp + nonce))` |

> 签名上报必须带齐四个签名请求头，否则返回 `6008`。未签名上报不带这四个请求头。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| mac | string | ✅ | 设备 MAC 地址，建议使用 `AA:BB:CC:DD:EE:FF` 格式；不能为空 |

**请求示例**

```jsonc
{
  "mac": "AA:BB:CC:DD:EE:FF" // 必填，设备 MAC 地址，建议使用 AA:BB:CC:DD:EE:FF 格式；不能为空
}
```

**旧客户端兼容字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `device_id` | string | 未签名请求不得传非空值，否则返回 `6014`；签名请求以 `X-Device-Id` 为准，忽略此字段 |
| `chip_uid` | string | 接受但不使用，新接入省略 |
| `device_rand` | string | 接受但不使用，新接入省略 |

**两种请求形态**

| 情况 | Header 签名 | 处理方式 |
|------|:--:|---------|
| 签名上报 | ✅ 四个全带且验签通过 | 跳过 L1、L2、L4 限制，校验设备 ID 与 MAC 是否一致，返回验证码 |
| 未签名上报 | ❌ | 执行完整的四层限频检查，返回验证码 |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "code": "386236", // 六位绑定验证码字符串，与顶层业务码 code 区分
    "temp_token": "<实际返回的 temp_token>", // 临时设备 JWT，供本次绑定的 MQTT 和 TTS 使用
    "temp_client_id": "tmp_a1b2c3d4" // 临时 MQTT ClientID / Username
  }
}
```

| 字段 | 说明 |
|------|------|
| data.code | string，6 位验证码，供用户绑定设备；与顶层数字业务码 code 区分 |
| data.temp_token | string，JWT，临时 MQTT 连接 Password，TTL = `code_ttl` |
| data.temp_client_id | string，临时 MQTT ClientID / Username，格式 `tmp_{8位hex}` |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败 |
| 6008 | 401 | 签名不完整、签名失败、时间戳偏差过大、Nonce 重放；时间戳格式或偏差错误会在 `msg` 中给出具体原因 |
| 6010 | 400 | mac 为空 |
| 6013 | 403 | 签名上报中的 MAC 与该 device_id 已记录的 MAC 不一致 |
| 6014 | 400 | 未签名上报的请求体包含非空 device_id |
| 40901 | 409 | 该 MAC 已有未消费验证码且本次未命中幂等重放（详见下方「重复上报同一 MAC 的行为」），附 `Retry-After` 头 |
| 429 | 429 | L2 单 IP 新 MAC 过多 / L3 同 MAC 请求超限 / L4 全局待处理码超限，附 `Retry-After` 头 |
| 50000 | 500 | 服务器内部错误（Redis/DB/系统异常） |

**重复上报同一 MAC 的行为**

验证码按 MAC 加锁：锁存活时间 = `code_ttl`（默认 190s）；**绑定消费验证码后立即释放锁**，TTS 播报（`/v1/device/tts`）只读取、不释放锁。同一 MAC 在同一个 `rate_limit_window`（默认 190s）内重复上报，结果取决于第几次上报：

| 上报次序（同一 `rate_limit_window` 内） | 返回 | 说明 |
|------|------|------|
| 第 1 次 | 200 | 生成新验证码 |
| 第 2 ~ `rate_limit_max_hits` 次（默认 ≤10） | 200，**返回与首次完全相同的 `code` / `temp_token` / `temp_client_id`** | 幂等重放：设备重启或重连后重复上报不会换码、也不报错，并绕过全局待处理码上限 |
| 超过 `rate_limit_max_hits` 次 | 429 | 同一 MAC 限频，`Retry-After` = `rate_limit_window` |

> 单个客户端按顺序重复上报同一 MAC 时，只会得到 200（返回原验证码）或超限后的 429。正常情况下不会返回 409。

**409（40901）触发条件**

409 表示该 MAC 仍持有未消费验证码，但本次请求没有命中上表的幂等重放，而是在新建验证码时遇到已有锁。这是并发与缓存时序边界的兜底返回，`Retry-After` = `code_ttl`。

常见原因如下：

- **并发重复上报**：同一 MAC 几乎同时发来两笔 Report，先抢到锁的返回 200，后到的拿 409。
- **限频窗口已过、验证码锁仍在**：当部署配置 `rate_limit_window < code_ttl` 时（默认两者相等，均为 190s），计数器先于锁过期，下一笔上报看上去像首次、不走重放，却撞上仍在的锁。
- **签名 / 匿名上报交错**：同一 MAC 先匿名上报、再带签名上报时，签名路径会作废已有匿名码并重取锁，期间并发请求可能撞锁。

收到 409 属瞬态错误，按 `Retry-After` 重试即可（重试通常会命中幂等重放，返回原码）。

---

<a id="get-v1devicetts"></a>

### 获取验证码语音

**接口**：`GET /v1/device/tts`

**调用方**：设备。

把 `/v1/device/report` 返回的 6 位设备验证码合成为 8kHz、单声道、16-bit little-endian PCM。该接口只接受与验证码同一次 Report 返回的 `temp_token`，不能使用正式 `mqtt_token` 或其他设备的临时 token。

**鉴权**： ✅ `Authorization: Bearer <temp_token>`

**查询参数**: `code` 为同一次 Report 返回的 6 位验证码；`fmt=wav` 时返回带 44 字节 RIFF/WAV 头的 `audio/wav`，不传时返回 `audio/pcm;rate=8000;channels=1;format=s16le`。

```http
GET /v1/device/tts?code=386236&fmt=wav
Authorization: Bearer <temp_token>
```

**成功响应**: HTTP 200，二进制音频；响应包含 `Cache-Control: no-store`。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 查询参数缺少 code |
| 401 | 401 | temp_token 缺失、过期或签名错误 |
| 40013 | 404 | code 无效、过期，或不属于该 temp_token |
| 50000 | 500 | Redis 或音频构建失败 |

**查询参数明细**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `code` | string | 是 | 本次 report 返回的六位验证码 |
| `fmt` | string | 否 | wav 返回 WAV；省略或其他值返回裸 PCM |

---

<a id="post-v1devicetoken"></a>

### 获取设备登录凭证

**接口**：`POST /v1/device/token`

**调用方**：设备。

已持有 device_id + device_key 的设备，用 HMAC 签名换取正式 MQTT 连接 token。

**鉴权**： 无（HMAC 签名）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| X-Device-Id | ✅ | 设备 ID |
| X-Timestamp | ✅ | Unix 秒级时间戳，与服务器偏差 ≤300s |
| X-Nonce | ✅ | 随机串，建议使用 16 位十六进制；300 秒内不可重复，服务端不限定为 16 位 |
| X-Signature | ✅ | `Base64(HMAC-SHA256(device_key, device_id + timestamp + nonce))` |
| X-MAC | 否 | 设备 MAC。带上才启用 device_id↔MAC 一致性校验（不一致→`6013`）与「同账号同 MAC 不能绑多个 device_id」校验（冲突→`6015`）；省略则跳过这两项校验 |

**无请求体**

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "mqtt_token": "<实际返回的 mqtt_token>" // 正式设备 JWT，用于 MQTT Password 和设备 HTTP Bearer
  }
}
```

**错误码**

| code | HTTP | 含义 | 设备动作 |
|------|------|------|---------|
| 6006 | 410 | 设备已解绑（user_id=0），需重新绑定 | 调用 Report（带签名 Header）获取验证码，重新走绑定流程 |
| 6008 | 401 | 任一 Header 字段为空、时间戳无效、签名不匹配、Nonce 重放；时间戳错误会返回“格式错误”或“设备与服务器时间偏差超过 300 秒” | 时间错误先同步设备时钟；其它情况检查 device_key 和签名算法 |
| 6013 | 403 | 带 X-MAC 且与设备已绑 MAC 不一致（疑似换 MAC/克隆） | 核对 X-MAC 与设备真实 MAC |
| 6015 | 409 | 带 X-MAC 且该 MAC 已绑定至本账号其它 device_id | 该 MAC 已在本账号其它设备绑定 |
| 50000 | 500 | 服务器内部错误 | 重试 |

> 签名算法：`Base64(HMAC-SHA256(device_key, device_id + timestamp + nonce))`

**签名示例 (C — mbedTLS)**

```c
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <mbedtls/base64.h>
#include <mbedtls/md.h>

/* 成功返回 0；参数、缓冲区或加密操作失败返回 -1。
 * 调用方须提供秒级 timestamp 和每次请求不同的 nonce。
 * sig_out 至少 45 字节：32 字节 SHA-256 摘要编码为 44 字符，再加结束符。 */
int device_sign(const char *device_id, const char *device_key,
                const char *timestamp, const char *nonce,
                char *sig_out, size_t sig_size)
{
    if (device_id == NULL || device_key == NULL || timestamp == NULL ||
        nonce == NULL || sig_out == NULL || sig_size < 45 ||
        device_id[0] == '\0' || device_key[0] == '\0' ||
        timestamp[0] == '\0' || nonce[0] == '\0') {
        return -1;
    }
    sig_out[0] = '\0';

    /* 签名原文不含分隔符；检查截断，不能对不完整原文计算签名。 */
    char raw[256];
    int raw_len = snprintf(raw, sizeof(raw), "%s%s%s", device_id, timestamp, nonce);
    if (raw_len < 0 || (size_t)raw_len >= sizeof(raw)) {
        return -1;
    }
    const mbedtls_md_info_t *md = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    unsigned char digest[32];
    if (md == NULL || mbedtls_md_hmac(md,
            (const unsigned char *)device_key, strlen(device_key),
            (const unsigned char *)raw, (size_t)raw_len, digest) != 0) {
        return -1;
    }

    /* 编码的是二进制 HMAC 摘要，不是摘要的十六进制文本。 */
    size_t written = 0;
    if (mbedtls_base64_encode((unsigned char *)sig_out, sig_size,
                             &written, digest, sizeof(digest)) != 0 ||
        written >= sig_size) {
        return -1;
    }
    sig_out[written] = '\0';
    return 0;
}
```

**返回字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.mqtt_token` | string | 正式设备 JWT，用于 MQTT Password 和设备 HTTP Bearer 鉴权；有效期以 token 的 exp 为准 |

---

<a id="post-v1deviceprofile"></a>

### 上报设备能力

**接口**：`POST /v1/device/profile`

**调用方**：设备。

设备信息上报接口。请求体中的 `profiles` 提供媒体能力，供“我的设备 → 更多 → 设备信息”按场景展示。该接口不修改正在进行的通话或媒体协商参数。

**鉴权**：正式设备 `mqtt_token`。设备身份仅取自 JWT，不接受请求体中的 `device_id`；用户 token、临时 token、缺少过期时间或已过期的 token 返回 HTTP 401 + `code=401`。

```jsonc
{
  "profiles": { // 按场景保存的设备媒体能力
    "stream": { // 实时查看场景；仅声明本机实际支持的能力
      "up_audio_streamid": 10, // 可选，设备发送音频的流 ID
      "up_video_streamid": 11, // 可选，设备发送视频的流 ID
      "down_audio_streamid": 14, // 可选，设备接收对讲音频的流 ID
      "down_video_streamid": 15, // 可选，设备接收对讲视频的流 ID
      "up_audio_mt": ["alaw"], // 可选，设备发送音频的编码列表，按首选顺序排列
      "up_video_mt": ["h264"], // 可选，设备发送视频的编码；stream/call 为数组，voip 为单个字符串
      "down_audio_mt": ["alaw"], // 可选，设备接收音频的编码；stream/call 为数组，voip 为单个字符串
      "down_video_mt": ["h264"], // 可选，设备接收视频的编码；stream/call 为数组，voip 为单个字符串
      "audio_rate": 8000, // 可选，音频采样率，单位 Hz
      "audio_channels": 1, // 可选，声道数：1 或 2
      "camera_rotation": 0, // 可选，画面顺时针旋转角度：0、90、180、270
      "hor_mirror": false, // 可选，是否水平镜像
      "vert_mirror": false, // 可选，是否垂直镜像
      "no_video": false, // 可选，是否明确声明无视频
      "aspect_ratio": "4:3", // 可选，画面宽高比；统一接口支持正数或宽:高字符串
      "object_fit": "contain" // 可选，画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
    },
    "call": { // 设备通话场景；仅声明本机实际支持的能力
      "up_audio_mt": ["alaw"], // 可选，设备发送音频的编码列表，按首选顺序排列
      "up_video_mt": ["h264"], // 可选，设备发送视频的编码；stream/call 为数组，voip 为单个字符串
      "down_audio_mt": ["opus", "amr"], // 可选，设备接收音频的编码；stream/call 为数组，voip 为单个字符串
      "down_video_mt": ["h264", "mjpeg"], // 可选，设备接收视频的编码；stream/call 为数组，voip 为单个字符串
      "audio_rate": 16000, // 可选，音频采样率，单位 Hz
      "audio_channels": 1, // 可选，声道数：1 或 2
      "camera_rotation": 0, // 可选，画面顺时针旋转角度：0、90、180、270
      "hor_mirror": false, // 可选，是否水平镜像
      "vert_mirror": false, // 可选，是否垂直镜像
      "no_video": false, // 可选，是否明确声明无视频
      "aspect_ratio": "4:3", // 可选，画面宽高比；统一接口支持正数或宽:高字符串
      "object_fit": "contain" // 可选，画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
    },
    "voip": { // 微信 VoIP 场景；仅声明本机实际支持的能力
      "screen_width": 640, // 可选，设备显示区域宽度，单位像素
      "screen_height": 480, // 可选，设备显示区域高度，单位像素
      "up_video_mt": "h264", // 可选，设备发送视频的编码；stream/call 为数组，voip 为单个字符串
      "down_video_mt": "mjpeg", // 可选，设备接收视频的编码；stream/call 为数组，voip 为单个字符串
      "down_audio_mt": "amr", // 可选，设备接收音频的编码；stream/call 为数组，voip 为单个字符串
      "audio_rate": 8000, // 可选，音频采样率，单位 Hz
      "audio_channels": 1, // 可选，声道数：1 或 2
      "camera_rotation": 90, // 可选，画面顺时针旋转角度：0、90、180、270
      "down_video_rotation": 1, // 可选，微信下行编码方向：0 默认、1 正向、2 保留旋转
      "aspect_ratio": 1.7777777778, // 可选，画面宽高比；统一接口支持正数或宽:高字符串
      "hor_mirror": true, // 可选，是否水平镜像
      "vert_mirror": false, // 可选，是否垂直镜像
      "object_fit": "contain", // 可选，画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
      "video_res_mode": "fit_screen", // 可选，下行视频尺寸模式：auto/fit_screen/fill_screen
      "calling_timeout_sec": 30, // 可选，呼叫超时，1–300 秒
      "no_video": false // 可选，是否明确声明无视频
    }
  }
}
```

`profiles` 必须包含至少一个场景：`stream`（实时查看）、`call`（设备通话）、`voip`（微信 VoIP）。正文最大 16 KiB。每个场景的字段均可省略，未知字段和 `null` 被拒绝。

| 字段 | 类型 | 适用场景 | 必填 | 说明 |
|---|---|---|:---:|---|
| `up_audio_mt` | string[] | `stream`、`call` | 否 | 设备发送音频的编码，最多 8 项，按首选顺序排列 |
| `down_audio_mt` | string[] | `stream`、`call` | 否 | 设备接收音频的编码，最多 8 项，按首选顺序排列 |
| `down_audio_mt` | string | `voip` | 否 | 设备接收微信小程序音频的编码 |
| `up_video_mt` | string[] | `stream`、`call` | 否 | 设备发送视频的编码，最多 8 项，按首选顺序排列 |
| `down_video_mt` | string[] | `stream`、`call` | 否 | 设备接收视频的编码，最多 8 项，按首选顺序排列 |
| `up_video_mt` | string | `voip` | 否 | 设备发送给微信小程序的视频编码 |
| `down_video_mt` | string | `voip` | 否 | 设备接收微信小程序视频的编码 |
| `up_audio_streamid` | integer | `stream` | 否 | 设备发送音频的流 ID，0–15；`stream` 默认 10 |
| `up_video_streamid` | integer | `stream` | 否 | 设备发送视频的流 ID，0–15；`stream` 默认 11 |
| `down_audio_streamid` | integer | `stream` | 否 | 设备接收音频的流 ID，0–15；`stream` 默认 14 |
| `down_video_streamid` | integer | `stream` | 否 | 设备接收视频的流 ID，0–15；`stream` 默认 15 |
| `audio_rate` | integer | 全部 | 否 | 音频采样率：8000、16000、24000、32000、44100 或 48000 Hz |
| `audio_channels` | integer | 全部 | 否 | 音频声道数：1 或 2 |
| `camera_rotation` | integer | 全部 | 否 | 画面顺时针旋转角度：0、90、180 或 270 |
| `down_video_rotation` | integer | `voip` | 否 | 微信下行视频编码方向：`0` 使用默认行为，`1` 输出正向画面，`2` 保留旋转画面；默认 `0`，可省略 |
| `hor_mirror` | boolean | 全部 | 否 | 是否水平镜像 |
| `vert_mirror` | boolean | 全部 | 否 | 是否垂直镜像 |
| `no_video` | boolean | 全部 | 否 | 是否明确声明该场景无视频 |
| `aspect_ratio` | number 或 string | 全部 | 否 | 正数比例，或 `宽:高` 字符串；字符串中的宽、高为 1–9999 |
| `object_fit` | string | 全部 | 否 | `stream`、`call` 支持 `fill`、`contain`、`cover`；`voip` 支持 `fill`、`contain` |
| `screen_width` | integer | `voip` | 否 | 设备显示区域像素宽度，范围 1–16384 |
| `screen_height` | integer | `voip` | 否 | 设备显示区域像素高度，范围 1–16384 |
| `video_res_mode` | string | `voip` | 否 | 下行视频尺寸模式：`auto`、`fit_screen` 或 `fill_screen` |
| `calling_timeout_sec` | integer | `voip` | 否 | 呼叫超时秒数，范围 1–300 |

音频编码支持 `alaw`、`g711a`、`pcm`、`opus`、`amr`、`amr_nb`、`amr_wb`、`aac`；视频编码支持 `h264`、`h265`、`mjpeg`、`none`。`stream`、`call` 的编码字段也接受以逗号、斜杠、分号、竖线或空白分隔的字符串，服务端按分隔符转换为能力列表；`voip` 的编码字段只接受单个字符串。

空数组表示明确不支持，省略字段表示未上报。设备只应声明自身实际支持的能力，接口允许的编码不代表每种业务都支持该编码。

每次请求**完整替换携带场景的能力快照**，未携带的场景保留。`{"profiles":{"call":{}}}` 清除设备通话场景的已报字段。不要把同一场景拆成多次字段增量上报；同场景请求须串行，重试复用原快照。重复请求幂等，最后提交的快照生效，不同场景并发上报不会相互覆盖。

**响应**：成功为 HTTP 200，`{"code":200,"msg":"ok"}`。参数错误为 HTTP 400 + `40000`；设备不存在或已解绑为 HTTP 410 + `6006`；存储失败为 HTTP 500 + `50000`。已解绑设备不能写入，设备能力不包含用户信息，重绑后仍可展示并由设备重新上报覆盖。

用户设备列表、微信 VoIP 呼入和设备呼出均读取这里保存的 `profiles.voip`。设备应在上线后、接受微信来电前完成上报。

**顶层请求字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `profiles` | object | 是 | 场景快照集合，至少包含一个允许的场景 |
| `profiles.stream` | object | 三选一或多选 | 实时查看能力快照 |
| `profiles.call` | object | 三选一或多选 | 设备通话能力快照 |
| `profiles.voip` | object | 三选一或多选 | 微信 VoIP 能力快照 |

场景中 `up_*` 表示设备发送能力，`down_*` 表示设备接收能力。`audio_rate`、`audio_channels`、`camera_rotation`、`down_video_rotation` 为整数；`hor_mirror`、`vert_mirror`、`no_video` 为布尔值。`down_video_rotation` 缺省时按 `0` 处理。服务端只返回设备实际已报的 streamid，不补齐缺省字段；显式 `0` 保留。字段或整个场景缺失时，由客户端逐字段使用默认值：`stream` 上行音频/视频为 `10/11`、下行音频/视频为 `14/15`。四个 streamid 字段仅适用于 `stream` 场景。其他字段无隐式补全值。

设备在建立实时查看连接前通过 `profiles.stream` 上报 streamid，并使实际发送、接收、订阅及关键帧处理使用相同值。同一连接的音频与视频不能共用流 ID。客户端订阅 `up_*_streamid`，向设备发送时使用 `down_*_streamid`；值为 `0` 时不能当成缺省。Web 实时查看读取 `profiles.stream` 的上行音视频和下行音频 ID；当前页面不发送视频。上报不会改写设备固件的媒体参数，也不会切换现有连接；修改后应重新建立连接。

---

<a id="user-server"></a>

## 账号与设备管理

服务：`user-server`

面向 H5 浏览器和微信小程序，处理账号与设备管理。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [获取人机验证配置](#get-v1configcaptcha) | Web、小程序 | GET | `/v1/config/captcha` | 无需登录鉴权 |
| [发送注册验证码](#post-v1usersend-code) | Web、小程序 | POST | `/v1/user/send-code` | 无需登录鉴权 |
| [注册账号](#post-v1userregister) | Web、小程序 | POST | `/v1/user/register` | 无需登录；邮箱验证码校验 |
| [登录账号](#post-v1userlogin) | Web、小程序 | POST | `/v1/user/login` | 无需登录鉴权 |
| [发送密码重置验证码](#post-v1userpassword-resetsend-code) | Web、小程序 | POST | `/v1/user/password-reset/send-code` | 无需登录鉴权 |
| [重置密码](#post-v1userpassword-reset) | Web、小程序 | POST | `/v1/user/password-reset` | 无需登录；邮箱验证码校验 |
| [查询设备绑定额度](#get-v1userquota) | Web、小程序 | GET | `/v1/user/quota` | 必需：用户 JWT（user_jwt） |
| [查询我的设备](#get-v1userdevicelist) | Web、小程序 | GET | `/v1/user/device/list` | 必需：用户 JWT（user_jwt） |
| [修改设备名称](#put-v1userdevicename) | Web、小程序 | PUT | `/v1/user/device/name` | 必需：用户 JWT（user_jwt） |
| [通过验证码绑定设备](#post-v1userdevicebind) | Web、小程序 | POST | `/v1/user/device/bind` | 必需：用户 JWT（user_jwt） |
| [通过设备 ID 绑定](#post-v1userdevicebind-by-id) | Web、小程序 | POST | `/v1/user/device/bind-by-id` | 必需：用户 JWT（user_jwt） |
| [解绑设备](#delete-v1userdevicereset) | Web、小程序 | DELETE | `/v1/user/device/reset` | 必需：用户 JWT（user_jwt） |
| [获取实时音视频凭证](#get-v1userdevicertc-token) | Web、小程序 | GET | `/v1/user/device/rtc-token` | 必需：用户 JWT（user_jwt） |
| [查询已上架开发板](#get-v1boards) | Web | GET | `/v1/boards` | 无需登录鉴权 |
| [查询开发板详情](#get-v1boardsslug) | Web | GET | `/v1/boards/:slug` | 无需登录鉴权 |
| [读取开发板图片](#get-v1board-imagesname) | Web | GET | `/v1/board-images/:name` | 无需登录鉴权 |
| [获取顶部导航链接](#get-v1confignavigation) | Web | GET | `/v1/config/navigation` | 无需登录鉴权 |
| [查询当前账号](#get-v1userme) | Web、小程序 | GET | `/v1/user/me` | 必需：用户 JWT（user_jwt） |

<a id="get-v1configcaptcha"></a>

### 获取人机验证配置

**接口**：`GET /v1/config/captcha`

**调用方**：Web、小程序。

获取当前人机验证 Provider 及其可公开的控件配置，用于初始化客户端控件。

**鉴权**： 无

**无请求参数**

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "provider": "yidun", // 当前人机验证提供方标识
    "enabled": true, // 是否启用人机验证
    "public_config": { // 提供方的公开控件参数，无密钥
      "captcha_id": "<实际返回的 captcha_id>", // 配置验证码控件 ID 时返回
      "mini_program_captcha_id": "<按实际配置返回的小程序控件ID>" // 可选，单独配置的小程序控件 ID
    },
    "captcha_id": "<实际返回的 captcha_id>" // 兼容旧客户端的控件 ID；未配置时为空
  }
}
```

`public_config` 仅包含可下发给客户端的配置，绝不包含密钥。`captcha_id` 为易盾兼容字段；新客户端应读取 `provider`、`enabled` 和 `public_config`。

**返回字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.provider` | string | 当前人机验证提供方标识 |
| `data.enabled` | boolean | 是否启用人机验证 |
| `data.public_config` | object<string,string> | 提供方的公开控件参数，无密钥 |
| `data.public_config.captcha_id` | string | 配置验证码控件 ID 时返回 |
| `data.captcha_id` | string | 兼容旧客户端的控件 ID；未配置时为空 |

---

<a id="post-v1usersend-code"></a>

### 发送注册验证码

**接口**：`POST /v1/user/send-code`

**调用方**：Web、小程序。

发送邮箱验证码（注册前调用）。

**鉴权**： 无

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| email | string | ✅ | 接收验证码的邮箱地址 |
| captcha | object | | 通用人机验证载荷，启用 Provider 时由客户端控件返回 |
| captcha.provider | string | | 签发验证票据的 Provider |
| captcha.token | string | | Provider 返回的验证票据 |
| captcha.metadata | object | | Provider 所需的非敏感附加字段 |
| captcha_id / validate / user | string | | 易盾兼容字段；新接入请使用 `captcha` |

**请求示例**

```jsonc
{
  "email": "user@example.com", // 必填，接收验证码的邮箱地址
  "captcha": { // 可选，通用人机验证载荷，启用 Provider 时由客户端控件返回
    "provider": "yidun", // 人机验证提供方标识
    "token": "<客户端验证控件返回的票据>", // 验证控件返回的一次性票据
    "metadata": { // 提供方要求的附加参数，值为字符串
      "captcha_id": "<公开配置返回的控件ID>" // 易盾校验使用的控件 ID，取自公开配置；其他提供方按实际要求填写
    }
  }
}
```

**易盾兼容请求示例**（供旧客户端使用；新接入使用上面的 `captcha` 对象）：

```jsonc
{
  "email": "user@example.com", // 必填，接收验证码的邮箱地址
  "captcha_id": "<易盾控件ID>", // 易盾兼容字段，控件 ID
  "validate": "<易盾验证票据>", // 易盾兼容字段，控件返回的验证票据
  "user": "example-user" // 易盾兼容字段，用户标识
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或 email 格式无效 |
| 40012 | 400 | 人机验证失败 |
| 429 | 429 | 触发邮件验证码统一限频；注册和找回密码共用同一邮箱、IP 计数，默认 15 分钟内同一邮箱 5 次、同一 IP 20 次，后台配置可调整 |
| 50000 | 500 | 邮件发送失败或服务器内部错误 |

---

<a id="post-v1userregister"></a>

### 注册账号

**接口**：`POST /v1/user/register`

**调用方**：Web、小程序。

注册新用户。

**鉴权**： 无

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| email | string | ✅ | 邮箱地址 |
| password | string | ✅ | 密码，最少 6 位 |
| code | string | ✅ | 邮箱收到的 6 位验证码 |

**请求示例**

```jsonc
{
  "email": "user@example.com", // 必填，邮箱地址
  "password": "ExamplePassword123!", // 必填，密码，最少 6 位
  "code": "386236" // 必填，注册邮箱收到的六位验证码
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "token": "<实际返回的 token>", // 用户 JWT，供后续 Bearer 鉴权使用
    "user_id": 1 // 注册账号的数字 ID
  }
}
```

> `token` 为后续鉴权接口的 Bearer JWT，包含 `user_id`、`auth_revision`、`iat` 和 `exp`。新用户的设备绑定额度取注册时生效的 `user-server.service.quota_per_user`；未发布后台配置时读取 YAML，默认值为 10。账号状态、密码或认证版本变化时，仅该用户的旧令牌失效；缺少 `auth_revision` 的历史令牌按初始版本 1 兼容处理。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或字段校验不通过 |
| 40013 | 400 | 验证码无效或已过期 |
| 4090 | 409 | 该邮箱已注册 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.token` | string | 用户 JWT，供后续 Bearer 鉴权使用 |
| `data.user_id` | integer | 注册账号的数字 ID |

---

<a id="post-v1userlogin"></a>

### 登录账号

**接口**：`POST /v1/user/login`

**调用方**：Web、小程序。

用户登录。

**鉴权**： 无

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| email | string | ✅ | 邮箱地址 |
| password | string | ✅ | 密码 |
| captcha | object | | 通用人机验证载荷，字段含义同发送验证码接口 |
| captcha_id / validate / user | string | | 易盾兼容字段；新接入请使用 `captcha` |

**请求示例**

```jsonc
{
  "email": "user@example.com", // 必填，邮箱地址
  "password": "ExamplePassword123!", // 必填，密码
  "captcha": { // 可选，通用人机验证载荷，字段含义同发送验证码接口
    "provider": "yidun", // 人机验证提供方标识
    "token": "<客户端验证控件返回的票据>", // 验证控件返回的一次性票据
    "metadata": { // 提供方要求的附加参数，值为字符串
      "captcha_id": "<公开配置返回的控件ID>" // 易盾校验使用的控件 ID，取自公开配置；其他提供方按实际要求填写
    }
  }
}
```

**易盾兼容请求示例**（供旧客户端使用；新接入使用上面的 `captcha` 对象）：

```jsonc
{
  "email": "user@example.com", // 必填，邮箱地址
  "password": "ExamplePassword123!", // 必填，密码
  "captcha_id": "<易盾控件ID>", // 易盾兼容字段，控件 ID
  "validate": "<易盾验证票据>", // 易盾兼容字段，控件返回的验证票据
  "user": "example-user" // 易盾兼容字段，用户标识
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "token": "<实际返回的 token>", // 用户 JWT，过期时间取自 exp
    "user_id": 1 // 当前账号的数字 ID
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或字段校验不通过 |
| 40012 | 400 | 人机验证失败 |
| 4091 | 401 | 邮箱或密码错误 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.token` | string | 用户 JWT，过期时间取自 exp |
| `data.user_id` | integer | 当前账号的数字 ID |

**人机验证子字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `captcha.provider` | string | 票据提供方 |
| `captcha.token` | string | 验证控件返回的票据 |
| `captcha.metadata` | object<string,string> | 提供方所需附加参数，值为字符串 |

启用人机验证时需提供有效载荷；未启用时可省略。

---

<a id="post-v1userpassword-resetsend-code"></a>

### 发送密码重置验证码

**接口**：`POST /v1/user/password-reset/send-code`

**调用方**：Web、小程序。

发送找回密码的邮箱验证码。为避免泄露邮箱是否已注册，格式正确且通过人机验证的请求均返回成功；只有已注册邮箱会收到邮件。

成功响应表示请求已受理；验证码邮件由后台异步投递，可能有短暂延迟。未收到邮件时可稍后重新发起请求。

**鉴权**： 无

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| email | string | ✅ | 注册邮箱地址 |
| captcha | object | | 通用人机验证载荷，字段含义同发送验证码接口 |
| captcha_id / validate / user | string | | 易盾兼容字段；新接入请使用 `captcha` |

**请求示例**

```jsonc
{
  "email": "user@example.com", // 必填，注册邮箱地址
  "captcha": { // 可选，通用人机验证载荷，字段含义同发送验证码接口
    "provider": "yidun", // 人机验证提供方标识
    "token": "<客户端验证控件返回的票据>", // 验证控件返回的一次性票据
    "metadata": { // 提供方要求的附加参数，值为字符串
      "captcha_id": "<公开配置返回的控件ID>" // 易盾校验使用的控件 ID，取自公开配置；其他提供方按实际要求填写
    }
  }
}
```

**易盾兼容请求示例**（供旧客户端使用；新接入使用上面的 `captcha` 对象）：

```jsonc
{
  "email": "user@example.com", // 必填，注册邮箱地址
  "captcha_id": "<易盾控件ID>", // 易盾兼容字段，控件 ID
  "validate": "<易盾验证票据>", // 易盾兼容字段，控件返回的验证票据
  "user": "example-user" // 易盾兼容字段，用户标识
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或 email 格式无效 |
| 40012 | 400 | 人机验证失败 |
| 429 | 429 | 邮件处理繁忙，或触发邮件验证码统一限频；注册和找回密码共用同一邮箱、IP 计数，默认 15 分钟内同一邮箱 5 次、同一 IP 20 次，后台配置可调整 |
| 50000 | 500 | 服务器内部错误 |

---

<a id="post-v1userpassword-reset"></a>

### 重置密码

**接口**：`POST /v1/user/password-reset`

**调用方**：Web、小程序。

使用找回密码验证码设置新密码。验证码仅可使用一次，且不能用于注册。

**鉴权**： 无

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| email | string | ✅ | 注册邮箱地址 |
| password | string | ✅ | 新密码，最少 6 位 |
| code | string | ✅ | 找回密码邮件中的 6 位验证码 |

**请求示例**

```jsonc
{
  "email": "user@example.com", // 必填，注册邮箱地址
  "password": "NewExamplePassword123!", // 必填，新密码，最少 6 位
  "code": "386236" // 必填，找回密码邮件中的六位验证码
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或字段校验不通过 |
| 40013 | 400 | 验证码无效或已过期 |
| 429 | 429 | 同一注册邮箱尝试超过 5 次，或同一 IP 尝试超过 20 次；限制窗口为验证码有效期 |
| 50000 | 500 | 服务器内部错误 |

---

### 用户接口鉴权

```
Authorization: Bearer <user_jwt>
```

用户接口使用 register / login 返回的 `token`，含 `user_id` claim。缺失或无效返回 **401**；公开配置接口无需鉴权，以各接口说明为准。

---

<a id="get-v1userquota"></a>

### 查询设备绑定额度

**接口**：`GET /v1/user/quota`

**调用方**：Web、小程序。

查询当前用户剩余设备配额。

**鉴权**： ✅

**无请求体**

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "quota": 8 // 当前用户剩余可绑定设备数
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | 未登录或 token 无效 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.quota` | integer | 当前用户剩余可绑定设备数 |

**请求参数**：无。

---

<a id="get-v1userdevicelist"></a>

### 查询我的设备

**接口**：`GET /v1/user/device/list`

**调用方**：Web、小程序。

响应设备条目的 `profiles` 按业务场景提供明确上报的媒体字段。包含可选的 `stream`、`call`、`voip` 对象，由 device-server 的设备能力上报接口提供。没有场景键时表示该场景能力未上报，不能从其他场景补值。媒体字段只出现在 `profiles` 中。


获取当前用户已绑定设备列表（含在线状态）。

**鉴权**： ✅

**无请求体**

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": [ // 业务数据
    {
      "device_id": "TIRZ00000001", // 设备 ID
      "device_name": "客厅学习机", // 用户设置的设备名称；新绑定默认空字符串，VoIP 授权前应先设置
      "status": 1, // 固定为 1，表示已绑定
      "mac": "AA:BB:CC:DD:EE:FF", // 设备 MAC 地址
      "bind_time": "2026-06-18T12:00:00", // 绑定时间，格式 YYYY-MM-DDTHH:MM:SS；无记录时为 null
      "online": true, // 设备当前是否在线
      "profiles": { // 按场景保存的设备媒体能力
        "stream": { // 实时查看场景；仅声明本机实际支持的能力
          "up_audio_mt": ["alaw"], // 设备发送音频的编码列表，按首选顺序排列
          "up_video_mt": ["h264"], // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
          "down_audio_mt": ["alaw"], // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
          "down_video_mt": ["h264"], // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
          "audio_rate": 8000, // 音频采样率，单位 Hz
          "audio_channels": 1, // 声道数：1 或 2
          "camera_rotation": 0, // 画面顺时针旋转角度：0、90、180、270
          "hor_mirror": false, // 是否水平镜像
          "vert_mirror": false, // 是否垂直镜像
          "no_video": false, // 是否明确声明无视频
          "aspect_ratio": "4:3", // 画面宽高比；统一接口支持正数或宽:高字符串
          "object_fit": "contain" // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
        },
        "call": { // 设备通话场景；仅声明本机实际支持的能力
          "up_audio_mt": ["alaw"], // 设备发送音频的编码列表，按首选顺序排列
          "up_video_mt": ["h264"], // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
          "down_audio_mt": ["opus", "amr"], // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
          "down_video_mt": ["h264", "mjpeg"], // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
          "audio_rate": 16000, // 音频采样率，单位 Hz
          "audio_channels": 1, // 声道数：1 或 2
          "camera_rotation": 0, // 画面顺时针旋转角度：0、90、180、270
          "hor_mirror": false, // 是否水平镜像
          "vert_mirror": false, // 是否垂直镜像
          "no_video": false, // 是否明确声明无视频
          "aspect_ratio": "4:3", // 画面宽高比；统一接口支持正数或宽:高字符串
          "object_fit": "contain" // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
        },
        "voip": { // 微信 VoIP 场景；仅声明本机实际支持的能力
          "screen_width": 640, // 设备显示区域宽度，单位像素
          "screen_height": 480, // 设备显示区域高度，单位像素
          "up_video_mt": "h264", // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
          "down_video_mt": "mjpeg", // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
          "down_audio_mt": "amr", // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
          "audio_rate": 8000, // 音频采样率，单位 Hz
          "audio_channels": 1, // 声道数：1 或 2
          "camera_rotation": 90, // 画面顺时针旋转角度：0、90、180、270
          "down_video_rotation": 1, // 微信下行编码方向：0 默认、1 正向、2 保留旋转
          "aspect_ratio": 1.7777777778, // 画面宽高比；统一接口支持正数或宽:高字符串
          "hor_mirror": true, // 是否水平镜像
          "vert_mirror": false, // 是否垂直镜像
          "object_fit": "contain", // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
          "video_res_mode": "fit_screen", // 下行视频尺寸模式：auto/fit_screen/fill_screen
          "calling_timeout_sec": 30, // 呼叫超时，1–300 秒
          "no_video": false, // 是否明确声明无视频
          "has_camera": true, // 只读，服务端派生的设备上行视频能力
          "has_screen": true, // 只读，服务端派生的设备下行视频能力
          "voip_room_type": "video" // 只读，有任一方向视频能力为 video，否则为 voice
        }
      }
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `data` | array | 当前用户的设备列表；没有设备时为空数组 |
| `data[].device_id` | string | 设备 ID |
| `data[].device_name` | string | 用户设置的设备名称；新绑定默认空字符串，VoIP 授权前应先设置 |
| `data[].status` | integer | 固定为 `1`，表示已绑定 |
| `data[].mac` | string | 设备 MAC 地址 |
| `data[].bind_time` | string 或 null | 绑定时间，格式 `YYYY-MM-DDTHH:MM:SS`；无记录时为 `null` |
| `data[].online` | boolean | 设备当前是否在线 |
| `data[].profiles` | object | 按 `stream`、`call`、`voip` 场景组织的设备能力；未上报时为空对象 |
| `data[].profiles.voip.down_video_rotation` | integer | 微信下行视频编码方向；`0` 或省略表示使用默认行为，`1` 输出正向画面，`2` 保留旋转画面 |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | 未登录或 token 无效 |
| 50000 | 500 | 服务器内部错误 |

**能力字段与空值**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data[].profiles` | object | 按场景返回设备能力快照 |
| `data[].profiles.stream` | object | 可选，实时查看能力 |
| `data[].profiles.call` | object | 可选，设备通话能力 |
| `data[].profiles.voip` | object | 可选，微信 VoIP 工作配置 |
| `data[].profiles.voip.has_camera` | boolean | 服务端根据 `no_video` 和 `up_video_mt` 派生，表示设备能否向小程序发送视频 |
| `data[].profiles.voip.has_screen` | boolean | 服务端根据 `no_video` 和 `down_video_mt` 派生，表示设备能否接收小程序视频 |
| `data[].profiles.voip.voip_room_type` | string | 服务端派生；有任一方向视频能力时为 `video`，否则为 `voice` |

由 `/v1/device/profile` 上报的场景，其完整字段、类型与枚举见 [`POST /v1/device/profile`](#post-v1deviceprofile)。`has_camera`、`has_screen` 和 `voip_room_type` 仅在 `profiles.voip` 中由服务端补充，设备不能上报。`bind_time` 在没有绑定时间时可为 `null`；镜像、旋转、宽高比和缩放方式未上报时可能省略。

**请求参数**：无。

---

<a id="put-v1userdevicename"></a>

### 修改设备名称

**接口**：`PUT /v1/user/device/name`

**调用方**：Web、小程序。

修改当前用户已绑定设备的名称。名称用于 `wx.requestDeviceVoIP.deviceName` 和
`wmpfVoip.callDevice.deviceName`；最多 13 个 Unicode 字符。修改接口只保存当前名称，
不会修改微信已保存的授权名称。

**鉴权**： ✅

**请求体**

```jsonc
{
  "device_id": "TIRZ00000001", // 设备 ID
  "device_name": "客厅学习机" // 用户设置的设备名称，最多 13 个字符
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "device_id": "TIRZ00000001", // 修改的设备 ID
    "device_name": "客厅学习机" // 保存后的设备名称
  }
}
```

已完成微信授权后再改名时，微信仍显示授权时的名称。用户需在微信“最近使用”中删除
本小程序以清空授权记录，再重新进入并授权，新的名称才会生效。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | JSON 解析失败、device_id 为空或名称超过 13 个字符 |
| 401 | 401 | 未登录或 token 无效 |
| 4040 | 404 | 设备不存在；部分用户接口为避免泄露归属信息，也用于设备不属于当前用户 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.device_id` | string | 修改的设备 ID |
| `data.device_name` | string | 保存后的设备名称 |

---

<a id="post-v1userdevicebind"></a>

### 通过验证码绑定设备

**接口**：`POST /v1/user/device/bind`

**调用方**：Web、小程序。

验证码绑定设备（用户输入设备 TTS 播报的 6 位码）。

**鉴权**： ✅

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| code | string | ✅ | 6 位验证码 |

**请求示例**

```jsonc
{
  "code": "386236" // 必填，设备本次上报的六位绑定验证码
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "device_id": "TIRZ00000001", // 绑定成功的设备 ID
    "msg": "bind success" // 绑定结果说明，固定 bind success
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或 code 字段校验不通过 |
| 4002 | 400 | 验证码无效或已过期（含输错验证码、码不存在） |
| 4003 | 422 | 设备配额已用完 |
| 401 | 401 | 未登录或 token 无效 |
| 4040 | 404 | 预烧 device_id 不在 device_pool 中（扫码预烧绑定路径） |
| 5001 | 504 | MQTT 下发 auth_grant 超时 |
| 6002 | 503 | 设备离线（上报与扫码间临时 MQTT 连接已断） |
| 6004 | 409 | 设备已被其他用户绑定 |
| 6010 | 400 | mac 为空 |
| 6011 | 403 | MAC 不符，疑似克隆 |
| 6012 | 503 | 设备池已耗尽 |
| 6013 | 403 | 预烧路径上报 MAC 与已绑 MAC 不一致 |
| 6015 | 409 | 该 MAC 已绑定至本账号其它 device_id |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.device_id` | string | 绑定成功的设备 ID |
| `data.msg` | string | 绑定结果说明，固定 bind success |

---

<a id="post-v1userdevicebind-by-id"></a>

### 通过设备 ID 绑定

**接口**：`POST /v1/user/device/bind-by-id`

**调用方**：Web、小程序。

按 device_id 直接绑定（无需验证码，device_id 须已存在于 `device_pool`）。

**鉴权**： ✅

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 设备 ID（须在 device_pool 中） |
| mac | string | 否 | 设备 MAC。带上才启用 MAC 一致性校验（`6013`）与同账号同 MAC 查重（`6015`）；省略则沿用该 device_id 已存指纹。公开绑定 UI 通常只提交 device_id |

旧客户端还可传 `chip_uid`（string，芯片标识）和 `device_rand`（string，设备随机标识），随设备指纹保存。MAC 是设备一致性校验依据，新接入无需提供这两个兼容字段。

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，设备 ID（须在 device_pool 中）
  "mac": "AA:BB:CC:DD:EE:FF" // 可选，设备 MAC；用于一致性校验和同账号查重，省略时沿用已存 MAC
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "device_id": "TIRZ00000001", // 绑定成功的设备 ID
    "msg": "bind success" // 绑定结果说明，固定 bind success
  }
}
```

> **在线证明**：当目标 device_id 尚无归属时，要求设备近期已通过签名 Report 证明持有对应 device_key（已建立临时 MQTT 连接），否则返回 6002。若设备已归属当前用户（重复绑定）或归属他人，不受此限制。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或 device_id 为空 |
| 4003 | 422 | 设备配额已用完 |
| 401 | 401 | 未登录或 token 无效 |
| 4040 | 404 | device_id 不在 device_pool 中 |
| 6002 | 503 | 设备无主且未通过在线证明 |
| 6004 | 409 | 设备已被其他用户绑定 |
| 6011 | 403 | MAC 不符，疑似克隆 |
| 6013 | 403 | 上报 MAC 与已绑 MAC 不一致（仅当请求带 mac） |
| 6015 | 409 | 该 MAC 已绑定至本账号其它 device_id（仅当请求带 mac） |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.device_id` | string | 绑定成功的设备 ID |
| `data.msg` | string | 绑定结果说明，固定 bind success |

---

<a id="delete-v1userdevicereset"></a>

### 解绑设备

**接口**：`DELETE /v1/user/device/reset`

**调用方**：Web、小程序。

解绑设备并释放配额，服务端尝试发送 `unbind` 通知并踢除 MQTT 连接。成功响应表示绑定关系已解除；设备名称、VoIP 授权和 profile、AI 角色绑定及通话关系由后台清理，响应时这些清理任务可能尚未完成。

**鉴权**： ✅

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 要解绑的设备 ID |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001" // 必填，要解绑的设备 ID
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "msg": "reset success" // 解绑结果说明，固定 reset success
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体 JSON 解析失败或 device_id 为空 |
| 401 | 401 | 未登录或 token 无效 |
| 4040 | 404 | 设备不存在或不属于当前用户 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.msg` | string | 解绑结果说明，固定 reset success |

---

<a id="get-v1userdevicertc-token"></a>

### 获取实时音视频凭证

**接口**：`GET /v1/user/device/rtc-token`

**调用方**：Web、小程序。

获取 TiRTC token（H5 直连 TiRTC 用）。

**鉴权**： ✅

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |

**查询参数**

| 参数 | 必填 | 说明 |
|------|:--:|------|
| device_id | ✅ | 设备 ID |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "token": "<实际返回的 token>", // 连接设备所需的 TiRTC 凭证
    "app_id": "2818153", // TiRTC 应用 ID
    "endpoint": "https://api-tirtc.tange365.com", // TiRTC 服务入口
    "in_call": false, // 设备是否正在一对一通话；不阻止本次发放凭证
    "profiles": { // 按场景保存的设备媒体能力
      "stream": { // 实时查看场景；仅声明本机实际支持的能力
        "up_audio_mt": ["alaw"], // 设备发送音频的编码列表，按首选顺序排列
        "up_video_mt": ["h264"], // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
        "down_audio_mt": ["alaw"], // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
        "down_video_mt": ["h264"], // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
        "audio_rate": 8000, // 音频采样率，单位 Hz
        "audio_channels": 1, // 声道数：1 或 2
        "camera_rotation": 0, // 画面顺时针旋转角度：0、90、180、270
        "hor_mirror": false, // 是否水平镜像
        "vert_mirror": false, // 是否垂直镜像
        "no_video": false, // 是否明确声明无视频
        "aspect_ratio": "4:3", // 画面宽高比；统一接口支持正数或宽:高字符串
        "object_fit": "contain" // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
      },
      "call": { // 设备通话场景；仅声明本机实际支持的能力
        "up_audio_mt": ["alaw"], // 设备发送音频的编码列表，按首选顺序排列
        "up_video_mt": ["h264"], // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
        "down_audio_mt": ["opus", "amr"], // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
        "down_video_mt": ["h264", "mjpeg"], // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
        "audio_rate": 16000, // 音频采样率，单位 Hz
        "audio_channels": 1, // 声道数：1 或 2
        "camera_rotation": 0, // 画面顺时针旋转角度：0、90、180、270
        "hor_mirror": false, // 是否水平镜像
        "vert_mirror": false, // 是否垂直镜像
        "no_video": false, // 是否明确声明无视频
        "aspect_ratio": "4:3", // 画面宽高比；统一接口支持正数或宽:高字符串
        "object_fit": "contain" // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
      },
      "voip": { // 微信 VoIP 场景；仅声明本机实际支持的能力
        "screen_width": 640, // 设备显示区域宽度，单位像素
        "screen_height": 480, // 设备显示区域高度，单位像素
        "up_video_mt": "h264", // 设备发送视频的编码；stream/call 为数组，voip 为单个字符串
        "down_video_mt": "mjpeg", // 设备接收视频的编码；stream/call 为数组，voip 为单个字符串
        "down_audio_mt": "amr", // 设备接收音频的编码；stream/call 为数组，voip 为单个字符串
        "audio_rate": 8000, // 音频采样率，单位 Hz
        "audio_channels": 1, // 声道数：1 或 2
        "camera_rotation": 90, // 画面顺时针旋转角度：0、90、180、270
        "down_video_rotation": 1, // 微信下行编码方向：0 默认、1 正向、2 保留旋转
        "aspect_ratio": 1.7777777778, // 画面宽高比；统一接口支持正数或宽:高字符串
        "hor_mirror": true, // 是否水平镜像
        "vert_mirror": false, // 是否垂直镜像
        "object_fit": "contain", // 画面缩放方式；voip 为 fill/contain，其他场景另支持 cover
        "video_res_mode": "fit_screen", // 下行视频尺寸模式：auto/fit_screen/fill_screen
        "calling_timeout_sec": 30, // 呼叫超时，1–300 秒
        "no_video": false, // 是否明确声明无视频
        "has_camera": true, // 只读，服务端派生的设备上行视频能力
        "has_screen": true, // 只读，服务端派生的设备下行视频能力
        "voip_room_type": "video" // 只读，有任一方向视频能力为 video，否则为 voice
      }
    }
  }
}
```

| 字段 | 说明 |
|------|------|
| token | TiRTC 连接 token，有效期 1 小时，scope=`connect:device://{device_id}` |
| app_id | TiRTC App ID |
| endpoint | TiRTC API 地址 |
| in_call | 设备当前是否在对讲中（`true` 时仍正常签发 token，由 H5 自行决定是否提示用户） |
| profiles | 设备能力快照，与 `GET /v1/user/device/list` 的 `profiles` 同构；设备未上报时省略该字段。H5 用 `profiles.stream` 自适应画布 |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 缺少 device_id 参数 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | device_id 不存在或不属于当前用户 |
| 50000 | 500 | 服务器内部错误或 token 构建失败 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.token` | string | 连接设备所需的 TiRTC 凭证 |
| `data.app_id` | string | TiRTC 应用 ID |
| `data.endpoint` | string | TiRTC 服务入口 |
| `data.in_call` | boolean | 设备是否正在一对一通话；不阻止本次发放凭证 |
| `data.profiles` | object | 可选。按 `stream`、`call`、`voip` 场景组织的设备能力，投影规则与设备列表一致（无效字段被丢弃）；设备未上报或读取失败时省略该字段。H5 实时查看读取 `profiles.stream`。场景内字段类型与枚举见 [`POST /v1/device/profile`](#post-v1deviceprofile) |

---

<a id="get-v1boards"></a>

### 查询已上架开发板

**接口**：`GET /v1/boards`

**调用方**：Web。

返回官网开发板目录。只包含后台已上架的条目，按 `sort_order` 从小到大排列；顺序相同时按名称排列。页面首次打开时请求一次，不定时刷新。

**鉴权**：无。

**请求参数**：无。

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "boards": [ // 已上架开发板，最多 100 条；无已上架条目时为空数组
      {
        "id": "6c349438-7fd4-44f1-a363-d728d62ae057", // 开发板条目的稳定标识
        "vendor": "示例厂商", // 厂商名称
        "name": "音视频开发板", // 页面展示名称
        "model": "BOARD-S3-01", // 完整型号，目录内唯一
        "chip": "ESP32-S3", // 芯片或平台名称
        "summary": "适合体验实时音视频、微信 VoIP、设备互呼和多人对讲。", // 简介，最多 160 个字符
        "capabilities": ["实时音视频", "微信 VoIP", "多人对讲"], // 能力标签，最多 10 项
        "adaptation_status": "ready", // 适配状态：ready、adapting 或 planned
        "image_url": "https://cdn.example.com/boards/board-s3-01.webp", // HTTPS 产品图片地址，或后台上传生成的 /v1/board-images/<name> 站内地址
        "purchase_url": "https://shop.example.com/board-s3-01", // HTTPS 购买地址；未配置时不返回
        "repository_url": "https://github.com/example/board-s3-01", // HTTPS 源码仓库地址；未配置时不返回
        "firmware_url": "https://downloads.example.com/board-s3-01.bin", // HTTPS 固件下载地址；未配置时不返回
        "flashing_guide_url": "https://docs.example.com/board-s3-01", // HTTPS 烧录指南地址；未配置时不返回
        "effect_video_url": "https://video.example.com/board-s3-01", // HTTPS 效果视频地址；未配置时不返回
        "detail_slug": "board-s3-01", // 详情地址标识，用于 /boards#<detail_slug> 和详情接口
        "sort_order": 10, // 展示顺序，数值越小越靠前
        "publish_status": "published", // 返回条目固定为 published
        "created_at": "2026-09-10T10:00:00+08:00", // 后台创建时间，ISO 8601；未记录时不返回
        "updated_at": "2026-09-10T10:00:00+08:00", // 后台最后修改时间，ISO 8601；未记录时不返回
        "published_at": "2026-09-10T10:00:00+08:00" // 最近上架时间，ISO 8601
      }
    ]
  }
}
```

**返回字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.boards` | object[] | 已上架开发板，最多 100 条；无已上架条目时为空数组 |
| `data.boards[].id` | string | 开发板条目的稳定标识 |
| `data.boards[].vendor` | string | 厂商名称 |
| `data.boards[].name` | string | 页面展示名称 |
| `data.boards[].model` | string | 完整型号，目录内唯一 |
| `data.boards[].chip` | string | 芯片或平台名称 |
| `data.boards[].summary` | string | 简介，最多 160 个字符 |
| `data.boards[].capabilities` | string[] | 能力标签，最多 10 项 |
| `data.boards[].adaptation_status` | string | 适配状态：`ready`、`adapting` 或 `planned` |
| `data.boards[].image_url` | string | HTTPS 产品图片地址，或后台上传生成的 `/v1/board-images/<name>` 站内地址 |
| `data.boards[].purchase_url` | string | HTTPS 购买地址；未配置时不返回 |
| `data.boards[].repository_url` | string | HTTPS 源码仓库地址；未配置时不返回 |
| `data.boards[].firmware_url` | string | HTTPS 固件下载地址；未配置时不返回 |
| `data.boards[].flashing_guide_url` | string | HTTPS 烧录指南地址；未配置时不返回 |
| `data.boards[].effect_video_url` | string | HTTPS 效果视频地址；未配置时不返回 |
| `data.boards[].detail_slug` | string | 详情地址标识，用于 `/boards#<detail_slug>` 和详情接口 |
| `data.boards[].sort_order` | integer | 展示顺序，数值越小越靠前 |
| `data.boards[].publish_status` | string | 返回条目固定为 `published` |
| `data.boards[].published_at` | string | 最近上架时间，ISO 8601 |
| `data.boards[].created_at` | string | 后台创建时间，ISO 8601；未记录时不返回 |
| `data.boards[].updated_at` | string | 后台最后修改时间，ISO 8601；未记录时不返回 |

响应使用 `Cache-Control: no-store`。页面每次进入时读取最新目录，不定时刷新。

---

<a id="get-v1boardsslug"></a>

### 查询开发板详情

**接口**：`GET /v1/boards/:slug`

**调用方**：Web。

根据详情地址标识查询一款已上架开发板。草稿、已下架和不存在的条目均不返回内容。

**鉴权**：无。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `slug` | string | 是 | 开发板的 `detail_slug`，由小写字母、数字和连字符组成 |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "6c349438-7fd4-44f1-a363-d728d62ae057", // 开发板条目的稳定标识
    "vendor": "示例厂商", // 厂商名称
    "name": "音视频开发板", // 页面展示名称
    "model": "BOARD-S3-01", // 完整型号，目录内唯一
    "chip": "ESP32-S3", // 芯片或平台名称
    "summary": "适合体验实时音视频、微信 VoIP、设备互呼和多人对讲。", // 简介，最多 160 个字符
    "capabilities": ["实时音视频", "微信 VoIP", "多人对讲"], // 能力标签，最多 10 项
    "adaptation_status": "ready", // 适配状态：ready、adapting 或 planned
    "image_url": "https://cdn.example.com/boards/board-s3-01.webp", // HTTPS 产品图片地址，或后台上传生成的 /v1/board-images/<name> 站内地址
    "purchase_url": "https://shop.example.com/board-s3-01", // HTTPS 购买地址；未配置时不返回
    "repository_url": "https://github.com/example/board-s3-01", // HTTPS 源码仓库地址；未配置时不返回
    "firmware_url": "https://downloads.example.com/board-s3-01.bin", // HTTPS 固件下载地址；未配置时不返回
    "flashing_guide_url": "https://docs.example.com/board-s3-01", // HTTPS 烧录指南地址；未配置时不返回
    "effect_video_url": "https://video.example.com/board-s3-01", // HTTPS 效果视频地址；未配置时不返回
    "detail_slug": "board-s3-01", // 详情地址标识，用于 /boards#<detail_slug> 和详情接口
    "sort_order": 10, // 展示顺序，数值越小越靠前
    "publish_status": "published", // 返回条目固定为 published
    "created_at": "2026-09-10T10:00:00+08:00", // 后台创建时间，ISO 8601；未记录时不返回
    "updated_at": "2026-09-10T10:00:00+08:00", // 后台最后修改时间，ISO 8601；未记录时不返回
    "published_at": "2026-09-10T10:00:00+08:00" // 最近上架时间，ISO 8601
  }
}
```

`data` 字段与目录接口的 `data.boards[]` 相同。未配置的可选资源链接和时间字段不返回。响应使用 `Cache-Control: no-store`。

**错误码**

| code | HTTP | 含义 |
|---|---|---|
| 40400 | 404 | 开发板不存在、尚未上架或已下架 |

---

<a id="get-v1board-imagesname"></a>

### 读取开发板图片

**接口**：`GET /v1/board-images/:name`

**调用方**：Web。

读取后台上传的开发板图片。`name` 只能使用上传接口返回的文件名，不应由客户端自行拼接。

**鉴权**：无。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `name` | string | 是 | 64 位小写十六进制内容摘要及扩展名；扩展名为 `jpg`、`png` 或 `webp` |

**成功响应**（HTTP 200），响应体为对应图片二进制，`Content-Type` 与图片格式一致。图片地址由内容生成且不可变，响应使用 `Cache-Control: public, max-age=31536000, immutable`。

图片不存在或名称格式无效时返回 HTTP 404，无 JSON 响应体。

---

<a id="get-v1confignavigation"></a>

### 获取顶部导航链接

**接口**：`GET /v1/config/navigation`

**调用方**：Web。

公开读取用户 Web 的顶部导航，无需鉴权。成功为 HTTP 200：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "links": [ // 已启用链接，最多 3 项，无配置为 []
      {
        "name": "接入文档", // 链接显示名称
        "url": "https://docs.example.com", // 跳转地址
        "enabled": true // 返回项均为 true
      }
    ],
    "revision": 1 // 配置版本；0 表示本地回退配置
  }
}
```

仅返回已启用链接，最多 3 项，按配置列表顺序排列；无配置时 `links` 为 `[]`，前端隐藏入口。使用 `_blank` 和 `rel="noopener noreferrer"` 打开。响应 `Cache-Control: no-store`；页面首次加载读取，不定时刷新。`revision=0` 表示使用本地回退配置。

**请求参数**：无。

**返回字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.links` | object[] | 已启用链接，最多 3 项，无配置为 [] |
| `data.links[].name` | string | 链接显示名称 |
| `data.links[].url` | string | 跳转地址 |
| `data.links[].enabled` | boolean | 返回项均为 true |
| `data.revision` | integer | 配置版本；0 表示本地回退配置 |

<a id="get-v1userme"></a>

### 查询当前账号

**接口**：`GET /v1/user/me`

**调用方**：Web、小程序。

使用用户 JWT 查询当前账号，不接受用户 ID 参数。成功为 HTTP 200：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "user_id": 1, // 当前账号 ID
    "email": "user@example.com" // 当前账号邮箱
  }
}
```

响应禁止缓存，不返回密码或令牌。鉴权失败返回 HTTP 401 + `401`，内部错误为 HTTP 500 + `50000`。Web 遇到受保护接口的鉴权失败时清除失效令牌，进入登录页并提示重新登录。

**请求参数**：无。

**返回字段**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.user_id` | integer | 当前账号 ID |
| `data.email` | string | 当前账号邮箱 |

---

<a id="voip-server"></a>

## 微信 VoIP

服务：`voip-server`

处理微信 IoT VoIP 通话全流程。

> **响应格式约定**：`/voip/device/*`、`/voip/user/*` 和 `/voip/internal/*`
> 成功时返回 HTTP 200 + `code=0`，业务失败时返回 HTTP 200 + 非零业务码。
> 只有 JWT 中间件鉴权失败返回 HTTP 401 + `code=401`。其中 `40203` 表示微信登录
> 状态无效，`40205` 表示微信 VoIP 授权无效，`40300` 表示无权访问资源，
> `40301` 表示内部服务凭证无效，`6006` 表示设备已解绑。
> `/voip/notification/*` 是微信回调，响应字段使用 `errcode`，不使用 `code`。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [验证微信回调地址](#get-v1voipnotificationwx_app_id) | 微信服务器 | GET | `/v1/voip/notification/:wx_app_id` | 必需：微信签名 |
| [接收微信呼叫通知](#post-v1voipnotificationwx_app_id) | 微信服务器 | POST | `/v1/voip/notification/:wx_app_id` | 必需：微信签名；AES 模式另验消息签名 |
| [上报微信 VoIP 配置（已弃用）](#post-v1voipdeviceprofile) | 旧版设备 | POST | `/v1/voip/device/profile` | 必需：正式设备 JWT（mqtt_token） |
| [查询设备的微信联系人](#get-v1voipdevicecontacts) | 设备 | GET | `/v1/voip/device/contacts` | 必需：正式设备 JWT（mqtt_token） |
| [查询微信联系人（兼容字段）](#get-v1voipdevicecallers) | 设备 | GET | `/v1/voip/device/callers` | 必需：正式设备 JWT（mqtt_token） |
| [设备发起微信呼叫](#post-v1voipdevicecall) | 设备 | POST | `/v1/voip/device/call` | 必需：正式设备 JWT（mqtt_token） |
| [关联微信登录](#post-v1voipuserwechat-mini-login) | 小程序 | POST | `/v1/voip/user/wechat-mini-login` | 必需：用户 JWT（user_jwt） |
| [查询指定设备的微信联系人](#get-v1voipusercontacts) | Web | GET | `/v1/voip/user/contacts` | 必需：用户 JWT（user_jwt） |
| [查询微信授权设备](#get-v1voipuserauth-list) | 小程序 | GET | `/v1/voip/user/auth-list` | 必需：用户 JWT（user_jwt） |
| [查询微信联系人名称](#get-v1voipusercontact-remark) | 小程序 | GET | `/v1/voip/user/contact-remark` | 必需：用户 JWT（user_jwt） |
| [修改微信联系人名称](#put-v1voipusercontact-remark) | 小程序 | PUT | `/v1/voip/user/contact-remark` | 必需：用户 JWT（user_jwt） |
| [保存微信设备授权](#post-v1voipuserreport-auth) | 小程序 | POST | `/v1/voip/user/report-auth` | 必需：用户 JWT（user_jwt） |
| [移除微信设备授权](#post-v1voipuserdelete-auth) | 小程序 | POST | `/v1/voip/user/delete-auth` | 必需：用户 JWT（user_jwt） |
| [获取微信设备授权票据](#post-v1voipusersn-ticket) | 小程序 | POST | `/v1/voip/user/sn-ticket` | 必需：用户 JWT（user_jwt） |
| [取消微信呼叫](#post-v1voipusercancel) | 小程序 | POST | `/v1/voip/user/cancel` | 必需：用户 JWT（user_jwt） |
| [清理设备业务关联（内部）](#post-v1voipinternalunbind) | 内部服务 | POST | `/v1/voip/internal/unbind` | 必需：内部密钥（X-Internal-Key） |

<a id="get-v1voipnotificationwx_app_id"></a>

### 验证微信回调地址

**接口**：`GET /v1/voip/notification/:wx_app_id`

**调用方**：微信服务器。

微信服务器 URL 验证回调。

**鉴权**： 微信签名校验

**成功响应**（HTTP 200）

返回 `echostr` 参数值（纯文本）。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `wx_app_id` | string | 是 | 已配置的微信小程序 AppID |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `signature` | string | 是 | 微信 Token、timestamp、nonce 的签名 |
| `timestamp` | string | 是 | 微信请求时间戳 |
| `nonce` | string | 是 | 微信随机串 |
| `echostr` | string | 是 | 验证成功后原样返回的字符串 |

**请求体**：无。失败仍返回 HTTP 200 的 JSON：`errcode`（integer）为 3（应用未配置）或 5（签名无效），`errmsg`（string）为错误说明。

---

<a id="post-v1voipnotificationwx_app_id"></a>

### 接收微信呼叫通知

**接口**：`POST /v1/voip/notification/:wx_app_id`

**调用方**：微信服务器。

微信服务器事件推送。处理 `iot_voip_notify` 事件。

**鉴权**： 微信签名校验 + AES 解密（若 `encrypt_type=aes`）

**流程**：

1. 校验签名
2. AES 解密（若加密）
3. 若 `action=join_voip_room`：调 TiRTC Token 服务获取 peer_id + token
4. 通过 MQTT 向设备推送 `call_incoming`

**成功响应**（HTTP 200）

```jsonc
{
  "errcode": 0, // 微信回调结果码，0 为成功
  "errmsg": "ok" // 微信回调结果说明
}
```

**错误码**

| errcode | 含义 |
|---------|------|
| 0 | 成功 |
| 2 | 意外的微信消息类型（非 `iot_voip_notify`） |
| 3 | `wx_app_id` 对应的微信 App 未配置 |
| 4 | 意外的 action（非 `join_voip_room`） |
| 5 | 查询参数 signature 校验失败 |
| 9 | 请求体为空、解析失败、AES 消息签名 msg_signature 无效或解密失败 |
| 10 | 向设备推送 `call_incoming` 失败，或同一房间 10 分钟内重复回调仍在处理中 |

> **去重 / 重试**：以 `voip:notify:{wx_app_id}:{room_id}` 为键做 10 分钟去重。微信重试时，若上一笔仍在处理中 → `errcode 10`；若已完成 → `errcode 0`（幂等返回成功，不再建立第二次 TiRTC 会话、不再向设备推第二次 `call_incoming`）。

**推送设备消息格式** (topic: `device/sn_{id}/cmd`):

```jsonc
{
  "type": "call_incoming", // 消息类型，固定 call_incoming
  "channel": "wx", // 通道，固定 wx
  "payload": { // 通知业务数据，字段含义如下
    "peer_id": "<实际返回的 peer_id>", // TiRTC WHIP 连接 URL
    "token": "<实际返回的 token>", // TiRTC JWT token
    "wx_app_id": "<实际返回的 wx_app_id>", // 微信 AppID
    "wx_model_id": "<实际返回的 wx_model_id>", // VoIP 硬件型号 ID
    "wx_room_id": "<实际返回的 wx_room_id>", // 微信 VoIP 房间 ID
    "wx_user_openid": "<实际返回的 wx_user_openid>", // 主叫用户 openid
    "wx_user_remark": "客厅联系人", // 当前设备联系人列表中该微信身份的统一备注名，未设置时为空
    "wx_server_token": "<实际返回的 wx_server_token>", // 微信服务端 token（设备接听时回传）
    "wx_session_key": "<实际返回的 wx_session_key>", // 微信会话密钥
    "wx_call_id": "<实际返回的 wx_call_id>", // Payload.id（Payload 可解析时携带）；服务端自动生成 Payload 时等于 /voip/device/call 返回的 call_id
    "wx_from": "<实际返回的 wx_from>", // 主叫标识（Payload 可解析时携带）
    "wx_room_type": "video", // 房间类型 voice/video（Payload 可解析时携带）
    "wx_payload": "eyJpZCI6Ii4uLiJ9" // 微信原始 Payload 字符串（通常是 Base64 文本），始终携带；服务端不改写该值
  }
}
```

| 字段 | 说明 |
|------|------|
| type | 消息类型，固定 `call_incoming` |
| channel | 通道，固定 `wx` |
| payload.peer_id | TiRTC WHIP 连接 URL |
| payload.token | TiRTC JWT token |
| payload.wx_app_id | 微信 AppID |
| payload.wx_model_id | VoIP 硬件型号 ID |
| payload.wx_room_id | 微信 VoIP 房间 ID |
| payload.wx_user_openid | 主叫用户 openid |
| payload.wx_user_remark | 当前设备联系人列表中该微信身份的统一备注名，未设置时为空 |
| payload.wx_server_token | 微信服务端 token（设备接听时回传） |
| payload.wx_session_key | 微信会话密钥 |
| payload.wx_payload | 微信原始 `Payload` 字符串（通常是 Base64 文本），始终携带；服务端不改写该值 |
| payload.wx_call_id | `Payload.id`（Payload 可解析时携带）；服务端自动生成 Payload 时等于 `/voip/device/call` 返回的 call_id |
| payload.wx_from | 主叫标识（Payload 可解析时携带） |
| payload.wx_room_type | 房间类型 `voice`/`video`（Payload 可解析时携带） |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `wx_app_id` | string | 是 | 已配置的微信小程序 AppID |

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `signature` | string | 是 | 微信 Token、timestamp、nonce 的签名 |
| `timestamp` | string | 是 | 微信请求时间戳 |
| `nonce` | string | 是 | 微信随机串 |
| `encrypt_type` | string | 否 | aes 表示加密 XML；其他值按明文 XML 解析 |
| `msg_signature` | string | AES 模式 | 包含密文的微信消息签名 |
| `openid` | string | 否 | 微信用户 OpenID；缺省时尝试从 Payload.to 获取 |

**XML 请求体**

根节点为 `xml`。AES 模式外层包含 `ToUserName`（string，接收方）和 `Encrypt`（string，加密消息）；解密后的内容与明文使用以下字段。

| 字段 | 类型 | 说明 |
|---|---|---|
| `ToUserName` | string | 接收方账号 |
| `FromUserName` | string | 发送方账号 |
| `CreateTime` | integer | 微信事件创建时间戳 |
| `MsgType` | string | 固定 event |
| `Event` | string | 固定 iot_voip_notify |
| `Action` | string | 固定 join_voip_room |
| `Sn` | string | 目标设备 ID |
| `RoomId` | string | 微信房间 ID |
| `SessionKey` | string | 微信会话密钥 |
| `ServerToken` | string | 微信服务端凭证 |
| `ModelId` | string | 设备型号 ID |
| `Payload` | string | 微信原始附加信息，通常为 Base64 JSON；解析后的 id/from/to/room_type 均为字符串，分别表示呼叫 ID、来源、目标 OpenID 和房间类型 |

**明文通知正文示例**

以下字段由微信产生；占位凭证不能用于建立呼叫。`Payload` 示例为 Base64 编码的 JSON，包含 `id`（呼叫 ID）、`from`（主叫标识）、`to`（目标 OpenID）、`room_type`（voice/video）。

```xml
<xml>
  <ToUserName>example_receiver</ToUserName> <!-- 接收方账号 -->
  <FromUserName>example_openid</FromUserName> <!-- 发送方账号 -->
  <CreateTime>1720000000</CreateTime> <!-- 事件创建时间，Unix 秒 -->
  <MsgType>event</MsgType> <!-- 固定为 event -->
  <Event>iot_voip_notify</Event> <!-- 固定的微信 VoIP 事件名 -->
  <Action>join_voip_room</Action> <!-- 加入微信 VoIP 房间 -->
  <Sn>TIRZ00000001</Sn> <!-- 目标设备 ID -->
  <RoomId>example_wx_room</RoomId> <!-- 本次微信房间 ID -->
  <SessionKey>WECHAT_SESSION_KEY</SessionKey> <!-- 微信会话密钥，占位值 -->
  <ServerToken>WECHAT_SERVER_TOKEN</ServerToken> <!-- 微信服务端凭证，占位值 -->
  <ModelId>HRHY_example</ModelId> <!-- 微信设备型号 ID -->
  <Payload>eyJpZCI6ImNhbGxfZXhhbXBsZV8wMDEiLCJmcm9tIjoiZXhhbXBsZV9vcGVuaWQiLCJ0byI6ImV4YW1wbGVfb3BlbmlkIiwicm9vbV90eXBlIjoidmlkZW8ifQ==</Payload> <!-- 微信原始透传信息，服务端不改写 -->
</xml>
```

**AES 模式外层正文示例**（与明文正文二选一；查询参数同时携带 `encrypt_type=aes` 和 `msg_signature`）：

```xml
<xml>
  <ToUserName>example_receiver</ToUserName> <!-- 接收方账号 -->
  <Encrypt>WECHAT_ENCRYPTED_MESSAGE</Encrypt> <!-- 微信生成的加密消息，占位值 -->
</xml>
```

这些字段由微信生成，设备和 H5 不直接构造此回调。返回 `errcode` 为 integer，`errmsg` 为 string；含义见本接口错误表。

---

<a id="post-v1voipdeviceprofile"></a>

### 上报微信 VoIP 配置（已弃用）

**接口**：`POST /v1/voip/device/profile`

**调用方**：旧版设备。

该路径仅用于兼容旧版设备。新设备统一调用
[`POST /v1/device/profile`](#post-v1deviceprofile)，并把下列字段放入
`profiles.voip`。两条路径使用同一份 VoIP 配置。

**鉴权**：`Authorization: Bearer <mqtt_token>`，JWT 必须包含 `device_id`。

**请求体**：JSON 对象，最大 512 字节。示例展示全部已定义字段；实际请求仅携带需要的可选项，移除注释后使用紧凑 JSON，并检查正文大小。

| 字段 | 类型 | 必填 | 说明 |
|---|---|:---:|---|
| `screen_width` | integer | 否 | 设备显示区域宽度 |
| `screen_height` | integer | 否 | 设备显示区域高度 |
| `camera_rotation` | integer | 否 | 顺时针旋转角度：`0`、`90`、`180`、`270` |
| `down_video_rotation` | integer | 否 | 微信下行视频编码方向：`0` 使用默认行为，`1` 输出正向画面，`2` 保留旋转画面；默认 `0`，可省略 |
| `aspect_ratio` | number | 否 | 视频宽高比，必须大于 0 |
| `hor_mirror` | boolean | 否 | 是否水平镜像 |
| `vert_mirror` | boolean | 否 | 是否垂直镜像 |
| `object_fit` | string | 否 | `fill` 或 `contain` |
| `audio_rate` | integer | 否 | 8000、16000、24000、32000、44100 或 48000 |
| `audio_channels` | integer | 否 | 1 或 2 |
| `video_mt` | string | 否 | 旧版统一视频编码；缺少方向字段时同时转换为 `up_video_mt` 和 `down_video_mt` |
| `up_video_mt` | string | 否 | 设备发给小程序的视频编码 |
| `down_video_mt` | string | 否 | 设备接收小程序视频的编码 |
| `down_audio_mt` | string | 否 | 设备接收小程序音频的编码 |
| `video_res_mode` | string | 否 | `auto`、`fit_screen` 或 `fill_screen` |
| `no_video` | boolean | 否 | 是否为纯语音设备 |
| `calling_timeout_sec` | integer | 否 | 呼叫超时秒数，范围 1–300 |

兼容接口保留旧请求中的扩展媒体字段。`device_id`、微信 Session、Room、Token、AppID、
ModelID 和 Payload 等会话身份字段不会写入；它们始终由服务端按当前呼叫生成。方向字段
与 `video_mt` 同时存在时，方向字段优先。用户设备列表只返回统一接口定义的公开字段，
不会把旧扩展字段透传给 Web 或小程序。

**请求示例**

```jsonc
{
  "screen_width": 640, // 可选，设备显示区域宽度
  "screen_height": 480, // 可选，设备显示区域高度
  "up_video_mt": "h264", // 可选，设备发给小程序的视频编码
  "down_video_mt": "mjpeg", // 可选，设备接收小程序视频的编码
  "down_audio_mt": "amr", // 可选，设备接收小程序音频的编码
  "audio_rate": 8000, // 可选，8000、16000、24000、32000、44100 或 48000
  "audio_channels": 1, // 可选，1 或 2
  "camera_rotation": 90, // 可选，顺时针旋转角度：0、90、180、270
  "down_video_rotation": 1, // 可选，微信下行视频编码方向：0 使用默认行为，1 输出正向画面，2 保留旋转画面；默认 0，可省略
  "aspect_ratio": 1.7777777778, // 可选，视频宽高比，必须大于 0
  "hor_mirror": true, // 可选，是否水平镜像
  "vert_mirror": false, // 可选，是否垂直镜像
  "object_fit": "contain", // 可选，fill 或 contain
  "video_res_mode": "fit_screen", // 可选，auto、fit_screen 或 fill_screen
  "calling_timeout_sec": 30, // 可选，呼叫超时秒数，范围 1–300
  "no_video": false, // 可选，是否为纯语音设备
  "video_mt": "h264" // 可选，旧版统一视频编码；缺少方向字段时同时转换为 up_video_mt 和 down_video_mt
}
```

**成功响应**：HTTP 200，

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

响应包含
`Deprecation: true` 和 `Link: </v1/device/profile>; rel="successor-version"` Header。

**错误码**

| code | HTTP | 含义 |
|---|---|---|
| 401 | 401 | 设备 JWT 缺失、无效或过期 |
| 40000 | 200 | JSON 格式、512 字节上限，或视频 UI 字段类型、取值不合法 |
| 6006 | 200 | 设备已解绑 |
| 50000 | 200 | 保存失败 |

---

<a id="get-v1voipdevicecontacts"></a>

### 查询设备的微信联系人

**接口**：`GET /v1/voip/device/contacts`

**调用方**：设备。

设备查询有效授权的小程序 VoIP 联系人。此接口只返回 `voip_device_auth` 中
`auth_status=active` 的联系人，
不包含设备联系人；查询完整联系人列表使用 call-server 的
`GET /v1/call/device/contacts`。

**鉴权**： ✅ `Authorization: Bearer <mqtt_token>`（JWT 需含 `device_id` claim）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "contacts": [ // 当前设备的有效 VoIP 联系人，按授权创建时间倒序排列；没有联系人时为 []
      {
        "wx_open_id": "<实际返回的 wx_open_id>", // 微信用户 OpenID；发起外呼时作为 wx_user_openid
        "wx_app_id": "<实际返回的 wx_app_id>", // 授权所属的微信小程序 AppID
        "wx_model_id": "<实际返回的 wx_model_id>", // 授权对应的微信设备型号 ID；发起外呼时服务端从授权记录读取
        "remark": "小雨", // 当前 wx_open_id + wx_app_id 的统一联系人名称；未设置时为空字符串
        "created_at": "2026-06-18T12:00:00Z" // 该设备授权记录的创建时间，RFC 3339 格式
      }
    ]
  }
}
```

`code`、`msg` 遵循 voip-server 的统一响应约定；`data` 字段如下：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.contacts | object[] | 当前设备的有效 VoIP 联系人，按授权创建时间倒序排列；没有联系人时为 `[]` |
| data.contacts[].wx_open_id | string | 微信用户 OpenID；发起外呼时作为 `wx_user_openid` |
| data.contacts[].wx_app_id | string | 授权所属的微信小程序 AppID |
| data.contacts[].wx_model_id | string | 授权对应的微信设备型号 ID；发起外呼时服务端从授权记录读取 |
| data.contacts[].remark | string | 当前 `wx_open_id + wx_app_id` 的统一联系人名称；未设置时为空字符串 |
| data.contacts[].created_at | string | 该设备授权记录的创建时间，RFC 3339 格式 |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 50000 | 200 | 数据库查询失败 |

**请求参数**：无。

---

<a id="get-v1voipdevicecallers"></a>

### 查询微信联系人（兼容字段）

**接口**：`GET /v1/voip/device/callers`

**调用方**：设备。

查询设备的微信联系人，供使用 `list` 返回字段的既有设备调用。

**鉴权**：`Authorization: Bearer <mqtt_token>`（设备 JWT）。

**请求参数**：无。

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "list": [ // 联系人列表，无联系人时为 []
      {
        "wx_open_id": "example_openid", // 微信用户 OpenID
        "wx_app_id": "example_appid", // 微信小程序 AppID
        "wx_model_id": "example_model", // 授权设备型号 ID
        "remark": "小雨", // 联系人名称，未设置时为空
        "created_at": "2026-06-18T12:00:00Z" // 授权记录创建时间
      }
    ]
  }
}
```

**成功响应**：HTTP 200，`code=0`、`msg=ok`。

| 返回字段 | 类型 | 说明 |
|---|---|---|
| `data.list` | object[] | 联系人列表，无联系人时为 [] |
| `data.list[].wx_open_id` | string | 微信用户 OpenID |
| `data.list[].wx_app_id` | string | 微信小程序 AppID |
| `data.list[].wx_model_id` | string | 授权设备型号 ID |
| `data.list[].remark` | string | 联系人名称，未设置时为空 |
| `data.list[].created_at` | string | 授权记录创建时间 |

**错误码**：HTTP 401 + `401` 表示设备凭证无效；HTTP 200 + `50000` 表示查询失败。

---

<a id="post-v1voipdevicecall"></a>

### 设备发起微信呼叫

**接口**：`POST /v1/voip/device/call`

**调用方**：设备。

设备主动呼叫用户。

**鉴权**： ✅ `Authorization: Bearer <mqtt_token>`（JWT 需含 `device_id` claim）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <mqtt_token>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 主叫设备 ID |
| wx_user_openid | string | ✅ | 被叫用户 openid |
| wx_room_type | string | ✅ | `voice` 或 `video` |
| wx_app_id | string | | 微信 AppID，不传则用默认；必须与有效授权记录一致 |
| wx_version_type | int | | 版本类型：`0`=正式版、`1`=开发版、`2`=体验版 |
| wx_listener_name | string | | 被叫方展示名称 |
| wx_query | string | | 自定义查询参数 |
| wx_caller_camera_status | int | | 主叫摄像头状态：`0`=开启、`1`=关闭 |
| wx_listener_camera_status | int | | 被叫摄像头状态：`0`=开启、`1`=关闭 |
| payload | string | | 自定义 payload |

**视频 UI 参数**

| 场景 | 行为 |
|------|------|
| profile 已上报视频 UI 字段 | 呼叫使用 profile 中的 `camera_rotation`、`aspect_ratio`、`hor_mirror`、`vert_mirror`、`object_fit` |
| profile 的 `down_video_rotation` 为 `1` 或 `2` | 设备呼小程序时写入微信 query 的 `encodeVideoRotation`，并传给 TiRTC 的 `down_video_rotation` |
| profile 未上报 `down_video_rotation`，或值为 `0` | 不传旋转参数，使用微信和 TiRTC 的默认行为 |
| `wx_query` 包含同名字段 | 以 profile 为准 |
| profile 未上报某个字段 | 不向 query 添加该字段，使用小程序插件默认值 |

调用方不需要在每次 `/device/call` 请求中重复传视频 UI 参数。
小程序视频 UI 使用 `query`，不读取 `payload` 或 `wxa_payload`。

**payload 行为**

| 请求方式 | 行为 |
|----------|------|
| 省略 `payload` | 接口生成包含 `id`、`from`、`to`、`room_type` 的 JSON；`id` 等于响应中的 `call_id` |
| 传入自定义 `payload` | 按原值透传；如需精确关联 MQTT 回铃，应自行包含 `id`、`from`、`to`、`room_type` |

`payload` / `wxa_payload` 仅用于加入房间和设备通知链路，微信和 TiRTC 不解析其业务内容。

**发起条件**

| 检查项 | 规则 |
|--------|------|
| 设备状态 | 设备必须仍处于绑定状态 |
| 联系人授权 | 授权必须为 `active`；`wx_model_id` 取自授权记录 |
| 小程序 | `wx_app_id` 用于选择小程序并匹配授权；省略时使用默认 AppID |
| 重复呼叫 | 同一设备或联系人 30 秒内不能重复发起；微信房间通知成功下发到在线设备后解除限制 |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，主叫设备 ID
  "wx_user_openid": "<联系人列表中的wx_open_id>", // 必填，被叫用户 openid
  "wx_room_type": "video", // 必填，voice 或 video
  "wx_app_id": "<联系人列表中的wx_app_id>", // 可选，微信 AppID，不传则用默认；必须与有效授权记录一致
  "wx_version_type": 0, // 可选，版本类型：0=正式版、1=开发版、2=体验版
  "wx_listener_name": "小雨", // 可选，被叫方展示名称
  "wx_query": "source=device", // 可选，自定义查询参数
  "wx_caller_camera_status": 0, // 可选，主叫摄像头状态：0=开启、1=关闭
  "wx_listener_camera_status": 0, // 可选，被叫摄像头状态：0=开启、1=关闭
  "payload": "{\"id\":\"call_example_001\",\"from\":\"TIRZ00000001\",\"to\":\"example_openid\",\"room_type\":\"video\"}" // 可选，自定义 payload
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "call_id": "<实际返回的 call_id>" // 本次微信 VoIP 呼叫的关联 ID
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 缺失、无效、过期或缺少 `device_id` claim |
| 40000 | 200 | JSON 解析失败、必填字段缺失、wx_room_type 非法或 device_id 与 JWT 不一致 |
| 40205 | 200 | 微信 VoIP 授权不存在或已失效 |
| 40900 | 200 | 同一设备或联系人短时间内重复发起 |
| 50001 | 200 | 微信 App 未配置 |
| 50002 | 200 | 微信 API 调用失败 |
| 50000 | 200 | 服务器内部错误（profile/授权查询、call_id 生成、Redis 预留等失败） |
| 6006 | 200 | 设备已解绑，需要重新完成设备绑定 |

微信主叫 API 返回错误码 `9` 时，服务端将授权标记为 `invalid`，通知设备刷新联系人，
并返回业务码 `40205`。该错误表示微信侧授权已不可用，不应直接等同于“用户主动取消”；
小程序需要重新检查微信授权状态并引导恢复。

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.call_id` | string | 本次微信 VoIP 呼叫的关联 ID |

---

<a id="post-v1voipuserwechat-mini-login"></a>

### 关联微信登录

**接口**：`POST /v1/voip/user/wechat-mini-login`

**调用方**：小程序。

微信 code 换 openid。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

成功后服务端会将当前用户、`wx_app_id` 与返回的 `wx_user_openid` 关联 24 小时，
供后续 `contact-remark` / `auth-list` / `report-auth` / `delete-auth` 校验；小程序在查询或上报授权前
应重新调用本接口。

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| code | string | ✅ | 微信登录 code |
| wx_app_id | string | | 微信 AppID，不传则用默认 |

**请求示例**

```jsonc
{
  "code": "<wx.login刚返回的code>", // 必填，wx.login 刚返回的临时代码
  "wx_app_id": "<实际小程序AppID>" // 可选，微信 AppID，不传则用默认
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "wx_user_openid": "<实际返回的 wx_user_openid>" // 当前用户在所指定小程序中的 OpenID
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | JSON 解析失败或 code 为空 |
| 50001 | 200 | 微信 App 未配置 |
| 50002 | 200 | 微信 API 调用失败 |
| 50000 | 200 | 服务器内部错误（如 24h 登录绑定写入失败） |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.wx_user_openid` | string | 当前用户在所指定小程序中的 OpenID |

---

<a id="get-v1voipusercontacts"></a>

### 查询指定设备的微信联系人

**接口**：`GET /v1/voip/user/contacts`

**调用方**：Web。

H5 查询指定设备的小程序 VoIP 联系人。此接口与设备接口分开鉴权，且只返回
`voip_device_auth` 中的联系人；查询完整联系人列表使用 call-server 的
`GET /v1/call/user/contacts?device_id=...`。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

**查询参数**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| device_id | ✅ | 当前用户名下的设备 ID |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "contacts": [ // 指定设备的有效 VoIP 联系人，按授权创建时间倒序排列；没有联系人时为 []
      {
        "wx_open_id": "<实际返回的 wx_open_id>", // 微信用户 OpenID
        "wx_app_id": "<实际返回的 wx_app_id>", // 授权所属的微信小程序 AppID
        "wx_model_id": "<实际返回的 wx_model_id>", // 授权对应的微信设备型号 ID
        "remark": "小雨", // 当前 wx_open_id + wx_app_id 的统一联系人名称；未设置时为空字符串
        "created_at": "2026-06-18T12:00:00Z" // 该设备授权记录的创建时间，RFC 3339 格式
      }
    ]
  }
}
```

`code`、`msg` 遵循 voip-server 的统一响应约定；`data.contacts` 的字段、排序和空列表行为与
`GET /v1/voip/device/contacts` 相同：

| 字段 | 类型 | 说明 |
|------|------|------|
| data.contacts | object[] | 指定设备的有效 VoIP 联系人，按授权创建时间倒序排列；没有联系人时为 `[]` |
| data.contacts[].wx_open_id | string | 微信用户 OpenID |
| data.contacts[].wx_app_id | string | 授权所属的微信小程序 AppID |
| data.contacts[].wx_model_id | string | 授权对应的微信设备型号 ID |
| data.contacts[].remark | string | 当前 `wx_open_id + wx_app_id` 的统一联系人名称；未设置时为空字符串 |
| data.contacts[].created_at | string | 该设备授权记录的创建时间，RFC 3339 格式 |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | 缺少 device_id |
| 40300 | 200 | 设备不属于当前用户 |
| 50000 | 200 | 数据库查询失败 |

---

<a id="get-v1voipuserauth-list"></a>

### 查询微信授权设备

**接口**：`GET /v1/voip/user/auth-list`

**调用方**：小程序。

查询当前微信用户在当前账号名下设备上的 VoIP 授权记录。只读取统一联系人名称时使用
`GET /v1/voip/user/contact-remark`。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

**查询参数**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| wx_app_id | | 微信 AppID，不传则使用默认 AppID |

服务端根据最近一次 `wechat-mini-login` 获取当前微信 OpenID，只返回同时满足以下条件的有效记录：

- 设备属于当前登录账号
- 授权记录属于当前微信 OpenID
- 授权记录属于指定小程序 AppID
- `auth_status=active`

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "list": [ // 当前微信身份在当前账号名下设备上的有效授权记录；没有授权时为 []
      {
        "device_id": "TIRZ00000001", // 已授权的设备 ID
        "remark": "小雨", // 当前 wx_open_id + wx_app_id 的统一联系人名称；未设置时为空字符串
        "authorized_device_name": "客厅学习机", // 创建该微信授权时使用的设备名称；不是设备当前绑定名称
        "auth_status": "active" // 授权状态；本接口只返回有效记录，因此固定为 active
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| data.list | object[] | 当前微信身份在当前账号名下设备上的有效授权记录；没有授权时为 `[]` |
| data.list[].device_id | string | 已授权的设备 ID |
| data.list[].remark | string | 当前 `wx_open_id + wx_app_id` 的统一联系人名称；未设置时为空字符串 |
| data.list[].authorized_device_name | string | 创建该微信授权时使用的设备名称；不是设备当前绑定名称 |
| data.list[].auth_status | string | 授权状态；本接口只返回有效记录，因此固定为 `active` |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40203 | 200 | 尚未完成 `wechat-mini-login`，微信登录状态不存在或已过期 |
| 50000 | 200 | Redis 或数据库查询失败 |

---

<a id="get-v1voipusercontact-remark"></a>

### 查询微信联系人名称

**接口**：`GET /v1/voip/user/contact-remark`

**调用方**：小程序。

查询当前小程序 OpenID 的统一联系人名称。小程序应先调用 `wechat-mini-login`；服务端
据此确定 OpenID，客户端不传 `wx_open_id`。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`

**查询参数**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| wx_app_id | | 微信 AppID，不传则使用默认 AppID |

**成功响应**

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "wx_open_id": "<实际返回的 wx_open_id>", // 当前微信登录状态对应的 OpenID
    "remark": "小雨" // 该小程序内统一联系人名称，未设置时为空
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| data.wx_open_id | string | 最近一次 `wechat-mini-login` 确定的当前微信用户 OpenID |
| data.remark | string | 当前 `wx_open_id + wx_app_id` 的统一联系人名称；尚未设置时为 `""` |

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40203 | 200 | 尚未完成 `wechat-mini-login`，微信登录状态不存在或已过期 |
| 50000 | 200 | Redis 或数据库查询失败 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.wx_open_id` | string | 当前微信登录状态对应的 OpenID |
| `data.remark` | string | 该小程序内统一联系人名称，未设置时为空 |

---

<a id="put-v1voipusercontact-remark"></a>

### 修改微信联系人名称

**接口**：`PUT /v1/voip/user/contact-remark`

**调用方**：小程序。

修改当前小程序 OpenID 的统一联系人名称。该名称会同步到同一
`wx_open_id + wx_app_id` 的全部设备授权记录；它不是设备名称。设备端、H5 和小程序
均可修改，最后一次成功写入生效，并向所有受影响设备推送 `callers_update`。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| wx_app_id | string | | 微信 AppID，不传则使用默认 AppID |
| remark | string | ✅ | 联系人名称，去除首尾空格后 1–64 个 Unicode 字符 |

```jsonc
{
  "wx_app_id": "<实际小程序AppID>", // 可选，微信 AppID，不传则使用默认 AppID
  "remark": "小雨" // 必填，联系人名称，去除首尾空格后 1–64 个 Unicode 字符
}
```

**成功响应**:

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

响应不包含 `data` 字段。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 200 | JSON 解析失败、remark 为空或超过 64 个字符 |
| 401 | 401 | JWT 鉴权失败 |
| 40203 | 200 | 尚未完成 `wechat-mini-login`，微信登录状态不存在或已过期 |
| 50000 | 200 | 数据库写入失败 |

---

<a id="post-v1voipuserreport-auth"></a>

### 保存微信设备授权

**接口**：`POST /v1/voip/user/report-auth`

**调用方**：小程序。

上报 VoIP 授权（用户在小程序完成 `wx.requestDeviceVoIP` 后调用）。成功后推送 `callers_update` 通知到设备。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

目标设备必须属于当前用户，且 `wx_open_id` 必须与同一用户最近一次
`wechat-mini-login` 的结果一致。

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 设备 ID |
| wx_open_id | string | ✅ | 微信用户 openid |
| wx_app_id | string | | 微信 AppID，不传则用默认 |
| wx_model_id | string | | 型号 ID，不传则用 App 配置的默认 model_id |
| remark | string | | 当前 OpenID 的统一联系人名称，去除首尾空格后最多 64 个字符；非空值会同步到该 OpenID 的所有设备；未传或空值沿用已保存名称；不是设备名称 |
| device_name | string | `authorization_created=true` | 本次微信授权使用的设备名称，最多 13 个 Unicode 字符；必须与当前绑定名称一致 |
| authorization_created | bool | | 本次是否新建了微信授权；新授权为 `true`，微信已授权或状态恢复上报为 `false` |

`remark` 属于 `wx_open_id + wx_app_id`，不是某一台设备。小程序可通过本接口或
`PUT /v1/voip/user/contact-remark` 修改，设备端和 H5 也可通过 call-server 的联系人
备注接口修改；所有入口采用最后一次成功写入生效。本接口未传或传入空 `remark` 时
沿用已保存名称。

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，设备 ID
  "wx_open_id": "<wechat-mini-login返回的OpenID>", // 必填，微信用户 openid
  "wx_app_id": "<实际小程序AppID>", // 可选，微信 AppID，不传则用默认
  "remark": "小雨", // 可选，当前 OpenID 的统一联系人名称，去除首尾空格后最多 64 个字符；非空值会同步到该 OpenID 的所有设备；未传或空值沿用已保存名称；不是设备名称
  "device_name": "客厅学习机", // authorization_created=true 时提供，本次微信授权使用的设备名称，最多 13 个 Unicode 字符；必须与当前绑定名称一致
  "authorization_created": true, // 可选，本次是否新建了微信授权；新授权为 true，微信已授权或状态恢复上报为 false
  "wx_model_id": "HRHY_example" // 可选，型号 ID，不传则用 App 配置的默认 model_id
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

成功响应不包含 `data` 字段。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | JSON/必填字段错误、名称超长，或新授权使用的设备名与当前绑定名称不一致 |
| 40203 | 200 | 尚未完成微信登录，或 wx_open_id 与当前微信登录不一致 |
| 40300 | 200 | 设备不属于当前用户 |
| 50000 | 200 | 数据库保存失败 |

---

<a id="post-v1voipuserdelete-auth"></a>

### 移除微信设备授权

**接口**：`POST /v1/voip/user/delete-auth`

**调用方**：小程序。

删除授权。实际删除到授权记录时推送 `callers_update` 通知到设备；重复删除保持幂等，
不会重复推送。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

目标设备必须属于当前用户，且 `wx_open_id` 必须与同一用户最近一次
`wechat-mini-login` 的结果一致。

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 设备 ID |
| wx_open_id | string | ✅ | 微信用户 openid |
| wx_app_id | string | | 微信 AppID，不传则用默认 |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，设备 ID
  "wx_open_id": "<wechat-mini-login返回的OpenID>", // 必填，微信用户 openid
  "wx_app_id": "<实际小程序AppID>" // 可选，微信 AppID，不传则用默认
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

成功响应不包含 `data` 字段。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | JSON 解析失败或 device_id / wx_open_id 缺失 |
| 40203 | 200 | 尚未完成微信登录，或 wx_open_id 与当前微信登录不一致 |
| 40300 | 200 | 设备不属于当前用户 |
| 50000 | 200 | 数据库删除失败 |

---

<a id="post-v1voipusersn-ticket"></a>

### 获取微信设备授权票据

**接口**：`POST /v1/voip/user/sn-ticket`

**调用方**：小程序。

获取 SN ticket。`device_id` 必须属于当前用户。响应中的 `device_name` 为设备绑定名称；
未设置名称时返回 `device_id`。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 设备 ID |
| wx_app_id | string | | 微信 AppID，不传则用默认 |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，设备 ID
  "wx_app_id": "<实际小程序AppID>" // 可选，微信 AppID，不传则用默认
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "sn_ticket": "<实际返回的 sn_ticket>", // 用于小程序设备 VoIP 授权的票据
    "device_name": "客厅学习机" // 当前设备名称，用于微信授权展示
  }
}
```

小程序必须将响应中的 `device_name` 原样传给
`wx.requestDeviceVoIP.deviceName`，并在 `report-auth` 中同步上报，避免页面缓存名称与
服务端当前名称不一致。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | JSON 解析失败或 device_id 为空 |
| 40300 | 200 | 设备不属于当前用户 |
| 50001 | 200 | 微信 App 未配置或缺少 model_id |
| 50002 | 200 | 微信 API 调用失败 |
| 50000 | 200 | 服务器内部错误（设备归属校验或名称查询失败） |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.sn_ticket` | string | 用于小程序设备 VoIP 授权的票据 |
| `data.device_name` | string | 当前设备名称，用于微信授权展示 |

---

<a id="post-v1voipusercancel"></a>

### 取消微信呼叫

**接口**：`POST /v1/voip/user/cancel`

**调用方**：小程序。

取消呼叫（小程序挂断后调用）。推送 `call_cancel` 通知到设备。`device_id` 必须属于当前用户。

**鉴权**： ✅ `Authorization: Bearer <user_jwt>`（JWT 需含 `user_id` claim）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 设备 ID |
| wx_room_id | string | | 微信房间 ID |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，设备 ID
  "wx_room_id": "<本次微信通话的房间ID>" // 可选，微信房间 ID
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | JSON 解析失败或 device_id 为空 |
| 40300 | 200 | 设备不属于当前用户 |
| 50000 | 200 | MQTT 推送失败 |

---

<a id="post-v1voipinternalunbind"></a>

### 清理设备业务关联（内部）

**接口**：`POST /v1/voip/internal/unbind`

**调用方**：内部服务。

服务间调用：设备解绑后清空设备名称，删除该设备的 VoIP profile 和全部授权记录，
清理未完成的外呼防重状态，并通知设备刷新联系人。

**鉴权**：`X-Internal-Key` 请求头，值需匹配服务端配置的内部调用密钥。

**请求体**：

```jsonc
{
  "device_id": "TIRZ00000001" // 必填，需要清理业务关联的设备 ID
}
```



**成功响应**：

```jsonc
{
  "code": 0, // 业务码：本接口成功为 0
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



| code | HTTP | 含义 |
|------|------|------|
| 40000 | 200 | JSON 解析失败或缺少 device_id |
| 40301 | 200 | 内部服务凭证未配置或不匹配 |
| 50000 | 200 | 数据库事务或清理操作失败 |

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 需要清理业务关联的设备 ID |

---

<a id="ai-server"></a>

## AI 对话与角色

服务：`ai-server`

面向 IoT 硬件设备和 H5 管理端，提供 AI 语音对话连接凭证与智能体配置。

H5 智能体管理页面为 `GET /v1/ai/agent?device_id=xxx`。该路径返回 HTML，
不是 JSON API；同源部署时需将 `/v1/ai/*` 代理到 ai-server，参见
[`thing-connect.nginx.conf`](deploy/nginx/thing-connect.nginx.conf)。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [获取 AI 对话凭证](#get-v1aitoken) | 设备 | GET | `/v1/ai/token` | 必需：正式设备 JWT（mqtt_token） |
| [列出角色](#get-v1airoles) | Web（含小程序内嵌页面） | GET | `/v1/ai/roles` | 必需：用户 JWT（user_jwt） |
| [查询默认角色](#get-v1airolesdefault) | Web（含小程序内嵌页面） | GET | `/v1/ai/roles/default` | 必需：用户 JWT（user_jwt） |
| [创建角色](#post-v1airoles) | Web（含小程序内嵌页面） | POST | `/v1/ai/roles` | 必需：用户 JWT（user_jwt） |
| [查询角色](#get-v1airolesid) | Web（含小程序内嵌页面） | GET | `/v1/ai/roles/:id` | 必需：用户 JWT（user_jwt） |
| [更新角色](#put-v1airolesid) | Web（含小程序内嵌页面） | PUT | `/v1/ai/roles/:id` | 必需：用户 JWT（user_jwt） |
| [删除角色](#delete-v1airolesid) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/roles/:id` | 必需：用户 JWT（user_jwt） |
| [查询设备角色](#get-v1aidevicedevice_idrole) | Web（含小程序内嵌页面） | GET | `/v1/ai/device/:device_id/role` | 必需：用户 JWT（user_jwt） |
| [设置设备角色](#put-v1aidevicedevice_idrole) | Web（含小程序内嵌页面） | PUT | `/v1/ai/device/:device_id/role` | 必需：用户 JWT（user_jwt） |
| [清除设备角色](#delete-v1aidevicedevice_idrole) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/device/:device_id/role` | 必需：用户 JWT（user_jwt） |
| [批量绑定角色](#post-v1aidevice-roles) | Web（含小程序内嵌页面） | POST | `/v1/ai/device-roles` | 必需：用户 JWT（user_jwt） |
| [批量查询角色绑定](#post-v1aidevice-rolesquery) | Web（含小程序内嵌页面） | POST | `/v1/ai/device-roles/query` | 必需：用户 JWT（user_jwt） |
| [批量删除角色绑定](#delete-v1aidevice-roles) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/device-roles` | 必需：用户 JWT（user_jwt） |
| [查询 TTS 音色](#get-v1aivoiceslanguagezh-cn) | Web（含小程序内嵌页面） | GET | `/v1/ai/voices` | 必需：用户 JWT（user_jwt） |
| [列出全局 MCP 工具](#get-v1aimcptools) | Web（含小程序内嵌页面） | GET | `/v1/ai/mcp/tools` | 必需：用户 JWT（user_jwt） |
| [查询全局 MCP 工具](#get-v1aimcptoolsid) | Web（含小程序内嵌页面） | GET | `/v1/ai/mcp/tools/:id` | 必需：用户 JWT（user_jwt） |
| [列出应用 MCP 工具](#get-v1aimcpapp-tools) | Web（含小程序内嵌页面） | GET | `/v1/ai/mcp/app-tools` | 必需：用户 JWT（user_jwt） |
| [创建应用 MCP 工具](#post-v1aimcpapp-tools) | Web（含小程序内嵌页面） | POST | `/v1/ai/mcp/app-tools` | 必需：用户 JWT（user_jwt） |
| [查询应用 MCP 工具](#get-v1aimcpapp-toolsid) | Web（含小程序内嵌页面） | GET | `/v1/ai/mcp/app-tools/:id` | 必需：用户 JWT（user_jwt） |
| [更新应用 MCP 工具](#put-v1aimcpapp-toolsid) | Web（含小程序内嵌页面） | PUT | `/v1/ai/mcp/app-tools/:id` | 必需：用户 JWT（user_jwt） |
| [删除应用 MCP 工具](#delete-v1aimcpapp-toolsid) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/mcp/app-tools/:id` | 必需：用户 JWT（user_jwt） |
| [列出设备插件](#get-v1aiplugins) | Web（含小程序内嵌页面） | GET | `/v1/ai/plugins` | 必需：用户 JWT（user_jwt） |
| [创建设备插件](#post-v1aiplugins) | Web（含小程序内嵌页面） | POST | `/v1/ai/plugins` | 必需：用户 JWT（user_jwt） |
| [查询设备插件](#get-v1aipluginsid) | Web（含小程序内嵌页面） | GET | `/v1/ai/plugins/:id` | 必需：用户 JWT（user_jwt） |
| [更新设备插件](#put-v1aipluginsid) | Web（含小程序内嵌页面） | PUT | `/v1/ai/plugins/:id` | 必需：用户 JWT（user_jwt） |
| [删除设备插件](#delete-v1aipluginsid) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/plugins/:id` | 必需：用户 JWT（user_jwt） |
| [列出知识库索引](#get-v1aiknowledgeindexes) | Web（含小程序内嵌页面） | GET | `/v1/ai/knowledge/indexes` | 必需：用户 JWT（user_jwt） |
| [创建知识库索引](#post-v1aiknowledgeindexes) | Web（含小程序内嵌页面） | POST | `/v1/ai/knowledge/indexes` | 必需：用户 JWT（user_jwt） |
| [查询知识库索引](#get-v1aiknowledgeindexesid) | Web（含小程序内嵌页面） | GET | `/v1/ai/knowledge/indexes/:id` | 必需：用户 JWT（user_jwt） |
| [更新知识库索引](#put-v1aiknowledgeindexesid) | Web（含小程序内嵌页面） | PUT | `/v1/ai/knowledge/indexes/:id` | 必需：用户 JWT（user_jwt） |
| [删除知识库索引](#delete-v1aiknowledgeindexesid) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/knowledge/indexes/:id` | 必需：用户 JWT（user_jwt） |
| [分页查询知识库文档](#get-v1aiknowledgeindexesiddocumentspage1page_size20) | Web（含小程序内嵌页面） | GET | `/v1/ai/knowledge/indexes/:id/documents` | 必需：用户 JWT（user_jwt） |
| [列出知识库文件](#get-v1aiknowledgefiles) | Web（含小程序内嵌页面） | GET | `/v1/ai/knowledge/files` | 必需：用户 JWT（user_jwt） |
| [上传知识库文件](#post-v1aiknowledgefiles) | Web（含小程序内嵌页面） | POST | `/v1/ai/knowledge/files` | 必需：用户 JWT（user_jwt） |
| [删除知识库文件](#delete-v1aiknowledgefilesid) | Web（含小程序内嵌页面） | DELETE | `/v1/ai/knowledge/files/:id` | 必需：用户 JWT（user_jwt） |
| [清理设备业务关联（内部）](#post-v1aiinternalunbind) | 内部服务 | POST | `/v1/ai/internal/unbind` | 必需：内部密钥（X-Internal-Key） |

<a id="get-v1aitoken"></a>

### 获取 AI 对话凭证

**接口**：`GET /v1/ai/token`

**调用方**：设备。

获取 AI 连接凭证。

**鉴权**：`Authorization: Bearer <mqtt_token>`（设备 JWT，需含 `device_id` claim）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <mqtt_token>`，由 device-server `/v1/device/token` 签发 |

**无请求体 / 查询参数**

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "peer_id": "<实际返回的 peer_id>", // AI 会话 TiRTC 连接目标
    "token": "<实际返回的 token>", // AI 会话连接凭证
    "role_id": "fin63bby1og0" // 实际使用的 AI 角色 ID
  }
}
```

| 字段 | 说明 |
|------|------|
| peer_id | WHIP 连接 URL，含 AI 角色信息 |
| token | TiRTC JWT token，用于建立 WHIP 连接 |
| role_id | 当前使用的角色 ID（优先设备绑定角色，否则 default_role_id） |

> 角色优先使用[设置设备角色](#put-v1aidevicedevice_idrole)保存的绑定。没有绑定、绑定读取失败或未配置数据库时，使用 `default_role_id`。批量角色接口管理的云端绑定不参与这里的角色选择。同一设备、同一角色的成功凭证缓存 60 秒。

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | 缺少 Authorization 头、JWT 无效或缺少 device_id claim |
| -1 | 200 | 上游探鸽云 API 网络/解析错误 |
| 上游透传 | 200 | 探鸽云返回的非零业务码直接透传给客户端 |
| 50000 | 500 | 服务器内部错误 |

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.peer_id` | string | AI 会话 TiRTC 连接目标 |
| `data.token` | string | AI 会话连接凭证 |
| `data.role_id` | string | 实际使用的 AI 角色 ID |

### AI 角色管理

以下接口需要配置 `tirtc_aichat`，并使用用户 JWT 鉴权。角色由探鸽云保存，本站记录角色归属和供设备获取 AI 凭证时使用的角色绑定。

应用 MCP 工具、设备插件和知识库列表包含用户自己的资源及配置的默认资源。默认资源可读取；更新或删除资源要求当前用户拥有该资源。

#### AI 资源字段

以下结构用于角色及资源接口。可选字段未配置时可能省略；上游返回的时间字符串原样保留。服务端没有声明的数值范围或默认值，由所选 AI 服务校验，客户端不要自行假定。

**角色请求体**

| 字段 | 类型 | 必填与说明 |
|---|---|---|
| `name` | string | 创建必填；更新可选，角色名称 |
| `avatar` | string | 可选，头像地址 |
| `parent_role_id` | string | 可选，继承的角色 ID |
| `agent_config` | object | 可选，行为配置，子字段见下表 |
| `service_config` | object | 可选，模型与语音服务配置，子字段见下表 |
| `user_params` | object | 可选，自定义键值参数，值可为任意 JSON 类型 |

**`agent_config` 子字段**

| 字段 | 类型 | 必填与说明 |
|---|---|---|
| `prompt` | string | 可选，角色提示词 |
| `welcome_text` | string | 可选，开场白 |
| `ali_rag` | object / null | 知识库绑定；显式传 `null` 清除绑定 |
| `ali_rag.index_id` | string | 设置知识库绑定时提供索引 ID |
| `ali_memory` | object | 可选，记忆配置 |
| `ali_memory.enable` | boolean | 记忆开关 |
| `mcp_tools` | string[] | 可选，绑定的 MCP 工具 ID |
| `device_plugins` | string[] | 可选，绑定的设备插件 ID |

**`service_config` 子字段**

| 字段 | 类型 | 必填与说明 |
|---|---|---|
| `name` | string | 可选，服务配置名称 |
| `type` | string | 服务类型：`custom-compose`、`coze` 或 `qwen-agent` |
| `config` | object | 对应服务类型的配置 |
| `config.tts` | object | `custom-compose` 的 TTS 组件 |
| `config.tts.provider` | string | TTS 提供方标识 |
| `config.tts.provider_params` | object | TTS 参数 |
| `config.tts.provider_params.voice` | string | 音色 ID，通过音色列表获取 |
| `config.tts.provider_params.volume` | integer | 音量，范围由 TTS 提供方定义 |
| `config.tts.provider_params.rate` | number | 语速，范围由 TTS 提供方定义 |
| `config.tts.provider_params.pitch` | number | 音调，范围由 TTS 提供方定义 |
| `config.tts.provider_params.language_hints` | string[] | 语言提示列表 |
| `config.app_id` | string | `coze` 或 `qwen-agent` 的应用 ID |
| `config.bot_id` | string | `coze` 的 Bot ID |
| `config.private_key` | string | `coze` 的私钥，敏感字段 |
| `config.public_key_id` | string | `coze` 的公钥 ID |
| `config.workflow_id` | string | `coze` 的可选工作流 ID |
| `config.api_key` | string | `qwen-agent` 的可选 API 密钥，敏感字段 |
| `config.workspace_id` | string | `qwen-agent` 的可选工作空间 ID |

角色请求会按上述结构转发；空字符串和空数组字段通常不转发。若携带 `agent_config` 却省略 `ali_rag`，该字段仍会以 `null` 转发；仅修改其他行为配置时，应同时带上需要保留的知识库绑定。

**服务配置的互斥形态**

角色示例展开 `custom-compose` 的完整字段。使用其他服务时，将整个 `service_config` 替换为以下对应结构；请求和响应使用相同结构，可选字段的实际返回取决于云端配置。

`coze`：

```jsonc
{
  "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
    "name": "Coze 服务", // 可选，服务配置名称
    "type": "coze", // 服务类型：custom-compose、coze 或 qwen-agent
    "config": { // 所选服务类型的配置
      "app_id": "<Coze应用ID>", // 所选 Coze/Qwen 服务的应用 ID
      "bot_id": "<Coze Bot ID>", // Coze Bot ID
      "private_key": "<Coze私钥>", // Coze 私钥，敏感字段；示例仅为占位值
      "public_key_id": "<Coze公钥ID>", // Coze 公钥 ID
      "workflow_id": "<Coze工作流ID>" // 可选，Coze 工作流 ID
    }
  }
}
```

`qwen-agent`：

```jsonc
{
  "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
    "name": "Qwen Agent 服务", // 可选，服务配置名称
    "type": "qwen-agent", // 服务类型：custom-compose、coze 或 qwen-agent
    "config": { // 所选服务类型的配置
      "app_id": "<Qwen应用ID>", // 所选 Coze/Qwen 服务的应用 ID
      "api_key": "<Qwen API密钥>", // 可选，Qwen 应用 API 密钥，敏感字段
      "workspace_id": "<Qwen工作空间ID>" // 可选，Qwen 工作空间 ID
    }
  }
}
```

**角色返回对象**

| 字段 | 类型 | 返回条件与说明 |
|---|---|---|
| `id` | string | 角色 ID |
| `name` | string | 可选，角色名称 |
| `avatar` | string | 可选，头像地址 |
| `app_id` | string | 可选，云端应用 ID |
| `user_id` | string | 可选，云端用户 ID，与本站数字用户 ID 区分 |
| `parent_role_id` | string | 可选，父角色 ID |
| `agent_config` | object | 可选，行为配置，子字段见上表 |
| `service_config` | object | 可选，服务配置，子字段见上表 |
| `user_params` | object | 可选，自定义参数 |
| `created_at` | string | 可选，云端创建时间 |
| `updated_at` | string | 可选，云端更新时间 |

**应用级 MCP 工具对象**

| 字段 | 类型 | 请求与返回说明 |
|---|---|---|
| `id` | string | 仅返回，工具 ID |
| `app_id` | string | 仅返回，可选的云端应用 ID |
| `enabled` | boolean | 请求可选，工具是否启用；返回包含实际值 |
| `config` | object | 创建必填，更新可选；返回可能省略 |
| `config.enable` | boolean | 可选，运行时开关；与外层 `enabled` 是不同字段 |
| `config.name` | string | 工具名称 |
| `config.url` | string | MCP 服务地址 |
| `config.description` | string | 可选，工具描述 |
| `config.type` | string | 可选，传输协议 `sse` 或 `streamableHttp` |
| `config.authentication` | object | 可选，服务认证配置 |
| `config.authentication.type` | string | 认证类型 `BearerToken` |
| `config.authentication.bearer_token` | string | 认证凭证，敏感字段 |

**设备插件对象**

| 字段 | 类型 | 请求与返回说明 |
|---|---|---|
| `id` | string | 仅返回，插件 ID |
| `app_id` | string | 仅返回，可选的云端应用 ID |
| `name` | string | 创建和更新必填，插件名称 |
| `action` | string | 创建和更新必填，设备指令标识 |
| `description` | string | 可选，插件说明 |
| `input_params` | object[] | 可选，输入参数定义 |
| `return_params` | object[] | 可选，返回参数定义，与输入参数使用相同结构 |
| `created_at` | string | 仅返回，可选的创建时间 |
| `updated_at` | string | 仅返回，可选的更新时间 |

`input_params[]` 和 `return_params[]` 的每项包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 参数名称，可选字段 |
| `type` | string | 参数类型：`string`、`integer`、`boolean`、`array` 或 `object` |
| `description` | string | 可选，参数说明 |
| `required` | boolean | 参数是否必填；未传时为 `false` |
| `enum` | string[] | 可选，允许的取值列表 |
| `default_value` | string | 可选，默认值的字符串表示 |

**知识库索引返回对象**

| 字段 | 类型 | 说明 |
|---|---|---|
| `index_id` | string | 知识库索引 ID |
| `name` | string | 索引名称 |
| `description` | string | 可选，索引描述 |
| `document_ids` | string[] | 可选，关联文档 ID 列表 |

<a id="get-v1airoles"></a>

#### 列出角色

**接口**：`GET /v1/ai/roles`

**调用方**：Web（含小程序内嵌页面）。

列出当前用户创建的角色。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 结果列表；元素示例完整展示对象字段
      {
        "id": "finxxxxxxxx", // 只读，角色 ID
        "name": "我的助手", // 名称
        "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
        "app_id": "2818153", // 只读，云端应用 ID
        "user_id": "cloud_user_example", // 只读，云端用户 ID，与本站数字用户 ID 区分
        "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
        "agent_config": { // 可选，角色行为配置
          "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
          "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
          "ali_rag": { // 知识库绑定；null 表示未绑定
            "index_id": "idx_001" // 知识库索引 ID
          },
          "ali_memory": { // 可选，记忆配置
            "enable": true // 记忆开关
          },
          "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
          "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
        },
        "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
          "name": "中文语音服务", // 可选，服务配置名称
          "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
          "config": { // 所选服务类型的配置
            "tts": { // 可选，custom-compose 的语音合成组件
              "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
              "provider_params": { // TTS 参数，取值范围由提供方定义
                "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
                "volume": 50, // 音量，范围由提供方定义
                "rate": 1.0, // 语速，范围由提供方定义
                "pitch": 1.0, // 音调，范围由提供方定义
                "language_hints": ["zh-CN"] // 语言提示列表
              }
            }
          }
        },
        "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
          "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
        },
        "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
        "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
      }
    ],
    "total": 1 // 结果数量，计数规则见本接口字段表
  }
}
```

**返回字段**：`data.items` 为角色对象数组，`data.total` 为本次返回的角色数（integer）；每项的完整字段见 [AI 资源字段](#ai-资源字段)。

**请求参数**：无。

<a id="get-v1airolesdefault"></a>

#### 查询默认角色

**接口**：`GET /v1/ai/roles/default`

**调用方**：Web（含小程序内嵌页面）。

获取全局默认角色详情。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "fin63bby1og0", // 只读，角色 ID
    "name": "默认助手", // 名称
    "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
    "app_id": "2818153", // 只读，云端应用 ID
    "user_id": "cloud_user_example", // 只读，云端用户 ID，与本站数字用户 ID 区分
    "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
    "agent_config": { // 可选，角色行为配置
      "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
      "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
      "ali_rag": { // 知识库绑定；null 表示未绑定
        "index_id": "idx_001" // 知识库索引 ID
      },
      "ali_memory": { // 可选，记忆配置
        "enable": true // 记忆开关
      },
      "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
      "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
    },
    "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
      "name": "中文语音服务", // 可选，服务配置名称
      "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
      "config": { // 所选服务类型的配置
        "tts": { // 可选，custom-compose 的语音合成组件
          "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
          "provider_params": { // TTS 参数，取值范围由提供方定义
            "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
            "volume": 50, // 音量，范围由提供方定义
            "rate": 1.0, // 语速，范围由提供方定义
            "pitch": 1.0, // 音调，范围由提供方定义
            "language_hints": ["zh-CN"] // 语言提示列表
          }
        }
      }
    },
    "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
      "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
    },
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | 未登录或 token 无效 |
| 40400 | 404 | 未配置 default_role_id，或 AI 云服务中不存在该默认角色 |
| 50200 | 502 | AI 云服务暂不可用 |

**返回字段**：`data` 为角色返回对象，完整字段见 [AI 资源字段](#ai-资源字段)。

**请求参数**：无。

<a id="post-v1airoles"></a>

#### 创建角色

**接口**：`POST /v1/ai/roles`

**调用方**：Web（含小程序内嵌页面）。

创建角色（代理至探鸽云，成功后记录到本地 `ai_user_role`）。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | ✅ | 角色名称 |
| agent_config | object | | 角色配置（prompt、welcome_text 等） |

**请求示例**

```jsonc
{
  "name": "我的助手", // 必填，角色名称
  "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
  "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
  "agent_config": { // 可选，角色配置（prompt、welcome_text 等）
    "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
    "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
    "ali_rag": { // 可选，知识库绑定；null 表示清除
      "index_id": "idx_001" // 知识库索引 ID
    },
    "ali_memory": { // 可选，记忆配置
      "enable": true // 记忆开关
    },
    "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
    "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
  },
  "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
    "name": "中文语音服务", // 可选，服务配置名称
    "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
    "config": { // 所选服务类型的配置
      "tts": { // 可选，custom-compose 的语音合成组件
        "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
        "provider_params": { // TTS 参数，取值范围由提供方定义
          "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
          "volume": 50, // 音量，范围由提供方定义
          "rate": 1.0, // 语速，范围由提供方定义
          "pitch": 1.0, // 音调，范围由提供方定义
          "language_hints": ["zh-CN"] // 语言提示列表
        }
      }
    }
  },
  "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
    "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
  }
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "finxxxxxxxx", // 只读，角色 ID
    "name": "我的助手", // 角色名称
    "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
    "app_id": "2818153", // 只读，云端应用 ID
    "user_id": "cloud_user_example", // 只读，云端用户 ID，与本站数字用户 ID 区分
    "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
    "agent_config": { // 角色配置（prompt、welcome_text 等）
      "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
      "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
      "ali_rag": { // 知识库绑定；null 表示未绑定
        "index_id": "idx_001" // 知识库索引 ID
      },
      "ali_memory": { // 可选，记忆配置
        "enable": true // 记忆开关
      },
      "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
      "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
    },
    "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
      "name": "中文语音服务", // 可选，服务配置名称
      "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
      "config": { // 所选服务类型的配置
        "tts": { // 可选，custom-compose 的语音合成组件
          "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
          "provider_params": { // TTS 参数，取值范围由提供方定义
            "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
            "volume": 50, // 音量，范围由提供方定义
            "rate": 1.0, // 语速，范围由提供方定义
            "pitch": 1.0, // 音调，范围由提供方定义
            "language_hints": ["zh-CN"] // 语言提示列表
          }
        }
      }
    },
    "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
      "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
    },
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**完整请求与返回字段**：见 [AI 资源字段](#ai-资源字段)中的角色请求体、嵌套配置与角色返回对象。创建成功后若详情读取失败，`data` 只保证包含 `id`，客户端可通过详情接口重试读取。

<a id="get-v1airolesid"></a>

#### 查询角色

**接口**：`GET /v1/ai/roles/:id`

**调用方**：Web（含小程序内嵌页面）。

查看角色详情。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户可访问的角色 ID |

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "finxxxxxxxx", // 只读，角色 ID
    "name": "我的助手", // 名称
    "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
    "app_id": "2818153", // 只读，云端应用 ID
    "user_id": "cloud_user_example", // 只读，云端用户 ID，与本站数字用户 ID 区分
    "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
    "agent_config": { // 可选，角色行为配置
      "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
      "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
      "ali_rag": { // 知识库绑定；null 表示未绑定
        "index_id": "idx_001" // 知识库索引 ID
      },
      "ali_memory": { // 可选，记忆配置
        "enable": true // 记忆开关
      },
      "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
      "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
    },
    "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
      "name": "中文语音服务", // 可选，服务配置名称
      "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
      "config": { // 所选服务类型的配置
        "tts": { // 可选，custom-compose 的语音合成组件
          "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
          "provider_params": { // TTS 参数，取值范围由提供方定义
            "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
            "volume": 50, // 音量，范围由提供方定义
            "rate": 1.0, // 语速，范围由提供方定义
            "pitch": 1.0, // 音调，范围由提供方定义
            "language_hints": ["zh-CN"] // 语言提示列表
          }
        }
      }
    },
    "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
      "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
    },
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**返回字段**：`data` 为角色返回对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

**空结果**：本地所有权校验通过后，若云端角色已不存在并返回空数据，本接口仍为 HTTP 200 + `code=200`，`data=null`。这与默认角色接口的 HTTP 404 不同。

<a id="put-v1airolesid"></a>

#### 更新角色

**接口**：`PUT /v1/ai/roles/:id`

**调用方**：Web（含小程序内嵌页面）。

更新角色。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**：[AI 资源字段](#ai-资源字段)中的角色请求体。所有顶层字段可选，`name` 无创建时的必填要求。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的角色 ID |

**请求示例**

```jsonc
{
  "name": "我的助手 v2", // 可选，角色名称
  "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
  "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
  "agent_config": { // 可选，角色行为配置
    "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
    "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
    "ali_rag": { // 可选，知识库绑定；null 表示清除
      "index_id": "idx_001" // 知识库索引 ID
    },
    "ali_memory": { // 可选，记忆配置
      "enable": true // 记忆开关
    },
    "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
    "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
  },
  "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
    "name": "中文语音服务", // 可选，服务配置名称
    "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
    "config": { // 所选服务类型的配置
      "tts": { // 可选，custom-compose 的语音合成组件
        "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
        "provider_params": { // TTS 参数，取值范围由提供方定义
          "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
          "volume": 50, // 音量，范围由提供方定义
          "rate": 1.0, // 语速，范围由提供方定义
          "pitch": 1.0, // 音调，范围由提供方定义
          "language_hints": ["zh-CN"] // 语言提示列表
        }
      }
    }
  },
  "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
    "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
  }
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "finxxxxxxxx", // 只读，角色 ID
    "name": "我的助手 v2", // 名称
    "avatar": "https://cdn.example.com/assistant.png", // 可选，角色头像地址
    "app_id": "2818153", // 只读，云端应用 ID
    "user_id": "cloud_user_example", // 只读，云端用户 ID，与本站数字用户 ID 区分
    "parent_role_id": "fin_parent_example", // 可选，继承的父角色 ID
    "agent_config": { // 可选，角色行为配置
      "prompt": "你是一个智能助手，请用简体中文回答。", // 可选，角色提示词
      "welcome_text": "你好！有什么可以帮你？", // 可选，开场白
      "ali_rag": { // 知识库绑定；null 表示未绑定
        "index_id": "idx_001" // 知识库索引 ID
      },
      "ali_memory": { // 可选，记忆配置
        "enable": true // 记忆开关
      },
      "mcp_tools": ["app_tool_001"], // 可选，绑定的 MCP 工具 ID 列表
      "device_plugins": ["plg_001"] // 可选，绑定的设备插件 ID 列表
    },
    "service_config": { // 可选，模型与语音服务配置；不同 type 的 config 结构不同
      "name": "中文语音服务", // 可选，服务配置名称
      "type": "custom-compose", // 服务类型：custom-compose、coze 或 qwen-agent
      "config": { // 所选服务类型的配置
        "tts": { // 可选，custom-compose 的语音合成组件
          "provider": "<TTS提供方标识>", // TTS 提供方标识，以实际服务为准
          "provider_params": { // TTS 参数，取值范围由提供方定义
            "voice": "<音色列表返回的ID>", // 音色列表返回的 ID
            "volume": 50, // 音量，范围由提供方定义
            "rate": 1.0, // 语速，范围由提供方定义
            "pitch": 1.0, // 音调，范围由提供方定义
            "language_hints": ["zh-CN"] // 语言提示列表
          }
        }
      }
    },
    "user_params": { // 可选，自定义参数对象，值可为任意 JSON 类型
      "locale": "zh-CN" // 自定义参数示例键，非固定协议字段
    },
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**返回字段**：`data` 为角色返回对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

**完整请求与返回字段**：见 [AI 资源字段](#ai-资源字段)中的角色请求体、嵌套配置与角色返回对象。

<a id="delete-v1airolesid"></a>

#### 删除角色

**接口**：`DELETE /v1/ai/roles/:id`

**调用方**：Web（含小程序内嵌页面）。

删除角色（云端 + 本地 `ai_user_role` 同步删除）。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的角色 ID |

**请求体**：无。

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

无 `data` 字段。

#### 角色 CRUD 通用错误码

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或必填字段缺失 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 角色不属于当前用户（无权操作） |
| 50200 | 502 | AI 服务暂不可用（探鸽云 API 调用失败） |
| 50000 | 500 | 服务器内部错误 |

---

<a id="get-v1aidevicedevice_idrole"></a>

#### 查询设备角色

**接口**：`GET /v1/ai/device/:device_id/role`

**调用方**：Web（含小程序内嵌页面）。

查询设备的角色绑定。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "default_role_id": "fin63bby1og0", // 全局默认角色 ID
    "role_id": "finxxxxxxxx" // 设备显式绑定的角色 ID，未设置时为空并使用默认角色
  }
}
```

> 设备未绑定时 `role_id` 为空字符串。

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.default_role_id` | string | 全局默认角色 ID |
| `data.role_id` | string | 设备显式绑定的角色 ID，未设置时为空并使用默认角色 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前用户绑定的设备 ID |

<a id="put-v1aidevicedevice_idrole"></a>

#### 设置设备角色

**接口**：`PUT /v1/ai/device/:device_id/role`

**调用方**：Web（含小程序内嵌页面）。

绑定设备到角色。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求头**

| 字段 | 必填 | 说明 |
|------|:--:|------|
| Authorization | ✅ | `Bearer <user_jwt>` |
| Content-Type | ✅ | `application/json` |

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| role_id | string | ✅ | 当前用户创建的角色 ID |

**请求示例**

```jsonc
{
  "role_id": "<本账号创建的角色ID>" // 必填，当前用户创建的角色 ID
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前用户绑定的设备 ID |

<a id="delete-v1aidevicedevice_idrole"></a>

#### 清除设备角色

**接口**：`DELETE /v1/ai/device/:device_id/role`

**调用方**：Web（含小程序内嵌页面）。

解除设备角色绑定。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前用户绑定的设备 ID |

**请求体**：无。

#### 设备角色绑定通用错误码

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或缺少 role_id |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 设备或角色不属于当前用户 |
| 50000 | 500 | 服务器内部错误 |

---

#### 设备角色批量操作（V2 代理）

这些接口通过探鸽云 `/v2/ai/device-roles` 管理云端绑定，需要用户 JWT。批量操作与单设备角色接口管理的绑定独立，不会同步修改 `/v1/ai/token` 使用的设备角色。要切换设备获取 AI 凭证时使用的角色，请调用[设置设备角色](#put-v1aidevicedevice_idrole)。

<a id="post-v1aidevice-roles"></a>

##### 批量绑定角色

**接口**：`POST /v1/ai/device-roles`

**调用方**：Web（含小程序内嵌页面）。

批量创建设备-角色绑定。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_ids | string[] | ✅ | 设备 ID 列表 |
| role_id | string | ✅ | 角色 ID |

**请求示例**

```jsonc
{
  "device_ids": ["TIRZ00000001", "TIRZ00000002"], // 必填，设备 ID 列表
  "role_id": "<本账号创建的角色ID>" // 必填，角色 ID
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

<a id="post-v1aidevice-rolesquery"></a>

##### 批量查询角色绑定

**接口**：`POST /v1/ai/device-roles/query`

**调用方**：Web（含小程序内嵌页面）。

批量查询设备-角色绑定。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_ids | string[] | ✅ | 设备 ID 列表 |

**请求示例**

```jsonc
{
  "device_ids": ["TIRZ00000001", "TIRZ00000002"] // 必填，设备 ID 列表
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 设备与角色绑定记录
      {
        "device_id": "TIRZ00000001", // 设备 ID
        "role_id": "finxxxxxxxx", // 绑定的角色 ID
        "created_at": 1720000000, // 云端返回的创建时间戳
        "updated_at": 1720000000 // 云端返回的更新时间戳
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 设备与角色绑定记录 |
| `data.items[].device_id` | string | 设备 ID |
| `data.items[].role_id` | string | 绑定的角色 ID |
| `data.items[].created_at` | integer | 云端返回的创建时间戳 |
| `data.items[].updated_at` | integer | 云端返回的更新时间戳 |

<a id="delete-v1aidevice-roles"></a>

##### 批量删除角色绑定

**接口**：`DELETE /v1/ai/device-roles`

**调用方**：Web（含小程序内嵌页面）。

批量删除设备-角色绑定。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_ids` | string[] | 是 | 设备 ID 列表，设备须属于当前用户 |
| `role_id` | string | 否 | 角色 ID；省略时按设备删除绑定 |


**请求示例**

```jsonc
{
  "device_ids": ["TIRZ00000001", "TIRZ00000002"], // 必填，设备 ID 列表，设备须属于当前用户
  "role_id": "finxxxxxxxx" // 可选，角色 ID；省略时按设备删除绑定
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**批量操作通用错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或必填字段缺失 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 设备或角色不属于当前用户 |
| 50200 | 502 | AI 服务暂不可用（探鸽云 API 调用失败） |
| 50000 | 500 | 服务器内部错误 |

---

#### TTS 音色

<a id="get-v1aivoiceslanguagezh-cn"></a>

##### 查询 TTS 音色

**接口**：`GET /v1/ai/voices?language=zh-CN`

**调用方**：Web（含小程序内嵌页面）。

获取可用 TTS 音色列表。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**查询参数**

| 参数 | 必填 | 说明 |
|------|:--:|------|
| language | | 语言过滤（如 `zh-CN`），空则返回全部 |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 音色列表
      {
        "id": "voice_001", // 音色 ID
        "name": "小云", // 音色名称
        "languages": ["zh-CN"], // 可选，支持的语言
        "model": "cosyvoice", // 可选，语音模型
        "scene": "default", // 可选，适用场景
        "sample_url": "<实际返回的 sample_url>" // 可选，试听音频地址
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 音色列表 |
| `data.items[].id` | string | 音色 ID |
| `data.items[].name` | string | 音色名称 |
| `data.items[].languages` | string[] | 可选，支持的语言 |
| `data.items[].model` | string | 可选，语音模型 |
| `data.items[].scene` | string | 可选，适用场景 |
| `data.items[].sample_url` | string | 可选，试听音频地址 |

---

#### MCP 工具（全局）

**空列表**：上游返回空数组时 `data.items` 为 `[]`；上游省略列表或返回 `null` 时，本接口的 `data.items` 也为 `null`。客户端需兼容这两种无结果形式。

<a id="get-v1aimcptools"></a>

##### 列出全局 MCP 工具

**接口**：`GET /v1/ai/mcp/tools`

**调用方**：Web（含小程序内嵌页面）。

列出内置全局 MCP 工具。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 全局 MCP 工具列表
      {
        "id": "tool_001", // 只读，MCP 工具 ID
        "name": "web_search", // 工具名称
        "description": "搜索互联网" // 可选，工具描述
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 全局 MCP 工具列表 |
| `data.items[].id` | string | 工具 ID |
| `data.items[].name` | string | 工具名称 |
| `data.items[].description` | string | 可选，工具描述 |

**请求参数**：无。

**空列表**：上游返回空数组时 `data.items` 为 `[]`；上游省略列表或返回 `null` 时，本接口的 `data.items` 也为 `null`。客户端需兼容这两种无结果形式。

<a id="get-v1aimcptoolsid"></a>

##### 查询全局 MCP 工具

**接口**：`GET /v1/ai/mcp/tools/:id`

**调用方**：Web（含小程序内嵌页面）。

查看单个全局 MCP 工具详情。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "tool_001", // 只读，MCP 工具 ID
    "name": "web_search", // 工具名称
    "description": "搜索互联网" // 可选，工具描述
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.id` | string | 工具 ID |
| `data.name` | string | 工具名称 |
| `data.description` | string | 可选，工具描述 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 全局 MCP 工具 ID |

---

#### MCP 工具（应用级）

> 应用级 MCP 工具在全局工具基础上添加自定义配置（URL、认证等）。所有接口需鉴权。

<a id="get-v1aimcpapp-tools"></a>

##### 列出应用 MCP 工具

**接口**：`GET /v1/ai/mcp/app-tools`

**调用方**：Web（含小程序内嵌页面）。

列出当前用户创建的应用级 MCP 工具，以及配置为全局默认的 MCP 工具。列表从本地索引
读取，只返回轻量引用；完整配置需调用单项详情接口。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 当前用户资源与配置的默认资源引用
      {
        "id": "app_tool_001", // 只读，MCP 工具 ID
        "name": "my_tool" // 资源名称
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 当前用户资源与配置的默认资源引用 |
| `data.items[].id` | string | 资源 ID，用于查询详情 |
| `data.items[].name` | string | 资源名称 |

**请求参数**：无。

<a id="post-v1aimcpapp-tools"></a>

##### 创建应用 MCP 工具

**接口**：`POST /v1/ai/mcp/app-tools`

**调用方**：Web（含小程序内嵌页面）。

创建应用级 MCP 工具。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| config | object | ✅ | 工具配置 |
| config.name | string | ✅ | 工具名称 |
| config.url | string | ✅ | MCP 服务 URL |
| config.description | string | | 工具描述 |
| config.type | string | | 传输协议：`sse` 或 `streamableHttp`；省略时由上游决定 |
| config.authentication | object | | 认证配置，`type` 仅支持 `BearerToken` |
| enabled | bool | | 是否启用；省略时由上游决定 |

**请求示例**

```jsonc
{
  "config": { // 必填，工具配置
    "enable": true, // 可选，工具运行时开关，与外层 enabled 区分
    "name": "my_tool", // 工具名称
    "url": "https://mcp.example.com/sse", // MCP 服务地址
    "description": "自定义工具", // 可选，工具说明
    "type": "sse", // 可选，传输协议：sse 或 streamableHttp
    "authentication": { // 可选，MCP 服务认证配置
      "type": "BearerToken", // 认证类型，目前为 BearerToken
      "bearer_token": "<MCP服务认证凭证>" // MCP 认证凭证，敏感字段；示例仅为占位值
    }
  },
  "enabled": true // 可选，是否启用；省略时由上游决定
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "app_tool_001", // 只读，MCP 工具 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "config": { // 工具配置
      "enable": true, // 可选，工具运行时开关，与外层 enabled 区分
      "name": "my_tool", // 工具名称
      "url": "https://mcp.example.com/sse", // MCP 服务地址
      "description": "自定义工具", // 可选，工具说明
      "type": "sse", // 可选，传输协议：sse 或 streamableHttp
      "authentication": { // 可选，MCP 服务认证配置
        "type": "BearerToken", // 认证类型，目前为 BearerToken
        "bearer_token": "<MCP服务认证凭证>" // MCP 认证凭证，敏感字段；示例仅为占位值
      }
    },
    "enabled": true // 是否启用；省略时由上游决定
  }
}
```

**完整字段**：请求和返回的所有子字段见 [AI 资源字段](#ai-资源字段)中的应用级 MCP 工具对象。

<a id="get-v1aimcpapp-toolsid"></a>

##### 查询应用 MCP 工具

**接口**：`GET /v1/ai/mcp/app-tools/:id`

**调用方**：Web（含小程序内嵌页面）。

查看单个应用级 MCP 工具。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户可访问的工具 ID |

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "app_tool_001", // 只读，MCP 工具 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "config": { // 工具配置对象
      "enable": true, // 可选，工具运行时开关，与外层 enabled 区分
      "name": "my_tool", // 工具名称
      "url": "https://mcp.example.com/sse", // MCP 服务地址
      "description": "自定义工具", // 可选，工具说明
      "type": "sse", // 可选，传输协议：sse 或 streamableHttp
      "authentication": { // 可选，MCP 服务认证配置
        "type": "BearerToken", // 认证类型，目前为 BearerToken
        "bearer_token": "<MCP服务认证凭证>" // MCP 认证凭证，敏感字段；示例仅为占位值
      }
    },
    "enabled": true // 是否启用
  }
}
```

**返回字段**：`data` 为应用级 MCP 工具对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="put-v1aimcpapp-toolsid"></a>

##### 更新应用 MCP 工具

**接口**：`PUT /v1/ai/mcp/app-tools/:id`

**调用方**：Web（含小程序内嵌页面）。

更新应用级 MCP 工具。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**：`config` 和 `enabled` 均可选。只切换启用状态时传 `enabled`，支持显式传 `false`。修改 `config` 时应提供要保留的完整配置，不要假定云端会保留省略的嵌套字段。

**请求示例**

```jsonc
{
  "config": { // 工具配置对象
    "enable": true, // 可选，工具运行时开关，与外层 enabled 区分
    "name": "my_tool", // 工具名称
    "url": "https://mcp.example.com/sse", // MCP 服务地址
    "description": "自定义工具", // 可选，工具说明
    "type": "sse", // 可选，传输协议：sse 或 streamableHttp
    "authentication": { // 可选，MCP 服务认证配置
      "type": "BearerToken", // 认证类型，目前为 BearerToken
      "bearer_token": "<MCP服务认证凭证>" // MCP 认证凭证，敏感字段；示例仅为占位值
    }
  },
  "enabled": false // 是否启用
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "app_tool_001", // 只读，MCP 工具 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "config": { // 工具配置对象
      "enable": true, // 可选，工具运行时开关，与外层 enabled 区分
      "name": "my_tool", // 工具名称
      "url": "https://mcp.example.com/sse", // MCP 服务地址
      "description": "自定义工具", // 可选，工具说明
      "type": "sse", // 可选，传输协议：sse 或 streamableHttp
      "authentication": { // 可选，MCP 服务认证配置
        "type": "BearerToken", // 认证类型，目前为 BearerToken
        "bearer_token": "<MCP服务认证凭证>" // MCP 认证凭证，敏感字段；示例仅为占位值
      }
    },
    "enabled": false // 是否启用
  }
}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的工具 ID |

**返回字段**：`data` 为应用级 MCP 工具对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="delete-v1aimcpapp-toolsid"></a>

##### 删除应用 MCP 工具

**接口**：`DELETE /v1/ai/mcp/app-tools/:id`

**调用方**：Web（含小程序内嵌页面）。

删除应用级 MCP 工具。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**MCP 工具通用错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或必填字段缺失 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 工具不属于当前用户（无权操作） |
| 40400 | 404 | 工具不存在 |
| 42900 | 429 | 工具创建额度已用尽（受 `tirtc_aichat.resource_quota.mcp` 限制） |
| 50200 | 502 | AI 服务暂不可用 |
| 50000 | 500 | 服务器内部错误 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的工具 ID |

**请求体**：无。

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

无 `data` 字段。

---

#### 设备插件

> 探鸽云设备插件 CRUD 代理。所有接口需鉴权。

<a id="get-v1aiplugins"></a>

##### 列出设备插件

**接口**：`GET /v1/ai/plugins`

**调用方**：Web（含小程序内嵌页面）。

列出当前用户创建的设备插件，以及配置为全局默认的设备插件。列表从本地索引读取，
只返回轻量引用；完整配置需调用单项详情接口。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 当前用户资源与配置的默认资源引用
      {
        "id": "plg_001", // 只读，设备插件 ID
        "name": "开灯" // 资源名称
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 当前用户资源与配置的默认资源引用 |
| `data.items[].id` | string | 资源 ID，用于查询详情 |
| `data.items[].name` | string | 资源名称 |

**请求参数**：无。

<a id="post-v1aiplugins"></a>

##### 创建设备插件

**接口**：`POST /v1/ai/plugins`

**调用方**：Web（含小程序内嵌页面）。

创建设备插件。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | ✅ | 插件名称 |
| action | string | ✅ | 设备端指令标识，仅允许 `[a-zA-Z0-9_]`，长度 1-64 |
| description | string | | 描述 |
| input_params | object[] | | 输入参数定义。子字段：`name`(string), `type`(string: `string`/`integer`/`boolean`/`array`/`object`), `description`(string), `required`(bool), `enum`(string[]), `default_value`(string) |
| return_params | object[] | | 返回值定义，格式同 `input_params` |

**请求示例**

```jsonc
{
  "name": "开灯", // 必填，插件名称
  "action": "turn_on", // 必填，设备端指令标识，仅允许 [a-zA-Z0-9_]，长度 1-64
  "description": "打开设备灯", // 可选，描述
  "input_params": [ // 可选，输入参数定义，各子字段见下方注释
    {
      "name": "mode", // 可选，输入参数名称
      "type": "string", // 参数类型：string/integer/boolean/array/object
      "description": "开灯模式", // 可选，输入参数含义
      "required": false, // 是否必填，未传时为 false
      "enum": ["normal", "night"], // 可选，允许值列表
      "default_value": "normal" // 可选，默认值的字符串表示
    }
  ],
  "return_params": [ // 可选，返回值定义，格式同 input_params
    {
      "name": "result", // 可选，返回参数名称
      "type": "string", // 参数类型：string/integer/boolean/array/object
      "description": "执行结果", // 可选，返回参数含义
      "required": true, // 是否必填，未传时为 false
      "enum": ["ok", "failed"], // 可选，允许值列表
      "default_value": "ok" // 可选，默认值的字符串表示
    }
  ]
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "plg_001", // 只读，设备插件 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "name": "开灯", // 插件名称
    "action": "turn_on", // 设备端指令标识，仅允许 [a-zA-Z0-9_]，长度 1-64
    "description": "打开设备灯", // 描述
    "input_params": [ // 输入参数定义，各子字段见下方注释
      {
        "name": "mode", // 可选，输入参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "开灯模式", // 可选，输入参数含义
        "required": false, // 是否必填，未传时为 false
        "enum": ["normal", "night"], // 可选，允许值列表
        "default_value": "normal" // 可选，默认值的字符串表示
      }
    ],
    "return_params": [ // 返回值定义，格式同 input_params
      {
        "name": "result", // 可选，返回参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "执行结果", // 可选，返回参数含义
        "required": true, // 是否必填，未传时为 false
        "enum": ["ok", "failed"], // 可选，允许值列表
        "default_value": "ok" // 可选，默认值的字符串表示
      }
    ],
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**完整字段**：请求和返回的所有子字段见 [AI 资源字段](#ai-资源字段)中的设备插件对象。

<a id="get-v1aipluginsid"></a>

##### 查询设备插件

**接口**：`GET /v1/ai/plugins/:id`

**调用方**：Web（含小程序内嵌页面）。

查看单个设备插件。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户可访问的插件 ID |

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "plg_001", // 只读，设备插件 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "name": "开灯", // 名称
    "action": "turn_on", // 设备指令标识，须与设备实现一致
    "description": "打开设备灯", // 说明文本
    "input_params": [ // 可选，设备指令的输入参数定义
      {
        "name": "mode", // 可选，输入参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "开灯模式", // 可选，输入参数含义
        "required": false, // 是否必填，未传时为 false
        "enum": ["normal", "night"], // 可选，允许值列表
        "default_value": "normal" // 可选，默认值的字符串表示
      }
    ],
    "return_params": [ // 可选，设备指令的返回参数定义
      {
        "name": "result", // 可选，返回参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "执行结果", // 可选，返回参数含义
        "required": true, // 是否必填，未传时为 false
        "enum": ["ok", "failed"], // 可选，允许值列表
        "default_value": "ok" // 可选，默认值的字符串表示
      }
    ],
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**返回字段**：`data` 为设备插件对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="put-v1aipluginsid"></a>

##### 更新设备插件

**接口**：`PUT /v1/ai/plugins/:id`

**调用方**：Web（含小程序内嵌页面）。

更新设备插件。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**：[AI 资源字段](#ai-资源字段)中的设备插件对象。`name`、`action` 必填；`description`、`input_params`、`return_params` 可选；`id`、`app_id` 和时间字段只用于返回。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的插件 ID |

**请求示例**

```jsonc
{
  "name": "开灯", // 名称
  "action": "turn_on", // 设备指令标识，须与设备实现一致
  "description": "打开设备灯", // 说明文本
  "input_params": [ // 可选，设备指令的输入参数定义
    {
      "name": "mode", // 可选，输入参数名称
      "type": "string", // 参数类型：string/integer/boolean/array/object
      "description": "开灯模式", // 可选，输入参数含义
      "required": false, // 是否必填，未传时为 false
      "enum": ["normal", "night"], // 可选，允许值列表
      "default_value": "normal" // 可选，默认值的字符串表示
    }
  ],
  "return_params": [ // 可选，设备指令的返回参数定义
    {
      "name": "result", // 可选，返回参数名称
      "type": "string", // 参数类型：string/integer/boolean/array/object
      "description": "执行结果", // 可选，返回参数含义
      "required": true, // 是否必填，未传时为 false
      "enum": ["ok", "failed"], // 可选，允许值列表
      "default_value": "ok" // 可选，默认值的字符串表示
    }
  ]
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "id": "plg_001", // 只读，设备插件 ID
    "app_id": "2818153", // 只读，云端应用 ID
    "name": "开灯", // 名称
    "action": "turn_on", // 设备指令标识，须与设备实现一致
    "description": "打开设备灯", // 说明文本
    "input_params": [ // 可选，设备指令的输入参数定义
      {
        "name": "mode", // 可选，输入参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "开灯模式", // 可选，输入参数含义
        "required": false, // 是否必填，未传时为 false
        "enum": ["normal", "night"], // 可选，允许值列表
        "default_value": "normal" // 可选，默认值的字符串表示
      }
    ],
    "return_params": [ // 可选，设备指令的返回参数定义
      {
        "name": "result", // 可选，返回参数名称
        "type": "string", // 参数类型：string/integer/boolean/array/object
        "description": "执行结果", // 可选，返回参数含义
        "required": true, // 是否必填，未传时为 false
        "enum": ["ok", "failed"], // 可选，允许值列表
        "default_value": "ok" // 可选，默认值的字符串表示
      }
    ],
    "created_at": "2026-09-01T10:00:00Z", // 只读，创建时间，保留云端返回格式
    "updated_at": "2026-09-01T10:00:00Z" // 只读，更新时间，保留云端返回格式
  }
}
```

**返回字段**：`data` 为设备插件对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="delete-v1aipluginsid"></a>

##### 删除设备插件

**接口**：`DELETE /v1/ai/plugins/:id`

**调用方**：Web（含小程序内嵌页面）。

删除设备插件。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**设备插件通用错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或 name/action 缺失 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 插件不属于当前用户（无权操作） |
| 40400 | 404 | 插件不存在 |
| 42900 | 429 | 插件创建额度已用尽（受 `tirtc_aichat.resource_quota.device_plugin` 限制） |
| 50200 | 502 | AI 服务暂不可用 |
| 50000 | 500 | 服务器内部错误 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的插件 ID |

**请求体**：无。

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

无 `data` 字段。

---

#### 知识库管理

> 探鸽云知识库 CRUD 代理。支持索引管理、文档列表和文件管理。所有接口需鉴权。

<a id="get-v1aiknowledgeindexes"></a>

##### 列出知识库索引

**接口**：`GET /v1/ai/knowledge/indexes`

**调用方**：Web（含小程序内嵌页面）。

列出当前用户创建的知识库索引，以及配置为全局默认的知识库索引。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 当前用户资源与配置的默认资源引用
      {
        "id": "idx_001", // 只读，知识库索引引用 ID
        "name": "产品手册" // 资源名称
      }
    ],
    "total": 1 // 返回的 items 数量
  }
}
```

> 列表从本地索引读取，仅返回 `{id, name}` 引用；`total` 等于 `items` 数量，包含当前
> 用户资源和配置的默认资源。索引完整信息见 `GET /v1/ai/knowledge/indexes/:id`；
> 索引下文档见 `GET /v1/ai/knowledge/indexes/:id/documents`。

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 当前用户资源与配置的默认资源引用 |
| `data.items[].id` | string | 资源 ID，用于查询详情 |
| `data.items[].name` | string | 资源名称 |
| `data.total` | integer | 返回的 items 数量 |

**请求参数**：无。

<a id="post-v1aiknowledgeindexes"></a>

##### 创建知识库索引

**接口**：`POST /v1/ai/knowledge/indexes`

**调用方**：Web（含小程序内嵌页面）。

创建知识库索引。返回的 `data` 为[AI 资源字段](#ai-资源字段)中的知识库索引对象，包含 `index_id`、`name` 及可选的 `description`、`document_ids`。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | ✅ | 索引名称 |
| description | string | ✅ | 索引描述 |

**请求示例**

```jsonc
{
  "name": "产品手册", // 必填，索引名称
  "description": "产品知识库" // 必填，索引描述
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "index_id": "idx_001", // 知识库索引 ID
    "name": "产品手册", // 索引名称
    "description": "产品知识库", // 索引描述
    "document_ids": [] // 关联的文档 ID 列表，不是上传文件 ID
  }
}
```

<a id="get-v1aiknowledgeindexesid"></a>

##### 查询知识库索引

**接口**：`GET /v1/ai/knowledge/indexes/:id`

**调用方**：Web（含小程序内嵌页面）。

查看单个知识库索引。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户可访问的知识库索引 ID |

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "index_id": "idx_001", // 知识库索引 ID
    "name": "产品手册", // 名称
    "description": "产品知识库", // 说明文本
    "document_ids": ["doc_001"] // 关联的文档 ID 列表，不是上传文件 ID
  }
}
```

**返回字段**：`data` 为知识库索引返回对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="put-v1aiknowledgeindexesid"></a>

##### 更新知识库索引

**接口**：`PUT /v1/ai/knowledge/indexes/:id`

**调用方**：Web（含小程序内嵌页面）。

更新知识库索引。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| name | string | | 索引名称 |
| description | string | | 索引描述 |
| document_ids | string[] | | 关联文档 ID 列表 |

**请求示例**

```jsonc
{
  "name": "产品手册 v2", // 可选，索引名称
  "description": "产品知识库", // 可选，索引描述
  "document_ids": ["doc_001", "doc_003"] // 可选，关联文档 ID 列表
}
```

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的知识库索引 ID |

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "index_id": "idx_001", // 知识库索引 ID
    "name": "产品手册 v2", // 索引名称
    "description": "产品知识库", // 索引描述
    "document_ids": ["doc_001", "doc_003"] // 关联文档 ID 列表
  }
}
```

**返回字段**：`data` 为知识库索引返回对象，完整字段及嵌套配置见 [AI 资源字段](#ai-资源字段)。

<a id="delete-v1aiknowledgeindexesid"></a>

##### 删除知识库索引

**接口**：`DELETE /v1/ai/knowledge/indexes/:id`

**调用方**：Web（含小程序内嵌页面）。

删除知识库索引。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 路径参数，当前用户创建的知识库索引 ID |

**请求体**：无。

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

无 `data` 字段。

<a id="get-v1aiknowledgeindexesiddocumentspage1page_size20"></a>

##### 分页查询知识库文档

**接口**：`GET /v1/ai/knowledge/indexes/:id/documents?page=1&page_size=20`

**调用方**：Web（含小程序内嵌页面）。

分页列出索引下的文档。当前用户必须拥有该索引，配置的默认知识库也允许读取。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

非当前用户资源返回 HTTP 403 + `code=40300`，并且不会向上游 AI 服务查询。

**查询参数**

| 参数 | 必填 | 默认值 | 说明 |
|------|:--:|:--:|------|
| page | | 1 | 页码；非正整数按默认值处理 |
| page_size | | 20 | 每页条数，范围 1–100；非法值按默认值处理 |

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 本页文档列表
      {
        "document_id": "doc_001", // 文档 ID
        "name": "快速入门.pdf", // 文档名称
        "status": "ready", // 可选，云端文档处理状态；服务端不固定枚举
        "size": 102400, // 可选，文档大小，单位字节
        "modified_at": 1720000000 // 可选，云端最后修改时间戳
      }
    ],
    "total": 2 // 上游返回的文档总数
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 本页文档列表 |
| `data.total` | integer | 上游返回的文档总数 |
| `data.items[].document_id` | string | 文档 ID |
| `data.items[].name` | string | 文档名称 |
| `data.items[].status` | string | 可选，云端文档处理状态；服务端不固定枚举 |
| `data.items[].size` | integer | 可选，文档大小，单位字节 |
| `data.items[].modified_at` | integer | 可选，云端最后修改时间戳 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 当前用户可访问的知识库索引 ID |

**空列表**：上游返回空数组时 `data.items` 为 `[]`；上游省略列表或返回 `null` 时，本接口的 `data.items` 也为 `null`。客户端需兼容这两种无结果形式。

<a id="get-v1aiknowledgefiles"></a>

##### 列出知识库文件

**接口**：`GET /v1/ai/knowledge/files`

**调用方**：Web（含小程序内嵌页面）。

列出当前用户已上传的知识库文件。服务端按本地所有权记录过滤上游结果，
不会返回其他用户上传的文件。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "items": [ // 当前用户拥有的文件
      {
        "file_id": "file_001", // 文件 ID
        "file_name": "manual.pdf", // 文件名称
        "file_type": "pdf", // 可选，文件类型
        "status": "done", // 可选，云端处理状态；服务端不固定枚举
        "size_in_bytes": 204800, // 可选，文件大小，单位字节
        "create_time": "2026-01-01T00:00:00Z" // 可选，云端创建时间
      }
    ]
  }
}
```

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.items` | object[] | 当前用户拥有的文件 |
| `data.items[].file_id` | string | 文件 ID |
| `data.items[].file_name` | string | 文件名称 |
| `data.items[].file_type` | string | 可选，文件类型 |
| `data.items[].status` | string | 可选，云端处理状态；服务端不固定枚举 |
| `data.items[].size_in_bytes` | integer | 可选，文件大小，单位字节 |
| `data.items[].create_time` | string | 可选，云端创建时间 |

**请求参数**：无。

<a id="post-v1aiknowledgefiles"></a>

##### 上传知识库文件

**接口**：`POST /v1/ai/knowledge/files`

**调用方**：Web（含小程序内嵌页面）。

上传知识库文件。上传成功后，文件 ID 会记录为当前用户资源，供后续列表
过滤和删除鉴权使用。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**Content-Type**: `multipart/form-data`

| 表单字段 | 类型 | 必填 | 说明 |
|----------|------|:--:|------|
| file | file | ✅ | 要上传的文件；服务端保留原始文件名并转发给上游 AI 服务 |

**请求示例**

`AI_SERVER` 为 ai-server 根地址，`USER_JWT` 为用户登录返回的 token，`manual.pdf` 为本地文件。`curl -F` 自动设置 multipart boundary。

```bash
# file 是必填文件字段；不手工设置 Content-Type。
curl -X POST "$AI_SERVER/v1/ai/knowledge/files" \
  -H "Authorization: Bearer $USER_JWT" \
  -F "file=@manual.pdf"
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "file_id": "file_001" // 上传后的文件 ID
  }
}
```

**错误码**： `40000`（缺少 file 或读取失败）、`401`（鉴权失败）、`50200`（上游 AI 服务不可用）、`50000`（上传响应缺少文件 ID 或本地所有权记录失败）

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.file_id` | string | 上传后的文件 ID |

<a id="delete-v1aiknowledgefilesid"></a>

##### 删除知识库文件

**接口**：`DELETE /v1/ai/knowledge/files/:id`

**调用方**：Web（含小程序内嵌页面）。

删除当前用户拥有的知识库文件。文件 ID 不属于当前用户时返回 HTTP 403 +
`code=40300`，且不会调用上游删除接口。

**鉴权**：`Authorization: Bearer <user_jwt>`（用户 JWT）

**知识库错误码**

| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | 请求体解析失败或必填字段缺失 |
| 401 | 401 | 未登录或 token 无效 |
| 40300 | 403 | 索引或知识文件不属于当前用户，或无权访问该资源 |
| 40400 | 404 | 单项索引不存在 |
| 42900 | 429 | 创建索引额度已用尽（受 `tirtc_aichat.resource_quota.kb` 限制） |
| 50200 | 502 | AI 服务暂不可用 |
| 50000 | 500 | 服务器内部错误 |

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | string | 是 | 当前用户上传的文件 ID |

**请求体**：无。

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

无 `data` 字段。

---

<a id="post-v1aiinternalunbind"></a>

### 清理设备业务关联（内部）

**接口**：`POST /v1/ai/internal/unbind`

**调用方**：内部服务。

服务间调用：设备解绑后删除本地设备角色绑定，并清理 AI 云服务中的设备角色绑定。

**鉴权**：`X-Internal-Key` 请求头，值需匹配服务端配置的内部调用密钥。

**请求体**：

```jsonc
{
  "device_id": "TIRZ00000001" // 必填，需要清理业务关联的设备 ID
}
```



**成功响应**：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



| code | HTTP | 含义 |
|------|------|------|
| 40000 | 400 | JSON 解析失败或缺少 device_id |
| 40301 | 403 | 内部服务凭证未配置或不匹配 |
| 50200 | 502 | AI 云服务解绑失败 |
| 50000 | 500 | 本地设备角色绑定清理失败 |

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 需要清理业务关联的设备 ID |

---

<a id="call-server"></a>

## 设备互呼与联系人

服务：`call-server`

提供设备间音视频通话，以及设备端和 Web 端的联系人管理接口。

> **响应格式约定：**
>
> - 成功时返回 HTTP 200 + `code=200`。
> - 业务失败时返回 HTTP 200 + 非 200 业务码。
> - JWT 中间件鉴权失败返回 HTTP 401 + `code=401`。
> - JWT 鉴权后的资源权限错误使用 `40300`，内部服务凭证错误使用 `40301`。
> - 所有端点都可能返回 HTTP 200 + `code=50000`（服务器内部错误），下列端点不再重复列出该通用错误。
>
> **跨域**: call-server 不加 CORS。H5 联系人页面通过 nginx 反向代理跟 user-server 统一到同一个域名下（见 [`thing-connect.nginx.conf`](deploy/nginx/thing-connect.nginx.conf)：公开 `/v1/call/*` 接口转发到 call-server，页面由 user-server 提供；内部接口禁止公网访问），浏览器全程同源。

### 设备端接口

用于设备发起和处理通话、管理本机联系人。请求头使用 `Authorization: Bearer <mqtt_token>`（正式设备 JWT）。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [发起设备呼叫](#post-v1callrequest) | 设备 | POST | `/v1/call/request` | 必需：正式设备 JWT（mqtt_token） |
| [获取接听凭证](#post-v1calldeviceinfo) | 设备 | POST | `/v1/call/device/info` | 必需：正式设备 JWT（mqtt_token） |
| [拒绝呼叫](#post-v1callreject) | 设备 | POST | `/v1/call/reject` | 必需：正式设备 JWT（mqtt_token） |
| [挂断通话](#post-v1callhangup) | 设备 | POST | `/v1/call/hangup` | 必需：正式设备 JWT（mqtt_token） |
| [取消呼叫](#post-v1callcancel) | 设备 | POST | `/v1/call/cancel` | 必需：正式设备 JWT（mqtt_token） |
| [查询一对一通话房间](#get-v1callroom) | 设备 | GET | `/v1/call/room` | 必需：正式设备 JWT（mqtt_token） |
| [查询本机联系人](#get-v1calldevicecontacts) | 设备 | GET | `/v1/call/device/contacts` | 必需：正式设备 JWT（mqtt_token） |
| [查询本机待审批申请](#get-v1calldevicecontactspending) | 设备 | GET | `/v1/call/device/contacts/pending` | 必需：正式设备 JWT（mqtt_token） |
| [发起联系人申请](#post-v1calldevicecontactsrequest) | 设备 | POST | `/v1/call/device/contacts/request` | 必需：正式设备 JWT（mqtt_token） |
| [审批联系人申请](#post-v1calldevicecontactsrespond) | 设备 | POST | `/v1/call/device/contacts/respond` | 必需：正式设备 JWT（mqtt_token） |
| [修改本机联系人备注](#put-v1calldevicecontactsremark) | 设备 | PUT | `/v1/call/device/contacts/remark` | 必需：正式设备 JWT（mqtt_token） |
| [删除本机联系人](#delete-v1calldevicecontacts) | 设备 | DELETE | `/v1/call/device/contacts` | 必需：正式设备 JWT（mqtt_token） |

<a id="post-v1callrequest"></a>

#### 发起设备呼叫

**接口**：`POST /v1/call/request`

**调用方**：设备。

发起呼叫（一对多）。

**鉴权**： ✅ `Authorization: Bearer <mqtt_token>`（设备 JWT，含 `device_id` claim）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| targets | string[] | ✅ | 被叫设备 ID 数组 |
| call_type | string | ✅ | `audio` 或 `video` |

**请求示例**

```jsonc
{
  "targets": ["TIRZ00000002", "TIRZ00000003"], // 必填，被叫设备 ID 数组
  "call_type": "video" // 必填，audio 或 video
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e", // 房间 ID，格式 d_roomid_ + 32 位十六进制（UUID v4 去横线）
    "online": { // 目标设备在线状态映射，true=在线、false=离线
      "TIRZ00000002": true, // 映射键为被叫设备 ID，值表示是否在线
      "TIRZ00000003": false // 映射键为被叫设备 ID，值表示是否在线
    },
    "offline": ["TIRZ00000003"] // string[] / null；建房时离线的设备 ID 列表，直接计入 rejected_by；所有被叫在线时为 null
  }
}
```

| 字段 | 说明 |
|------|------|
| room_id | 房间 ID，格式 `d_roomid_` + 32 位十六进制（UUID v4 去横线） |
| online | 目标设备在线状态映射，`true`=在线、`false`=离线 |
| offline | string[] / null；建房时离线的设备 ID 列表，直接计入 rejected_by；所有被叫在线时为 null |

> `room_id` 前缀 `d_` 与微信 VoIP 的 `wx_room_id` 区分，避免跨系统排查时混淆。

**错误码**

| code | 含义 |
|------|------|
| 40000 | targets 为空或 call_type 不是 audio/video，或呼叫了自己 |
| 40205 | 存在非"已接受"联系人的 target（整单失败，不做部分过滤） |
| 40201 | 所有 target 均离线 |
| 40202 | 主叫已在其他房间中（`data.room_id` 为已有房间，需先 `/v1/call/hangup` 或 `/v1/call/cancel` 才能重呼） |

> 建房间时离线的 target 直接计入 `rejected_by`（它们收不到 `call_incoming`，永远不会主动拒接）。

---

<a id="post-v1calldeviceinfo"></a>

#### 获取接听凭证

**接口**：`POST /v1/call/device/info`

**调用方**：设备。

接听来电（`purpose=call`）。该操作会执行 SETNX/DEL 并发送 MQTT 通知，因此使用 POST。

**鉴权**： ✅ `Authorization: Bearer <mqtt_token>`（设备 JWT）

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| device_id | string | ✅ | 主叫设备 ID（从 `call_incoming` 中获取） |
| room_id | string | ✅ | 房间 ID（从 `call_incoming` 中获取） |
| purpose | string | ✅ | 必须是 `"call"`（call-server 不实现 `live_preview`） |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，主叫设备 ID（从 call_incoming 中获取）
  "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e", // 必填，房间 ID（从 call_incoming 中获取）
  "purpose": "call" // 必填，必须是 "call"（call-server 不实现 live_preview）
}
```

**成功响应**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "token": "<实际返回的 token>", // 被叫连接主叫所需的 TiRTC token
    "device_id": "TIRZ00000001" // 主叫设备 ID
  }
}
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 401 | 401 | JWT 鉴权失败 |
| 40000 | 200 | 缺少 device_id/room_id，或 purpose 不是 call |
| 40210 | 200 | 房间已被其他设备抢接 |
| 40300 | 200 | 调用者不是该房间的合法 caller/target |
| 40400 | 200 | 房间不存在（已取消或已过期） |

> 接听者如果已锁定在另一个房间，服务端会先释放原房间，并通过 `room_cancel{reason:"caller_left"}` 通知原房间对方，然后接听新来电。该流程没有“忙”分支；设备不想切换房间时，应调用 `/v1/call/reject` 拒接。

**返回字段说明**

| 字段 | 类型 | 说明 |
|---|---|---|
| `data.token` | string | 被叫连接主叫所需的 TiRTC token |
| `data.device_id` | string | 主叫设备 ID |

---

<a id="post-v1callreject"></a>

#### 拒绝呼叫

**接口**：`POST /v1/call/reject`

**调用方**：设备。

拒接来电。

**鉴权**： ✅ 设备 JWT，且必须是该房间的 target 之一

**请求体**：

```jsonc
{
  "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e", // 必填，要拒绝的一对一通话房间 ID
  "reason": "busy" // 可选，拒绝原因，默认 decline；传入值转发给主叫
}
```

（`reason` 建议值 `busy` | `decline`，默认 `decline`；服务端不校验，原样透传给对端）

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



**错误码**： `401`（JWT 鉴权失败，HTTP 401）、`40000`（缺 room_id）、`40300`（不是该房间 target，HTTP 200）、`40400`（房间不存在）

> 所有 target（含离线预拒接的）都拒接后，房间解散，主叫收到 `room_cancel{reason:"all_rejected"}`。

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_id` | string | 是 | 要拒绝的一对一通话房间 ID |
| `reason` | string | 否 | 拒绝原因，默认 decline；传入值转发给主叫 |

---

<a id="post-v1callhangup"></a>

#### 挂断通话

**接口**：`POST /v1/call/hangup`

**调用方**：设备。

挂断，释放房间。**鉴权**： ✅ 设备 JWT，且必须是 caller 或 answered_by。

**请求体**：

```jsonc
{
  "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e", // 必填，已接通的一对一通话房间 ID
  "reason": "hangup" // 可选，默认 hangup；可传 p2p_error 等原因，原样转发
}
```

（`reason` 建议值 `hangup` | `p2p_error`，默认 `hangup`；服务端不校验，原样透传给对端）

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



**错误码**： `401`（JWT 鉴权失败，HTTP 401）、`40000`、`40300`（不是 caller/answered_by，HTTP 200）、`40400`

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_id` | string | 是 | 已接通的一对一通话房间 ID |
| `reason` | string | 否 | 默认 hangup；可传 p2p_error 等原因，原样转发 |

---

<a id="post-v1callcancel"></a>

#### 取消呼叫

**接口**：`POST /v1/call/cancel`

**调用方**：设备。

主叫取消呼叫（仅 caller 可调用）。**鉴权**： ✅ 设备 JWT。

**请求体**：

```jsonc
{
  "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e" // 必填，主叫要取消的房间 ID
}
```



**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



**错误码**： `401`（JWT 鉴权失败，HTTP 401）、`40000`、`40300`（非 caller，HTTP 200）、`40400`

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_id` | string | 是 | 主叫要取消的房间 ID |

---

<a id="get-v1callroom"></a>

#### 查询一对一通话房间

**接口**：`GET /v1/call/room`

**调用方**：设备。

查询当前设备的一对一通话房间，用于进程重启后恢复状态。多人对讲的房间关系使用 [`GET /v1/call/group/device/assignment`](#get-v1callroomdeviceassignment) 查询。

**鉴权**： ✅ 设备 JWT

**成功响应** — 不在一对一通话房间时省略 `data`；这不表示设备未加入多人对讲房间

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "room_id": "d_roomid_c5b745c0bf61494e84a8432b199a693e", // 一对一通话房间 ID，格式 d_roomid_ + 32 位十六进制；不能用于多人对讲接口
    "status": "answered", // active=呼叫中（未接听）、answered=已接听
    "caller": "TIRZ00000001", // 主叫设备 ID
    "call_type": "video", // audio 或 video
    "role": "callee" // 当前设备在该房间中的角色：caller 或 callee
  }
}
```

| 字段 | 说明 |
|------|------|
| room_id | 一对一通话房间 ID，格式 `d_roomid_` + 32 位十六进制；不能用于多人对讲接口 |
| status | `active`=呼叫中（未接听）、`answered`=已接听 |
| caller | 主叫设备 ID |
| call_type | `audio` 或 `video` |
| role | 当前设备在该房间中的角色：`caller` 或 `callee` |

**请求参数**：无。

---

<a id="get-v1calldevicecontacts"></a>

#### 查询本机联系人

**接口**：`GET /v1/call/device/contacts`

**调用方**：设备。

设备侧联系人列表，同时返回**设备联系人**（`call_contact` 表）和 **VoIP 联系人**（`voip_device_auth` 表，微信小程序授权用户）。用 `type` 字段区分。

**鉴权**： ✅ 设备 JWT。

**成功响应**

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "contacts": [ // 联系人对象数组；没有联系人时为 []
      {
        "device_id": "TIRZ00000002", // device 联系人为对方设备 ID；voip 联系人为 wx_open_id（无独立设备身份）
        "type": "device", // 联系人类型：device（设备联系人）或 voip（微信授权联系人）；设备必须按此字段选择呼叫接口
        "remark": "门铃", // device 为本设备对该联系人的备注；voip 为当前 wx_open_id + wx_app_id 的统一联系人名称；未设置时为空字符串
        "source": "manual", // 联系人来源：manual（跨账号申请）、auto（同账号自动关联）或 voip（小程序授权）
        "online": true // 对方设备当前是否在线
      },
      {
        "id": 3, // voip_device_auth 表主键；PUT /v1/call/device/contacts/remark 不使用它，而是使用 peer_id
        "device_id": "<实际返回的 device_id>", // device 联系人为对方设备 ID；voip 联系人为 wx_open_id（无独立设备身份）
        "type": "voip", // 联系人类型：device（设备联系人）或 voip（微信授权联系人）；设备必须按此字段选择呼叫接口
        "source": "voip", // 联系人来源：manual（跨账号申请）、auto（同账号自动关联）或 voip（小程序授权）
        "remark": "妈妈", // device 为本设备对该联系人的备注；voip 为当前 wx_open_id + wx_app_id 的统一联系人名称；未设置时为空字符串
        "wx_open_id": "<实际返回的 wx_open_id>", // 微信用户 OpenID；与该项的 device_id 相同
        "wx_app_id": "<实际返回的 wx_app_id>", // 授权所属的微信小程序 AppID
        "wx_model_id": "<实际返回的 wx_model_id>" // 授权对应的微信设备型号 ID；发起 VoIP 外呼时由 voip-server 从授权记录读取
      }
    ]
  }
}
```

`code`、`msg` 遵循 call-server 的统一响应约定；`data` 字段如下。标记为“仅 device”或
“仅 voip”的字段在另一种联系人对象中不返回，而不是返回 `null`。

| 字段 | 适用 type | 说明 |
|------|:--:|------|
| data.contacts | — | 联系人对象数组；没有联系人时为 `[]` |
| data.contacts[].device_id | 全部 | device 联系人为对方设备 ID；voip 联系人为 `wx_open_id`（无独立设备身份） |
| data.contacts[].type | 全部 | 联系人类型：`device`（设备联系人）或 `voip`（微信授权联系人）；设备必须按此字段选择呼叫接口 |
| data.contacts[].id | 仅 voip | `voip_device_auth` 表主键；`PUT /v1/call/device/contacts/remark` 不使用它，而是使用 `peer_id` |
| data.contacts[].remark | 全部 | device 为本设备对该联系人的备注；voip 为当前 `wx_open_id + wx_app_id` 的统一联系人名称；未设置时为空字符串 |
| data.contacts[].source | 全部 | 联系人来源：`manual`（跨账号申请）、`auto`（同账号自动关联）或 `voip`（小程序授权） |
| data.contacts[].online | 仅 device | 对方设备当前是否在线 |
| data.contacts[].wx_open_id | 仅 voip | 微信用户 OpenID；与该项的 `device_id` 相同 |
| data.contacts[].wx_app_id | 仅 voip | 授权所属的微信小程序 AppID |
| data.contacts[].wx_model_id | 仅 voip | 授权对应的微信设备型号 ID；发起 VoIP 外呼时由 voip-server 从授权记录读取 |

> **设备联系人**：同账号下的其他设备会在首次拉取时懒创建为 `source:"auto"` 的已接受联系人（无需事件驱动）。跨账号需走 `request`/`respond` 申请流程。
>
> **VoIP 联系人**：只要用户在小程序完成授权（`voip-server` 的 `POST /v1/voip/user/report-auth`）即出现在列表里，无需设备侧申请/审批。设备呼叫时根据 `type` 选择走 `POST /v1/call/request`（device）还是 `POST /v1/voip/device/call`（voip），两条呼叫链路完全独立。

**请求参数**：无。

---

<a id="get-v1calldevicecontactspending"></a>

#### 查询本机待审批申请

**接口**：`GET /v1/call/device/contacts/pending`

**调用方**：设备。

查询当前设备可以审批的联系人申请。只返回当前设备是非发起方的 pending 请求。

**鉴权**： ✅ 设备 JWT

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "pending": [ // 当前设备可审批的联系人申请；没有待审批申请时为 []
      {
        "type": "device", // 联系人类型；申请流程只适用于设备联系人，因此固定为 device
        "peer_device_id": "TIRZ00000001", // 发起申请的对方设备 ID；审批时作为 peer_device_id
        "created_at": "2026-07-22T14:00:00+08:00" // 申请创建时间，RFC 3339 格式
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| data.pending | object[] | 当前设备可审批的联系人申请；没有待审批申请时为 `[]` |
| data.pending[].type | string | 联系人类型；申请流程只适用于设备联系人，因此固定为 `device` |
| data.pending[].peer_device_id | string | 发起申请的对方设备 ID；审批时作为 `peer_device_id` |
| data.pending[].created_at | string | 申请创建时间，RFC 3339 格式 |

收到 `channel:"device"` 的 `callers_update` 后，设备应同时刷新联系人列表和 pending 列表。当前没有 `contacts_update` 事件。

`callers_update.payload` 字段：

| 字段 | 说明 |
|------|------|
| action | `request`（申请）/ `accept`（同意）/ `reject`（拒绝）/ `delete`（删除）/ `remark`（备注变化） |
| contact_type | `device` 或 `voip`；联系人申请相关动作固定为 `device` |
| peer_id | 对端标识；device 为设备 ID，voip 为 `wx_open_id` |

**请求参数**：无。

---

<a id="post-v1calldevicecontactsrequest"></a>

#### 发起联系人申请

**接口**：`POST /v1/call/device/contacts/request`

**调用方**：设备。

发起跨账号联系人申请。同账号设备会直接自动接受，不走 pending 流程。该接口只适用于设备联系人；VoIP 联系人没有申请流程。

**鉴权**： ✅ 设备 JWT

**请求体**：

```jsonc
{
  "target_device_id": "TIRZ00000002" // 必填，对端设备 ID，不可为本机
}
```



**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "status": "pending", // 跨账号申请为 pending；同账号设备直接建立联系人时为 accepted
    "source": "manual" // 跨账号申请为 manual；同账号自动联系人为 auto
  }
}
```

| 字段 | 说明 |
|------|------|
| data.status | 跨账号申请为 `pending`；同账号设备直接建立联系人时为 `accepted` |
| data.source | 跨账号申请为 `manual`；同账号自动联系人为 `auto` |

成功后向目标设备的 `device/sn_{target_device_id}/notify` 推送：

```jsonc
{
  "type": "callers_update", // 固定为 callers_update，通知设备刷新联系人
  "channel": "device", // 固定为 device，设备联系人通知通道
  "payload": { // 通知业务数据，字段含义如下
    "action": "request", // 联系人变更动作，本例 request 表示收到申请
    "contact_type": "device", // 联系人类型：device 或 voip；申请流程固定为 device
    "peer_id": "TIRZ00000001" // 申请发起方设备 ID
  }
}
```

目标设备收到后应提示联系人申请，并重新拉取联系人和 pending 列表。

**错误码**： `40000`（缺参数/呼叫自己）、`40400`（target 不存在）、`40206`（已是联系人）、`40207`（已有待处理申请）、`40209`（超过 `max_contacts_per_device`）

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `target_device_id` | string | 是 | 对端设备 ID，不可为本机 |

---

<a id="post-v1calldevicecontactsrespond"></a>

#### 审批联系人申请

**接口**：`POST /v1/call/device/contacts/respond`

**调用方**：设备。

审批联系人申请（仅接收方可调用）。

**鉴权**： ✅ 设备 JWT

**请求体**：

```jsonc
{
  "peer_device_id": "TIRZ00000001", // 必填，申请方设备 ID
  "action": "accept" // 必填，accept 同意或 reject 拒绝
}
```

（`action`: `accept` | `reject`）

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "status": "accepted" // 状态，枚举与含义见本接口字段表
  }
}
```

`data.status` 为审批后的状态：`accepted` 或 `rejected`。成功后向申请发起设备推送
`callers_update`。

**错误码**： `40000`、`40205`（申请不存在或非法响应）、`40209`（申请方或接收方联系人数量已达上限）

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `peer_device_id` | string | 是 | 申请方设备 ID |
| `action` | string | 是 | accept 同意或 reject 拒绝 |

---

<a id="put-v1calldevicecontactsremark"></a>

#### 修改本机联系人备注

**接口**：`PUT /v1/call/device/contacts/remark`

**调用方**：设备。

修改联系人备注，设备联系人和 VoIP 联系人统一走这一个接口，服务端按 `peer_id` 自动判断类型。
当 `peer_id` 是 VoIP 联系人的 `wx_open_id` 时，修改的是该 OpenID 的统一联系人名称，
同一小程序下所有已授权设备都会更新，并收到 `callers_update`；不是修改设备名称。

**鉴权**： ✅ 设备 JWT

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| peer_id | string | ✅ | 设备联系人传对方 `device_id`；VoIP 联系人传 `wx_open_id` |
| remark | string | | 备注内容，空字符串清空备注，最多 64 个 Unicode 字符 |

**请求示例**

```jsonc
{
  "peer_id": "TIRZ00000002", // 必填，设备联系人传对方 device_id；VoIP 联系人传 wx_open_id
  "remark": "门铃" // 可选，备注内容，空字符串清空备注，最多 64 个 Unicode 字符
}
```

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

响应不包含 `data` 字段。

**错误码**： `40000`（缺 peer_id 或 remark 超过 64 个字符）、`40205`（peer_id 既不是已接受的设备联系人，也不是本设备的 VoIP 授权用户）

---

<a id="delete-v1calldevicecontacts"></a>

#### 删除本机联系人

**接口**：`DELETE /v1/call/device/contacts`

**调用方**：设备。

删除已接受的跨账号手动联系人（`source:"manual"`，软删除为 status=3，**双向生效**：自己和对方都失去该联系人），成功后向对端推送 `channel:"device"` 的 `callers_update`，对端应重新拉取联系人。同账号 `source:"auto"` 联系人属于账号内设备拓扑，不允许删除；VoIP 联系人的移除走小程序取消授权，不在此接口。

**鉴权**： ✅ 设备 JWT

**查询参数**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:--:|------|
| peer_id | string | ✅ | 对方 `device_id` |

**请求示例**

```
DELETE /v1/call/device/contacts?peer_id=TIRZ00000002
```

**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

响应不包含 `data` 字段。

**错误码**： `40000`（缺 peer_id）、`40205`（联系人不存在、不是 accepted 状态或已删除）、`40211`（同账号 auto 联系人受保护，不允许删除）

**查询参数明细**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `peer_id` | string | 是 | 要删除的对端设备 ID |

**请求体**：无。

---

### Web 端联系人管理

由 `call-server` 提供，路径前缀为 `/v1/call/user/contacts`。用户可查询和管理自己绑定设备的联系人。

**鉴权**：请求头使用 `Authorization: Bearer <user_jwt>`。`user_jwt` 为注册或登录接口返回的 `token`，不能使用设备的 `mqtt_token`。凭证缺失、无效或过期时返回 HTTP 401、`code=401`；无权操作目标设备或联系人时返回 HTTP 200、`code=40300`。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [查询设备联系人](#get-v1callusercontactsdevice_idxxx) | Web | GET | `/v1/call/user/contacts` | 必需：用户 JWT（user_jwt） |
| [查询账号待审批申请](#get-v1callusercontactspending) | Web | GET | `/v1/call/user/contacts/pending` | 必需：用户 JWT（user_jwt） |
| [为设备申请联系人](#post-v1callusercontactsrequest) | Web | POST | `/v1/call/user/contacts/request` | 必需：用户 JWT（user_jwt） |
| [审批设备联系人申请](#post-v1callusercontactsrespond) | Web | POST | `/v1/call/user/contacts/respond` | 必需：用户 JWT（user_jwt） |
| [修改设备联系人备注](#put-v1callusercontactsremark) | Web | PUT | `/v1/call/user/contacts/remark` | 必需：用户 JWT（user_jwt） |
| [删除设备联系人](#delete-v1callusercontactsid) | Web | DELETE | `/v1/call/user/contacts/:id` | 必需：用户 JWT（user_jwt） |

<a id="get-v1callusercontactsdevice_idxxx"></a>

#### 查询设备联系人

**接口**：`GET /v1/call/user/contacts?device_id=xxx`

**调用方**：Web。

查询当前用户某台设备的完整联系人列表，同时返回设备联系人和 VoIP 联系人。

**查询参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前用户绑定的设备 ID |

**请求体**：无。

**成功响应**：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "contacts": [ // 指定设备的联系人对象数组；没有联系人时为 []
      {
        "id": 12, // 对应数据表的数字主键：device 来自 call_contact，voip 来自 voip_device_auth
        "device_id": "TIRZ00000002", // device 联系人为对方设备 ID；voip 联系人为 wx_open_id
        "type": "device", // device 或 voip
        "remark": "门铃", // device 为指定设备对该联系人的备注；voip 为当前 wx_open_id + wx_app_id 的统一联系人名称
        "source": "manual", // manual、auto 或 voip
        "online": true // 对方设备当前是否在线
      },
      {
        "id": 3, // 对应数据表的数字主键：device 来自 call_contact，voip 来自 voip_device_auth
        "device_id": "<实际返回的 device_id>", // device 联系人为对方设备 ID；voip 联系人为 wx_open_id
        "type": "voip", // device 或 voip
        "source": "voip", // manual、auto 或 voip
        "remark": "妈妈", // device 为指定设备对该联系人的备注；voip 为当前 wx_open_id + wx_app_id 的统一联系人名称
        "wx_open_id": "<实际返回的 wx_open_id>", // 微信用户 OpenID；与该项的 device_id 相同
        "wx_app_id": "<实际返回的 wx_app_id>", // 授权所属的微信小程序 AppID
        "wx_model_id": "<实际返回的 wx_model_id>" // 授权对应的微信设备型号 ID
      }
    ]
  }
}
```

| 字段 | 适用 type | 说明 |
|------|:--:|------|
| data.contacts | — | 指定设备的联系人对象数组；没有联系人时为 `[]` |
| data.contacts[].id | 全部 | 对应数据表的数字主键：device 来自 `call_contact`，voip 来自 `voip_device_auth` |
| data.contacts[].device_id | 全部 | device 联系人为对方设备 ID；voip 联系人为 `wx_open_id` |
| data.contacts[].type | 全部 | `device` 或 `voip` |
| data.contacts[].remark | 全部 | device 为指定设备对该联系人的备注；voip 为当前 `wx_open_id + wx_app_id` 的统一联系人名称 |
| data.contacts[].source | 全部 | `manual`、`auto` 或 `voip` |
| data.contacts[].online | 仅 device | 对方设备当前是否在线 |
| data.contacts[].wx_open_id | 仅 voip | 微信用户 OpenID；与该项的 `device_id` 相同 |
| data.contacts[].wx_app_id | 仅 voip | 授权所属的微信小程序 AppID |
| data.contacts[].wx_model_id | 仅 voip | 授权对应的微信设备型号 ID |

**错误码**：`40000`（缺少 `device_id`）、`40300`（设备不属于当前用户）。

<a id="get-v1callusercontactspending"></a>

#### 查询账号待审批申请

**接口**：`GET /v1/call/user/contacts/pending`

**调用方**：Web。

查询当前用户名下所有设备可以审批的联系人申请。

**成功响应**：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "pending": [ // 当前用户可审批的申请；没有待审批申请时为 []
      {
        "id": 12, // call_contact 表主键；审批时作为 POST /v1/call/user/contacts/respond 的 id
        "type": "device", // 联系人类型；申请流程只适用于设备联系人，因此固定为 device
        "initiator_device": "TIRZ00000001", // 发起申请的设备 ID
        "target_device": "TIRZ00000002", // 当前用户负责审批的接收设备 ID
        "created_at": "2026-07-22T14:00:00+08:00" // 申请创建时间，RFC 3339 格式
      }
    ]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| data.pending | object[] | 当前用户可审批的申请；没有待审批申请时为 `[]` |
| data.pending[].id | integer | `call_contact` 表主键；审批时作为 `POST /v1/call/user/contacts/respond` 的 `id` |
| data.pending[].type | string | 联系人类型；申请流程只适用于设备联系人，因此固定为 `device` |
| data.pending[].initiator_device | string | 发起申请的设备 ID |
| data.pending[].target_device | string | 当前用户负责审批的接收设备 ID |
| data.pending[].created_at | string | 申请创建时间，RFC 3339 格式 |

**请求参数**：无。

<a id="post-v1callusercontactsrequest"></a>

#### 为设备申请联系人

**接口**：`POST /v1/call/user/contacts/request`

**调用方**：Web。

**鉴权**：用户 JWT。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 本账号的发起设备 ID |
| `target_device_id` | string | 是 | 对端设备 ID，不可与本方相同 |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，本账号的发起设备 ID
  "target_device_id": "TIRZ00000002" // 必填，对端设备 ID，不可与本方相同
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "status": "pending", // 状态，枚举与含义见本接口字段表
    "source": "manual" // 联系人来源：manual 跨账号申请，auto 同账号自动关联
  }
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`。`data.status`（string）为 pending 或 accepted；`data.source`（string）为 manual 或 auto。同账号设备直接 accepted/auto。

**错误码**：JWT 失败为 HTTP 401 + `401`；业务错误为 HTTP 200。`40000` 参数错误、`40300` 无权操作、`40400` 联系人或设备不存在、`50000` 内部错误。已存在联系人或申请分别返回 `40206`、`40207`，数量达到上限返回 `40209`。

---

<a id="post-v1callusercontactsrespond"></a>

#### 审批设备联系人申请

**接口**：`POST /v1/call/user/contacts/respond`

**调用方**：Web。

**鉴权**：用户 JWT。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | integer | 是 | 待审批联系人记录 ID |
| `action` | string | 是 | accept 或 reject |

**请求示例**

```jsonc
{
  "id": 12, // 必填，待审批联系人记录 ID
  "action": "accept" // 必填，accept 或 reject
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "status": "accepted" // 状态，枚举与含义见本接口字段表
  }
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`。`data.status`（string）为 accepted 或 rejected。只能由申请接收方所属账号审批。

**错误码**：JWT 失败为 HTTP 401 + `401`；业务错误为 HTTP 200。`40000` 参数错误、`40300` 无权操作、`40205` 申请不存在或非法响应、`40209` 申请方或接收方联系人数量已达上限、`50000` 内部错误。

---

<a id="put-v1callusercontactsremark"></a>

#### 修改设备联系人备注

**接口**：`PUT /v1/call/user/contacts/remark`

**调用方**：Web。

**鉴权**：用户 JWT。

**请求体**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 本账号的设备 ID |
| `peer_id` | string | 是 | 对端设备 ID 或微信 OpenID |
| `remark` | string | 否 | 最多 64 个 Unicode 字符；空字符串清除备注 |

**请求示例**

```jsonc
{
  "device_id": "TIRZ00000001", // 必填，本账号的设备 ID
  "peer_id": "TIRZ00000002", // 必填，对端设备 ID 或微信 OpenID
  "remark": "门铃" // 可选，最多 64 个 Unicode 字符；空字符串清除备注
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`。无 `data` 字段。VoIP 名称同步到同一小程序下的授权设备。

**错误码**：JWT 失败为 HTTP 401 + `401`；业务错误为 HTTP 200。`40000` 参数错误、`40300` 无权操作、`40205` 申请不存在或非法响应、`40209` 申请方或接收方联系人数量已达上限、`50000` 内部错误。

---

<a id="delete-v1callusercontactsid"></a>

#### 删除设备联系人

**接口**：`DELETE /v1/call/user/contacts/:id`

**调用方**：Web。

**鉴权**：用户 JWT。

**路径参数**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | integer | 是 | 路径参数，manual 联系人的正整数记录 ID |

**请求体**：无。

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`。无 `data` 字段。auto 联系人不能删除，VoIP 联系人通过取消授权移除。

**错误码**：JWT 失败为 HTTP 401 + `401`；业务错误为 HTTP 200。`40000` 参数错误、`40300` 无权操作、`40205` 申请不存在或非法响应、`40209` 申请方或接收方联系人数量已达上限、`50000` 内部错误。受保护联系人返回 `40211`。

---

### 内部服务接口

仅供服务间调用，使用 `X-Internal-Key`，不对公网开放。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [清理设备业务关联（内部）](#post-v1callinternalunbind) | 内部服务 | POST | `/v1/call/internal/unbind` | 必需：内部密钥（X-Internal-Key） |

<a id="post-v1callinternalunbind"></a>

#### 清理设备业务关联（内部）

**接口**：`POST /v1/call/internal/unbind`

**调用方**：内部服务。

服务间调用：设备解绑时永久删除所有涉及该设备的 `call_contact` 记录（包括待审批、已拒绝和已软删除记录），释放房间，并向原有未删除联系人的对端发送 `callers_update`。

**鉴权**： `X-Internal-Key` 请求头，值需匹配配置 `internal.key`

**请求体**：

```jsonc
{
  "device_id": "TIRZ00000001" // 必填，需要清理业务关联的设备 ID
}
```



**成功响应**:

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok" // 结果说明，业务判断使用 code
}
```



**错误码**： `40301`（key 不匹配或未配置）、`40000`（缺 device_id）；错误仍使用 HTTP 200。

**请求体字段**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 需要清理业务关联的设备 ID |

---

## 多人对讲（call-server）

操作流程和设备信令见[设备多人对讲](device-room.md)。下列 JSON 接口均禁止缓存，请求体上限为 4096 字节。

每台设备同一时间只能加入一个多人对讲房间。设备已有房间关系时，创建新房间或加入其他房间会被拒绝；客户端须先调用退出接口，再创建或加入。

**公共请求头**

| 请求头 | 类型 | 必填条件与说明 |
|---|---|---|
| `Authorization` | string | JSON 接口必填，`Bearer <JWT>`；Web 接口用用户 JWT，设备接口用正式设备 JWT |
| `Content-Type` | string | POST 必填，`application/json` |

### Web 端接口

用于用户在 Web 页面查询和管理自己绑定设备的房间。JSON 接口使用 `Authorization: Bearer <user_jwt>`；对讲页面本身无需鉴权。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [打开多人对讲页面](#get-v1callroompage) | Web | GET | `/v1/call/group/page` | 页面无需鉴权；页面操作需用户 JWT |
| [查询设备的多人对讲房间](#get-v1callroomwebdevicedevice_id) | Web | GET | `/v1/call/group/web/device/:device_id` | 必需：用户 JWT（user_jwt） |
| [为设备创建多人对讲房间](#post-v1callroomwebdevicedevice_idcreate) | Web | POST | `/v1/call/group/web/device/:device_id/create` | 必需：用户 JWT（user_jwt） |
| [安排设备加入多人对讲](#post-v1callroomwebdevicedevice_idjoin) | Web | POST | `/v1/call/group/web/device/:device_id/join` | 必需：用户 JWT（user_jwt） |
| [安排设备退出多人对讲](#post-v1callroomwebdevicedevice_idleave) | Web | POST | `/v1/call/group/web/device/:device_id/leave` | 必需：用户 JWT（user_jwt） |

<a id="get-v1callroompage"></a>

#### 打开多人对讲页面

**接口**：`GET /v1/call/group/page`

**调用方**：Web。

返回多人对讲 H5 页面。HTML 本身无需鉴权，页面查询和操作仍需用户 JWT。

| 查询参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 页面操作需要 | 当前账号绑定的设备 ID |

**返回**：HTTP 200，`Content-Type: text/html; charset=utf-8`，正文为 HTML，无 JSON 返回字段。

<a id="get-v1callroomwebdevicedevice_id"></a>

#### 查询设备的多人对讲房间

**接口**：`GET /v1/call/group/web/device/:device_id`

**调用方**：Web。

**鉴权**：用户 JWT，只能操作自己绑定的设备。

| 路径参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前账号绑定的设备 ID |

**查询参数**：无。

**请求体**：无。

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomwebdevicedevice_idcreate"></a>

#### 为设备创建多人对讲房间

**接口**：`POST /v1/call/group/web/device/:device_id/create`

**调用方**：Web。

**鉴权**：用户 JWT，只能操作自己绑定的设备。

| 路径参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前账号绑定的设备 ID |

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `password` | string | 否 | 空字符串或省略表示无密码；设置时为四位 ASCII 数字 |

没有密码时也需发送 `{}`。创建成功后保存设备的加入关系。

设备已有房间关系时返回 `40923`，须先退出当前房间。

**请求示例**

```jsonc
{
  "password": "1234" // 可选，空字符串或省略表示无密码；设置时为四位 ASCII 数字
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomwebdevicedevice_idjoin"></a>

#### 安排设备加入多人对讲

**接口**：`POST /v1/call/group/web/device/:device_id/join`

**调用方**：Web。

**鉴权**：用户 JWT，只能操作自己绑定的设备。

| 路径参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前账号绑定的设备 ID |

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_code` | string | 是 | 六位 ASCII 数字房间号，保留前导零 |
| `password` | string | 有密码时 | 四位数字密码，无密码房间可省略 |

重复加入当前房间直接返回已有关系；设备已在其他房间时返回 `40923`，须先退出当前房间。

**请求示例**

```jsonc
{
  "room_code": "001234", // 必填，六位 ASCII 数字房间号，保留前导零
  "password": "1234" // 有密码时时提供，四位数字密码，无密码房间可省略
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomwebdevicedevice_idleave"></a>

#### 安排设备退出多人对讲

**接口**：`POST /v1/call/group/web/device/:device_id/leave`

**调用方**：Web。

**鉴权**：用户 JWT，只能操作自己绑定的设备。

| 路径参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `device_id` | string | 是 | 当前账号绑定的设备 ID |

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_id` | string | 否 | 原始房间 ID；省略或空字符串时不校验 |
| `assignment_version` | integer | 否 | 当前关系版本；省略或 0 时不校验，非零须与当前版本一致 |

发送 `{}` 表示退出当前房间；携带校验字段可避免误退出已切换的房间。

设备当前没有房间关系时直接返回成功，关系版本保持不变。

**请求示例**

```jsonc
{
  "room_id": "group_room_78c2cdf66ee1283cb84fcb15444fdf68", // 可选，原始房间 ID；省略或空字符串时不校验
  "assignment_version": 3 // 可选，当前关系版本；省略或 0 时不校验，非零须与当前版本一致
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

### 设备端接口

用于设备查询本机房间、加入或退出房间、领取连接凭证和上报状态。使用 `Authorization: Bearer <mqtt_token>`（正式设备 JWT），设备身份由 token 确定，不能使用用户 JWT 或临时设备 token。

**接口列表**

| 接口名称 | 调用方 | 方法 | 路径 | 鉴权要求与方式 |
|---|---|---|---|---|
| [查询本机多人对讲房间](#get-v1callroomdeviceassignment) | 设备 | GET | `/v1/call/group/device/assignment` | 必需：正式设备 JWT（mqtt_token） |
| [本机创建多人对讲房间](#post-v1callroomdevicecreate) | 设备 | POST | `/v1/call/group/device/create` | 必需：正式设备 JWT（mqtt_token） |
| [本机加入多人对讲房间](#post-v1callroomdevicejoin) | 设备 | POST | `/v1/call/group/device/join` | 必需：正式设备 JWT（mqtt_token） |
| [本机退出多人对讲房间](#post-v1callroomdeviceleave) | 设备 | POST | `/v1/call/group/device/leave` | 必需：正式设备 JWT（mqtt_token） |
| [领取多人对讲连接凭证](#post-v1callroomdeviceconnect-token) | 设备 | POST | `/v1/call/group/device/connect-token` | 必需：正式设备 JWT（mqtt_token） |
| [上报多人对讲状态和续租](#post-v1callroomdevicepresence) | 设备 | POST | `/v1/call/group/device/presence` | 必需：正式设备 JWT（mqtt_token） |

<a id="get-v1callroomdeviceassignment"></a>

#### 查询本机多人对讲房间

**接口**：`GET /v1/call/group/device/assignment`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**：无。

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomdevicecreate"></a>

#### 本机创建多人对讲房间

**接口**：`POST /v1/call/group/device/create`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `password` | string | 否 | 空字符串或省略表示无密码；设置时为四位 ASCII 数字 |

没有密码时也需发送 `{}`。创建成功后保存设备的加入关系。

设备已有房间关系时返回 `40923`，须先退出当前房间。

**请求示例**

```jsonc
{
  "password": "1234" // 可选，空字符串或省略表示无密码；设置时为四位 ASCII 数字
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomdevicejoin"></a>

#### 本机加入多人对讲房间

**接口**：`POST /v1/call/group/device/join`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_code` | string | 是 | 六位 ASCII 数字房间号，保留前导零 |
| `password` | string | 有密码时 | 四位数字密码，无密码房间可省略 |

重复加入当前房间直接返回已有关系；设备已在其他房间时返回 `40923`，须先退出当前房间。

**请求示例**

```jsonc
{
  "room_code": "001234", // 必填，六位 ASCII 数字房间号，保留前导零
  "password": "1234" // 有密码时时提供，四位数字密码，无密码房间可省略
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomdeviceleave"></a>

#### 本机退出多人对讲房间

**接口**：`POST /v1/call/group/device/leave`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `room_id` | string | 否 | 原始房间 ID；省略或空字符串时不校验 |
| `assignment_version` | integer | 否 | 当前关系版本；省略或 0 时不校验，非零须与当前版本一致 |

发送 `{}` 表示退出当前房间；携带校验字段可避免误退出已切换的房间。

设备当前没有房间关系时直接返回成功，关系版本保持不变。

**请求示例**

```jsonc
{
  "room_id": "group_room_78c2cdf66ee1283cb84fcb15444fdf68", // 可选，原始房间 ID；省略或空字符串时不校验
  "assignment_version": 3 // 可选，当前关系版本；省略或 0 时不校验，非零须与当前版本一致
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 的全部字段见[房间关系返回字段](#房间关系返回字段)。变更接口成功表示关系已保存，设备连接结果需再次查询。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomdeviceconnect-token"></a>

#### 领取多人对讲连接凭证

**接口**：`POST /v1/call/group/device/connect-token`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**（以下字段全部必填）

| 字段 | 类型 | 说明 |
|---|---|---|
| `room_id` | string | 原始业务房间 ID，长度 1–64 字节 |
| `assignment_version` | integer | 当前关系版本，大于 0 |
| `session_id` | string | 设备生成的会话 ID，长度 8–64 字节；每次重建连接使用新 ID |

**请求示例**

```jsonc
{
  "room_id": "group_room_78c2cdf66ee1283cb84fcb15444fdf68", // 原始业务房间 ID，长度 1–64 字节
  "assignment_version": 3, // 当前关系版本，大于 0
  "session_id": "<本次新生成的会话ID>" // 必填，本次新生成的会话 ID；保存并供 presence 复用
}
```

**成功响应示例**（HTTP 200）

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "peer_id": "<TiRTC返回的完整连接目标>", // TiRTC 连接目标
    "token": "<本设备的TiRTC连接凭证>", // 连接凭证，只供当前设备使用
    "heartbeat_seconds": 15, // 状态上报间隔，单位秒
    "lease_seconds": 45, // 连接租约时长，单位秒
    "expires_at": 1900000000 // 上游提供时返回的凭证到期时间
  }
}
```

**成功响应**：HTTP 200，`code=200`、`msg=ok`，`data` 为以下对象。

| 返回字段 | 类型 | 返回条件与说明 |
|---|---|---|
| `data.peer_id` | string | TiRTC 连接目标 |
| `data.token` | string | 连接凭证，只供当前设备使用 |
| `data.heartbeat_seconds` | integer | 状态上报间隔，单位秒 |
| `data.lease_seconds` | integer | 连接租约时长，单位秒 |
| `data.expires_at` | integer | 上游提供时返回的凭证到期时间 |

领取凭证会预占容量，尚不计入在线人数。使用凭证连接 TiRTC 并完成 `join_room` 后，再上报 `joined`。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

<a id="post-v1callroomdevicepresence"></a>

#### 上报多人对讲状态和续租

**接口**：`POST /v1/call/group/device/presence`

**调用方**：设备。

**鉴权**：正式设备 JWT，设备身份取自 token。

**查询参数**：无。

**请求体**（以下字段全部必填）

| 字段 | 类型 | 说明 |
|---|---|---|
| `room_id` | string | 原始业务房间 ID，长度 1–64 字节 |
| `assignment_version` | integer | 当前关系版本，大于 0 |
| `session_id` | string | 设备生成的会话 ID，长度 8–64 字节；每次重建连接使用新 ID |
| `state` | string | connecting、joined、suspended、left 或 connect_failed |

**请求示例**

```jsonc
{
  "room_id": "group_room_78c2cdf66ee1283cb84fcb15444fdf68", // 多人对讲房间 ID，后续连接和上报时原样传递；不是六位 room_code 或一对一通话 ID
  "assignment_version": 3, // 房间关系版本，连接和上报时携带查询到的版本
  "session_id": "<领取凭证时使用的会话ID>", // 必填，当前 connect-token 使用的同一 session_id
  "state": "joined" // 必填，connecting/joined/suspended/left/connect_failed；加入成功后才报 joined
}
```

**成功响应**：HTTP 200，

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": null // 此接口成功时固定为 null
}
```

按凭证返回的 `heartbeat_seconds` 周期上报。`joined` 确认加入并续租；`connecting` 报告连接中状态但不延长租约；`suspended`、`left`、`connect_failed` 释放当前连接。上报 `left` 不删除房间关系，持久退出须调用 `leave`。

**失败响应**：见[多人对讲错误处理](#多人对讲错误处理)，客户端按数值 `code` 判断。

### 房间关系返回字段

查询和变更成功返回 HTTP 200：

```jsonc
{
  "code": 200, // 业务码：本接口成功为 200
  "msg": "ok", // 结果说明，业务判断使用 code
  "data": { // 业务数据
    "device_id": "device-1", // 当前设备 ID
    "room_id": "group_room_78c2cdf66ee1283cb84fcb15444fdf68", // 多人对讲房间 ID，后续连接和上报时原样传递；不是六位 room_code 或一对一通话 ID
    "room_code": "001234", // 六位数字房间号，按字符串处理并保留前导零
    "desired_state": "joined", // 设备应保持的房间关系
    "assignment_version": 3, // 房间关系版本，连接和上报时携带查询到的版本
    "state": "assigned", // 设备在房间中的执行状态
    "password_set": true, // 房间是否设置密码，不返回密码本身
    "online_count": 0, // 房间中租约有效且已报告加入成功的设备数
    "online": false // 当前设备是否在线，不等同于已加入房间
  }
}
```

| 字段 | 类型 | 含义 |
|---|---|---|
| `device_id` | string | 当前设备 ID |
| `room_id` | string | 多人对讲房间 ID，后续连接和上报时原样传递；不是六位 `room_code` 或一对一通话 ID |
| `room_code` | string | 六位数字房间号，按字符串处理并保留前导零 |
| `desired_state` | string | 设备应保持的房间关系 |
| `assignment_version` | integer | 房间关系版本，连接和上报时携带查询到的版本 |
| `state` | string | 设备在房间中的执行状态 |
| `password_set` | boolean | 房间是否设置密码，不返回密码本身 |
| `online_count` | integer | 房间中租约有效且已报告加入成功的设备数 |
| `online` | boolean | 当前设备是否在线，不等同于已加入房间 |

尚无房间关系时，`room_id`、`room_code`、`desired_state` 和 `state` 可为空字符串，`assignment_version` 为 0。`desired_state` 有关系时为 `joined` 或 `left`。变更成功表示关系已保存，设备实际执行结果以之后的查询为准。

| `state` | 含义 |
|---|---|
| `assigned` | 已保存加入关系，等待设备处理 |
| `waiting_device` | 设备离线，等待上线 |
| `connecting` | 设备正在连接房间 |
| `joined` | 设备已加入房间 |
| `suspended` | 对讲暂停 |
| `connect_failed` | 连接失败或租约失效 |
| `left` | 已退出 |
| `room_closed` | 房间已关闭 |

连接预占计入房间容量，但不计入 `online_count`。

`online` 和 `online_count` 的实时值来自查询接口。create、join、leave 返回保存的关系快照，不能用其中的在线字段判断当前连接；需要时再调用查询接口。

### 多人对讲错误处理

| 业务码 | 含义与处理 |
|---|---|
| 40000 | 参数不合法，检查六位数字房间号、可选四位数字密码及会话标识 |
| 40300 | 当前账号无设备权限或设备未绑定，刷新绑定状态 |
| 40320 | 房间密码错误，重新输入 |
| 40400 | 房间不存在或已关闭，重新同步 |
| 40920 | 房间容量已满，稍后重试 |
| 40921 | 关系版本或连接代次过期，读取最新关系 |
| 40923 | 设备已在其他多人对讲房间，先退出当前房间再创建或加入 |
| 42900 | 请求过频，退避重试 |
| 42920 | 同一设备连续五次密码错误，十分钟后重试 |
| 50200 | 连接凭证服务不可用，退避重试 |
| 50000 | 服务端内部错误，稍后重试 |

业务错误使用 HTTP 200 和数值 `code`；鉴权失败遵循 call-server 现有 JWT 中间件约定。客户端按 `code` 判断，不按 `msg` 文本分支。接口不会向 H5 返回密码、密码校验值或设备连接凭证。

## 错误码汇总

同一个业务码在不同服务中可能具有不同 HTTP 状态或语义，客户端应先按服务和接口判断，
不要只建立一张跨服务的全局映射。下表列出各服务实际使用的返回码；
单个接口只会返回其接口章节列出的子集。

### device-server / user-server / ai-server（HTTP 状态型响应）

| code | HTTP | 说明 |
|------|------|------|
| 200 | 200 | 成功 |
| 4002 | 400 | 验证码无效或已过期（含输错验证码、码不存在） |
| 4003 | 422 | 设备配额已用完 |
| 4040 | 404 | 设备不存在或不属于当前用户 |
| 4090 | 409 | 邮箱已注册 |
| 4091 | 401 | 邮箱或密码错误 |
| 40000 | 400 | 请求参数错误（JSON 解析失败、必填字段缺失等） |
| 40012 | 400 | 人机验证失败 |
| 40013 | 400/404 | 用户注册验证码无效时为 HTTP 400；设备 TTS 验证码无效时为 HTTP 404 |
| 401 | 401 | 未登录或 token 无效（缺少 Authorization 头 / JWT 无效 / 过期） |
| 40300 | 403 | 无权操作资源（rtc-token 的设备归属校验，以及 AI 角色、设备和资源归属校验） |
| 40301 | 403 | AI 内部服务凭证无效 |
| 40400 | 404 | 资源未找到（agent default role 未配置/未找到） |
| 40901 | 409 | 验证已在进行中 |
| 429 | 429 | 请求过频繁（L2 单 IP 新 MAC 过多 / L3 同 MAC 频率 / L4 全局上限） |
| 42900 | 429 | AI MCP、设备插件或知识库创建额度已用尽 |
| 50000 | 500 | 服务器内部错误 |
| 5001 | 504 | MQTT 下发 auth_grant 超时 |
| 50200 | 502 | AI 服务暂不可用（探鸽云 API 调用失败） |
| 6002 | 503 | 设备离线（bind-by-id 无主设备无临时 MQTT 连接） |
| 6004 | 409 | 设备已被其他用户绑定 |
| 6006 | 410 | 设备已解绑（user_id=0） |
| 6008 | 401 | HMAC 签名校验失败、签名 Header 不完整、时间戳无效/偏差过大或 Nonce 重放；具体原因见 `msg` |
| 6010 | 400 | mac 为空 |
| 6011 | 403 | MAC 不符，疑似克隆 |
| 6012 | 503 | 设备池已耗尽 |
| 6013 | 403 | 签名 Report、Token 或绑定请求中的 MAC 与 device_id 已记录的 MAC 不一致 |
| 6014 | 400 | 未签名 Report 请求体包含非空 device_id |
| 6015 | 409 | 同 MAC 已绑定至本账号其它设备 |

### voip-server

| code | HTTP | 说明 |
|------|------|------|
| 0 | 200 | 成功 |
| 401 | 401 | JWT 鉴权失败（中间件直接返回，不经 apiresp） |
| 40000 | 200 | 请求参数错误 |
| 40203 | 200 | 微信登录状态不存在、已过期或 OpenID 不匹配 |
| 40205 | 200 | 微信 VoIP 联系人或授权不存在/已失效 |
| 40300 | 200 | 无权访问指定设备或资源 |
| 40301 | 200 | 内部服务凭证无效 |
| 40400 | 200 | 资源未找到 |
| 40900 | 200 | 资源冲突 |
| 50000 | 200 | 内部服务器错误 |
| 50001 | 200 | 微信 App 配置错误 |
| 50002 | 200 | 微信 API 调用失败 |
| 6006 | 200 | 设备已解绑，需要重新绑定 |

### call-server

| code | HTTP | 说明 |
|------|------|------|
| 200 | 200 | 成功 |
| 401 | 401 | JWT 鉴权失败（中间件直接返回） |
| 40000 | 200 | 请求参数错误 |
| 40201 | 200 | 被叫全部离线 |
| 40202 | 200 | 主叫忙（已在其他房间中） |
| 40205 | 200 | 联系人不存在（或非已接受状态） |
| 40206 | 200 | 联系人已存在 |
| 40207 | 200 | 已有待处理的联系人申请 |
| 40209 | 200 | 联系人数量达上限 |
| 40210 | 200 | 房间已被抢接 |
| 40211 | 200 | 同账号自动联系人受保护，不允许删除 |
| 40300 | 200 | 无权操作指定房间、设备或联系人 |
| 40301 | 200 | 内部服务凭证无效 |
| 40400 | 200 | 房间/资源未找到 |
| 50000 | 200 | 内部服务器错误 |

### 微信通知回调 errcode

| errcode | 含义 |
|---------|------|
| 0 | 成功 |
| 2 | 意外的信令消息 |
| 3 | wx_app_id 未配置 |
| 4 | 意外的 action |
| 5 | 查询参数 signature 校验失败 |
| 9 | 请求体无效 |
| 10 | TiRTC/MQTT 处理失败，或同一房间的上一笔回调仍在处理中 |
