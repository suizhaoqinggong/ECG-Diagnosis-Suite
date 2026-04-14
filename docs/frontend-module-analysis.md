# ECG Diagnosis Suite - 前端核心页面模块化拆解

## 一、页面截图

### 1.1 主界面（空状态）
![HomePage Empty State](./homepage-empty.png)

### 1.2 主界面（含诊断报告）
![HomePage With Report](./homepage-with-report.png)

---

## 二、整体架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HomePage (首页)                                 │
├─────────────────────┬───────────────────────────────────────────────────────┤
│                     │                                                       │
│  Sidebar Module     │              Main Content Area                        │
│  (左侧边栏模块)      │              (主内容区)                                │
│                     │                                                       │
│  ┌───────────────┐  │  ┌─────────────────────────────────────────────────┐  │
│  │  Header       │  │  │  Page Header (页面头部)                          │  │
│  │  - Logo       │  │  │  - 标题/描述                                     │  │
│  │  - New Chat   │  │  │  - 用户登录按钮                                  │  │
│  └───────────────┘  │  └─────────────────────────────────────────────────┘  │
│                     │                                                       │
│  ┌───────────────┐  │  ┌─────────────────────────────────────────────────┐  │
│  │  Session List │  │  │  Conversation Area (对话区域)                    │  │
│  │  (会话列表)    │  │  │                                                 │  │
│  └───────────────┘  │  │  ┌─────────────┐  ┌──────────────────────────┐  │  │
│                     │  │  │ EmptyState  │  │ ConversationMessage      │  │  │
│  ┌───────────────┐  │  │  │  (空状态引导) │  │ (消息条目)                │  │  │
│  │  Settings     │  │  │  └─────────────┘  │  ├─ UserMessage         │  │  │
│  │  (设置区)      │  │  │                   │  ├─ AssistantMessage     │  │  │
│  └───────────────┘  │  │                   │  └─ DiagnosisReport       │  │  │
│                     │  │                   └──────────────────────────┘  │  │
└─────────────────────┘  └─────────────────────────────────────────────────┘  │
                         ┌─────────────────────────────────────────────────┐  │
                         │  ChatComposer (聊天输入器)                       │  │
                         │  - 文本输入框                                    │  │
                         │  - 文件附件                                      │  │
                         │  - 提交按钮                                      │  │
                         └─────────────────────────────────────────────────┘  │
                                                                              │
                         ┌─────────────────────────────────────────────────┐  │
                         │  AuthModal (认证弹窗) - 条件渲染                  │  │
                         └─────────────────────────────────────────────────┘  │
──────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、模块划分详解

### 3.1 会话侧边栏模块 (ConversationSidebar)

**文件位置**: `frontend/src/components/ConversationSidebar.tsx`

**功能描述**:
- **Header 区域**: 展示品牌标识 "ECG Workspace / Diagnosis Studio" 和新建会话按钮
- **Session List**: 历史会话列表，支持切换、重命名、删除会话
- **Settings 区域**: 本地存储开关、清除历史按钮

**核心交互**:
| 功能 | 说明 |
|------|------|
| 会话切换 | 点击会话卡片切换到对应对话 |
| 会话管理 | 支持重命名、删除单个会话 |
| 持久化控制 | 非登录用户可开关 localStorage 存储 |
| 响应式设计 | 移动端抽屉式，桌面端固定侧边栏 |

**Props 接口**:
```typescript
interface ConversationSidebarProps {
  sessions: ChatSession[]
  activeSessionId: string
  onSelectSession: (sessionId: string) => void
  onCreateSession: () => void
  onRenameSession: (id: string, title: string) => void
  onDeleteSession: (id: string) => void
  persistenceEnabled: boolean
  onTogglePersistence: () => void
  // ... 其他
}
```

---

### 3.2 页面头部模块 (Page Header)

**文件位置**: `frontend/src/pages/HomePage.tsx` (lines 132-161)

**功能描述**:
- **副标题**: "Writing-first interface" 设计定位说明
- **主标题**: 当前会话标题（动态显示）
- **描述文本**: 页面功能简介
- **用户区**: 登录/注册按钮或用户菜单

**设计特点**:
- 采用文档式排版，非传统聊天界面
- 大字号标题，简洁留白

---

### 3.3 对话消息模块 (ConversationMessage)

**文件位置**: `frontend/src/components/ConversationMessage.tsx`

**功能描述**:
- **角色标识**: 区分 "You" (用户) 和 "ECG Analyst" (AI)
- **时间戳**: 消息创建时间
- **内容渲染**: 支持多段落文本
- **附件展示**: 显示上传的文件信息
- **状态管理**: pending / error / complete

**子组件**:

#### 3.3.1 PendingIndicator (处理中指示器)
- 上传进度条 (Uploading)
- ECG 波形动画 (Processing)

#### 3.3.2 ErrorMessage (错误消息)
- 错误详情展示
- 重试按钮

#### 3.3.3 DiagnosisReport (诊断报告) ⭐核心模块

**文件位置**: `frontend/src/components/DiagnosisReport.tsx`

**功能区块**:

| 区块 | 说明 |
|------|------|
| Diagnosis Overview | 主诊断结果大标题展示 |
| Confidence Card | 置信度、严重程度、ICD编码 |
| Action Buttons | 复制报告、打印 |
| QCWarning | 信号质量警告（条件渲染） |
| Clinical Interpretation | 临床解释文本 |
| Key Findings | 关键发现列表 |
| Top Signals | Top3 预测类别 |
| All Predictions | 全类别概率条形图 |
| Recommendations | 医疗建议 |
| Follow-up | 随访建议 |
| Limitations | 免责声明 |

---

### 3.4 空状态引导模块 (EmptyStateGuide)

**文件位置**: `frontend/src/components/EmptyStateGuide.tsx`

**功能描述**:
- 三步引导卡片：Attach ECG data → Add a note → Review results
- 图标 + 标题 + 描述的三段式结构
- 在新会话无消息时显示

---

### 3.5 聊天输入器模块 (ChatComposer)

**文件位置**: `frontend/src/components/ChatComposer.tsx`

**功能描述**:

| 功能区域 | 说明 |
|---------|------|
| 附件展示区 | 已选文件列表，支持删除 |
| 文本输入区 | 多行文本框，支持粘贴图片 |
| 文件上传 | 支持 ECG 图像 (.png/.jpg) 或信号对 (.dat+.hea) |
| 提交控制 | Cmd/Ctrl+Enter 快捷键，加载状态禁用 |

**交互细节**:
- 粘贴板图片自动识别并上传
- 键盘快捷键提交
- 文件类型限制与提示

---

### 3.6 移动端头部模块 (MobileHeader)

**文件位置**: `frontend/src/components/MobileHeader.tsx`

**功能描述**:
- 汉堡菜单按钮（打开侧边栏）
- 仅在移动端显示

---

### 3.7 会话菜单模块 (SessionMenu)

**文件位置**: `frontend/src/components/SessionMenu.tsx`

**功能描述**:
- 下拉菜单：Rename / Delete
- 内联重命名输入框

---

## 四、状态管理架构

### 4.1 Workspace State (useWorkspaceController)

**文件位置**: `frontend/src/controllers/useWorkspaceController.ts`

```typescript
interface WorkspaceState {
  persisted: {
    sessions: ChatSession[]      // 会话列表
    persistenceEnabled: boolean  // 是否持久化
  }
  composer: {
    draft: string               // 输入框草稿
    attachments: Attachment[]   // 待上传附件
  }
  submission: {
    phase: 'idle' | 'uploading' | 'processing'
    progress: number | null
    abortController: AbortController | null
  }
  ui: {
    isSidebarOpen: boolean
    renamingSessionId: string | null
    isDragging: boolean         // 拖拽状态
  }
}
```

### 4.2 数据流

```
User Action → dispatch → Reducer → State Update → Re-render
                ↓
         localStorage (条件持久化)
                ↓
         API Call → Backend → Response → Update Message
```

---

## 五、组件依赖关系图

```
HomePage
├── ConversationSidebar
│   └── SessionMenu
├── MobileHeader
├── EmptyStateGuide (条件渲染)
├── ConversationMessage[]
│   ├── PendingIndicator (条件渲染)
│   ├── ErrorMessage (条件渲染)
│   └── DiagnosisReport (条件渲染)
│       ├── QCWarning (条件渲染)
│       └── ProbabilityBar
├── ChatComposer
└── AuthModal (条件渲染)
```

---

## 六、设计系统 (Design Tokens)

| Token | 用途 |
|-------|------|
| `--bg` | 页面背景色 |
| `--surface` / `--surface-strong` | 卡片背景 |
| `--ink` / `--ink-soft` / `--ink-muted` | 文字层级 |
| `--border` / `--border-strong` | 边框 |
| `--accent` | 主强调色（ECG波形绿）|
| `--reading-copy` | 正文排版字体 |

**布局特点**:
- 大圆角设计 (20px-32px)
- 柔和阴影 (rgba(84,69,53,0.08))
- 文档式留白
- 双栏布局 (Sidebar + Main)

---

## 七、总结

本页面采用 **Writing-first Interface** 设计理念，将传统聊天界面转化为文档式阅读体验。核心模块划分清晰：

1. **ConversationSidebar** - 会话导航与管理
2. **ConversationMessage** - 消息展示与状态管理
3. **DiagnosisReport** - 诊断结果的专业化呈现
4. **ChatComposer** - 用户输入与文件上传

通过 `useWorkspaceController` 统一管理复杂状态，实现会话切换、消息提交、报告展示等核心功能的流畅体验。
