# Tests

自动化测试入口说明。

## 当前测试布局

- `backend/tests/`：后端单元与集成测试
- `frontend/src/__tests__/`：前端组件与控制器测试
- `tests/`：仓库级基础测试

## 运行方式

### 后端

```bash
./backend/.venv/bin/python -m pytest -q tests backend/tests
```

### 前端

```bash
cd frontend
npm test -- --run
```

仓库当前不再保留手工 smoke-check 脚本，日常验证以自动化测试为准。
