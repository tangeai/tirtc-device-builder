# ESP32-S3 工程模板

工程生成器创建一个独立的 ESP-IDF 项目，适合开发者先跑通设备绑定、H5 音视频和 AI 对讲，再在明确的媒体 seam 后接入自己的摄像头、麦克风、扬声器与按键。

## 生成工程

从仓库根目录执行。Windows CMD 使用一行命令最不容易混淆：

```bat
python .\kit-src\device-sim\scripts\create_esp32_project.py D:\workspace\my-esp32-device --name my_esp32_device
```

Windows PowerShell 同样可以使用一行命令：

```powershell
python .\kit-src\device-sim\scripts\create_esp32_project.py D:\workspace\my-esp32-device --name my_esp32_device
```

需要分行时，CMD 的续行符是 `^`，PowerShell 的续行符是反引号 `` ` ``；续行符后面不能再有空格。工程目录可以包含 `-`，`--name` 指定的 ESP-IDF 工程名只能使用小写字母、数字和下划线。

Linux 或 macOS 使用：

```bash
python kit-src/device-sim/scripts/create_esp32_project.py \
  ./my-esp32-device \
  --name my_esp32_device
```

生成器要求输出目录不存在，不覆盖已有工程。默认把仓库内的 ESP32-S3 TiRTC SDK 2.5.0 和必要的平台模块复制到新工程，因此生成结果可以独立构建。模板不复制媒体文件。

```bash
cd my-esp32-device
idf.py set-target esp32s3
idf.py build
idf.py -p <SERIAL_PORT> flash monitor
```

模板的硬件基线是 ESP32-S3 N16R8、ESP-IDF 5.5.x。生成工程内的 `README.md` 说明首次配网、验证码绑定、H5 验收、AI 控制台命令和产品化 TODO。

## 模板边界

模板包含：

- Wi-Fi SoftAP 配网、设备验证码绑定、NVS 凭证与 MQTT 上线；
- 单路 H5 会话，向 H5 发送 G.711A 音频和 H.264 视频，接收 H5 对讲音频；
- AI token、WHIP、`start_session`/`end_session` 和双向 G.711A 音频；
- 空媒体适配器、串口状态命令和集中式硬件 TODO。

其它业务模块不进入生成工程。SDK 类型只出现在 `starter_tirtc`，会话顺序只由 `starter_runtime` 管理，硬件替换集中在 `starter_media`。
