# 部署指南

## 🐳 Docker部署（推荐）

### 前置要求
- Docker 20+
- Docker Compose 2+
- 至少4GB内存

### 快速部署

```bash
# 1. 克隆项目
cd ECG-Diagnosis-Suite

# 2. 配置环境变量
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. 准备模型文件
# 将模型文件放到 models/weights/ecg_model.pth

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f

# 6. 访问应用
# http://localhost
```

### Docker命令

```bash
# 查看运行状态
docker-compose ps

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 清理数据
docker-compose down -v
```

---

## ☁️ 云服务部署

### 阿里云部署

#### 1. 购买服务器
- 推荐配置: 2核4G
- 系统: Ubuntu 22.04
- 带宽: 3Mbps

#### 2. 安装Docker
```bash
# 更新包
sudo apt update

# 安装Docker
curl -fsSL https://get.docker.com | sh

# 安装Docker Compose
sudo apt install docker-compose-plugin

# 添加当前用户到docker组
sudo usermod -aG docker $USER
```

#### 3. 部署应用
```bash
# 上传代码
scp -r ECG-Diagnosis-Suite user@server:/home/user/

# SSH登录
ssh user@server

# 启动服务
cd ECG-Diagnosis-Suite
docker-compose up -d
```

#### 4. 配置域名（可选）
```nginx
# /etc/nginx/sites-available/ecg-diagnosis
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
    }
}
```

---

### AWS部署

#### 1. EC2实例
- AMI: Ubuntu 22.04
- 实例类型: t3.medium
- 安全组: 开放80, 443端口

#### 2. 使用ECS（可选）
```bash
# 构建并推送镜像
docker build -t ecg-backend ./backend
docker push your-ecr-repo/ecg-backend

# 使用ECS部署
aws ecs create-cluster --cluster-name ecg-cluster
```

---

## 📊 生产环境配置

### 环境变量配置

```bash
# backend/.env
DEBUG=False
SECRET_KEY=your-production-secret-key
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/ecg_db
DEVICE=cuda  # 如果有GPU
```

### Nginx配置

```nginx
# 启用HTTPS
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 安全headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }
}
```

### 性能优化

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## 🔒 安全配置

### 1. 防火墙
```bash
# 只开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. SSL证书（Let's Encrypt）
```bash
# 安装Certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 数据库安全
```bash
# 使用强密码
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# 限制数据库访问
# 只允许内网访问
```

---

## 📈 监控和日志

### 日志管理
```bash
# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 日志轮转
# 在docker-compose.yml中添加
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### 监控（可选）
```yaml
# 添加Prometheus监控
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
```

---

## 🔄 更新和维护

### 更新代码
```bash
# 拉取最新代码
git pull

# 重新构建
docker-compose build

# 重启服务
docker-compose up -d
```

### 数据备份
```bash
# 备份数据库
docker exec ecg-db pg_dump -U ecg ecg_db > backup.sql

# 备份上传文件
tar -czf uploads_backup.tar.gz data/uploads/
```

### 健康检查
```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查磁盘空间
df -h

# 检查内存使用
free -h
```

---

## 🐛 故障排查

### 服务无法启动
```bash
# 检查日志
docker-compose logs

# 检查端口占用
lsof -i :80
lsof -i :8000

# 检查容器状态
docker ps -a
```

### 数据库连接失败
```bash
# 检查数据库状态
docker exec -it ecg-db psql -U ecg -d ecg_db

# 检查网络
docker network ls
docker network inspect ecg-network
```

### 性能问题
```bash
# 查看资源使用
docker stats

# 优化配置
# 增加worker数量
# 启用缓存
# 使用CDN
```

---

**最后更新**: 2026-03-12
