# 🚀 云服务器部署指南

**项目**: ECG智能诊断系统
**部署方式**: Docker + 云服务器
**预计时间**: 2-3小时
**难度**: ⭐⭐⭐

---

## 📋 部署架构

```
用户浏览器
    ↓
域名 (可选)
    ↓
Nginx反向代理
    ↓
前端容器 (React) - 端口80
后端容器 (FastAPI) - 端口8000
    ↓
PostgreSQL数据库
Redis缓存
```

---

## 🏢 第一步：选择云服务商

### 国内推荐

#### 1. 阿里云（推荐）⭐⭐⭐⭐⭐

**优势**:
- 国内访问速度快
- 文档完善
- 学生优惠

**推荐配置**:
```
实例类型: ecs.t6-c1m2.large (2核4GB)
操作系统: Ubuntu 22.04 64位
带宽: 3Mbps
系统盘: 40GB SSD
价格: 约¥100-150/月
```

**学生优惠**:
- 学生认证后可享受超低价
- 约¥10-30/月

**购买链接**: https://www.aliyun.com/

---

#### 2. 腾讯云 ⭐⭐⭐⭐

**优势**:
- 价格实惠
- 新用户优惠多

**推荐配置**:
```
实例类型: S5.MEDIUM4 (2核4GB)
价格: 约¥80-120/月
```

**��买链接**: https://cloud.tencent.com/

---

#### 3. 华为云 ⭐⭐⭐

**优势**:
- 企业级服务
- 安全性高

---

### 国外推荐

#### AWS (亚马逊) ⭐⭐⭐⭐

**推荐配置**:
```
实例类型: t3.medium (2核4GB)
区域: 新加坡或东京
价格: 约$30-50/月
```

**免费套餐**:
- 新用户12个月免费
- t2.micro (1核1GB)

---

## 💻 第二步：购买和配置服务器

### 以阿里云为例

#### 1. 购买服务器

1. 登录阿里云控制台
2. 选择"云服务器ECS"
3. 点击"创建实例"
4. 选择配置:
   - 地域: 华北2（北京）或华东1（杭州）
   - 实例规格: 2核4GB
   - 镜像: Ubuntu 22.04 64位
   - 存储: 40GB SSD
   - 网络: 按使用流量
   - 带宽: 3Mbps

5. 设置密码（记住root密码）
6. 确认订单并支付

---

#### 2. 配置安全组

**重要！开放必要端口**

```
入方向规则:
- 22端口 (SSH) - 允许
- 80端口 (HTTP) - 允许
- 443端口 (HTTPS) - 允许
- 8000端口 (后端API) - 可选

出方向规则:
- 全部允许
```

**操作步骤**:
1. 在实例详情页，点击"安全组"
2. 点击"配置规则"
3. 添加上述端口规则

---

## 🔌 第三步：连接到服务器

### Windows用户

#### 使用PuTTY或XShell

**下载地址**:
- PuTTY: https://www.putty.org/
- XShell: https://www.xshell.com/

**连接信息**:
```
主机: 你的服务器公网IP
端口: 22
用户名: root
密码: 购买时设置的密码
```

---

### Mac/Linux用户

使用终端SSH连接：

```bash
ssh root@你的服务器公网IP

# 输入密码（不会显示，直接输入后按回车）
```

**示例**:
```bash
ssh root@123.456.789.123
```

---

## 🛠️ 第四步：服务器环境配置

### 1. 更新系统

连接到服务器后，首先更新系统：

```bash
# 更新包列表
apt update

# 升级已安装的包
apt upgrade -y

# 安装必要的工具
apt install -y git curl wget vim
```

---

### 2. 安装Docker

```bash
# 安装Docker
curl -fsSL https://get.docker.com | bash

# 启动Docker服务
systemctl start docker
systemctl enable docker

# 验证安装
docker --version
```

**预期输出**:
```
Docker version 24.0.x, build xxxxxxx
```

---

### 3. 安装Docker Compose

```bash
# 安装Docker Compose
apt install -y docker-compose

# 验证安装
docker-compose --version
```

---

### 4. 安装Nginx（可选，用于反向代理）

```bash
apt install -y nginx
systemctl start nginx
systemctl enable nginx
```

---

## 📦 第五步：部署项目

### 1. 克隆项目代码

```bash
# 创建工作目录
mkdir -p /opt/projects
cd /opt/projects

# 克隆GitHub仓库
git clone https://github.com/suizhaoqinggong/ECG-Diagnosis-Suite.git

# 进入项目目录
cd ECG-Diagnosis-Suite
```

---

### 2. 配置环境变量

```bash
# 创建后端环境变量文件
cat > backend/.env << 'EOF'
DEBUG=False
SECRET_KEY=your-production-secret-key-change-this
DATABASE_URL=postgresql+asyncpg://ecg:password@db:5432/ecg_db
REDIS_URL=redis://redis:6379/0
DEVICE=cpu
MODEL_PATH=./models/weights/ecg_model.pth
CORS_ORIGINS=http://你的服务器IP,http://你的域名
EOF

# 创建前端环境变量文件
cat > frontend/.env << 'EOF'
VITE_API_BASE_URL=http://你的服务器IP:8000
# 或使用域名: VITE_API_BASE_URL=https://你的域名
EOF
```

**⚠️ 重要**: 替换`你的服务器IP`和`你的域名`为实际值

---

### 3. 准备模型文件（可选）

如果有训练好的模型权重：

```bash
# 创建模型目录
mkdir -p models/weights

# 上传模型文件
# 方法1: 使用scp从本地上传
scp /path/to/your/model.pth root@服务器IP:/opt/projects/ECG-Diagnosis-Suite/models/weights/

# 方法2: 或从其他服务器下载
wget -O models/weights/ecg_model.pth https://your-model-url
```

---

### 4. 使用Docker Compose部署

```bash
# 确保在项目根目录
cd /opt/projects/ECG-Diagnosis-Suite

# 构建并启动所有服务
docker-compose up -d

# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

**预期输出**:
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
ecg-backend         "uvicorn app.main:ap…"   backend             running             0.0.0.0:8000->8000/tcp
ecg-frontend        "nginx -g 'daemon of…"   frontend            running             0.0.0.0:80->80/tcp
ecg-db              "docker-entrypoint.s…"   db                  running             5432/tcp
ecg-redis           "docker-entrypoint.s…"   redis               running             6379/tcp
```

---

### 5. 验证部署

```bash
# 测试后端API
curl http://localhost:8000/health

# 测试前端
curl -I http://localhost
```

**在本地浏览器访问**:
- 前端: http://你的服务器IP
- 后端API: http://你的服务器IP:8000/docs

---

## 🌐 第六步：配置域名（可选）

### 1. 购买域名

**推荐域名注册商**:
- 阿里云（万网）
- 腾讯云
- GoDaddy
- Namecheap

**价格**: ¥10-100/年

---

### 2. 域名解析

**阿里云域名解析配置**:

1. 登录阿里云域名控制台
2. 找到你的域名，点击"解析"
3. 添加记录:

```
记录类型: A
主机记录: @ (或 www)
解析路线: 默认
记录值: 你的服务器公网IP
TTL: 10分钟
```

**示例**:
```
记录类型: A
主机记录: ecg
记录值: 123.456.789.123
```

访问: http://ecg.你的域名.com

---

## 🔒 第七步：配置HTTPS（推荐）

### 使用Let's Encrypt免费证书

#### 1. 安装Certbot

```bash
# 安装Certbot
apt install -y certbot python3-certbot-nginx
```

---

#### 2. 获取SSL证书

```bash
# 停止Nginx（如果正在运行）
systemctl stop nginx

# 获取证书
certbot certonly --standalone -d 你的域名

# 按提示输入邮箱地址
# 同意服务条款
```

**证书位置**:
```
/etc/letsencrypt/live/你的域名/fullchain.pem
/etc/letsencrypt/live/你的域名/privkey.pem
```

---

#### 3. 配置Nginx

创建Nginx配置文件：

```bash
cat > /etc/nginx/sites-available/ecg-diagnosis << 'EOF'
# HTTP重定向到HTTPS
server {
    listen 80;
    server_name 你的域名;
    return 301 https://$server_name$request_uri;
}

# HTTPS配置
server {
    listen 443 ssl http2;
    server_name 你的域名;

    # SSL证书
    ssl_certificate /etc/letsencrypt/live/你的域名/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/你的域名/privkey.pem;

    # SSL优化
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;

    # 安全headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 前端
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

# 启用配置
ln -s /etc/nginx/sites-available/ecg-diagnosis /etc/nginx/sites-enabled/

# 测试配置
nginx -t

# 重启Nginx
systemctl restart nginx
```

---

#### 4. 自动续期

```bash
# 测试自动续期
certbot renew --dry-run

# 添加定时任务自动续期
crontab -e

# 添加以下行（每天凌晨2点检查并续期）
0 2 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## 📊 第八步：监控和维护

### 1. 查看服务状态

```bash
# 查看Docker容器状态
docker-compose ps

# 查看资源使用
docker stats

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

### 2. 更新代码

```bash
cd /opt/projects/ECG-Diagnosis-Suite

# 拉取最新代码
git pull

# 重新构建并启动
docker-compose down
docker-compose up -d --build
```

---

### 3. 数据备份

```bash
# 备份数据库
docker exec ecg-db pg_dump -U ecg ecg_db > backup_$(date +%Y%m%d).sql

# 备份上传的文件
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz data/uploads/
```

---

### 4. 性能监控

安装监控工具（可选）：

```bash
# 安装htop
apt install -y htop

# 安装netstat
apt install -y net-tools

# 查看系统资源
htop

# 查看网络连接
netstat -tuln
```

---

## 🐛 常见问题解决

### 问题1: 端口被占用

```bash
# 查看端口占用
lsof -i :80
lsof -i :8000

# 杀死占用进程
kill -9 <PID>
```

---

### 问题2: Docker服务无法启动

```bash
# 查看Docker状态
systemctl status docker

# 重启Docker
systemctl restart docker

# 查看Docker日志
journalctl -u docker
```

---

### 问题3: 容器启动失败

```bash
# 查看容器日志
docker-compose logs

# 重新构建
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

### 问题4: 内存不足

```bash
# 查看内存使用
free -h

# 创建swap文件
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

### 问题5: 无法访问

**检查清单**:
1. 安全组端口是否开放
2. 防火墙是否允许
3. Docker容器是否正常运行
4. Nginx配置是否正确

```bash
# 检查防火墙
ufw status

# 开放端口
ufw allow 80
ufw allow 443
ufw allow 8000
```

---

## 💰 成本估算

### 阿里云方案

```
服务器（2核4GB）: ¥100-150/月
域名: ¥10-100/年
HTTPS证书: 免费
带宽流量: ¥10-30/月

总计: 约¥120-180/月
```

**学生优惠**: 约¥10-40/月

---

### 腾讯云方案

```
服务器（2核4GB）: ¥80-120/月
域名: ¥10-100/年
总计: 约¥90-150/月
```

---

### AWS方案

```
服务器（t3.medium）: $30-50/月
域名: $10-15/年
流量: $5-10/月

总计: 约$35-60/月
```

---

## 📋 部署检查清单

部署前确认：

- [ ] 已购买云服务器
- [ ] 已配置安全组开放端口
- [ ] 已安装Docker和Docker Compose
- [ ] 已克隆项目代码
- [ ] 已配置环境变量
- [ ] 已上传模型文件（如有）
- [ ] 已启动Docker服务
- [ ] 已验证服务可访问
- [ ] 已配置域名（可选）
- [ ] 已配置HTTPS（推荐）

---

## 🎯 快速部署命令总结

```bash
# 1. 连接服务器
ssh root@你的服务器IP

# 2. 安装Docker
curl -fsSL https://get.docker.com | bash

# 3. 克隆项目
git clone https://github.com/suizhaoqinggong/ECG-Diagnosis-Suite.git
cd ECG-Diagnosis-Suite

# 4. 配置环境变量
vim backend/.env
vim frontend/.env

# 5. 启动服务
docker-compose up -d

# 6. 查看状态
docker-compose ps

# 7. 访问测试
curl http://localhost:8000/health
```

---

## 🚀 部署成功标志

当你可以：
- ✅ 通过IP访问前端界面
- ✅ 通过API文档测试功能
- ✅ 上传ECG图片获得诊断结果
- ✅ （可选）通过域名访问
- ✅ （推荐）使用HTTPS安全访问

恭喜！部署成功！🎉

---

## 📞 需要帮助？

### 我可以帮你：

1. **购买服务器指导**
   - 推荐配置
   - 选择地域
   - 设置安全组

2. **环境配��**
   - 安装依赖
   - 配置环境变量
   - 调试问题

3. **域名配置**
   - 域名购买
   - 解析配置
   - HTTPS证书

4. **问题排查**
   - 查看日志
   - 解决错误
   - 性能优化

---

**创建时间**: 2026-03-12
**难度**: ⭐⭐⭐
**预计时间**: 2-3小时
**维护难度**: ⭐⭐

---

<div align="center">

**📖 完整的部署指南已准备好！**

**需要我帮你做什么？**

**1. 详细指导某个步骤** | **2. 提供具体的命令** | **3. 解决特定问题**

</div>
