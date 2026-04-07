# ECG 智能诊断系统 - 系统架构设计文档

**版本**: 1.0
**日期**: 2026-04-07
**文档类型**: 系统架构设计

---

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构总览](#2-系统架构总览)
3. [技术栈选型](#3-技术栈选型)
4. [后端架构](#4-后端架构)
5. [前端架构](#5-前端架构)
6. [机器学习模型架构](#6-机器学习模型架构)
7. [数据流与业务流程](#7-数据流与业务流程)
8. [数据库设计](#8-数据库设计)
9. [安全设计](#9-安全设计)
10. [部署架构](#10-部署架构)

---

## 1. 项目概述

### 1.1 项目背景

ECG 智能诊断系统是一个面向医疗场景的 AI 辅助诊断平台，支持用户上传心电图图像（PNG/JPG）或标准信号文件（.dat/.hea），通过深度学习模型自动分析并生成诊断报告。系统设计遵循"文档式对话"理念，将诊断过程呈现为可阅读、可回溯的医疗记录。

### 1.2 核心功能

| 功能模块 | 描述 |
|---------|------|
| **图像诊断** | 上传 ECG 纸质报告照片，自动提取 12 导联信号并分析 |
| **信号诊断** | 上传标准 WFDB 格式 (.dat+.hea) 信号文件进行分析 |
| **对话式记录** | 以会话形式管理多次诊断，支持历史回溯 |
| **增强报告** | 模板或 LLM 生成的结构化临床报告 |
| **质量管控** | 多级质量检查，包括图像验证、信号提取 QC、导联相关性分析 |
| **用户系统** | 支持匿名使用（本地存储）和注册登录（云端同步） |

### 1.3 设计目标

- **准确性**: 基于 CardioFormer Transformer 模型，在 PTB-XL 数据集上训练
- **可解释性**: 提供置信度、Top-3 预测、质量指标等多维度信息
- **鲁棒性**: 多层安全机制，防御恶意输入和异常数据
- **可扩展性**: 模块化架构，支持模型升级和功能扩展
- **双语支持**: 中文优先界面，英文标签保留

---

## 2. 系统架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              前端层 (Frontend)                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │   React 18   │ │   TypeScript │ │  TailwindCSS │ │    Axios     │         │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘         │
│                              (单页应用 SPA)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ HTTP / WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API 层 (Backend)                                │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                        FastAPI (Python 3.11)                         │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────────┐  │   │
│  │  │  诊断路由    │ │  认证路由    │ │  会话路由    │ │   限流中间件    │  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ SQL / File I/O
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             服务层 (Services)                                │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐  │
│  │ DiagnosisService│ │ReportService   │ │  AuthService   │ │ECGDataLoader │  │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Tensor / Array
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           模型层 (ML Pipeline)                               │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     CardioFormer Service (Singleton)                 │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │   │
│  │  │Image Decoder │ │Image→Signal  │ │Signal Quality│ │ CardioFormer │  │   │
│  │  │  (Layer 0)   │ │  (Layer 1)   │ │   (Gate)     │ │  (Inference) │  │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ SQL / File
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            数据层 (Data)                                     │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ ┌──────────────┐  │
│  │   SQLite/MySQL │ │  Local Files   │ │ Model Weights  │ │   Session    │  │
│  │   (SQLAlchemy) │ │  (Uploads/Reports)│ │   (.ckpt)   │ │  localStorage│  │
│  └────────────────┘ └────────────────┘ └────────────────┘ └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件关系图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            用户交互层                                     │
│     ChatComposer ◄────► ConversationMessage ◄────► DiagnosisReport      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ useWorkspaceController
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           状态管理层                                      │
│         WorkspaceState (useReducer) ──┬── persisted (sessions)          │
│                                       ├── composer (draft/attachments)  │
│                                       ├── submission (upload/progress)  │
│                                       └── ui (sidebar/flags)            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
         ┌─────────────────────┐        ┌─────────────────────┐
         │   diagnosisApi      │        │      chatApi        │
         │  /api/diagnose      │        │   /api/chat/*       │
         │  /api/diagnose-dat  │        │                     │
         └─────────────────────┘        └─────────────────────┘
                    │                               │
                    └───────────────┬───────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           业务服务层                                      │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐  │
│   │  File Upload │   │Image-to-Sig │   │  ML Model   │   │   Report    │  │
│   │   Security   │   │   Extraction│   │  Inference  │   │ Generation  │  │
│   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 技术栈选型

### 3.1 后端技术栈

| 类别 | 技术选型 | 版本 | 选型理由 |
|-----|---------|------|---------|
| **Web 框架** | FastAPI | 0.109+ | 原生异步支持、自动 OpenAPI 文档、Pydantic 验证 |
| **数据库 ORM** | SQLAlchemy 2.0 | 2.0+ | 异步支持、类型安全、Alembic 迁移 |
| **数据库** | SQLite (dev) / MySQL (prod) | - | 开发便捷，生产可靠 |
| **认证** | PyJWT + scrypt | - | JWT 访问令牌 + HttpOnly Cookie 刷新令牌 |
| **ML 框架** | PyTorch | 2.0+ | 动态图、丰富的预训练生态 |
| **信号处理** | wfdb + scipy | - | 标准 ECG 格式支持、重采样 |
| **图像处理** | OpenCV + PIL | - | 工业级图像处理、EXIF 支持 |
| **部署** | Uvicorn + Gunicorn | - | ASGI 服务器、生产级 worker 管理 |

### 3.2 前端技术栈

| 类别 | 技术选型 | 版本 | 选型理由 |
|-----|---------|------|---------|
| **UI 框架** | React | 18.3+ | 并发特性、成熟生态 |
| **语言** | TypeScript | 5.4+ | 类型安全、IDE 支持 |
| **构建工具** | Vite | 5.1+ | 快速 HMR、优化构建 |
| **样式** | TailwindCSS | 3.4+ | 原子化 CSS、设计系统一致 |
| **状态管理** | useReducer + Context | - | 足够复杂的本地状态，无需 Redux |
| **HTTP 客户端** | Axios | 1.6+ | 拦截器、上传进度、取消令牌 |
| **测试** | Vitest + Testing Library | - | Vite 原生集成、组件测试 |

### 3.3 机器学习技术栈

| 组件 | 技术 | 说明 |
|-----|------|------|
| **主模型** | CardioFormer | 多粒度 Transformer，基于 patch 的注意力机制 |
| **辅助模型** | ResNet1D | 用于传导障碍检测的轻量级 CNN |
| **CV 流程** | OpenCV + NumPy | 图像校正、网格抑制、信号提取 |
| **信号处理** | SciPy | 重采样、滤波、Savitzky-Golay 平滑 |
| **质量分析** | NumPy/Pandas | 导联相关性、平坦度检测 |

---

## 4. 后端架构

### 4.1 项目结构

```
backend/
├── app/
│   ├── main.py                    # FastAPI 应用入口
│   ├── core/
│   │   ├── config.py              # Pydantic Settings 配置
│   │   ├── database.py            # 异步 SQLAlchemy 引擎
│   │   ├── security.py            # 密码哈希、JWT
│   │   ├── upload.py              # 文件上传安全处理
│   │   ├── rate_limit.py          # 滑动窗口限流器
│   │   └── auth_dependencies.py   # 认证依赖注入
│   ├── api/
│   │   ├── auth.py                # 认证路由 (/api/auth/*)
│   │   ├── chat.py                # 会话路由 (/api/chat/*)
│   │   └── diagnosis.py           # 诊断路由 (/api/diagnose)
│   ├── models/
│   │   ├── user.py                # 用户 ORM
│   │   ├── refresh_token.py       # 刷新令牌 ORM
│   │   ├── chat.py                # 会话/消息 ORM
│   │   ├── db_models.py           # 诊断记录 ORM
│   │   └── enums.py               # 枚举定义
│   └── services/
│       ├── diagnosis_service.py   # 诊断业务流程
│       ├── ecg_dat_loader.py      # DAT/HEA 文件加载
│       └── report/                # 报告生成子包
├── ml/                            # 机器学习模块
│   ├── cardioformer_model.py      # CardioFormer 架构
│   ├── cardioformer_service.py    # 推理服务包装器
│   ├── ecg_image_converter.py     # 图像转信号提取
│   ├── image_decoder.py           # 安全图像解码
│   ├── image_validator.py         # ECG 图像验证
│   └── signal_quality.py          # 信号质量分析
└── alembic/                       # 数据库迁移
```

### 4.2 核心模块设计

#### 4.2.1 配置管理 (config.py)

使用 Pydantic Settings 实现类型安全的配置：

```python
class Settings(BaseSettings):
    # 应用配置
    APP_NAME: str = "ECG Diagnosis API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "production"] = "development"

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./ecg_db.sqlite"

    # 上传限制
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".png", ".jpg", ".jpeg", ".dat", ".hea"}

    # 模型配置
    MODEL_CHECKPOINT_PATH: Optional[str] = None
    DEVICE: str = "cpu"
    CONFIDENCE_THRESHOLD: float = 0.7

    # LLM 报告
    LLM_REPORT_ENABLED: bool = False
    LLM_REPORT_PROVIDER: Literal["openai", "anthropic"] = "openai"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )
```

#### 4.2.2 认证系统

**双令牌机制**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   登录/注册  │────►│ Access Token │────►│  API 访问   │
│             │     │ (15分钟, JWT)│     │  Authorization: Bearer
└─────────────┘     └─────────────┘     └─────────────┘
        │
        │           ┌─────────────┐
        └──────────►│ Refresh Token│◄────┐
                    │(7天, HttpOnly)│     │ 自动刷新
                    └─────────────┘     │
                           ▲─────────────┘
```

**安全特性**:
- 密码: scrypt 哈希
- JWT: HS256 签名
- 刷新令牌: 家族机制（检测重放攻击）
- CSRF: Origin 头验证
- 限流: 滑动窗口（内存/数据库双后端）

#### 4.2.3 限流器设计

```python
class SlidingWindowRateLimiter:
    """滑动窗口限流器，支持内存和数据库双后端"""

    async def check_rate_limit(
        self,
        scope_key: str,           # 限流维度 (ip/user)
        max_requests: int,        # 窗口内最大请求数
        window_seconds: int       # 窗口大小（秒）
    ) -> RateLimitResult:
        # 根据配置自动选择后端
        if self.backend == "memory":
            return self._check_memory(scope_key, max_requests, window_seconds)
        else:
            return await self._check_database(scope_key, max_requests, window_seconds)
```

---

## 5. 前端架构

### 5.1 项目结构

```
frontend/src/
├── main.tsx                       # React 入口
├── App.tsx                        # 根组件
├── index.css                      # 全局样式 + CSS 变量
├── pages/
│   └── HomePage.tsx               # 单页布局
├── components/
│   ├── ChatComposer.tsx           # 消息输入 + 文件附件
│   ├── ConversationMessage.tsx    # 单条消息渲染
│   ├── ConversationSidebar.tsx    # 会话列表侧边栏
│   ├── DiagnosisReport.tsx        # 诊断报告展示
│   ├── QCWarning.tsx              # 质量警告组件
│   └── ...
├── controllers/
│   ├── useWorkspaceController.ts  # 主状态管理 Hook
│   ├── workspaceReducer.ts        # Reducer + 状态定义
│   └── messageMappers.ts          # 消息格式转换
├── api/
│   ├── client.ts                  # Axios 实例配置
│   ├── index.ts                   # 诊断 API
│   └── chat.ts                    # 会话 API
├── auth/
│   ├── AuthProvider.tsx           # 认证上下文
│   ├── store.ts                   # 模块级认证状态
│   └── api.ts                     # 认证 API
├── types/
│   └── chat.ts                    # TypeScript 类型定义
└── utils/
    ├── storage.ts                 # localStorage 管理
    ├── clipboard.ts               # 剪贴板工具
    └── index.ts                   # 通用工具
```

### 5.2 状态管理设计

**单一 State Tree**:

```typescript
interface WorkspaceState {
  // 持久化状态（保存到 localStorage 或云端）
  persisted: {
    sessions: ChatSession[];        // 所有会话
    activeSessionId: string;        // 当前会话 ID
    persistenceEnabled: boolean;    // 是否启用持久化
    storageVersion: number;         // 数据版本（迁移用）
  };

  // 编辑器状态
  composer: {
    draft: string;                  // 输入框文本
    attachments: PendingAttachment[]; // 待上传附件
    pairStatus: 'empty' | 'partial' | 'matched' | 'mismatch' | 'image';
    validationErrors: string[];     // 验证错误
  };

  // 提交状态
  submission: {
    activeMessageId: string | null;
    phase: 'idle' | 'uploading' | 'processing' | 'succeeded' | 'failed';
    progress: number | null;        // 上传进度 0-100
    error: string | null;
    canRetry: boolean;
  };

  // UI 状态
  ui: {
    isDragging: boolean;            // 拖拽中
    isSidebarOpen: boolean;         // 移动端侧边栏
    renamingSessionId: string | null;
    printableMessageId: string | null;
    storageWarning: string | null;
  };
}
```

**Action 设计** (24 个 Action Types):

```typescript
type WorkspaceAction =
  | { type: 'HYDRATE'; sessions: ChatSession[]; activeSessionId: string }
  | { type: 'SET_DRAFT'; value: string }
  | { type: 'ADD_FILES'; files: FileList | File[] }
  | { type: 'REMOVE_FILE'; id: string }
  | { type: 'SUBMIT_STARTED'; messageId: string }
  | { type: 'SUBMIT_UPLOAD_PROGRESS'; progress: number }
  | { type: 'SUBMIT_PROCESSING' }
  | { type: 'SUBMIT_SUCCEEDED'; result: DiagnosisResultData }
  | { type: 'SUBMIT_FAILED'; error: string }
  | { type: 'CREATE_SESSION'; session?: ChatSession }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }
  | ...;
```

### 5.3 组件设计原则

**文档式对话 UI**:
- 使用衬线字体 (`reading-copy`) 呈现正文，模拟纸质医疗记录
- 信息流自上而下，非传统聊天泡泡
- 温暖羊皮纸色调 (`--bg: #f5f1ea`)，降低阅读疲劳
- 大圆角卡片 (`border-radius: 32px`)，柔和阴影

**文件上传交互**:
```
三种入口:
1. 点击按钮: 选择图片 或 选择 .dat+.hea
2. 粘贴: 检测剪贴板中的图片
3. 拖拽: 拖放文件到页面任意位置

智能分类:
- 图片: 只允许单张，替换已有
- DAT/HEA: 必须成对，基本名匹配
- 混合: 禁止（图片 vs 信号二选一）
```

---

## 6. 机器学习模型架构

### 6.1 CardioFormer 模型

**架构类型**: 多粒度 Transformer
**输入**: `[B, 12, 1000]` - 12 导联，1000 采样点
**输出**: `[B, 5]` - 5 类 PTB-XL 超类概率

#### 6.1.1 核心创新: 多粒度 Patch 嵌入

```
输入信号 [12, 1000]
    │
    ├──► Patch Len 8  ──► 125 tokens ──► Intra-Attention ──┐
    │                                                        │
    ├──► Patch Len 16 ──► 63 tokens  ──► Intra-Attention ──┼──► Inter-Attention
    │                                                        │      (路由器 Token)
    └──► Patch Len 32 ──► 32 tokens  ──► Intra-Attention ──┘
                                                                  │
                                                                  ▼
                                                    跨粒度信息融合 (220 tokens total)
                                                                  │
                                                                  ▼
                                                    6 层 Encoder + 分类头
                                                                  │
                                                                  ▼
                                                    5 类 Sigmoid 概率输出
```

**关键组件**:

| 组件 | 功能 |
|-----|------|
| `CrossChannelTokenEmbedding` | 2D 卷积跨 12 导联提取特征 |
| `ListPatchEmbedding` | 生成多粒度 token 序列 |
| `CardioformerLayer` | Intra-granularity (自注意力) + Inter-granularity (跨粒度) |
| `ResNetBlockType1` | 瓶颈残差块，用于特征精炼 |
| `EncoderLayer` | 注意力 + 残差块 + LayerNorm |

**分类类别**:

| 索引 | 英文 | 中文 | ICD-10 |
|-----|------|-----|--------|
| 0 | NORM | 正常 | - |
| 1 | MI | 心肌梗死 | I21.x |
| 2 | STTC | ST-T 改变 | - |
| 3 | CD | 传导障碍 | I44.x-I45.x |
| 4 | HYP | 心室肥大 | I51.7 |

**推理特性**:
- 多标签: Sigmoid 激活，阈值 0.5 检测并存疾病
- Top-3 预测: 返回概率最高的 3 个类别
- 置信度: 基于最高概率的 4 级划分 (>=0.85, >=0.7, >=0.5, <0.5)

### 6.2 图像转信号流程 (ECGImageToSignal)

多层防御式图像处理流水线:

```
Layer 0: 安全解码 (safe_decode_image)
    ├── 解压炸弹保护 (MAX_IMAGE_PIXELS)
    ├── 零尺寸检查
    ├── EXIF 方向校正
    └── 超大图下采样 (max 4096px)

Layer 1: ECG 验证 (ECGImageValidator)
    ├── 宽高比检查 (0.3-5.0)
    ├── 暗像素比率 (0.001-0.75)
    ├── 内容带检测 (>=3 条水平带)
    └── 最低分辨率 (400px)

Layer 2: 预处理 (ECGImageToSignal)
    ├── 偏斜检测 (-45° to +45°，投影方差最大化)
    ├── 偏斜校正 (>2° 且置信度 >0.3)
    ├── 网格线抑制 (HSV 色彩分离 + FFT 周期抑制)
    └── Otsu 二值化

Layer 3: 布局检测
    ├── 投影分析识别布局类型
    ├── 支持: 12x1, 6x2, 4x3+1, 3x4
    └── 失败时回退到均匀分割

Layer 4: 信号提取
    ├── 每导联区域逐列扫描
    ├── 质心跟踪 (连续性约束)
    ├── 缺失值插值
    ├── Savitzky-Golay 平滑
    └── 共享归一化 (保留导联间幅度关系)

Layer 5: 质量评估
    ├── 逐导联 QC: 覆盖率、平坦度、跳变率、SNR
    ├── 整体质量: pass/warn/fail
    └── 信号质量门: 导联间相关性 >0.9 视为"坍塌"
```

### 6.3 辅助模型

**ResNet1D**: 轻量级 CNN 基线
- 用于传导障碍专项检测
- 架构: Stem + 3 层残差块 + GAP + 分类器
- 相比 CardioFormer 更快，但准确率较低

**信号质量分析器**:
- 检测"导联间坍塌"（所有导联几乎相同）
- 检测平坦导联（标准差 < 0.005）
- 作为质量门，阻止低质量信号进入模型推理

---

## 7. 数据流与业务流程

### 7.1 图像诊断完整流程

```
用户上传 ECG 图像
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. 前端处理                                                  │
│    ├── 文件类型验证 (.png/.jpg/.jpeg)                        │
│    ├── 大小检查 (<10MB)                                      │
│    └── 显示上传进度                                          │
└─────────────────────────────────────────────────────────────┘
        │
        ▼ POST /api/diagnose
┌─────────────────────────────────────────────────────────────┐
│ 2. API 层                                                    │
│    ├── 限流检查 (IP/用户级)                                  │
│    ├── 文件名清理 (防路径遍历)                                │
│    └── 保存到临时目录                                        │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. 图像解码层 (safe_decode_image)                            │
│    ├── 解压炸弹保护                                          │
│    ├── EXIF 方向校正                                         │
│    └── 超大图下采样                                          │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. 图像验证层 (ECGImageValidator)                            │
│    ├── 宽高比检查                                            │
│    ├── 内容带检测                                            │
│    └── 非 ECG 图像拒绝                                       │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. 信号提取层 (ECGImageToSignal)                             │
│    ├── 偏斜检测与校正                                        │
│    ├── 网格线抑制                                            │
│    ├── 布局检测                                              │
│    ├── 逐导联信号提取                                        │
│    └── 质量评估 (QC)                                         │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. 信号质量门 (analyze_signal_quality)                       │
│    ├── 导联间相关性检查                                      │
│    └── 坍塌检测 ──► 失败则跳过推理                           │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. 模型推理 (CardioFormerService)                            │
│    ├── Z-score 归一化                                        │
│    ├── CardioFormer 前向传播                                 │
│    ├── Sigmoid 激活                                          │
│    ├── Top-1/Top-3 预测                                      │
│    └── 多标签检测                                            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. 报告生成 (DiagnosisReportService)                         │
│    ├── 症状数据库查询 (严重度/ICD/建议)                       │
│    ├── 模板报告生成                                          │
│    └── 可选: LLM 增强报告                                    │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. 响应组装 (DiagnosisResponse)                              │
│    ├── 预测结果 + 置信度                                     │
│    ├── 质量警告 + 流水线警告                                 │
│    ├── 完整报告                                              │
│    └── 医疗免责声明                                          │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. 清理                                                     │
│    └── 删除临时上传文件                                      │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 前端状态流转

```
初始状态
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 会话管理                                                     │
│ ├── 未登录: 使用 localStorage 存储会话                        │
│ └── 已登录: 同步到云端数据库                                  │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
用户输入 (文本/附件)
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ 验证阶段                                                     │
│ ├── 文件组合验证 (图片 或 dat+hea)                           │
│ ├── 大小验证                                                 │
│ └── 配对验证 (基本名匹配)                                    │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ 验证通过
┌─────────────────────────────────────────────────────────────┐
│ 提交阶段 (SUBMIT_STARTED)                                    │
│ ├── 创建 pending 消息                                        │
│ ├── 上传文件 (带进度)                                        │
│ └── 可取消 (AbortController)                                 │
└─────────────────────────────────────────────────────────────┘
    │
    ▼ 上传完成
┌─────────────────────────────────────────────────────────────┐
│ 处理阶段 (SUBMIT_PROCESSING)                                 │
│ └── 显示 ECG 脉冲动画                                        │
└─────────────────────────────────────────────────────────────┘
    │
    ├──► 成功 (SUBMIT_SUCCEEDED)
    │      ├── 更新消息状态为 completed
    │      ├── 填充诊断结果
    │      └── 持久化会话
    │
    └──► 失败 (SUBMIT_FAILED)
           ├── 更新消息状态为 error
           ├── 记录错误详情
           └── 显示重试按钮
```

---

## 8. 数据库设计

### 8.1 ER 图

```
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│      users      │       │  refresh_tokens  │       │ chat_sessions   │
├─────────────────┤       ├──────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────┤ id (PK)          │       │ id (PK)         │
│ email (UQ)      │       │ user_id (FK)     │       │ user_id (FK)    │────┐
│ hashed_password │       │ token_hash (UQ)  │       │ title           │    │
│ display_name    │       │ family_id        │       │ created_at      │    │
│ is_active       │       │ expires_at       │       │ updated_at      │    │
│ created_at      │       └──────────────────┘       └─────────────────┘    │
│ updated_at      │                                          │              │
└─────────────────┘                                          │              │
                                                             │              │
                                                             ▼              │
                                                    ┌─────────────────┐    │
                                                    │  chat_messages  │    │
                                                    ├─────────────────┤    │
                                                    │ id (PK)         │    │
                                                    │ session_id (FK) │────┘
                                                    │ role            │
                                                    │ type            │
                                                    │ content         │
                                                    │ attachments (JSON)
                                                    │ result (JSON)   │
                                                    │ status          │
                                                    │ created_at      │
                                                    └─────────────────┘

┌─────────────────────────┐      ┌─────────────────────────┐
│    diagnosis_records    │      │   rate_limit_counters   │
├─────────────────────────┤      ├─────────────────────────┤
│ id (PK)                 │      │ id (PK)                 │
│ image_path              │      │ scope_key               │
│ user_id (FK, nullable)  │      │ window_start            │
│ prediction              │      │ hits                    │
│ confidence              │      │ expires_at              │
│ severity                │      └─────────────────────────┘
│ icd_code                │
│ description             │
│ recommendations (JSON)  │
│ created_at              │
└─────────────────────────┘
```

### 8.2 关键表结构

**chat_sessions** - 会话表
```sql
CREATE TABLE chat_sessions (
    id VARCHAR(36) PRIMARY KEY,        -- UUID v4
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_updated (user_id, updated_at)
);
```

**chat_messages** - 消息表
```sql
CREATE TABLE chat_messages (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL,
    role ENUM('user', 'assistant') NOT NULL,
    type ENUM('intro', 'prompt', 'guidance', 'diagnosis') NOT NULL,
    content TEXT NOT NULL,
    attachments JSON,                  -- 文件摘要数组
    result JSON,                       -- 诊断结果完整数据
    result_schema_version INT,         -- 用于数据迁移
    status ENUM('pending', 'completed', 'error'),
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_session_created (session_id, created_at)
);
```

---

## 9. 安全设计

### 9.1 分层安全策略

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: 应用安全                                                │
│ ├── 医疗免责声明                                                │
│ └── 诊断结果不可用于临床诊断提示                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 4: API 安全                                                │
│ ├── JWT 认证 + 刷新令牌轮换                                     │
│ ├── CSRF Origin 验证                                            │
│ ├── 滑动窗口限流                                                │
│ └── 输入验证 (Pydantic)                                         │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: 文件安全                                                │
│ ├── 文件名清理 (防路径遍历)                                     │
│ ├── 扩展名白名单                                                │
│ ├── 大小限制 (10MB)                                             │
│ └── 解压炸弹保护                                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: 网络安全                                                │
│ ├── CORS 配置                                                   │
│ ├── 安全响应头 (HSTS, CSP, X-Frame-Options)                     │
│ └── 可信主机验证                                                │
├─────────────────────────────────────────────────────────────────┤
│ Layer 1: 基础设施                                                │
│ ├── 容器隔离 (Docker)                                           │
│ └── 非 root 用户运行                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 关键安全措施

**文件上传安全**:
```python
# 1. 文件名清理
def sanitize_filename(filename: str) -> str:
    # 移除路径组件，仅保留基本名
    base = os.path.basename(filename)
    # 安全字符白名单
    safe = re.sub(r'[^a-zA-Z0-9._-]', '_', base)
    return safe[:100]  # 长度限制

# 2. 扩展名验证
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.dat', '.hea'}
if ext.lower() not in ALLOWED_EXTENSIONS:
    raise HTTPException(400, "不支持的文件类型")

# 3. 分块读取验证大小
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
```

**图像解码安全**:
```python
# 防止解压炸弹
with _image_decode_lock:
    original_max = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = IMAGE_MAX_PIXELS  # 1.78亿像素
    try:
        image = Image.open(io.BytesIO(data))
        image.load()  # 强制解码
    finally:
        Image.MAX_IMAGE_PIXELS = original_max
```

**认证安全**:
- 密码: scrypt 哈希 (salt + 内存硬)
- JWT: 15 分钟过期，HS256 签名
- 刷新令牌: 7 天过期，HttpOnly Secure Cookie
- 令牌家族: 检测重放攻击，发现则吊销整个家族

---

## 10. 部署架构

### 10.1 Docker Compose 部署

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+asyncmy://user:pass@db:3306/ecg
      - DEVICE=cpu
    volumes:
      - ./models:/app/models:ro
      - ./data:/app/data
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: mysql:8.4
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_DATABASE=ecg
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping"]

volumes:
  mysql_data:
```

### 10.2 生产环境配置

```bash
# .env (production)
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<随机生成的强密钥>

# 数据库
DATABASE_URL=mysql+asyncmy://ecg:${DB_PASSWORD}@db:3306/ecg_db

# CORS (明确指定允许的来源)
CORS_ORIGINS=["https://ecg.example.com"]
ALLOWED_HOSTS=["ecg.example.com"]

# LLM 报告 (可选)
LLM_REPORT_ENABLED=true
LLM_REPORT_PROVIDER=openai
OPENAI_API_KEY=${OPENAI_API_KEY}

# 模型
MODEL_CHECKPOINT_PATH=/app/models/checkpoints/best.ckpt
DEVICE=cpu
```

### 10.3 性能优化

| 优化点 | 策略 |
|-------|------|
| **模型加载** | 启动时预加载，单例模式，避免重复初始化 |
| **图像处理** | 超大图预下采样 (4096px)，减少内存占用 |
| **数据库** | 连接池、异步会话、关键字段索引 |
| **静态资源** | Nginx gzip 压缩、长期缓存、immutable 头 |
| **并发处理** | `asyncio.to_thread()` 将 CPU 密集任务 offload 到线程池 |

---

## 附录

### A. API 端点汇总

| 方法 | 路径 | 认证 | 说明 |
|-----|------|------|------|
| POST | /api/auth/register | 否 | 用户注册 |
| POST | /api/auth/login | 否 | 用户登录 |
| POST | /api/auth/refresh | Cookie | 刷新令牌 |
| POST | /api/auth/logout | 否 | 登出 |
| GET | /api/chat/sessions | 是 | 列会话 |
| POST | /api/chat/sessions | 是 | 创建会话 |
| GET | /api/chat/sessions/:id/messages | 是 | 获取消息 |
| POST | /api/chat/sessions/:id/messages | 是 | 批量创建消息 |
| POST | /api/diagnose | 可选 | 图像诊断 |
| POST | /api/diagnose-dat | 可选 | 信号文件诊断 |
| GET | /health | 否 | 健康检查 |

### B. 目录结构约定

```
项目根目录/
├── backend/               # Python FastAPI 后端
├── frontend/              # React + Vite 前端
├── models/                # 模型权重文件
│   └── checkpoints/
│       └── best.ckpt
├── data/                  # 数据目录 (开发用)
│   ├── uploads/           # 临时上传文件
│   └── reports/           # 生成报告
└── docs/                  # 文档
```

### C. 开发/生产切换检查清单

- [ ] `ENVIRONMENT` 设置为 `production`
- [ ] `SECRET_KEY` 更换为随机强密钥
- [ ] `DEBUG` 设置为 `false`
- [ ] `CORS_ORIGINS` 指定明确来源
- [ ] 运行 `alembic upgrade head` 迁移数据库
- [ ] 确认模型 checkpoint 文件存在且可读
- [ ] 配置外部 MySQL 数据库
- [ ] 启用 HTTPS (nginx/traefik)
- [ ] 禁用 API 文档 (`API_DOCS_ENABLED=false`)

---

**文档结束**
