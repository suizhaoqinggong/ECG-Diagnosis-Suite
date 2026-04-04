#!/bin/bash
# 手工验证双文件上传功能

echo "=================================="
echo "测试.dat+.hea双文件上传"
echo "=================================="
echo ""

# 检查参数
if [ $# -lt 2 ]; then
    echo "用法: $0 <dat文件路径> <hea文件路径>"
    echo ""
    echo "示例:"
    echo "  $0 record.dat record.hea"
    exit 1
fi

DAT_FILE=$1
HEA_FILE=$2

# 检查文件是否存在
if [ ! -f "$DAT_FILE" ]; then
    echo "❌ 错误: .dat文件不存在: $DAT_FILE"
    exit 1
fi

if [ ! -f "$HEA_FILE" ]; then
    echo "❌ 错误: .hea文件不存在: $HEA_FILE"
    exit 1
fi

echo "📁 上传文件:"
echo "   .dat: $DAT_FILE"
echo "   .hea: $HEA_FILE"
echo ""

# 执行上传
echo "🔄 上传中..."
RESPONSE=$(curl -s -X POST http://127.0.0.1:8000/api/diagnose-dat \
    -F "files=@$DAT_FILE" \
    -F "files=@$HEA_FILE")

# 检查响应
if echo "$RESPONSE" | grep -q "prediction"; then
    echo "✅ 上传成功！"
    echo ""
    echo "📊 诊断结果:"
    echo "$RESPONSE" | python3 -m json.tool
else
    echo "❌ 上传失败"
    echo "$RESPONSE"
fi
