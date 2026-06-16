# CLAUDE.md — LiveTalking 数字人模型

> 最后更新：2026-06-16（GitHub 版本管理 + P0/P1 黑屏修复 + 商业审查）
> 本项目从主项目 `Digital_Human_Project` 中独立，专注于 LiveTalking wav2lip 数字人模型的部署与定制。

---

## 一、项目概述

基于 [LiveTalking](https://github.com/lipku/LiveTalking)（Apache 2.0）+ [不蠢不蠢 wav2lip](https://github.com/buchunbuchun/wav2lip384) 的 wav2lip 数字人模型，支持：
- 视频流驱动：输入一段人物视频，通过音频驱动口型同步
- WebRTC 实时推流：浏览器端低延迟渲染
- 多形象管理：可自定义训练/导入数字人形象
- 对话交互：LLM 流式对话 + TTS 语音合成 + 视频口型同步
- **wav2lip256 单模型**

| 维度         | 详情                                                         |
| ------------ | ------------------------------------------------------------ |
| **GitHub**   | LiveTalking: https://github.com/lipku/LiveTalking            |
| **GitHub**   | wav2lip384: https://github.com/buchunbuchun/wav2lip384       |
| **许可证**   | **Apache 2.0（可商用）**                                     |
| **核心能力** | 实时交互流式数字人，音视频同步对话                           |
| **技术路线** | wav2lip256 / MuseTalk / ER-NeRF 多模型切换                   |
| **中文支持** | ✅                                                            |
| **推理速度** | wav2lip256: **~60 FPS**（RTX 5060 Ti 8GB）                    |
| **显存需求** | **RTX 5060 Ti（8GB）即可**（256 模型 ~215MB 权重 + 推理）      |
| **实时性**   | ✅ 完全满足（≥25 FPS 即实时，实测远超）                       |
| **TTS 集成** | EdgeTTS / Fish-Speech / CosyVoice / GPT-SoVITS / 腾讯 / 豆包 |
| **传输协议** | WebRTC / RTMP 推流 / 虚拟摄像头                              |
| **特殊能力** | 说话打断、多并发                                             |

---

## 二、目录结构

```
live-talking/
├── CLAUDE.md                       # 本文件
├── .gitignore                      # Git 忽略（env/、权重、来源素材）
├── new_update/                     # 来源素材（不蠢不蠢整合包、LiveTalking 2.0.2）
├── tools/
│   └── miniconda/                  # Miniconda 包管理器（Windows 原生）
└── LiveTalking/
    ├── env/                        # conda Python 3.10 环境
    ├── docs/
    │   └── 数字人开发事项.md        # 开发历史 + 优化存档
    ├── launcher/
    │   ├── server.py               # Flask 启动器（:8000）— 进程管理 + Web UI
    │   └── templates/
    │       └── index.html          # 管理端 Web UI（Bootstrap 5），含 256/384 选择器
    └── code/
        ├── app.py                  # 主服务入口（:8010）
        ├── config.py               # CLI 参数（含 --wav2lip_model）
        ├── llm.py                  # LLM 流式对话引擎
        ├── registry.py             # 插件注册（avatar/tts/streamout）
        ├── requirements.txt        # Python 依赖
        ├── models/
        │   └── wav2lip256.pth      # ★ 不蠢不蠢 256 权重（215 MB）
        ├── data/
        │   ├── avatars/            # 数字人形象数据
        │   │   ├── orange01/                       # ★ AI 形象
        │   │   ├── orange02/                       # ★ AI 形象
        │   │   ├── orange03/                       # ★ AI 形象
        │   │   ├── static/                         # ★ 静态形象
        │   │   ├── wav2lip_avatar_female_model/     # 内置：年轻女性
        │   │   ├── wav2lip_avatar_glass_man/        # 内置：戴眼镜男性
        │   │   └── wav2lip_avatar_long_hair_girl/   # 内置：长发女性
        │   └── custom_config.json
        ├── avatars/
        │   ├── base_avatar.py      # BaseAvatar 基类
        │   ├── wav2lip/
        │   │   ├── genavatar.py     # 形象生成
        │   │   └── models/
        │   │       ├── conv.py              # v2 卷积层
        │   │       ├── wav2lip_v2.py        # 256 模型架构
        │   │       └── __init__.py          # 模型导出
        │   │       ├── conv_384.py          # （废弃）SAM 卷积层
        │   │       └── wav2lip.py           # （废弃）SAM 384 模型架构
        │   ├── musetalk/           # musetalk 引擎（备选）
        │   └── ultralight/         # ultralight 引擎（备选）
        ├── tts/
        │   ├── edge.py             # Edge TTS（免费，当前默认）
        │   └── ...
        ├── server/
        │   ├── webrtc.py           # WebRTC 推流实现
        │   └── ...
        └── web/
```

---

## 三、核心端口与启动

### 端口清单

| 端口 | 进程 | 说明 |
|:--:|------|------|
| 8000 | `launcher/server.py` | 启动器 + 管理端 Web UI |
| 8010 | `code/app.py` (wav2lip) | 数字人推理 + WebRTC 推流 |

### 启动命令

```powershell
# 唯一入口 — 启动器会自动拉起 :8010 进程
cd e:\Digital_human\live-talking\LiveTalking\launcher
..\env\python.exe server.py

# 浏览器访问
http://localhost:8000
```

### 启动器职责

`launcher/server.py` 是一个进程管理器 + 反向代理：

| API | 方法 | 说明 |
|-----|------|------|
| `/api/status` | GET | 查询运行状态 |
| `/api/avatars` | GET | 列出所有可用形象 |
| `/api/avatar/<id>/preview` | GET | 形象预览图 |
| `/api/start` | POST | 启动数字人服务 |
| `/api/stop` | POST | 停止数字人服务 |
| `/api/proxy/offer` | POST | WebRTC offer 代理 → :8010 |
| `/api/proxy/human` | POST | 对话消息代理 → :8010 |
| `/api/proxy/record` | POST | 录制控制代理 → :8010 |

### Web UI 功能（`templates/index.html`）

Bootstrap 5 风格管理面板：

| 区域 | 功能 |
|------|------|
| 形象选择 | 水平滚动卡片，缩略图预览 |
| 进程控制 | 一键启停 + 状态指示（绿/黄/红） |
| 对话模式 | 文字输入 + 按住录音（浏览器 SpeechRecognition）+ 聊天历史 |
| 朗读模式 | TTS 纯朗读 |
| 视频画面 | WebRTC 视频流 + 尺寸调节滑块 |
| 视频录制 | 录制当前对话输出 |

---

## 四、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| Python | 3.10 (conda) | `LiveTalking\env\` |
| 推理框架 | PyTorch 2.11.0+cu128 | CUDA 加速 |
| 视频推理 | wav2lip (Wav2Lip v2) | 音频驱动的口型同步 |
| 语音合成 | Edge TTS (edgetts) | 免费，中文女声 `zh-CN-YunxiaNeural` |
| 实时通信 | WebRTC (aiortc) | 视频+音频推流到浏览器 |
| LLM | 通义千问 (DashScope) | 流式对话生成 |
| Web 服务 | Flask | 启动器 + REST API |
| 前端 | Bootstrap 5 | 管理端 UI |

---

## 五、当前进度

### 已完成

| 事项 | 日期 | 说明 |
|------|:--:|------|
| wav2lip256 模型集成 | 05-26 | 不蠢不蠢 wav2lip 权重 + LiveTalking 2.0.2 代码 |
| LiveTalking 2.0.2 升级 | 05-26 | 纯原始代码部署，旧优化存档在 docs/ |
| Git 仓库初始化 | 05-26 | 排除 env/、权重文件、new_update/ |
| 4K OOM 修复 | 05-26 | genavatar 缩略图检测 + 原帧裁剪，支持 4K 视频 |
| static 形象训练 | 05-28 | static.mp4 → 256 模型，300 帧，1280×1280 |
| orange02 重建 | 05-28 | 更新 girl002.mp4 后重新训练，226 帧，1280×1280 |
| 分辨率全链路分析 | 05-28 | 澄清 full_imgs(≤1280px) / face_imgs(256×256) / 模型(256/192) 三层 |
| 清理冗余形象和模型 | 06-16 | 删除 syl/xp 形象，删除 wav2lip384.pth，统一只用 256 |
| 之前优化恢复验证 | 06-16 | lip_gain 口型放大 + 静音冻结 + 边界混合已生效，无下巴抽搐，清晰度正常 |
| GitHub 版本管理 | 06-16 | 初始化 Git 仓库，推送至 github.com/Peng-OnTheWay/Livetalking_Realesea_Linux |
| P0-1 异常丢帧修复 | 06-16 | paste_back_frame 异常时降级为原始帧而非 continue，消除黑屏根因 |
| P0-2 偶数分辨率全覆盖 | 06-16 | x264 偶数安全网从仅 >720p 扩展到所有帧，消除编码崩溃 |
| P1-2 静音帧 deepcopy | 06-16 | 静音帧深拷贝防止 cv2.putText 污染原始帧缓存 |
| 商业产品审查 | 06-16 | 完成 5 维度审查（可用性/稳定性/性能/安全性/可运维性） |
| 之前所有工作 | — | 见 `docs/数字人开发事项.md` |

### 已知问题

| 问题 | 说明 | 状态 |
|------|------|:--:|
| 形象切换需冷重启 | 切换形象需杀进程重启，耗时 ~10s | 📋 待实现热切换 |
| orange01 抽搐 | 说话↔静音跳变，`enable_transition=False` 被关闭 | 📋 待开启平滑过渡 |

> 之前的 P0/P1 黑屏问题已于 06-16 修复。

---

## 六、形象管理

### 现有形象

| ID | 名称 | 来源 | face_imgs | 状态 |
|----|------|------|:--:|:--:|
| `orange01` | orange01 | girl001 AI生成视频 | 256×256 × 241 帧 | ✅ 1280×1280 |
| `orange02` | orange02 | girl002 AI生成视频（05-28更新） | 256×256 × 226 帧 | ✅ 1280×1280 |
| `orange03` | orange03 | girl003 AI生成视频 | 256×256 × 241 帧 | ✅ |
| `static` | static | static.mp4 | 256×256 × 300 帧 | ✅ 1280×1280 |
| `wav2lip_avatar_female_model` | 年轻女性 | 内置 | 256×256 × 550 帧 | ✅ |
| `wav2lip_avatar_glass_man` | 戴眼镜男性 | 内置 | 256×256 | ✅ |
| `wav2lip_avatar_long_hair_girl` | 长发女性 | 内置 | 256×256 | ✅ |

### 创建新形象

```powershell
cd LiveTalking/code
..\env\python.exe -m avatars.wav2lip.genavatar --img_size 256 --avatar_id <新形象名> --video_path <视频路径> --face_det_batch_size 4
```

> ⚠️ **`--img_size` 必须 ≥ 256**。默认值 96 会导致 face_imgs 经过 6 层 stride-2 卷积后只剩 2×2，无法通过 kernel 4×4，推理崩溃。
>
> ⚠️ **必须用 `-m` 模块方式运行**，不能直接 `python avatars\wav2lip\genavatar.py`，否则 `ModuleNotFoundError: No module named 'avatars'`。
>
> ⚠️ **`full_imgs` 自动限制 max_side=1280（720p）**：video2imgs 内置缩放，超过 1280px 自动缩小。这是为了兼容 WebRTC x264 编码器。
>
> ⚠️ **`--face_det_batch_size 4`** 强烈建议添加：RTX 5060 Ti 8GB 显存下默认 16 会导致 OOM 不断降级，训练卡死。
>
> ⚠️ **AI 生成的视频建议关闭循环播放**：AI 生成视频的帧间像素不一致（即使肉眼看不出来），静音时循环播放会产生"抽搐"效果。`process_frames()` 已内置冻结机制，静音时固定显示同一帧。真人拍摄的视频不需要此优化。

> ⚠️ **`--img_size` 必须 ≥ 256**。默认值 96 会导致 face_imgs 经过 6 层 stride-2 卷积后只剩 2×2，无法通过 kernel 4×4，推理崩溃。
>
> ⚠️ **必须用 `-m` 模块方式运行**，不能直接 `python avatars\wav2lip\genavatar.py`，否则 `ModuleNotFoundError: No module named 'avatars'`。
>
> ⚠️ **AI 生成的视频建议关闭循环播放**：AI 生成视频的帧间像素不一致（即使肉眼看不出来），静音时循环播放会产生"抽搐"效果。`process_frames()` 已内置冻结机制，静音时固定显示同一帧。真人拍摄的视频不需要此优化。

### 形象数据结构

```
data/avatars/<avatar_id>/
├── full_imgs/         # 原始帧（来自视频抽帧）
│   ├── 00000000.png
│   └── ...
├── face_imgs/         # 裁剪后的人脸（必须 256×256）
│   ├── 00000000.png
│   └── ...
└── coords.pkl         # 人脸框坐标 (y1, y2, x1, x2)，用于 paste_back_frame
```

---

## 七、TTS 配置

当前使用 **Edge TTS**（免费，无需 API Key）：

```
--tts edgetts
--REF_FILE zh-CN-YunxiaNeural
```

启动时由 `launcher/server.py` 第 170 行硬编码传入 `app.py`。切换 TTS 后端只需修改此行的 `--tts` 参数。

| TTS 后端 | 参数值 | 是否需要 API Key |
|----------|--------|:--:|
| Edge TTS | `edgetts` | ❌ 免费 |
| 千问 TTS | `qwentts` | ✅ DashScope（已过期） |
| Azure TTS | `azuretts` | ✅ Azure Speech Key |
| CosyVoice | `cosyvoice` | 需独立部署 TTS Server |

---

## 八、关键问题与解决方案

### 问题 1：形象推理崩溃（已归档，syl 形象已删除）

```
RuntimeError: Calculated padded input size per channel: (2 x 2).
Kernel size: (4 x 4). Kernel size can't be greater than actual input size
```

**根因**：`genavatar.py --img_size` 默认 96，生成 96×96 的 face_imgs。wav2lip face_encoder 有 6 层 stride=2 卷积：96→48→24→12→6→3→2。第 8 层 kernel=4×4 > 2×2，崩溃。

**解决**：`cv2.resize` 把 497 张 face_imgs 从 96×96 缩放到 256×256（`INTER_LANCZOS4`）。coords.pkl 无需修改，`paste_back_frame` 中的 `cv2.resize(pred_frame, (x2-x1, y2-y1))` 自适应。

### 问题 2：千问 API Key 过期

**根因**：启动器硬编码 `--tts qwentts`，DashScope API Key 已失效。

**解决**：切换为 `--tts edgetts --REF_FILE zh-CN-YunxiaNeural`。Edge TTS 完全免费，合成耗时 ~1.5s，效果良好。

---

## 九、GitHub 仓库

| 项目 | 详情 |
|------|------|
| **地址** | https://github.com/Peng-OnTheWay/Livetalking_Realesea_Linux |
| **分支** | `main` |
| **已排除** | 模型权重 (`*.pth`)、形象数据 (`data/avatars/`)、`env/`、`tools/`、`new_update/` |

服务器部署时需手动拖入模型权重和形象数据。

---

## 十、对主项目的接口

数字人作为独立服务运行，主项目 `Digital_Human_Project` 通过以下方式对接：

| 接口 | 协议 | 说明 |
|------|------|------|
| `POST http://localhost:8010/human` | REST | 发送对话文本（`{text, type, sessionid}`） |
| WebRTC `http://localhost:8010/offer` | WebRTC | 获取视频+音频流 |
| 启动器 `http://localhost:8000` | Web | 管理端 UI（形象选择、启停、对话测试） |

主项目无需关心数字人内部实现，只需知道 `:8010` 这个服务地址。

---

## 十、开发规范

- 所有命令在 `live-talking/LiveTalking/` 目录下执行
- Python 环境：`env/python.exe`（conda Python 3.10）
- 启动器是唯一入口，不要直接启动 `code/app.py`
- 新增形象用 `--img_size 256`
- 当前 TTS 默认 `edgetts`，不要回退到 `qwentts`

---

## 十一、手机端/客户端接入

本项目采用 **服务器端渲染 + WebRTC 推流** 架构，天然支持轻量客户端（手机/Web/小程序）：

```
GPU 服务器（RTX 5060 Ti 8GB）         客户端（手机/浏览器）
┌─────────────────────────┐         ┌──────────────────┐
│ TTS → Wav2Lip 推理      │  WebRTC │ 接收 H.264 视频流  │
│ → 渲染口型视频帧        │ ═══════→│ 播放音频+显示画面  │
│ → WebRTC 推流 :8010     │         │ （无需GPU/模型）   │
└─────────────────────────┘         └──────────────────┘
```

| 方案 | 说明 | 适用场景 |
|------|------|------|
| **方案 A：服务器推理（推荐）** | 手机只需 WebRTC 播放器，接入 `:8010/offer` | 任何智能手机，1-2 周开发 |
| 方案 B：手机本地推理 | 需 ONNX 转换 + 量化，仅旗舰机可行 | 离线场景，2-3 月开发 |

> 这与 HeyGen、D-ID、硅基智能等商用产品架构一致。

