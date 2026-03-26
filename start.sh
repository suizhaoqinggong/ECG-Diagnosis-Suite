#!/bin/bash
# ECG Diagnosis Suite - 快速启动脚本

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
DEFAULT_CHECKPOINT="$PROJECT_ROOT/models/checkpoints/best.ckpt"
ALT_CHECKPOINT="$PROJECT_ROOT/models/weights/best.ckpt"

echo "================================"
echo "ECG Diagnosis Suite - 启动"
echo "================================"
echo ""

# 检查是否在正确的目录
if [ ! -f "$BACKEND_DIR/app/main.py" ]; then
    echo "❌ 错误：项目结构不完整，找不到 backend/app/main.py"
    exit 1
fi

# 检查Python环境
if [ ! -d "$BACKEND_DIR/venv" ]; then
    echo "❌ 错误：虚拟环境不存在，请先运行:"
    echo "   cd \"$BACKEND_DIR\" && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 检查模型权重
MODEL_CHECKPOINT_PATH="${MODEL_CHECKPOINT_PATH:-}"
if [ -z "$MODEL_CHECKPOINT_PATH" ]; then
    if [ -f "$DEFAULT_CHECKPOINT" ]; then
        MODEL_CHECKPOINT_PATH="$DEFAULT_CHECKPOINT"
    elif [ -f "$ALT_CHECKPOINT" ]; then
        MODEL_CHECKPOINT_PATH="$ALT_CHECKPOINT"
    fi
fi

if [ -z "$MODEL_CHECKPOINT_PATH" ]; then
    echo "⚠️  警告：模型权重文件不存在（可通过 MODEL_CHECKPOINT_PATH 指定）"
    echo "   系统将使用随机初始化（仅用于测试）"
fi

echo "✅ 环境检查通过"
echo ""

# 启动后端
echo "🚀 启动后端服务..."
cd "$BACKEND_DIR"
MODEL_CHECKPOINT_PATH="$MODEL_CHECKPOINT_PATH" venv/bin/python -m uvicorn app.main:app --reload --port 8000 > /tmp/ecg_backend.log 2>&1 &
BACKEND_PID=$!
echo "   后端PID: $BACKEND_PID"
echo "   后端日志: /tmp/ecg_backend.log"

# 等待后端启动
echo ""
echo "⏳ 等待后端启动..."
sleep 5

# 检查后端是否启动成功
if curl -s http://127.0.0.1:8000/docs > /dev/null 2>&1; then
    echo "✅ 后端启动成功"
    echo "   API文档: http://127.0.0.1:8000/docs"
else
    echo "❌ 后端启动失败，请检查日志:"
    echo "   tail -50 /tmp/ecg_backend.log"
    exit 1
fi

echo ""
echo "================================"
echo "🎉 系统启动完成！"
echo "================================"
echo ""
echo "服务状态:"
echo "  后端API: http://127.0.0.1:8000"
echo "  API文档: http://127.0.0.1:8000/docs"
echo ""
echo "支持的输入格式:"
echo "  - 图片: .png, .jpg, .jpeg"
echo "  - ECG数据: .dat (PTB-XL格式，需配套.hea文件)"
echo ""
echo "测试命令:"
echo "  # 图片上传"
echo "  curl -X POST http://127.0.0.1:8000/api/diagnose -F 'file=@test.png'"
echo ""
echo "  # .dat + .hea 文件上传"
echo "  curl -X POST http://127.0.0.1:8000/api/diagnose-dat -F 'files=@record.dat' -F 'files=@record.hea'"
echo ""
echo "启动前端:"
echo "  cd \"$PROJECT_ROOT/frontend\" && npm run dev"
echo ""
echo "停止服务:"
echo "  kill $BACKEND_PID"
echo ""
