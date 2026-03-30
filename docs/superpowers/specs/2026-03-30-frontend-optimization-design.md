# ECG Diagnosis Suite 前端全面优化设计

日期: 2026-03-30

## 背景

ECG Diagnosis Suite 前端当前是一个单页应用，5 个组件，依赖极简（React + Axios + Tailwind）。核心组件 `HomePage.tsx` 有 517 行，承载了所有状态管理、文件验证、API 调用和 localStorage 持久化。UI 风格为温暖的文档/编辑器风格（羊皮纸色调、衬线字体、大圆角）。

目标用户为医学生和研究人员，使用场景包括学习和科研。

## 策略

**用户体验优先 + 最小架构清理。** 统一使用 `useWorkspaceController`（基于 `useReducer`）编排所有状态，UI 层拆为纯展示组件。无障碍/错误语义/对比度作为每个模块的验收标准，不作为最后补丁。

## 模块优先级

| 优先级 | 模块 | UX 改善 | 伴随架构清理 |
|--------|------|---------|-------------|
| P0 | 诊断提交体验 | 两阶段进度（uploading → processing）、占位卡片、错误恢复 | 提取 `useWorkspaceController`，补消息状态模型 |
| P1 | 诊断报告可视化 | 概率条形图、ICD 复制、打印单份报告、临床解释折叠 | 提取 `DiagnosisReport` 纯展示组件 |
| P2 | 会话管理 | 删除/重命名、隐私开关、清空全部历史、字节预算裁剪 | 会话 CRUD 从 controller 暴露 |
| P3 | 移动端适配 | 侧边栏抽屉、报告响应式、文件选择器优先 | 纯 CSS/组件调整 |
| P4 | 全局体验补全 | 空状态引导、.dat+.hea 配对反馈、代码清理 | 统一 @/ 路径别名 |

---

## 架构：useWorkspaceController

核心状态管理基于 `useReducer`，统一编排 session、composer、submit 逻辑。UI 层只消费 dispatch 和派生状态，不做业务逻辑。

### State 结构

State 分为 4 块：持久化层（会话、隐私开关）、编辑器层（草稿、附件）、提交层（诊断进度）、UI 层（抽屉、拖拽等易失状态）。File、AbortController、拖拽态等不可序列化的内容仅存在于 controller 的易失引用层，不进 reducer 持久化快照。

```typescript
interface WorkspaceState {
  persisted: {
    sessions: ChatSession[];
    activeSessionId: string;
    persistenceEnabled: boolean;    // 隐私开关
    storageVersion: number;         // 数据版本号，用于后续迁移
  };

  composer: {
    draft: string;
    attachments: PendingAttachment[];
    pairStatus: 'empty' | 'partial' | 'matched' | 'mismatch' | 'image';
    validationErrors: string[];
  };

  submission: {
    activeMessageId: string | null; // 占位卡片的消息 ID
    phase: 'idle' | 'uploading' | 'processing' | 'succeeded' | 'failed';
    progress: number | null;        // 0-100，仅 uploading 阶段
    error: string | null;
    canRetry: boolean;
  };

  ui: {
    isDragging: boolean;
    isSidebarOpen: boolean;
    renamingSessionId: string | null;
    printableMessageId: string | null;
    storageWarning: string | null;
  };
}
```

Controller 内部持有易失引用（不进 state）：`lastFiles: File[] | null`、`abortController: AbortController | null`。

### Action 类型

```typescript
type WorkspaceAction =
  // 初始化
  | { type: 'HYDRATE'; sessions: ChatSession[]; activeSessionId: string }

  // 会话
  | { type: 'CREATE_SESSION' }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'RENAME_SESSION'; id: string; title: string }
  | { type: 'DELETE_SESSION'; id: string }
  | { type: 'CLEAR_ALL_SESSIONS' }
  | { type: 'TOGGLE_PERSISTENCE' }
  | { type: 'PRUNE_SESSIONS' }
  | { type: 'STORAGE_WRITE_FAILED'; error: string }

  // 消息
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }

  // 编辑器
  | { type: 'SET_DRAFT'; value: string }
  | { type: 'ADD_FILES'; files: FileList | File[] }
  | { type: 'REMOVE_FILE'; id: string }
  | { type: 'CLEAR_COMPOSER' }

  // 提交
  | { type: 'SUBMIT_STARTED'; messageId: string }
  | { type: 'SUBMIT_UPLOAD_PROGRESS'; progress: number }
  | { type: 'SUBMIT_PROCESSING' }
  | { type: 'SUBMIT_SUCCEEDED'; result: DiagnosisResultData }
  | { type: 'SUBMIT_FAILED'; error: string }
  | { type: 'SUBMIT_RETRY' }
  | { type: 'SUBMIT_CANCEL' }

  // UI
  | { type: 'SET_DRAG_ACTIVE'; active: boolean }
  | { type: 'SET_SIDEBAR_OPEN'; open: boolean }
  | { type: 'SET_RENAMING'; sessionId: string | null }
  | { type: 'SET_PRINTABLE_MESSAGE'; messageId: string | null }
```

### Hook 接口

```typescript
interface UseWorkspaceControllerReturn {
  state: WorkspaceState;
  dispatch: React.Dispatch<WorkspaceAction>;

  // 派生状态
  activeSession: ChatSession | null;
  isSubmitting: boolean;

  // 便捷方法
  submit: () => Promise<void>;
  retry: () => Promise<void>;
  cancelSubmission: () => void;
}
```

### 实现约束

1. **持久化边界：** `persisted` 块同步到 localStorage（当 `persistenceEnabled` 为 true）。其余三个块（composer、submission、ui）仅存于内存，不序列化。File 和 AbortController 放 controller 的易失引用层，不进 reducer。
2. **重试语义：** retry 只保证当前页面生命周期内有效（依赖内存中的 `lastFiles` 引用）。页面刷新后 File 对象丢失，重试按钮降级为"请重新选择文件并提交"。
3. **取消请求：** submit 时创建 AbortController，dispatch `SUBMIT_CANCEL` 时调用 `abort()`，占位卡片变为错误状态。
4. **数据版本：** `storageVersion` 写入 localStorage，后续消息模型扩展时可做迁移。当前版本号为 1。

### 消息模型扩展

```typescript
interface ConversationMessage {
  id: string;
  role: 'assistant' | 'user';
  type: 'intro' | 'prompt' | 'guidance' | 'diagnosis';
  title?: string;
  content: string;
  createdAt: number;
  attachments?: AttachedFileSummary[];
  result?: DiagnosisResultData;

  // 新增字段
  status?: 'pending' | 'completed' | 'error';  // 用于占位卡片状态管理
  errorDetail?: string;                          // 错误详情，用于卡片内重试
}
```

Controller 内部维护 `pendingMessageId`，submit 时创建 pending 消息 append 到会话，成功/失败时通过 `UPDATE_MESSAGE` 替换内容。

---

## 跨模块验收标准

以下验收项不归属于单个模块，而是需要在所有模块完成后整体检查。

### 状态机验收
- [ ] 上传中切会话 → 回到原会话后进度仍在
- [ ] 失败后重试 → 占位卡片恢复为 uploading 状态
- [ ] 删除活跃会话 → 自动创建新会话并切换
- [ ] 关闭持久化 → 刷新后会话丢失
- [ ] 存储配额超限 → 自动裁剪最旧会话
- [ ] 刷新页面 → persisted 状态正确恢复，submission 归零

### 无障碍验收
- [ ] 键盘可完成：上传文件、重命名会话、删除确认、抽屉开关、打印报告
- [ ] 错误消息使用 `role="alert"` 对读屏可见
- [ ] 进度变化通过 `aria-live="polite"` 区域播报
- [ ] 抽屉打开时焦点陷阱在抽屉内
- [ ] 所有动画尊重 `prefers-reduced-motion`

### 输出验收
- [ ] 打印页仅包含目标报告（由 `printableMessageId` 指定）
- [ ] 打印页包含：模型来源/版本、生成时间、免责声明、ICD 参考说明
- [ ] 颜色在灰度打印下仍可读（条形图、严重程度标签）

### 测试要求
- [ ] Reducer 核心状态迁移有单元测试（vitest）
- [ ] 关键用户路径有集成测试（至少：提交流程、会话 CRUD、存储裁剪）

---

## P0: 诊断提交体验

### UX 改善

1. **两阶段进度指示**
   - `uploading` 阶段：文件传输进度条（基于 Axios `onUploadProgress`），文案"正在上传文件…"
   - `processing` 阶段：进度条满，切换为脉冲动画心电图波形 SVG + "AI 正在分析心电数据…"
   - 避免进度条先到 100% 再空等的误导体验

2. **占位卡片**
   - 提交时立即在对话区域插入一条 status=pending 的助手消息
   - 卡片内容随 phase 变化：uploading 显示进度条 → processing 显示波形动画
   - 成功时替换为完整诊断报告（status=completed）
   - 失败时变为错误卡片（status=error），显示错误描述 + 重试按钮

3. **per-session pending 状态**
   - 提交期间不禁止切换会话，用户可浏览其他历史记录
   - pending 状态绑定在特定会话上，切换回来仍可见进度
   - 提交期间禁止同一会话重复提交

4. **取消分析**
   - 占位卡片上增加"取消"按钮
   - 点击后调用 AbortController 中断请求
   - 占位卡片变为错误状态，文案"分析已取消"

5. **提交按钮改善**
   - idle: 发送图标 + "发送"
   - uploading: 旋转图标 + "上传中…"
   - processing: 旋转图标 + "分析中…"
   - 禁用期间 `opacity-50` + `cursor-not-allowed`

### 验收标准

- [ ] 提交后 300ms 内可见占位卡片
- [ ] 上传进度条平滑更新
- [ ] 上传完成后自动切换到 processing 动画
- [ ] 诊断期间可切换会话
- [ ] 可取消进行中的分析
- [ ] 失败后可一键重试
- [ ] 自动滚动到占位卡片位置
- [ ] 所有交互元素有 aria-label
- [ ] 按钮颜色对比度 ≥ 4.5:1

---

## P1: 诊断报告可视化

### UX 改善

1. **概率分布水平条形图**
   - 每个预测结果显示为水平条形图，宽度按概率比例计算
   - Top 3 预测用 `var(--accent)` 主色调，其余用 `var(--border)` 浅灰
   - 条形图右端显示百分比数值
   - 适应窄屏：容器 flex 布局，标签和条形图可换行

2. **报告交互增强**
   - ICD 代码旁增加复制按钮（点击后 "已复制 ✓" 反馈，2 秒后恢复）
   - ICD 代码下方小字标注："参考编码，不可直接用于临床诊断或计费"
   - 严重程度颜色编码标签：mild 绿 / moderate 琥珀 / severe 红
   - 置信度数值旁增加小型环形进度指示器
   - 报告顶部固定展示：模型来源/版本、生成时间、输入类型、免责声明

3. **打印单份报告**
   - 报告卡片右上角增加打印图标按钮
   - 点击后 `@media print` 仅渲染当前诊断报告
   - 隐藏侧边栏、输入区域、其他消息
   - 报告顶部显示日期、诊断 ID、项目名称
   - 使用 `.reading-copy` 衬线字体

4. **面向医学生/研究人员的细节**
   - 临床解释增加展开/收起功能，默认展开
   - 关键发现以编号列表展示
   - 建议和后续步骤分区显示
   - 明确区分"模型概率"与"临床概率"的标签

5. **结果导出为文本**
   - 报告卡片右上角（打印按钮旁）增加"复制文本"按钮
   - 点击后将报告内容格式化为纯文本（包含所有概率、ICD 代码、建议等）复制到剪贴板
   - 反馈"报告已复制到剪贴板"

### 架构清理：提取 DiagnosisReport 纯展示组件

```
ConversationMessage.tsx (~60 行)
  ├── intro/prompt/guidance 消息 → 简单文本渲染
  └── diagnosis 消息 → <DiagnosisReport result={message.result} />

DiagnosisReport.tsx (~200 行，纯展示)
  ├── 报告头部（模型信息、时间、免责声明）
  ├── 概率分布条形图
  ├── 严重程度标签 + 置信度指示器
  ├── ICD 代码（可复制）
  ├── 临床解释（可折叠）
  ├── 关键发现列表
  ├── 建议与后续步骤
  ├── 打印按钮
  └── 复制文本按钮
```

### 验收标准

- [ ] 概率条形图宽度准确反映百分比
- [ ] ICD 代码可一键复制并有反馈
- [ ] 报告可复制为纯文本
- [ ] 打印输出仅包含单份报告，布局整洁
- [ ] 报告头部展示模型版本和免责声明
- [ ] 严重程度标签颜色对比度 ≥ 3:1
- [ ] 折叠/展开有键盘支持（Enter/Space）
- [ ] 语义化 HTML（section/h3/dl/dt/dd）

---

## P2: 会话管理

### UX 改善

1. **隐私开关**
   - 侧边栏底部增加"在本机保存历史"开关（默认开启，保持向后兼容）
   - 关闭时：不写入 localStorage，页面刷新后会话丢失，显示提示"历史记录不会保存到本机"
   - 关闭时已存储的历史保留可读，但不再更新
   - 随时可在设置中重新开启

2. **清空全部历史**
   - 隐私开关旁增加"清空全部历史"按钮
   - 点击弹出确认对话框（不可 undo）
   - 确认后清除 localStorage，创建新的空会话

3. **会话操作交互**
   - 会话项 hover 时右侧浮现操作菜单（三点图标）
   - 菜单项：重命名、删除
   - 重命名：inline 编辑框，Enter 确认，Escape 取消
   - 删除：确认气泡，确认后移除并切换到相邻会话
   - 删除当前活跃会话时自动创建新会话
   - 操作菜单对键盘可达（Tab + Enter 展开，Escape 关闭）
   - 触屏设备：长按触发菜单

4. **字节预算存储裁剪**
   - 监控 localStorage 使用量（而非条数）
   - 设置字节预算上限（如 4MB）
   - 超出时按 LRU 策略裁剪最旧会话（跳过当前活跃会话）
   - 裁剪顺序：先删最旧会话的全部消息（保留 intro），再删整个会话
   - 裁剪时 toast 提示"已自动清理旧会话以释放空间"
   - `QuotaExceededError` 兜底：写入失败时回滚本次变更，toast 提示"存储空间不足，请清理历史"
   - 单条诊断报告超过 100KB 时警告"此报告较大，可能影响存储"

5. **.dat + .hea 配对反馈**
   - 添加文件后立即检查配对状态
   - 配对状态可视化：✅ "文件对完整" / ⚠️ "缺少 .hea 文件" / ⚠️ "缺少 .dat 文件"
   - 文件名匹配校验（.dat 和 .hea 前缀应相同）

### 架构

会话 CRUD 通过 `useWorkspaceController` 的 dispatch 暴露：
- `CREATE_SESSION`、`SWITCH_SESSION`、`RENAME_SESSION`、`DELETE_SESSION`
- `CLEAR_ALL_SESSIONS`、`TOGGLE_PERSISTENCE`
- Controller 内部处理 localStorage 读写、容量检测、LRU 裁剪

### 验收标准

- [ ] 隐私开关可切换，关闭后不写入 localStorage
- [ ] 清空全部历史有确认对话框
- [ ] 重命名支持 Enter/Escape 键盘操作
- [ ] 删除后正确切换到相邻会话
- [ ] 存储裁剪按字节而非条数
- [ ] .dat+.hea 配对状态实时反馈
- [ ] 操作菜单键盘和触屏可达
- [ ] 所有操作有 aria-label

---

## P3: 移动端适配

### UX 改善

1. **侧边栏抽屉模式**
   - 移动端（< lg 断点）侧边栏默认隐藏
   - 顶部增加汉堡按钮（三条横线 SVG），点击后侧边栏从左侧滑出
   - 半透明遮罩覆盖主内容区域
   - 抽屉打开时禁止背景滚动（body overflow: hidden）
   - 选择会话后自动关闭抽屉
   - 点击遮罩或 Escape 关闭抽屉

2. **对话区域全屏化**
   - 移动端对话区域占满全宽
   - 顶部栏：汉堡菜单按钮（左）+ 应用标题（中）
   - ChatComposer 保持底部固定
   - 侧边栏底部控件（隐私开关、清空历史）在抽屉中可用

3. **诊断报告响应式**
   - 报告卡片改为堆叠式小卡片
   - 概率条形图保持完整宽度，不受卡片边距挤压
   - 长文本区块（临床解释、建议）默认折叠，点击展开
   - body 字号 16px → 14px
   - 报告头部信息两列改单列

4. **文件上传移动端适配**
   - 优先使用系统文件选择器（点击触发）
   - 隐藏拖拽区域（移动端不常见拖拽操作）
   - 文件 chip 单行显示，超长文件名截断加省略号
   - .dat+.hea 配对反馈在移动端同样可用

### 验收标准

- [ ] 抽屉滑入/滑出动画流畅（< 300ms）
- [ ] 抽屉打开时背景不可滚动
- [ ] 报告在 375px 宽度下可读
- [ ] 条形图不溢出容器
- [ ] 触控目标 ≥ 44x44px
- [ ] 文件选择器在 iOS Safari 和 Android Chrome 可用

---

## P4: 全局体验补全

### UX 改善

1. **空状态引导设计**
   - 新会话（仅有 intro 消息时），对话区域展示引导区：
     - 一句话说明："上传心电图图片或 .dat+.hea 文件对，开始 AI 辅助诊断"
     - 两个入口卡片：📷 图片诊断 | 📁 数据文件诊断
     - 点击卡片触发对应文件选择器
   - 有消息后引导区域自动消失
   - 引导区支持键盘聚焦和激活

2. **错误处理增强**
   - 网络错误：在对话区域插入错误消息卡片（红色左边框）
   - 错误卡片包含：错误描述 + "重试"按钮
   - 4xx 错误文案："文件格式不支持，请检查后重试"
   - 5xx 错误文案："服务暂时不可用，请稍后重试"
   - 网络断开文案："网络连接已断开，请检查网络设置"

3. **无障碍优化**
   - 所有交互元素添加 `aria-label`
   - 诊断报告用语义化 HTML（`<section>`、`<h3>`、`<dl>`/`<dt>`/`<dd>`）
   - Tab 可遍历所有交互元素，焦点样式可见
   - 颜色对比度满足 WCAG AA（正文 ≥ 4.5:1，大文字 ≥ 3:1）
   - 动画尊重 `prefers-reduced-motion` 系统设置

### 代码清理

1. 删除 `api/index.ts` 中未使用的 `getHistory` 函数
2. 删除 `tailwind.config.js` 中未使用的 `primary` 调色板
3. 删除 `.env.example` 中未使用的环境变量（`VITE_ENABLE_PWA`、`VITE_ENABLE_ANALYTICS`、`VITE_API_TIMEOUT`、`VITE_MAX_FILE_SIZE`、`VITE_ALLOWED_TYPES`）
4. 统一导入路径为 `@/` 别名（替换相对路径 `../`）
5. 修复 `HomePage.tsx:453` 的 `error: any` 类型转换为适当的类型守卫

### 验收标准

- [ ] 空状态引导在首次访问时可见
- [ ] 错误卡片有明确的错误类型区分
- [ ] 所有按钮和输入有 aria-label
- [ ] Tab 键可达所有交互元素
- [ ] 焦点样式清晰可见
- [ ] 颜色对比度通过 WCAG AA 检测
- [ ] 无未使用的导出函数和配置
- [ ] 导入路径统一使用 `@/` 别名
