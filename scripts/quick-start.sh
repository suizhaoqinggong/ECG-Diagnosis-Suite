#!/bin/bash

# Quick start script for ECG Diagnosis Suite

echo "🚀 ECG Diagnosis Suite - Quick Start"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 未安装${NC}"
    echo "请安装 Python 3.10 或更高版本"
    exit 1
fi

echo -e "${GREEN}✅ Python 已安装${NC}"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js 未安装${NC}"
    echo "请安装 Node.js 18 或更高版本"
    exit 1
fi

echo -e "${GREEN}✅ Node.js 已安装${NC}"

# Setup backend
echo ""
echo "📦 设置后端..."
cd backend

if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装Python依赖..."
pip install -q -r requirements.txt

# Setup frontend
echo ""
echo "📦 设置前端..."
cd ../frontend

if [ ! -d "node_modules" ]; then
    echo "安装前端依赖..."

    # Check if pnpm is installed
    if command -v pnpm &> /dev/null; then
        pnpm install
    else
        npm install
    fi
fi

# Create .env files if not exist
cd ..
if [ ! -f "backend/.env" ]; then
    echo "创建后端环境变量文件..."
    cp backend/.env.example backend/.env
fi

if [ ! -f "frontend/.env" ]; then
    echo "创建前端环境变量文件..."
    cp frontend/.env.example frontend/.env
fi

# Create necessary directories
echo ""
echo "📁 创建必要目录..."
mkdir -p data/uploads data/reports data/datasets
mkdir -p models/weights models/checkpoints
mkdir -p logs

echo ""
echo -e "${GREEN}✅ 设置完成！${NC}"
echo ""
echo "🎯 下一步操作："
echo ""
echo "1️⃣  启动后端："
echo "    cd backend"
echo "    source venv/bin/activate"
echo "    uvicorn app.main:app --reload"
echo ""
echo "2️⃣  启动前端（新终端）："
echo "    cd frontend"
echo "    pnpm dev  # 或 npm run dev"
echo ""
echo "3️⃣  访问应用："
echo "    前端: http://localhost:5173"
echo "    后端: http://localhost:8000"
echo "    API文档: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}⚠️  注意: 需要将训练好的模型放到 models/weights/ 目录${NC}"
echo ""
