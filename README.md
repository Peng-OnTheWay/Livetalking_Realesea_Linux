# LiveTalking 数字人 — Linux 部署说明

> ✅ **已部署** (2026-06-18)：服务器 RTX 3090 + CUDA 12.5，conda 环境 `/mnt/xp/livetalking-env/`

## 当前部署状态

| 项目 | 状态 |
|------|:--:|
| 视频 WebRTC 推流 | ✅ 正常 |
| 形象数据 (7 个) | ✅ 可用 |
| TTS 音频 (EdgeTTS) | ✅ 正常 |
| 单端口运行 (:8010) | ✅ 已精简 |

## 快速开始

### 1. 环境要求

- **OS**: Ubuntu 20.04+ / CentOS 7+
- **GPU**: NVIDIA GPU + 驱动 + CUDA 12.x（推荐 8GB+ 显存）
- **Python**: 3.10+

### 2. 部署

```bash
# SSH 到服务器，进入本目录
cd LiveTalking_Release_linux

# 一键部署
bash setup.sh
```

### 3. 启动

```bash
# 默认形象 orange03 + 默认音色 甜美导游
bash start.sh

# 或指定形象和音色
bash start.sh orange01 zh-CN-YunxiaNeural
```

浏览器访问: `http://<服务器IP>:8010/dashboard.html`

> 注：`launcher/` 目录是调试用的启动器（:8000），日常运行无需使用。

---

## 端口说明

| 端口 | 进程 | 用途 |
|:--:|------|------|
| 8010 | `code/app.py` | 数字人推理 + WebRTC 推流 + 管理面板 |

---

## API 接口

### C 端（游客端）— 观看数字人视频

C 端需要实现 WebRTC 播放器，握手流程：

1. **POST** `http://<服务器IP>:8010/offer`
   - Body: `{ "sdp": "<SDP offer>", "type": "offer" }`
   - 返回: `{ "sdp": "<SDP answer>", "type": "answer" }`
2. 建立 WebRTC PeerConnection 后接收 H.264 视频流 + 音频流

参考实现: `code/web/webrtcapi.html`（一个完整的 WebRTC 观众页面示例）

### B 端（管理端）— 控制数字人

B 端使用启动器的代理 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 查询运行状态 |
| GET | `/api/avatars` | 列出所有可用形象 |
| POST | `/api/start` | 启动服务 `{avatar_id, tts, ref_file, wav2lip_model}` |
| POST | `/api/stop` | 停止服务 |
| POST | `/api/proxy/human` | 发送对话文本 `{text, type, sessionid}` |

B 端管理面板已内置: `http://<服务器IP>:8000`（Bootstrap 5 界面，支持形象选择、TTS 切换、启停、对话测试、录制）

---

## 训练新数字人形象

```bash
cd LiveTalking_Release_linux/code

# 从视频生成数字人形象
python3 -m avatars.wav2lip.genavatar \
    --img_size 256 \
    --avatar_id <新形象名> \
    --video_path <视频文件路径> \
    --face_det_batch_size 4
```

参数说明：
- `--img_size 256`：必须 ≥256，否则推理崩溃
- `--face_det_batch_size 4`：8GB 显存推荐值，避免 OOM
- 视频建议 ≤1280px 宽/高（WebRTC 编码器限制）
- AI 生成视频建议关闭循环播放（帧间不一致会抽搐，代码已内置静音冻结）

---

## 目录结构

```
LiveTalking_Release_linux/
├── setup.sh                  # Linux 一键部署脚本
├── README.md                 # 本文件
├── CLAUDE.md                 # 项目状态快照
├── launcher/
│   ├── server.py             # Flask 启动器 (:8000)
│   └── templates/
│       └── index.html        # B 端管理面板
├── code/
│   ├── app.py                # 主服务入口 (:8010)
│   ├── config.py             # CLI 参数配置
│   ├── llm.py                # LLM 流式对话
│   ├── requirements.txt      # Python 依赖
│   ├── models/
│   │   └── wav2lip256.pth    # 模型权重 (215MB)
│   ├── data/
│   │   └── avatars/          # 数字人形象数据
│   ├── avatars/              # 形象引擎代码
│   │   └── wav2lip/
│   │       └── genavatar.py  # 形象训练脚本
│   ├── tts/                  # TTS 后端
│   ├── server/               # WebRTC 推流
│   └── web/                  # 前端页面
└── docs/                     # 开发文档
```

---

## 形象列表

| 形象 ID | 来源 | 帧数 |
|---------|------|:--:|
| orange01 | AI 生成 | 241 |
| orange02 | AI 生成 | 226 |
| orange03 | AI 生成 | 241 |
| static | 静态视频 | 300 |
| wav2lip_avatar_female_model | 内置 | 550 |

---

## 常见问题

**Q: 启动后无法从外网访问？**
A: 检查防火墙/安全组是否开放 8000 和 8010 端口（8010 需要 UDP 支持 WebRTC）。

**Q: WebRTC 连接失败？**
A: 如果服务器在 NAT 后面，可能需要配置 STUN/TURN 服务器。云服务器一般有公网 IP 可直接连接。

**Q: 推理速度慢？**
A: 确认 PyTorch 安装了 CUDA 版本：`python3 -c "import torch; print(torch.cuda.is_available())"`
