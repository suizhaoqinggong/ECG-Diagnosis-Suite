# Tests

自动化测试入口说明。

## 当前测试布局

- `backend/tests/`：后端单元与集成测试
- `frontend/src/__tests__/`：前端组件与控制器测试
- `tests/`：仓库级基础测试

## 运行方式

### 后端

```bash
cd backend
pytest -q tests
```

### 前端

```bash
cd frontend
npm test -- --run
```

## 手工检查

历史上的模型联调脚本已经移动到 `scripts/manual_checks/`，不再作为
`pytest` 自动发现的一部分。

```bash
python scripts/manual_checks/check_cardioformer_integration.py
```
