# 服务器部署指南

## 适用场景

这份文档面向单机云服务器部署，默认使用：

- `docker-compose.prod.yml`
- `.env.production`
- Nginx 反向代理
- MySQL 8.4

如果你只是本机联调，请直接看 [deployment.md](/Users/azure/ECG-Diagnosis-Suite/docs/deployment.md)。

## 推荐服务器

- Ubuntu 22.04 LTS
- 2 vCPU / 4 GB RAM 起步
- 至少 40 GB SSD

## 1. 安装 Docker 与 Compose

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo apt install -y docker-compose-plugin
docker --version
docker compose version
```

## 2. 准备代码与环境文件

```bash
git clone <your-repo-url> ECG-Diagnosis-Suite
cd ECG-Diagnosis-Suite
cp .env.production.example .env.production
```

至少检查这些配置项：

```env
APP_DOMAIN=your-domain.com
MYSQL_DATABASE=ecg_db
MYSQL_USER=ecg
MYSQL_PASSWORD=change-me
MYSQL_ROOT_PASSWORD=change-me-too
SECRET_KEY=change-me
MODEL_CHECKPOINT_PATH=/app/models/checkpoints/best.ckpt
```

## 3. 启动生产栈

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

验证状态：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml ps
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f backend
```

## 4. 检查服务

- 前端首页：`https://your-domain.com`
- 健康检查：`https://your-domain.com/health`
- API 文档：仅在启用 `API_DOCS_ENABLED=True` 时暴露

## 5. 开放端口

建议仅开放：

- `22/tcp`
- `80/tcp`
- `443/tcp`

不要直接把数据库端口暴露到公网。

## 6. 后续维护

更新服务：

```bash
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

停止服务：

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml down
```

更完整的生产说明见
[production-deployment.md](/Users/azure/ECG-Diagnosis-Suite/docs/production-deployment.md)。
