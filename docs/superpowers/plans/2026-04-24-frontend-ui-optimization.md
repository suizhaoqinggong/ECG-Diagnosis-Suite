# Frontend UI Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish visual quality of 3 frontend areas — ChatComposer, ConversationSidebar, and HomePage header — with micro-interactions, animations, and refined infohierarchy.

**Architecture:** Pure CSS + React component changes only. No state management changes, no new dependencies, no backend changes. Each task is a self-contained component modification paired with its CSS additions.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Vite, Vitest

---

### Task 1: ChatComposer — Auto-resize textarea + send button animation

**Files:**
- Modify: `frontend/src/components/ChatComposer.tsx`
- Modify: `frontend/src/index.css`

#### Step 1: Add CSS animations and styles to index.css

Add the send button pulse keyframe and a rotating loading animation before the `@media print` block (around line 125):

```css
@keyframes send-pulse {
  0% { transform: scale(1); }
  30% { transform: scale(0.94); }
  60% { transform: scale(1.03); }
  100% { transform: scale(1); }
}

.send-btn-click {
  animation: send-pulse 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin-slow {
  animation: spin 1.2s linear infinite;
}

/* File tag delete button */
.file-tag-btn {
  transition: all 0.2s ease;
}
.file-tag-btn:hover {
  background: rgba(255,255,255,0.9);
  transform: scale(1.1);
}
```

#### Step 2: Add auto-resize textarea and button refs

In `ChatComposer.tsx`, modify the imports to add `useRef` and `useCallback`. Currently imports `{ memo }` from 'react'. Change to:

```tsx
import { memo, useCallback, useRef } from 'react'
```

#### Step 3: Add refs and callbacks inside the component

Inside the `ChatComposer` function body, before the `handlePaste` handler, add:

```tsx
const textareaRef = useRef<HTMLTextAreaElement>(null)
const btnRef = useRef<HTMLButtonElement>(null)

const autoResize = useCallback(() => {
  const el = textareaRef.current
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(Math.max(el.scrollHeight, 84), 280)}px`
}, [])

const handleSendClick = useCallback(() => {
  if (btnRef.current) {
    btnRef.current.classList.remove('send-btn-click')
    // Force reflow to restart animation
    void btnRef.current.offsetWidth
    btnRef.current.classList.add('send-btn-click')
  }
  onSubmit()
}, [onSubmit])
```

#### Step 4: Modify ArrowIcon to accept className

Change the `ArrowIcon` helper function:

```tsx
function ArrowIcon({ className = '' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`h-4 w-4 ${className}`} aria-hidden="true">
      ...
    </svg>
  )
}
```

(Keep the SVG path contents unchanged.)

#### Step 5: Update textarea element

Find the textarea element:
```tsx
<textarea
  value={draft}
  onChange={(event) => onDraftChange(event.target.value)}
  onKeyDown={handleKeyboardSubmit}
  onPaste={handlePaste}
  disabled={isLoading}
  rows={4}
  ...
/>
```

Change to:
```tsx
<textarea
  ref={textareaRef}
  value={draft}
  onChange={(event) => {
    onDraftChange(event.target.value)
    autoResize()
  }}
  onInput={autoResize}
  onKeyDown={handleKeyboardSubmit}
  onPaste={handlePaste}
  disabled={isLoading}
  className="... min-h-[84px] max-h-[280px] ..."
  ...
/>
```

Key changes:
- Add `ref={textareaRef}`
- Remove `rows={4}`, add `min-h-[84px] max-h-[280px]`
- Add `onInput={autoResize}` for paste/drag resize
- Call `autoResize()` on each `onChange` too
- Remove `min-h-[120px]` from className, replace with `min-h-[84px] max-h-[280px]`
- Keep `resize-none`

Update the `transition` property in the textarea className: add `transition-[height] duration-100 ease` for smooth height animation.

#### Step 6: Update send button

Find the send button element. Change it to:

```tsx
<button
  ref={btnRef}
  type="button"
  onClick={handleSendClick}
  disabled={isLoading || !hasContent}
  className="inline-flex items-center gap-2 rounded-full bg-[#2f2b26] px-5 py-3 text-sm font-medium text-white transition hover:bg-[#1f1c18] disabled:cursor-not-allowed disabled:bg-[#b7aa9b]"
>
  {isLoading ? (
    <ArrowIcon className="animate-spin-slow" />
  ) : (
    <ArrowIcon />
  )}
  Send
</button>
```

Key changes:
- Add `ref={btnRef}`
- Change `onClick` from `onSubmit` to `handleSendClick`
- Change loading indicator: keep "Send" text always, spin the arrow icon on loading
- Remove `{isLoading ? 'Analyzing' : 'Send'}` logic

#### Step 7: Update file tag delete button hover

Find the file remove button (the `×` button) and change its className to:

```tsx
className="rounded-full p-1 text-[var(--ink-muted)] transition-all duration-200 hover:bg-white/80 hover:text-[var(--ink)] hover:scale-110"
```

Key change: add `hover:scale-110` and change `transition` to `transition-all duration-200`.

#### Step 8: Run tests

Run: `npx vitest run frontend/src/__tests__/components/` 2>&1 | tail -20
Expected: All existing tests pass. No tests should need changes since we only changed UI behavior, not logic.

#### Step 9: Verify no TypeScript errors

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

#### Step 10: Commit

```bash
git add frontend/src/components/ChatComposer.tsx frontend/src/index.css
git commit -m "feat(ui): add auto-resize textarea and send button animation to ChatComposer"
```

---

### Task 2: ConversationSidebar — hover lift, indicator bar, fade mask, status dots

**Files:**
- Modify: `frontend/src/components/ConversationSidebar.tsx`
- Modify: `frontend/src/index.css`

#### Step 1: Add sidebar CSS to index.css

Add before the `@media print` block:

```css
/* Sidebar card lift on hover */
.sidebar-card {
  position: relative;
  transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
              box-shadow 0.25s cubic-bezier(0.22, 1, 0.36, 1);
}

.sidebar-card:not(.sidebar-card-active):hover {
  transform: translate3d(0, -1px, 0);
  box-shadow: 0 4px 12px rgba(84, 69, 53, 0.08);
}

/* Active session indicator bar */
.sidebar-card-active .sidebar-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 28px;
  background: var(--accent);
  border-radius: 0 3px 3px 0;
}

/* Status dot pulse for active session */
@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.sidebar-dot-active {
  animation: dot-pulse 2.5s ease-in-out infinite;
}

/* Scroll fade mask */
.sidebar-scroll-container {
  -webkit-mask-image: linear-gradient(to bottom, black 85%, transparent 100%);
  mask-image: linear-gradient(to bottom, black 85%, transparent 100%);
}
```

#### Step 2: Add hover lift class and indicator bar to session buttons

In `ConversationSidebar.tsx`, find the session button. Currently:

```tsx
<button
  key={session.id}
  type="button"
  onClick={() => {
    onSelectSession(session.id)
    onClose()
  }}
  className={clsx(
    'rounded-[24px] border px-4 py-4 text-left transition',
    session.id === activeSessionId
      ? 'border-[var(--border-strong)] bg-[var(--surface-strong)] shadow-[0_16px_40px_rgba(84,69,53,0.08)]'
      : 'border-transparent bg-transparent hover:border-[var(--border)] hover:bg-[rgba(255,252,247,0.65)]',
  )}
>
```

Change to:

```tsx
<button
  key={session.id}
  type="button"
  onClick={() => {
    onSelectSession(session.id)
    onClose()
  }}
  className={clsx(
    'sidebar-card rounded-[24px] border px-4 py-4 text-left transition',
    session.id === activeSessionId
      ? 'sidebar-card-active border-transparent bg-[var(--surface-strong)] shadow-[0_16px_40px_rgba(84,69,53,0.08)]'
      : 'border-transparent bg-transparent hover:border-[var(--border)] hover:bg-[rgba(255,252,247,0.65)]',
  )}
>
  {session.id === activeSessionId && (
    <div className="sidebar-indicator" />
  )}
```

Key changes:
- Add `sidebar-card` class to all buttons
- Add `sidebar-card-active` class to active button
- Change active button border from `border-[var(--border-strong)]` to `border-transparent` (indicator replaces it)
- Add the indicator bar `<div>` element for the active session
- Remove the `transition` shorthand (we now use the CSS class's explicit transitions)

#### Step 3: Add status dots

Inside the session button, around the title section. Currently:

```tsx
<div className="min-w-0">
  {renamingSessionId === session.id ? (
    <SessionMenu ... />
  ) : (
    <>
      <p className="truncate text-sm font-semibold text-[var(--ink)]">
        {session.title}
      </p>
      <p className="mt-2 overflow-hidden text-sm leading-6 text-[var(--ink-soft)]">
        {session.preview}
      </p>
    </>
  )}
</div>
```

Change to:

```tsx
<div className="min-w-0">
  {renamingSessionId === session.id ? (
    <SessionMenu ... />
  ) : (
    <>
      <div className="flex items-center gap-2.5">
        <span
          className={clsx(
            'block w-[6px] h-[6px] rounded-full shrink-0',
            session.id === activeSessionId
              ? 'bg-[var(--accent)] sidebar-dot-active'
              : 'bg-[var(--ink-muted)] opacity-40',
          )}
        />
        <p className="truncate text-sm font-semibold text-[var(--ink)]">
          {session.title}
        </p>
      </div>
      <p className="mt-2 overflow-hidden text-sm leading-6 text-[var(--ink-soft)]">
        {session.preview}
      </p>
    </>
  )}
</div>
```

#### Step 4: Add fade mask to scroll container

Find the scroll container div that wraps the session list:

```tsx
<div className="soft-scrollbar flex-1 overflow-y-auto px-4 pb-5 lg:pb-6">
```

Change to:

```tsx
<div className="sidebar-scroll-container soft-scrollbar flex-1 overflow-y-auto px-4 pb-5 lg:pb-6">
```

#### Step 5: Enhance backdrop blur on mobile overlay

Find the mobile overlay div:

```tsx
{isOpen && (
  <div
    className="fixed inset-0 z-40 bg-black/30 lg:hidden"
    onClick={onClose}
    aria-hidden="true"
  />
)}
```

Change to:

```tsx
{isOpen && (
  <div
    className="fixed inset-0 z-40 bg-black/30 backdrop-blur-md transition-opacity duration-300 lg:hidden"
    onClick={onClose}
    aria-hidden="true"
  />
)}
```

Key changes: add `backdrop-blur-md transition-opacity duration-300`.

#### Step 6: Run TypeScript check

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

#### Step 7: Run tests

Run: `npx vitest run frontend/src/__tests__/components/` 2>&1 | tail -20
Expected: All existing tests pass.

#### Step 8: Commit

```bash
git add frontend/src/components/ConversationSidebar.tsx frontend/src/index.css
git commit -m "feat(ui): enhance ConversationSidebar with hover lift, indicator bar, dots, and fade mask"
```

---

### Task 3: HomePage header — scroll shrink + info hierarchy

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/index.css`

#### Step 1: Add scroll shrink CSS to index.css

Add before the `@media print` block:

```css
/* Header scroll transition */
.header-scroll-transition {
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
```

#### Step 2: Add scroll state to HomePage

In `HomePage.tsx`, after the existing `useState` calls (around line 30), add:

```tsx
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

This should go after `const mainRef = useRef<HTMLElement>(null)` and `const [showAuthModal, setShowAuthModal] = useState(false)`, but before the `handleRenamingChange` callback.

#### Step 3: Update tag to badge style and conditionally hide description

Find the header element. Change the tag from:

```tsx
<p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
  Writing-first interface
</p>
```

To:

```tsx
<p
  className={clsx(
    'inline-block rounded-full bg-[var(--accent-soft)] px-3 py-0.5 text-[0.65rem] font-medium uppercase tracking-[0.25em] text-[var(--accent)] header-scroll-transition',
    isScrolled && 'opacity-0',
  )}
>
  Writing-first interface
</p>
```

(Note: `clsx` is already imported in HomePage.tsx — used in ConversationSidebar but the import is in the sidebar file. HomePage.tsx doesn't currently import `clsx`. We need to add it.)

Wait, let me check the imports... HomePage.tsx doesn't use clsx. I'll use a ternary or inline condition instead, or add the import.

Actually, looking at the file, HomePage.tsx doesn't import clsx. I'll just use a conditional class string approach:

```tsx
<p className={`inline-block rounded-full bg-[var(--accent-soft)] px-3 py-0.5 text-[0.65rem] font-medium uppercase tracking-[0.25em] text-[var(--accent)] header-scroll-transition ${isScrolled ? 'opacity-0' : ''}`}>
  Writing-first interface
</p>
```

#### Step 4: Conditionally change header padding and title size

Wrap header className and title with scroll-aware classes.

Change header from:
```tsx
<header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
```
To:
```tsx
<header className={`header-scroll-transition border-b border-[var(--border)] px-4 md:px-8 ${isScrolled ? 'py-3 shadow-[0_1px_0_var(--border)]' : 'py-6'}`}>
```

This replaces the fixed `py-6` with a scroll-conditional padding, and adds a bottom shadow when scrolled.

Change the session title from:
```tsx
<h2 className="reading-copy mt-2 text-3xl tracking-tight text-[var(--ink)] md:text-[2.8rem]">
```
To:
```tsx
<h2 className={`reading-copy header-scroll-transition mt-2 tracking-tight text-[var(--ink)] ${isScrolled ? 'text-xl md:text-xl' : 'text-3xl md:text-[2.8rem]'}`}>
```

Key: different responsive font sizes based on scroll state.

#### Step 5: Conditionally hide description text

Change the description from:
```tsx
<p className="mt-3 max-w-2xl text-base leading-7 text-[var(--ink-soft)]">
  A document-style conversation for ECG interpretation...
</p>
```
To:
```tsx
{!hasUserMessages && (
  <p className={`header-scroll-transition mt-3 max-w-2xl text-base leading-7 text-[var(--ink-soft)] ${isScrolled ? 'opacity-0 invisible max-h-0 mt-0' : ''}`}>
    A document-style conversation for ECG interpretation, designed to read like notes rather than chat bubbles.
  </p>
)}
```

Key changes:
- Wrap in `!hasUserMessages` check to hide description when there are user messages (info hierarchy)
- Add scroll-driven fade-out: opacity, invisible, collapse margin/height

#### Step 6: Enhance login button hover

Find the login/register button:
```tsx
<button
  type="button"
  onClick={() => setShowAuthModal(true)}
  className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)]"
>
  登录 / 注册
</button>
```

Change to add `hover:bg-[var(--accent-soft)]`:
```tsx
className="rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--accent-soft)] hover:text-[var(--ink)]"
```

Key changes: add `transition-all duration-200` and `hover:bg-[var(--accent-soft)]`.

#### Step 7: Run TypeScript check

Run: `cd frontend && npx tsc --noEmit`
Expected: No TypeScript errors.

#### Step 8: Run tests

Run: `npx vitest run frontend/src/__tests__/` 2>&1 | tail -30
Expected: All existing tests pass. No behavioral changes should break any tests.

#### Step 9: Manual verification checklist

- Open the app in browser
- Verify: textarea auto-resizes as you type multiple lines
- Verify: send button pulses on click
- Verify: loading state shows spinning arrow, not "Analyzing" text
- Verify: file tag delete button scales on hover
- Verify: sidebar cards lift on hover
- Verify: active session shows left indicator bar
- Verify: status dots display in sidebar
- Verify: sidebar scroll fades at bottom
- Verify: mobile overlay has better blur
- Verify: header tag appears as rounded badge
- Verify: scrolling down shrinks header padding/title
- Verify: description hides when messages exist
- Verify: description fades on scroll
- Verify: login button hover shows background transition

#### Step 10: Commit

```bash
git add frontend/src/pages/HomePage.tsx frontend/src/index.css
git commit -m "feat(ui): add scroll-shrink header and refined info hierarchy to HomePage"
```
