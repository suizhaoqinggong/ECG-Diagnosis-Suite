# 快速开发指南

## 🚀 快速开始（5分钟上手）

### 方式一：本地开发（推荐新手）

```bash
# 1. 启动后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# 2. 新终端启动前端
cd frontend
pnpm install
pnpm dev

# 3. 访问应用
# 前端: http://localhost:5173
# 后端: http://localhost:8000/docs
```

### 方式二：Docker部署（推荐生产）

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 📦 核心依赖说明

### 后端核心依赖
```
fastapi          - Web框架
uvicorn          - ASGI服务器
torch            - 深度学习
opencv-python    - 图像处理
sqlalchemy       - ORM
reportlab        - PDF生成
```

### 前端核心依赖
```
react            - UI框架
typescript       - 类型系统
tailwindcss      - CSS框架
axios            - HTTP客户端
react-dropzone   - 文件上传
```

---

## 🔧 常见开发任务

### 1. 添加新的API端点

```python
# backend/app/api/diagnosis.py

@router.get("/stats")
async def get_stats():
    """获取统计信息"""
    return {
        "total_diagnoses": 100,
        "accuracy": 0.95
    }
```

### 2. 添加新的前端页面

```typescript
// frontend/src/pages/NewPage.tsx
export default function NewPage() {
  return <div>New Page</div>;
}

// frontend/src/App.tsx 中添加路由
import NewPage from './pages/NewPage';
```

### 3. 修改样式

```typescript
// 使用 Tailwind CSS
<div className="bg-primary-600 text-white p-4">
  内容
</div>
```

### 4. 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "Add new table"

# 执行迁移
alembic upgrade head
```

---

## 🐛 调试技巧

### 后端调试
```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用 ipdb（推荐）
import ipdb; ipdb.set_trace()
```

### 前端调试
```typescript
// React DevTools
// 浏览器扩展: React Developer Tools

// Console 日志
console.log('Debug:', data);
```

### API测试
```bash
# 使用 httpie（推荐）
http POST http://localhost:8000/api/diagnose file@test.png

# 或使用 curl
curl -X POST http://localhost:8000/api/diagnose \
  -F "file=@test.png"
```

---

## 📝 代码规范

### Python代码规范
```bash
# 格式化代码
black app/
isort app/

# 类型检查
mypy app/

# 代码检查
pylint app/
```

### TypeScript代码规范
```bash
# 代码检查
pnpm lint

# 格式化
pnpm format
```

---

## 🔐 安全注意事项

### 环境变量管理
```bash
# ❌ 不要提交 .env 文件
.env

# ✅ 使用 .env.example 作为模板
cp .env.example .env
```

### 密钥管理
```python
# ❌ 不要硬编码密钥
SECRET_KEY = "123456"  # 错误！

# ✅ 使用环境变量
import os
SECRET_KEY = os.getenv("SECRET_KEY")
```

### 文件上传安全
```python
# 验证文件类型
if not file.content_type.startswith('image/'):
    raise HTTPException(400, "只支持图片")

# 验证文件大小
if file.size > MAX_UPLOAD_SIZE:
    raise HTTPException(400, "文件过大")
```

---

## 🚢 部署清单

### 部署前检查
- [ ] 所有环境变量已配置
- [ ] 数据库已创建
- [ ] 模型文件已上传
- [ ] HTTPS证书已配置
- [ ] 防火墙规则已设置
- [ ] 日志目录已创建

### 部署步骤
```bash
# 1. 拉取代码
git pull

# 2. 构建镜像
docker-compose build

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f

# 5. 健康检查
curl http://localhost:8000/health
```

---

## 📊 性能优化

### 后端优化
```python
# 使用异步处理
async def process_image(image):
    # 异步图像处理
    pass

# 使用缓存
from functools import lru_cache

@lru_cache(maxsize=100)
def get_symptom_info(symptom):
    return SYMPTOM_DATABASE[symptom]
```

### 前端优化
```typescript
// 使用 React.memo
const Component = React.memo(function Component() {
  // ...
});

// 使用 useMemo
const memoizedValue = useMemo(() => computeExpensiveValue(a, b), [a, b]);

// 代码分割
const LazyComponent = React.lazy(() => import('./HeavyComponent'));
```

---

## 🧪 测试

### 后端测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_api.py

# 生成覆盖率报告
pytest --cov=app tests/
```

### 前端测试
```bash
# 运行测试
pnpm test

# 测试覆盖率
pnpm test:coverage
```

---

## 📚 有用的资源

### 官方文档
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [React文档](https://react.dev/)
- [Tailwind CSS文档](https://tailwindcss.com/)
- [PyTorch文档](https://pytorch.org/docs/)

### 学习资源
- [FastAPI教程](https://fastapi.tiangolo.com/tutorial/)
- [React教程](https://react.dev/learn)
- [TypeScript手册](https://www.typescriptlang.org/docs/)

### 工具推荐
- [PyCharm](https://www.jetbrains.com/pycharm/) - Python IDE
- [VSCode](https://code.visualstudio.com/) - 通用编辑器
- [Postman](https://www.postman.com/) - API测试
- [TablePlus](https://tableplus.com/) - 数据库管理

---

## ❓ 常见问题

### Q1: 端口被占用怎么办？
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>
```

### Q2: 依赖安装失败？
```bash
# Python依赖
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir

# 前端依赖
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### Q3: 模型加载失败？
```bash
# 检查模型文件是否存在
ls -lh models/weights/

# 检查文件权限
chmod 644 models/weights/*.pth
```

### Q4: 数据库连接失败？
```bash
# 检查数据库是否运行
docker ps | grep postgres

# 检查连接字符串
echo $DATABASE_URL
```

---

## 🆘 获取帮助

1. 查看文档: `docs/` 目录
2. API文档: http://localhost:8000/docs
3. 提Issue: GitHub Issues
4. 搜索错误信息: Google / StackOverflow

---

**最后更新**: 2026-03-12
