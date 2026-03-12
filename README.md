# ECG Diagnosis Suite

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![React](https://img.shields.io/badge/react-18+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**智能心电图诊断系统 - AI-Powered ECG Diagnosis Platform**

[English](#english) | [中文](#中文)

</div>

---

## 中文

### 📖 项目简介

**ECG Diagnosis Suite** 是一个基于深度学习的心电图智能诊断系统，用户只需上传ECG波形图，即可获得AI诊断结果和个性化健康报告。

### ✨ 核心功能

- 🖼️ **图片上传** - 支持拖拽、点击上传、手机拍照
- 🤖 **AI诊断** - 基于深度学习模型的智能分类
- 📊 **结果可视化** - 置信度展示、症状解释
- 📄 **健康报告** - 自动生成PDF诊断报告
- 🎨 **现代UI** - 响应式设计，支持移动端

### 🛠️ 技术栈

#### 前端
- **React 18** + TypeScript
- **Tailwind CSS** - 样式框架
- **Vite** - 构建工具
- **Axios** - HTTP客户端

#### 后端
- **FastAPI** - 高性能Web框架
- **PyTorch** - 深度学习框架
- **OpenCV** - 图像处理
- **PostgreSQL** - 数据库

#### AI模型
- **PyTorch** - 模型训练
- **ONNX Runtime** - 模型推理优化

### 📁 项目结构

```
ECG-Diagnosis-Suite/
├── frontend/                # 前端项目
│   ├── src/
│   │   ├── components/     # React组件
│   │   ├── pages/          # 页面
│   │   ├── api/            # API接口
│   │   └── utils/          # 工具函数
│   ├── public/             # 静态资源
│   └── package.json
│
├── backend/                 # 后端项目
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── models/         # 数据库模型
│   │   ├── services/       # 业务逻辑
│   │   └── core/           # 核心配置
│   ├── ml/                 # 机器学习模块
│   │   ├── models/         # 模型定义
│   │   └── preprocessing/  # 数据预处理
│   └── requirements.txt
│
├── models/                  # 模型文件
│   ├── weights/            # 训练好的权重
│   └── checkpoints/        # 训练检查点
│
├── data/                    # 数据目录
│   ├── uploads/            # 上传的图片
│   ├── reports/            # 生成的报告
│   └── datasets/           # 数据集
│
├── docs/                    # 文档
├── scripts/                 # 脚本工具
├── tests/                   # 测试文件
└── README.md
```

### 🚀 快速开始

#### 前置要求

- Node.js 18+
- Python 3.10+
- PostgreSQL 15+ (或使用SQLite for demo)

#### 1. 克隆项目

```bash
cd /Users/azure/paper/ECG-Diagnosis-Suite
```

#### 2. 后端设置

```bash
# 创建虚拟环境
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务
uvicorn app.main:app --reload
```

#### 3. 前端设置

```bash
# 新终端窗口
cd frontend

# 安装依赖
pnpm install  # 或 npm install

# 启动开发服务器
pnpm dev  # 或 npm run dev
```

#### 4. 访问应用

- 前端: http://localhost:5173
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 📊 使用流程

```
1. 打开网页
   ↓
2. 上传ECG图片（拖拽或点击）
   ↓
3. 点击"开始诊断"
   ↓
4. 查看AI诊断结果
   ↓
5. 导出PDF健康报告
```

### 🎯 开发路线

- [x] 项目结构搭建
- [ ] 后端API开发
- [ ] 前端界面开发
- [ ] AI模型集成
- [ ] PDF报告生成
- [ ] 测试和优化
- [ ] 部署上线

### 📝 更新日志

#### v1.0.0 (2026-03-12)
- 🎉 项目初始化
- 📁 创建项目结构
- 📝 编写基础文档

### 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

### ⚠️ 免责声明

本系统仅供学术研究和教育目的，**不用于临床诊断**。诊断结果需由持证医师审核确认。

---

## English

### 📖 Introduction

**ECG Diagnosis Suite** is an AI-powered ECG diagnosis system. Users can upload ECG waveform images and receive AI diagnosis results with personalized health reports.

### ✨ Key Features

- 🖼️ **Image Upload** - Drag & drop, click to upload, or camera capture
- 🤖 **AI Diagnosis** - Deep learning-based intelligent classification
- 📊 **Visualization** - Confidence display and symptom explanation
- 📄 **Health Reports** - Auto-generated PDF diagnosis reports
- 🎨 **Modern UI** - Responsive design with mobile support

### 🛠️ Tech Stack

#### Frontend
- **React 18** + TypeScript
- **Tailwind CSS**
- **Vite**
- **Axios**

#### Backend
- **FastAPI**
- **PyTorch**
- **OpenCV**
- **PostgreSQL**

#### AI Model
- **PyTorch** - Model training
- **ONNX Runtime** - Optimized inference

### 🚀 Quick Start

#### Prerequisites

- Node.js 18+
- Python 3.10+
- PostgreSQL 15+ (or SQLite for demo)

#### 1. Setup Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

#### 2. Setup Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

#### 3. Access Application

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 📄 License

MIT License - See [LICENSE](LICENSE) file

### ⚠️ Disclaimer

This system is for **academic research and educational purposes only**, not for clinical diagnosis. Results should be reviewed by certified physicians.

---

<div align="center">

**Made with ❤️ by ECG Diagnosis Suite Team**

</div>
