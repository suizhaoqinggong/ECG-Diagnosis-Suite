# 部署指南

## 本地 Docker Compose

这是最直接的整仓部署方式，适合本机联调或演示环境。

### 前置要求

- Docker 24+
- Docker Compose v2
- 至少 4GB 可用内存

### 启动

```bash
docker compose up --build
```

> 如果是本地直接运行（不用 Docker），才需要复制 `.env` 文件：
> ```bash
> cp backend/.env.example backend/.env
> cp frontend/.env.example frontend/.env
> ```

默认服务：

- 前端：`http://localhost`
- 后端：`http://localhost:8000`
- MySQL：`localhost:3306`（仅开发环境暴露，生产环境不暴露）

### 常用命令

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose down
docker compose down -v
```

## 环境变量

### 后端

至少确认这些值：

```env
DEBUG=False
SECRET_KEY=change-me
DATABASE_URL=mysql+asyncmy://ecg:ecg123456@db:3306/ecg_db
DEVICE=cpu
MODEL_CHECKPOINT_PATH=/app/models/checkpoints/best.ckpt
```

### 前端

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 模型文件

后端会按以下顺序查找检查点：

1. `backend/models/checkpoints/best.ckpt`
2. `backend/models/weights/best.ckpt`
3. `models/checkpoints/best.ckpt`
4. `models/weights/best.ckpt`

也可以通过 `MODEL_CHECKPOINT_PATH` 显式覆盖。

## 生产环境

如果是服务器正式部署，请使用生产配置和专用部署脚本：

```bash
cp .env.production.example .env.production
# 编辑 .env.production 填入真实值
bash deploy.sh
```

详细说明见 [production-deployment.md](./production-deployment.md)。
