# Tests

测试文件目录。

## 测试类型

### 单元测试
- `test_api.py` - API测试
- `test_preprocessing.py` - 预处理测试
- `test_model.py` - 模型测试

### 集成测试
- `test_integration.py` - 集成测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=app tests/
```
