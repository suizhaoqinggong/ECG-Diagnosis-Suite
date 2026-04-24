# 前端 UI 视觉优化设计文档

## 概述

对 ECG Diagnosis Suite 前端三个核心区域进行视觉质感提升和动效优化。不改变现有功能逻辑，专注打磨 UI 细节、过渡动效和交互反馈。

## 影响范围

- `frontend/src/components/ConversationSidebar.tsx`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/components/ChatComposer.tsx`
- `frontend/src/index.css`

无需修改后端、API 层、状态管理逻辑或类型定义。

---

## A. 侧边栏 — ConversationSidebar

### 1. 会话卡片 Hover 动效

**当前**: 只有 `border-color` 和 `background` 的简单 transition。

**改为**:
- hover 时卡片轻微上浮：`translate3d(0, -1px, 0)` 配合 `box-shadow` 增强
- transition: `all 0.25s cubic-bezier(0.22, 1, 0.36, 1)`（平滑缓出）
- 非选中态卡片 hover 时背景从 `transparent` 过渡到 `rgba(255,252,247,0.65)`（已有，保留）

```css
/* 新增 */
.sidebar-card-hover {
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}
.sidebar-card-hover:hover {
  transform: translate3d(0, -1px, 0);
  box-shadow: 0 4px 12px rgba(84, 69, 53, 0.08);
}
```

### 2. 选中态：左侧指示条

**当前**: 使用 `border-[var(--border-strong)]` 让整个边框变粗来标识选中。

**改为**:
- 移除选中态的特殊边框，改用左侧 3px 宽的圆角竖线
- 竖线颜色使用 `var(--accent)`，带 `border-radius: 0 3px 3px 0`
- 选中卡片背景保留 `var(--surface-strong)` + 轻微阴影

```
┌─────────────────────┐
│ ▌ 会话标题            │  ← 左侧 3px 指示条
│   预览文字...          │
└─────────────────────┘
```

### 3. 侧边栏滑出/滑入动效

**当前**: 简单的 `translate-x` + `duration-300` 过渡。

**改为**:
- 添加 `backdrop-filter: blur(4px)` 在遮罩层上（已有 `backdrop-blur-sm`，增强为 `backdrop-blur-md`）
- 遮罩层 opacity 过渡从 0 → 1，配合 `duration-300 ease-out`
- 侧边栏本身加入微妙的 `ease-out` 曲线微调

### 4. 滚动区域底部渐变淡出

**当前**: 滚动到底部时内容直接消失。

**改为**:
- 在 `.soft-scrollbar` 容器底部叠加一个 `h-8` 的渐淡遮罩
- 使用 `mask-image: linear-gradient(to bottom, transparent 0%, black 20%)`（从下往上 20% 开始渐变）

### 5. 会话状态小圆点

**当前**: 所有会话卡片外观一致。

**改为**:
- 在会话标题前增加一个 6px 小圆点
- 有未读更新或诊断结果时使用 `var(--accent)` 色
- 普通会话使用 `var(--ink-muted)` 半透明色
- 活跃会话小圆点轻微脉冲动效

---

## B. 顶部区域 — HomePage header

### 1. 信息层级增强

**当前**:
```
[Writing-first interface]      ← 小标签
会话标题 (3xl → 2.8rem)        ← 大标题
简介文案 (text-base)            ← 描述
                                [登录/注册]
```

**改为**:
- 将小标签 "Writing-first interface" 改为徽章样式：`rounded-full` + 极小字重 + 柔和背景
- 会话标题保持现有尺寸，但添加 `opacity` 过渡（用于滚动动效联动）
- 简介文案只在会话为空时显示，有对话内容后自动隐藏
- 登录/注册按钮 hover 动效微调（加背景色过渡）

### 2. 滚动动效（Sticky Header 收缩）

**实现细节**：
- 监听 `mainRef` 的 `scroll` 事件（或 window scroll 如果页面滚动）
- 滚动阈值：60px
- **滚动 >60px 时**：
  - header 高度从 `py-6` 收缩到 `py-3`
  - 标题字号从 `text-3xl` 缩小到 `text-xl`
  - 简介文案渐隐消失（`opacity: 0`）
  - header 底部增加细阴影 `shadow-[0_1px_0_var(--border)]`
  - transition: `all 0.3s cubic-bezier(0.22, 1, 0.36, 1)`
- **回到顶部时**：所有属性恢复原始值
- 实现方式：通过 `useState` + `useEffect` + `scroll` 事件监听
- 注意：仅在桌面端应用该动效（移动端 viewport 小，保持简洁）

```typescript
// 概念代码 - 在 HomePage 中添加
const [isScrolled, setIsScrolled] = useState(false)

useEffect(() => {
  const container = mainRef.current
  if (!container) return
  const handleScroll = () => {
    setIsScrolled(container.scrollTop > 60)
  }
  container.addEventListener('scroll', handleScroll, { passive: true })
  return () => container.removeEventListener('scroll', handleScroll)
}, [])
```

---

## D. 输入区 — ChatComposer

### 1. 输入框自动伸缩

**当前**: 固定 `rows={4}` + `min-h-[120px]`，内容超出时出现滚动条。

**改为**:
- 移除固定 rows 属性
- 使用 `useRef` + `onInput` 事件监听 `scrollHeight`
- 自动调整高度：最小 3 行文字高度（约 80px），最大 10 行（约 320px）
- 超出最大高度时显示滚动条
- 初始发送后输入框高度重置为最小高度
- 添加平滑过渡：`transition: height 0.1s ease`

```typescript
// 概念代码 - 在 ChatComposer 中添加
const textareaRef = useRef<HTMLTextAreaElement>(null)

const autoResize = useCallback(() => {
  const el = textareaRef.current
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(Math.max(el.scrollHeight, 80), 320)}px`
}, [])

// 在 onChange 中调用 autoResize
```

### 2. 发送按钮点击动效

**当前**: 按钮仅通过 disabled 样式变化，无点击反馈。

**改为**:
- 点击时：`scale(0.94)` 瞬间缩小，然后弹性恢复
- 使用 CSS `@keyframes` 实现：

```css
@keyframes send-pulse {
  0% { transform: scale(1); }
  30% { transform: scale(0.94); }
  70% { transform: scale(1.02); }
  100% { transform: scale(1); }
}

.send-btn-click {
  animation: send-pulse 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}
```

- 提交加载态：发送按钮内部图标改为旋转动画（SVG 旋转 `spin`）
- 按钮文字在加载时保持 "发送" 不变（当前改 "Analyzing" 文字长度变化导致布局跳动）

### 3. 文件标签删除按钮动效

**当前**: 删除按钮 hover 时颜色变化简单。

**改为**:
- hover 时背景色平滑过渡
- 删除时微缩放效果

---

## 不动的内容

- 不修改任何后端代码
- 不修改状态管理逻辑（workspaceReducer、useWorkspaceController）
- 不修改 API 层
- 不修改类型定义
- 不修改认证相关组件（AuthModal、UserMenu）
- 不添加新 npm 依赖

---

## 实现顺序

1. **D. ChatComposer** — 自动伸缩输入框 + 按钮动效（最独立，不影响其他区域）
2. **A. ConversationSidebar** — hover 动效、指示条、淡出遮罩、小圆点
3. **B. HomePage header** — 信息层级 + 滚动收缩动效
