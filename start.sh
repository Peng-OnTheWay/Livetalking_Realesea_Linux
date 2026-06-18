#!/bin/bash
# ============================================================
# LiveTalking 数字人 — 启动脚本 (单端口 :8010)
# 用法: bash start.sh [avatar_id] [tts_voice]
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/code"

# 默认参数（可通过命令行覆盖）
AVATAR_ID="${1:-orange03}"
TTS_VOICE="${2:-zh-CN-YunxiaNeural}"
WAV2LIP_MODEL="256"

# 自动检测 Python（优先 conda 环境，其次系统 python3）
PYTHON=""
if [ -f "/mnt/xp/livetalking-env/bin/python" ]; then
    PYTHON="/mnt/xp/livetalking-env/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
elif command -v python &>/dev/null; then
    PYTHON="python"
else
    echo "❌ 未找到 Python"
    exit 1
fi

echo "=========================================="
echo " LiveTalking 数字人服务"
echo " 形象: $AVATAR_ID"
echo " 音色: $TTS_VOICE"
echo " 端口: 8010"
echo " Python: $PYTHON"
echo "=========================================="

exec $PYTHON app.py \
    --transport webrtc \
    --model wav2lip \
    --tts edgetts \
    --avatar_id "$AVATAR_ID" \
    --wav2lip_model "$WAV2LIP_MODEL" \
    --REF_FILE "$TTS_VOICE"
