#!/bin/bash
# ============================================================
# LiveTalking 数字人 — Linux 服务器部署脚本
# 用法: bash setup.sh
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "========================================"
echo " LiveTalking 数字人 — Linux 部署"
echo " 目录: $SCRIPT_DIR"
echo "========================================"

# ─── 1. 检查 Python ──────────────────────────────────────
PYTHON=""
for cmd in python3.10 python3 python; do
    if command -v $cmd &>/dev/null; then
        VER=$($cmd --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR=$(echo $VER | cut -d. -f1)
        MINOR=$(echo $VER | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "❌ 未找到 Python 3.10+，请先安装"
    echo "   conda create -n livetalking python=3.10"
    echo "   conda activate livetalking"
    exit 1
fi
echo "✅ 使用 Python: $PYTHON ($($PYTHON --version))"

# ─── 2. 检查 CUDA ───────────────────────────────────────
if command -v nvidia-smi &>/dev/null; then
    echo "✅ NVIDIA GPU 驱动已安装"
    nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || true
else
    echo "⚠️  未检测到 nvidia-smi，请确认 GPU 驱动和 CUDA 已安装"
fi

# ─── 3. 安装 Python 依赖 ───────────────────────────────
echo ""
echo "📦 安装 Python 依赖..."
cd "$SCRIPT_DIR/code"

# 如果 torch 未安装则安装 CUDA 版本
if ! $PYTHON -c "import torch" 2>/dev/null; then
    echo "   安装 PyTorch (CUDA)..."
    $PYTHON -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
fi

$PYTHON -m pip install -r requirements.txt

echo ""
echo "========================================"
echo " ✅ 部署完成！"
echo "========================================"
echo ""
echo "启动方式："
echo "  cd $SCRIPT_DIR/launcher"
echo "  $PYTHON server.py"
echo ""
echo "然后浏览器访问: http://<服务器IP>:8000"
echo ""
echo "训练新形象："
echo "  cd $SCRIPT_DIR/code"
echo "  $PYTHON -m avatars.wav2lip.genavatar --img_size 256 --avatar_id <新形象名> --video_path <视频路径> --face_det_batch_size 4"
echo ""
