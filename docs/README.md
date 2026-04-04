# ECG Diagnosis Suite Docs

当前仓库的主要文档入口。

## 文档索引

- [API 文档](./api.md)
- [项目优化方案](./optimization-plan.md)
- [开发指南](./development.md)
- [部署指南](./deployment.md)
- [服务器部署指南](./deployment-guide.md)
- [生产部署说明](./production-deployment.md)

## 项目概览

ECG Diagnosis Suite 是一个用于 ECG 图像与信号分析的工程化 MVP，包含：

- ECG 图片上传诊断
- `.dat + .hea` 信号对上传诊断
- 诊断历史与聊天会话持久化
- 用户认证与刷新令牌机制
- 模板化或可选 LLM 增强报告

## 当前技术栈

- 前端：React 18 + TypeScript + Vite + Tailwind CSS
- 后端：FastAPI + SQLAlchemy + PyTorch
- 数据库：MySQL（Docker 默认）或 SQLite（本地默认回退）
- 部署：Docker Compose + Nginx
