# 设备统一状态机与业务抢占规则

同一台设备同时接入 H5 实时、微信 VoIP、AI 对讲和设备互呼时，建议通过统一状态机管理 TiRTC 生命周期、MQTT 消息路由和业务抢占。

> 这里说明多业务共存时的设备端主干设计。设备上线和 MQTT 规范见 [device-integration.md](device-integration.md)，各业务接入细节见 [device-h5-live.md](device-h5-live.md)、[device-voip.md](device-voip.md)、[device-ai.md](device-ai.md) 和 [device-call.md](device-call.md)。
>
> `generation` 是区分新旧会话的递增代次，`pending` 是最多保存一通来电的待接记录，`deadline` 是按单调时钟计算的超时截止时刻。迟到回调、锁顺序和产品移植细节见 [多业务会话并发控制与产品实现参考](device-session-arbiter.md)。

**文档导航：** [返回总览](README.md) | [返回设备入口](device-integration.md) | [H5 实时](device-h5-live.md) | [微信 VoIP](device-voip.md) | [AI 对讲](device-ai.md) | [设备呼设备](device-call.md)

## 目录

- [接入原则](#接入原则)
- [统一状态机](#统一状态机)
- [业务抢占规则](#业务抢占规则)
- [MQTT 消息路由](#mqtt-消息路由)
- [H5 实时与通话并存策略](#h5-实时与通话并存策略)
- [推荐实现方式](#推荐实现方式)

---

## 接入原则

设备的主媒体资源只能由一个前台业务独占时，可按以下原则处理：

1. **同一时刻只允许一个 TiRTC 业务会话占用主媒体资源**
2. H5 实时流视为“后台常驻流”，VoIP、AI 和设备互呼视为“前台抢占会话”
3. 前台会话开始前暂停实时流，结束后恢复实时流
4. VoIP 与设备呼设备的来电都通过 MQTT 到达，但必须交给各自独立状态机处理
5. 冲突来电不要“排队自动接听”，要么自动拒接，要么明确进入 pending 态等待用户/业务层处理

Linux C 参考实现按这套原则实现：`SessionArbiter` 维护唯一的前台 owner、pending 和 generation，`SessionCoordinator` 只负责 `STREAM`、`VOIP`、`AI`、`CALL` 的停止、启动和恢复。

---

## 统一状态机

推荐把设备整体状态分成两层。

### 1. 顶层资源拥有者

这一层只回答一个问题：**当前谁拥有 TiRTC 主媒体资源。**

| 状态 | 说明 |
|------|------|
| `STREAM` | H5 实时预览常驻推流 |
| `VOIP` | 微信 VoIP 会话 |
| `AI` | AI 对讲会话 |
| `CALL` | 设备呼设备会话 |
| `NONE` | 启动中、切换中或停止状态 |

推荐规则：

- 启动完成后默认进入 `STREAM`
- 进入 `VOIP`、`AI` 或 `CALL` 前，先停止 `STREAM`
- `VOIP`、`AI` 或 `CALL` 结束后，自动恢复 `STREAM`

### 2. 各业务自己的子状态机

每条业务链路再维护自己的局部状态，不要混在总状态机里。

例如：

- VoIP：`IDLE -> CONNECTING -> IN_CALL`
- AI：`IDLE -> CONNECTING -> IN_CALL`
- 设备呼设备：`IDLE -> OUTGOING / PENDING / IN_CALL`
- H5 实时：`IDLE -> LISTENING -> STREAMING`

这样可以把 MQTT 路由、业务 HTTP 调用和媒体会话分开。需要增加录音、报警或云存储等能力时，也不必重写整套状态机。

---

## 业务抢占规则

下面的规则与 Linux C 参考实现一致，可作为资源互斥产品的起始策略。最终产品仍需结合交互方式和硬件资源验证。

### 1. H5 实时是后台态

- 默认启动实时流
- 当 `VOIP`、`AI` 或 `CALL` 任一会话开始时，暂停实时流
- 当前台会话结束时，再恢复实时流

### 2. AI 与其它通话互斥

- AI 会话进行中收到 VoIP 来电：自动拒接 VoIP
- AI 会话进行中收到设备呼设备来电：自动 `busy` 拒接
- AI 会话进行中，不允许再发起 VoIP 或设备呼设备

AI 通常会占用麦克风、扬声器和主会话上下文，与人工通话并行运行容易造成资源冲突。是否需要互斥，还要结合产品的硬件资源和交互方式判断。

### 3. VoIP 与设备呼设备互斥

- VoIP 进行中收到设备呼设备来电：`busy` 拒接
- 设备呼设备进行中收到 VoIP 来电：VoIP 直接拒接

Linux C 参考实现在 [main.c](device-sim/device-sim-c/src/main.c) 注册 MQTT 回调。所有来电、终端动作和 SDK 异步结束事件先进入 `SessionArbiter`，由 Arbiter 原子判断 pending、owner、room_id 和 generation。

准入成功后，`SessionCoordinator` 才会串行停止 STREAM 并启动目标业务。各业务模块无需互相读取状态来拼接冲突判断。

### 4. 全局只保留一个 pending 来电

Linux C 参考实现使用一个带 `room_id`、代次和 45 秒有效期的全局待接记录 `pending`。VoIP 和设备来电按到达顺序保留第一通，后来的来电立即以 busy 拒绝，不能覆盖已有来电。这样可以保证 `accept` 始终对应一个确定的房间。

如果产品需要 VoIP 优先等抢占策略，应按
[显式抢占协议](device-session-arbiter.md#4-默认冲突策略)实现，不能在 SDK
回调里直接覆盖当前状态。

---

## MQTT 消息路由

统一状态机不等于把所有 MQTT 处理写在一个大函数里。推荐做法是：

- 总路由器只按 `type + channel` 分发
- VoIP 状态机只处理自己的消息
- 设备呼设备状态机只处理自己的消息
- AI 不消费 MQTT 呼叫消息

推荐分工如下：

| 消息 | 去向 | 说明 |
|------|------|------|
| `call_incoming` + `channel=wx` | VoIP 状态机 | 微信来电 |
| `call_cancel` | VoIP 状态机 | 微信侧取消/挂断 |
| `callers_update` + VoIP 来源 | VoIP 状态机 | 微信授权列表变化 |
| `call_incoming` + `channel=device` | 设备呼设备状态机 | 设备来电 |
| `room_cancel` | 设备呼设备状态机 | 房间结束 |
| `call_reject` | 设备呼设备状态机 | 某个被叫拒接 |
| `callers_update` + call 来源 | 设备呼设备状态机 | 联系人变化 |

对应代码如下：

- MQTT 回调注册与总入口：[device-sim/device-sim-c/src/main.c](device-sim/device-sim-c/src/main.c)
- 会话准入与竞态仲裁：[device-sim/device-sim-c/src/session_arbiter.c](device-sim/device-sim-c/src/session_arbiter.c)
- 会话资源协调器：[device-sim/device-sim-c/src/session_coordinator.c](device-sim/device-sim-c/src/session_coordinator.c)
- MQTT 连接与按 `type + channel` 分发：[device-sim/device-sim-c/src/device_flow.c](device-sim/device-sim-c/src/device_flow.c)

---

## H5 实时与通话并存策略

设备通话期间，服务端仍允许 H5 申请实时 token：

- [`GET /v1/user/device/rtc-token`](api-reference.md#get-v1userdevicertc-token) 会返回 `in_call`
- 即使 `in_call=true`，也仍会签发 token

H5 实时是否与通话并存，主要由设备端决定。

可以选择以下两种策略：

### 策略 A：严格互斥

- 通话中暂停实时流
- H5 即使连上，也看不到实时音视频或只能看到断流

优点：

- 设备实现简单
- 摄像头 / 麦克风 / 编码器资源压力小

缺点：

- H5 预览体验会中断

### 策略 B：预览继续，业务独占上行控制

- 通话中仍允许 H5 看实时视频
- 但禁止 H5 talkback，或禁止 H5 抢占主音频链路

优点：

- 监控类场景体验更连续

缺点：

- 设备端要解决多路音视频复用
- 更容易出现“谁在占麦克风 / 扬声器”的资源冲突

如果没有明确产品需求，建议先做 **策略 A**。

---

## 推荐实现方式

设备端代码可拆成五层：

1. `device_flow`
   - 负责设备上线、MQTT 长连接、消息收发
2. `session_router`
   - 只负责按消息类型把 MQTT 分发到各业务状态机
3. `session_arbiter`
   - 负责来电准入、唯一 owner、待接记录、超时与会话代次隔离
4. `session_coordinator`
   - 不判断业务优先级，只串行停止当前适配器、启动目标适配器和恢复 STREAM
5. `voip`、`ai`、`call`、`stream`
   - 各自负责本业务 HTTP、媒体、命令和局部状态机

这套结构将 MQTT 协议、TiRTC 生命周期、业务规则和媒体线程分开。增加业务时，只需接入仲裁器和生命周期适配器，不必重写原有协议。

device-sim-c 是仓库中的 Linux C 参考实现，代码组织如下：

- 组合入口：[device-sim/device-sim-c/src/main.c](device-sim/device-sim-c/src/main.c)
- 会话仲裁器：[device-sim/device-sim-c/src/session_arbiter.c](device-sim/device-sim-c/src/session_arbiter.c)
- 会话协调器：[device-sim/device-sim-c/src/session_coordinator.c](device-sim/device-sim-c/src/session_coordinator.c)
- MQTT 路由：[device-sim/device-sim-c/src/device_flow.c](device-sim/device-sim-c/src/device_flow.c)
- 完整并发控制与产品实现参考：[device-session-arbiter.md](device-session-arbiter.md)

产品二次开发时建议保留 Router → Arbiter → Coordinator/业务适配器的职责边界。非 Linux 目标应作为独立移植实现自己的任务、同步、队列和硬件适配，并重新完成竞态测试。

## 多人对讲 ROOM

ROOM 表示设备持续收听多人房间，持有共享 TiRTC 资源时暂停空闲 STREAM。AI、CALL、VOIP 可抢占 ROOM；ROOM 不能抢占它们，也不能越过待接听的呼叫。业务结束后，设备从 call-server 读取当前 `assignment_version` 与期望房间，再申请新的连接租约恢复 ROOM。

抢占、断开、关系变化和关闭均同步关闭本机 PTT，清空成员列表与旧媒体状态。迟到连接、音频和状态上报由本机会话代次、连接句柄及服务端租约标识共同隔离。恢复默认只收听，不能沿用上一次的按下状态。公开协议见 [设备多人对讲](device-room.md)。
