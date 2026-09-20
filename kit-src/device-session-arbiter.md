# 多业务会话并发控制与产品实现参考

这份文档说明一台设备同时承载 H5 实时、微信 VoIP、AI 对讲和设备互呼时，如何通过统一仲裁器处理并发、取消、超时和迟到回调。文中的 Linux C 代码只适用于 `device-sim-c`；其他操作系统或芯片需要独立移植并重新验证。

> 业务接入顺序和协议字段分别见 [设备接入总览](device-integration.md)、[H5 实时](device-h5-live.md)、[微信 VoIP](device-voip.md)、[AI 对讲](device-ai.md) 和 [设备互呼](device-call.md)。这里讨论的只是设备端并发控制，不改变任何 HTTP、MQTT 或 TiRTC 对外接口。

**文档导航：** [返回总览](README.md) | [统一状态机](device-session-model.md) | [二次开发](device-porting.md) | [Linux C 参考实现](device-sim/device-sim-c/README.md) | [Python 模拟器](device-sim/device-sim-py/README.md)

## 1. 适用范围与结论

这套方案适用于以下资源只能由一个前台业务独占的设备：

- 同一套 TiRTC 生命周期；
- 同一个麦克风、扬声器或音频 codec；
- 同一个摄像头、编码器或主码流；
- 同一个产品交互焦点。

整体设计分为六点：

1. 用一个 `SessionArbiter` 决定谁有权使用资源。
2. 用一个 `SessionCoordinator` 执行 TiRTC 的 Stop/Start 切换。
3. 每个业务保留自己的局部状态机，不直接读取其它业务的内部状态。
4. 每次取得所有权时递增 `generation`（会话代次）；回调必须携带并核对该数值，旧代次不能修改新会话。
5. 每个异步阶段必须记录结束时刻 `deadline`；失败、取消和超时都进入同一个结束出口。
6. SDK 回调只投递事件，不在回调栈里执行 Stop/Uninit。

这套策略组合了有限状态机、有界事件队列、单一状态写入者、单调时钟超时和旧回调隔离。不同产品可以采用其他组合，但队列容量、超时和优先级都必须根据实际资源验证。

如果硬件能真正并行运行多套 RTC、编码器和音频链路，应把“唯一资源”扩展成资源集合，而不是绕过仲裁器。

## 2. 模块边界

```text
MQTT 线程 ─┐
终端/UI 任务 ─┼─> SessionRouter ─> SessionArbiter ─> SessionCoordinator ─> TiRTC 适配器
定时器任务 ─┤                         │                         │
SDK 回调 ───┘                         └<── 生命周期事件队列 <───┘
```

| 模块 | 只负责 | 不负责 |
|---|---|---|
| `SessionRouter` | 校验消息、按 `type + channel` 分发 | 直接 Stop/Start SDK |
| `SessionArbiter` | pending、owner、session_id、generation、冲突策略 | HTTP、媒体帧、硬件 IO |
| `SessionCoordinator` | 串行 Stop 当前适配器、Start 目标适配器、恢复 STREAM | 判断业务优先级 |
| `STREAM/VOIP/AI/CALL` | 自己的 HTTP、信令和局部状态 | 查询其它业务来拼冲突条件 |
| 生命周期队列 | 将回调线程的结束事件送到安全任务 | 决定事件是否仍有效 |

保持这个边界后，新增业务只需要注册新的 kind 和生命周期适配器，不需要修改旧业务的互斥判断。

## 3. 两层状态模型

### 3.1 顶层仲裁状态

仲裁器维护三组数据：

```c
struct arbiter_state {
    optional<pending_ticket> pending; /* 最多一个待接槽位 */
    optional<session_kind> owner;     /* 最多一个前台所有者 */
    uint64_t generation;              /* 每次新所有权递增 */
    bool owner_cancelled;
};
```

`STREAM` 是空闲基线，不计入 `owner`：

| Arbiter owner | Coordinator current | 说明 |
|---|---|---|
| `NONE` | `STREAM` | 正常空闲，H5 实时工作 |
| `NONE` + pending | `STREAM` | 来电等待用户决定，H5 继续工作 |
| `VOIP` | `VOIP` | 微信通话独占资源 |
| `AI` | `AI` | AI 对讲独占资源 |
| `CALL` | `CALL` | 设备互呼独占资源 |
| `NONE` | `NONE` | 启停的短暂过渡态或系统关闭 |

### 3.2 业务局部状态

业务模块仍维护自己的状态，例如：

```text
VoIP: IDLE -> OUTGOING/PENDING -> CONNECTING -> IN_CALL -> IDLE
AI:   IDLE -> CONNECTING -> WAIT_START_RESPONSE -> IN_CALL -> IDLE
CALL: IDLE -> OUTGOING/PENDING -> CONNECTING -> IN_CALL -> IDLE
```

局部状态用于处理协议步骤；它不能代替顶层所有权。某模块显示 `IDLE` 不代表资源一定空闲，资源结论只能从仲裁器读取。

## 4. 默认冲突策略

C/Python 参考实现采用确定性的非抢占策略：

- H5 实时是后台基线，前台业务开始时暂停，结束后恢复。
- 全局只有一个待接槽位，first-wins。
- 已有 pending 时，后来的 VoIP 或设备来电直接 busy 拒绝。
- 已有 `VOIP/AI/CALL` owner 时，任何其它前台业务都不能开始。
- 不在底层偷偷做“VoIP 优先于 AI”之类的抢占。
- 本设备 VoIP 外呼的回铃属于当前 VOIP，会继续当前会话，不作为新来电。

这套默认规则的优点是结果与线程调度无关，容易测试，也不会在用户不知情时切断正在进行的业务。

产品如果确实需要优先级抢占，应实现显式协议：

```text
请求抢占 -> 标记旧 owner 正在终止 -> 等待旧 generation 完成
        -> 取得新 generation -> 启动新业务
```

不能收到高优先级事件后直接修改 `owner`，否则旧 SDK 回调可能终止新会话。

## 5. 待接记录（代码字段 `pending`）

来电到达时先原子申请 pending：

```text
offer_pending(kind, room_id, ttl):
    lock
    清理已超时的待接记录
    如果 owner != NONE 或 pending 已存在: BUSY
    pending = {kind, room_id, pending_generation++, deadline}
    unlock
```

待接记录必须包含：

- `kind`：VOIP 或 CALL；
- `session_id`：通常是 `room_id`；
- `pending_generation`；
- 单调时钟 deadline。

取消消息必须同时匹配 kind 和 session_id。这样旧房间的迟到取消不会清除新房间。

接听时需要原子消费待接记录：

```text
PENDING(room-A)
    -> begin(kind, consume_pending=true, session_id=room-A)
    -> STARTING(owner=kind, owner_session_id=room-A)
```

如果启动失败且同一待接记录没有被取消，可以恢复 pending；如果启动期间已收到同房间取消，则禁止恢复。

## 6. 会话代次（代码字段 `generation`）：阻止迟到回调

每次创建新 owner 时递增 generation，并返回一份会话标识（代码类型为 `session_lease`）：

```c
struct session_lease {
    enum session_kind kind;
    uint64_t generation;
    char session_id[...];
};
```

所有异步结束事件必须携带启动时的 lease：

```text
finish(kind, generation):
    只有 owner.kind == kind 且 owner.generation == generation 才生效
```

典型场景：

```text
CALL generation=41 结束
CALL generation=42 启动
旧的 generation=41 disconnected 晚到
-> 因 generation 不匹配被忽略
```

Python 特别要注意：lease 必须在进入可能同步回调的 SDK action 之前保存。C 参考实现先取得并保存 lease，再调用业务 action。否则第二次同类会话同步失败时可能误用上一代 lease。

generation 使用 64 位无符号整数。产品不应在设备重启后持久化它；它只保护当前进程或本次启动周期。

## 7. 启动、提交与回滚

启动操作分为三步：

1. 仲裁器在锁内预留 owner 和 generation。
2. 协调器停止 STREAM 并启动目标 SDK 适配器。
3. 业务执行 HTTP/WHIP/Connect action。

任何一步失败都必须：

```text
清理当前 generation 的局部状态
-> 归还 owner
-> 恢复 STREAM
-> 必要时恢复尚未取消的待接记录
```

成功响应也要验证结构。比如 HTTP 返回 `code=200` 但没有 `data.room_id`，仍属于失败，不能让 owner 留在 CALL。

业务函数不允许仅把自己的状态设为 `IDLE` 后返回。它必须抛出/返回失败，或发送一次 terminal event，让仲裁器归还所有权。

## 8. 统一结束出口

以下事件都进入同一个结束流程：

- 用户挂断或取消；
- 对端挂断、拒接或取消；
- HTTP/SDK 立即失败；
- SDK 异步连接失败；
- 服务端返回错误；
- 等待超过截止时刻；
- 媒体线程发生不可恢复错误。

它们最终都执行：

```text
terminal_event(lease)
    -> 生命周期队列
    -> 校验 generation
    -> Stop 当前业务适配器
    -> Start STREAM
```

terminal event 必须幂等。相同 generation 的重复事件只能产生一次有效回收。

SDK 回调线程不得直接执行 Stop/Uninit，原因包括：

- SDK 可能持有内部锁；
- Disconnect 可能同步触发另一个回调；
- 媒体线程可能仍在 SDK Send 调用栈内；
- Uninit 可能释放当前 callback table。

Linux C 参考实现使用常驻生命周期队列；其他平台应在独立移植中提供固定长度事件队列，不要为每次回调动态创建任务。

## 9. 超时截止时刻（代码字段 `deadline`）

“SDK 通常会回调”不能作为资源释放条件。每个异步阶段都必须有 deadline：

| 阶段 | C/Python 参考值 | 超时动作 |
|---|---:|---|
| pending 来电 | 45 秒 | 清 ticket，STREAM 不受影响 |
| VoIP 外呼等待回铃 | 30 秒 | 清外呼状态，释放 VOIP |
| VoIP 等待 WHIP 回调 | 10 秒 | 失效 generation，释放 VOIP |
| VoIP 等待 `0x2000` | 10 秒 | Disconnect，释放 VOIP |
| AI 等待 WHIP 回调 | 10 秒 | 失效 generation，释放 AI |
| AI 等待 `start_session` 响应 | 10 秒 | Disconnect，释放 AI |
| 设备外呼等待接听 | 30 秒 | 取消房间，释放 CALL |
| 设备 P2P Connect | 每次 10 秒，最多 3 次 | 全部失败后挂断并释放 CALL |

产品可以调整数值，但不能删除 deadline。计时必须使用 monotonic clock；校时、时区变化和 NTP 不能延长会话。

超时与成功回调同时到达时，先取得状态锁的一方获胜：

- 成功先提交：timer 看到状态已推进，什么也不做；
- timeout 先提交：generation 失效，迟到成功只断开旧 handle。

## 10. MQTT 和外部数据校验

MQTT、HTTP 和 SDK command 都是不可信输入。进入状态机前至少检查：

- 根节点和 payload 必须是预期 JSON 类型；
- `room_id`、token、peer_id 必须是字符串；
- 必填字符串不能为空；
- 数字、null、数组不能传给 `%s` 或 `strcmp`；
- session_id 不匹配时只能记录并忽略；
- malformed 来电应拒绝或丢弃，不能覆盖已有 pending。

C 推荐统一封装：

```c
const char *json_string_or_empty(const cJSON *object, const char *key);
```

不要直接使用 `cJSON_GetObjectItem(...)->valuestring`。

## 11. 锁和线程规则

Linux C 参考实现使用：

- `transition_lock`：串行整个 Stop/Start 转换；
- `state_lock`：保护 owner、ticket、generation 和 deadline；
- 业务私有锁：保护本业务局部状态；
- 生命周期 queue：让 SDK 回调快速返回。

必须固定锁顺序：

```text
transition_lock -> arbiter state_lock -> coordinator lock -> business lock
```

回调投递结束事件时只短暂取得 queue/state lock，不反向等待 transition lock。

Python 需要同样遵守此规则。GIL 不能替代状态锁，因为 ctypes SDK 回调、Timer 和媒体线程可以并发进入。

## 12. 非 Linux 产品的独立移植原则

如果目标系统使用固定任务和消息队列，可让一个 `session task` 成为 owner、pending 和 generation 的唯一写入者：

```text
MQTT task ─┐
SDK callback ─┼─> fixed event queue ─> session task（唯一写 arbiter）
UI task ────┤
timer task ──┘
```

session task 是 owner、pending 和 generation 的唯一写者，大部分状态不再需要多把 mutex。SDK callback 只复制最小事件：

```c
struct session_event {
    uint8_t type;
    uint8_t kind;
    uint64_t generation;
    char session_id[64];
    int error;
};
```

移植建议：

| Linux 参考实现 | 固定任务/消息队列平台的独立实现 |
|---|---|
| pthread mutex/condition | 平台 mutex + 固定队列，或单一 session task |
| detached/background thread | 固定任务，不按事件创建任务 |
| `clock_gettime(CLOCK_MONOTONIC)` | tick count 转毫秒，处理 tick wrap |
| `malloc/calloc` callback context | 固定对象池或 generation 索引 |
| 动态 finish deque | 固定环形队列 |
| 文件音视频 | 摄像头/I2S/codec/环形缓冲 |
| printf 日志 | UART/RTT 异步日志队列 |

资源受限设备应预先计算：

- 最大同时存在的旧 callback context；
- 生命周期队列深度；
- MQTT 拒接队列深度；
- session_id 和 token 的最大长度；
- 最坏情况下 Stop/Start 所需时间。

队列满不能静默丢弃 terminal event。可以设置 `needs_reconcile` 标志，由 session task 下一轮强制检查“业务已 IDLE 但 owner 仍存在”的不变量。

ISR 中不能运行仲裁器，只能使用 ISR-safe queue 投递简化事件。

## 13. 可检查的不变量

开发和现场诊断时持续检查：

1. `owner == NONE` 时，Coordinator 最终应为 STREAM 或系统正在关闭。
2. `owner != NONE` 时不能存在新的待接记录。
3. 同一时刻最多一个业务 adapter 处于 started。
4. terminal generation 小于当前 generation 时不能改变状态。
5. 所有 CONNECTING/WAITING 状态都有非零 deadline。
6. deadline 到期后，有限时间内 owner 必须归还。
7. SDK Uninit 前 callback count 和媒体 worker count 必须归零。

建议日志至少包含：

```text
event, kind, session_id, generation, old_owner, new_owner, reason, deadline
```

不要记录 device_key、完整 token 或用户敏感媒体。

## 14. 故障注入验收矩阵

正常通话测试不能证明竞态正确。至少覆盖：

| 用例 | 期望 |
|---|---|
| 第二次同类会话在 action 内同步失败 | 使用新 lease 释放，恢复 STREAM |
| 旧成功 callback 晚于新会话 | 断开旧 handle，不修改新状态 |
| SDK 永远不回 callback | 超时处理释放 owner |
| AI 永远不回 `start_session` | 超时后 Disconnect 并恢复 STREAM |
| VoIP 永远不回铃 | 30 秒 deadline 释放 VOIP |
| cancel 与成功 callback 同时发生 | 只有一个提交成功 |
| MQTT `room_id=null/数字/数组` | 不崩溃，不改变其它房间 |
| 重复 disconnected/end_session | 幂等，只恢复一次 |
| H5 恢复第一次失败 | 有限重试，生命周期 worker 继续存活 |
| finish queue 满 | 触发 reconcile/告警，不静默遗失 |

测试应使用 fake clock/fake timer，不要真的等待 10、30、45 秒。

## 15. 参考代码

C：

- 仲裁策略：[session_arbiter.c](device-sim/device-sim-c/src/session_arbiter.c)
- TiRTC 切换：[session_coordinator.c](device-sim/device-sim-c/src/session_coordinator.c)
- 组合与 timeout poll：[main.c](device-sim/device-sim-c/src/main.c)
- 故障测试：[test_core.c](device-sim/device-sim-c/tests/test_core.c)

Python：

- 仲裁策略：[session_arbiter.py](device-sim/device-sim-py/session_arbiter.py)
- TiRTC 切换：[session_coordinator.py](device-sim/device-sim-py/session_coordinator.py)
- lease 发布：[device_rtc_runtime.py](device-sim/device-sim-py/device_rtc_runtime.py)
- AI 代次与 timeout：[rtc_ai.py](device-sim/device-sim-py/rtc_ai.py)
- 故障测试：[test_session_arbiter.py](device-sim/device-sim-py/test_session_arbiter.py)、[test_rtc_ai.py](device-sim/device-sim-py/test_rtc_ai.py)、[test_rtc_voip.py](device-sim/device-sim-py/test_rtc_voip.py)

## 16. 新增业务的接入清单

新增需要独占 RTC 的业务时：

1. 增加新的 `SessionKind`。
2. 注册 start/stop adapter。
3. 定义是否需要待接记录和 session_id。
4. 所有入口先经过 arbiter。
5. 启动前发布 lease。
6. 为每个异步阶段设置 deadline。
7. 所有失败进入统一 terminal event。
8. 所有 callback 校验 generation 和 handle。
9. 定义 busy/拒绝的外部行为。
10. 增加迟到 callback、timeout、malformed input 和重复结束测试。

新业务需要完成以上十项，才能接入统一竞态策略。
