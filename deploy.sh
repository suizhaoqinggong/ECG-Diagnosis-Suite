#!/bin/bash
# ECG智能诊断系统 - 一键部署脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "   ECG智能诊断系统 - 自动部署脚本"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    print_error "请使用root用户运行此脚本"
    echo "运行: sudo bash $0"
    exit 1
fi

# 步骤1: 更新系统
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 1/8: 更新系统"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
print_info "更新软件包列表..."
apt update -qq

print_info "升级已安装的软件包..."
apt upgrade -y -qq

print_info "安装必要工具..."
apt install -y -qq git curl wget vim > /dev/null 2>&1

print_success "系统更新完成"

# 步骤2: 安装Docker
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 2/8: 安装Docker"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if command -v docker &> /dev/null; then
    print_success "Docker已安装"
    docker --version
else
    print_info "正在安装Docker..."
    curl -fsSL https://get.docker.com | bash > /dev/null 2>&1

    # 启动Docker
    systemctl start docker
    systemctl enable docker

    print_success "Docker安装完成"
    docker --version
fi

# 步骤3: 安装Docker Compose
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 3/8: 安装Docker Compose"
echo "━━━━━━━━━━━━━━━━��━━━━━━━━━━━━━━━━━━━━━━━"

if command -v docker-compose &> /dev/null; then
    print_success "Docker Compose已安装"
    docker-compose --version
else
    print_info "正在安装Docker Compose..."
    apt install -y -qq docker-compose > /dev/null 2>&1

    print_success "Docker Compose安装完成"
    docker-compose --version
fi

# 步骤4: 克隆项目代码
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 4/8: 获取项目代码"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PROJECT_DIR="/opt/ECG-Diagnosis-Suite"

if [ -d "$PROJECT_DIR" ]; then
    print_info "项目目录已存在，正在更新..."
    cd $PROJECT_DIR
    git pull
else
    print_info "正在克隆项目代码..."
    mkdir -p /opt
    cd /opt
    git clone https://github.com/suizhaoqinggong/ECG-Diagnosis-Suite.git
    cd ECG-Diagnosis-Suite
fi

print_success "代码已准备就绪"
print_info "项目位置: $(pwd)"

# 步骤5: 配置环境变量
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 5/8: 配置环境变量"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 获取服务器IP
SERVER_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || echo "YOUR_SERVER_IP")

print_info "检测到服务器IP: $SERVER_IP"

# 创建后端环境变量
print_info "创建后端环境变量文件..."
cat > backend/.env << EOF
DEBUG=False
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql+asyncpg://ecg:ecg123456@db:5432/ecg_db
REDIS_URL=redis://redis:6379/0
DEVICE=cpu
MODEL_PATH=./models/weights/ecg_model.pth
CORS_ORIGINS=http://$SERVER_IP,http://localhost
EOF

# 创建前端环境变量
print_info "创建前端环境变量文件..."
cat > frontend/.env << EOF
VITE_API_BASE_URL=http://$SERVER_IP:8000
VITE_APP_NAME=ECG Diagnosis Suite
EOF

print_success "环境变量配置完成"

# 步骤6: 创建必要目录
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 6/8: 创建必要目录"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━���━━━━━━━━━━━"

mkdir -p data/uploads
mkdir -p data/reports
mkdir -p models/weights
mkdir -p logs

print_success "目录创建完成"

# 步骤7: 构建并启动服务
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 7/8: 启动服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "停止旧服务（如果存在）..."
docker-compose down > /dev/null 2>&1 || true

print_info "构建Docker镜像（这可能需要几分钟）..."
docker-compose build -q

print_info "启动服务..."
docker-compose up -d

print_success "服务启动成功"

# 等待服务启动
echo ""
print_info "等待服务启动（30秒）..."
sleep 30

# 步骤8: 验证部署
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "步骤 8/8: 验证部署"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

print_info "检查容器状态..."
docker-compose ps

echo ""
print_info "测试后端API..."
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    print_success "后端API正常运行"
else
    print_error "后端API启动失败，请查看日志"
    docker-compose logs backend
fi

print_info "测试前端..."
if curl -f -s -I http://localhost:80 | grep -q "200 OK"; then
    print_success "前端正常运行"
else
    print_error "前端启动失败，请查看日志"
    docker-compose logs frontend
fi

# 显示访问信息
echo ""
echo "=========================================="
echo "   🎉 部署成功！"
echo "=========================================="
echo ""
echo "📋 访问信息:"
echo ""
echo "   前端界面:"
echo "   http://$SERVER_IP"
echo ""
echo "   后端API文档:"
echo "   http://$SERVER_IP:8000/docs"
echo ""
echo "   健康检查:"
echo "   http://$SERVER_IP:8000/health"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 常用命令:"
echo ""
echo "   查看日志:"
echo "   docker-compose logs -f"
echo ""
echo "   查看状态:"
echo "   docker-compose ps"
echo ""
echo "   重启服务:"
echo "   docker-compose restart"
echo ""
echo "   停止服务:"
echo "   docker-compose down"
echo ""
echo "   更新代码:"
echo "   git pull && docker-compose up -d --build"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
print_success "部署完成！请在浏览器中访问系统"
echo ""
