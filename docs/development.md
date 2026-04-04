# 开发指南

## 本地开发

### 前置要求

- Node.js 18+
- `uv`
- 可选：MySQL 8+（不配置时后端默认回退到 SQLite）

### 1. 配置后端

```bash
cd backend
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
```

如果只想快速跑通本地环境，可以保留 `DATABASE_URL` 为 SQLite。
如果要接入 MySQL，请把 `backend/.env` 中的 `DATABASE_URL` 改成 MySQL DSN。

### 2. 启动后端

```bash
cd backend
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

也可以直接在仓库根目录运行：

```bash
./start.sh
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认地址：

- 前端：`http://localhost:5173`
- 后端：`http://127.0.0.1:8000`
- Swagger：`http://127.0.0.1:8000/docs`

## 测试

### 自动化测试

```bash
# Backend
cd backend
pytest -q tests

# Frontend
cd frontend
npm test -- --run
```

### 手工冒烟检查

历史上的模型联调脚本已移动到 `scripts/manual_checks/`，例如：

```bash
python scripts/manual_checks/check_cardioformer_integration.py
python scripts/manual_checks/check_upload_fix.py /path/to/record.dat /path/to/record.hea
```

这些脚本依赖本地模型文件或运行中的后端，不属于稳定 CI 覆盖。

## 常用环境变量

### 后端

- `DATABASE_URL`
- `MODEL_CHECKPOINT_PATH`
- `DEVICE`
- `SECRET_KEY`
- `OPENAI_API_KEY`

模板见 [backend/.env.example](/Users/azure/ECG-Diagnosis-Suite/backend/.env.example)。

### 前端

- `VITE_API_BASE_URL`
- `VITE_API_TIMEOUT`

模板见 [frontend/.env.example](/Users/azure/ECG-Diagnosis-Suite/frontend/.env.example)。

## 调试建议

- 后端问题优先看 `http://127.0.0.1:8000/health`
- 上传问题优先检查文件名、扩展名和 `.dat/.hea` 是否同名
- 前端接口问题先确认 `VITE_API_BASE_URL` 是否指向正确后端
