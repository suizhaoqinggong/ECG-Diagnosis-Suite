interface SavePromptProps {
  isOpen: boolean
  onClose: () => void
  onLogin: () => void
  onSkip: () => void
}

export default function SavePrompt({ isOpen, onClose, onLogin, onSkip }: SavePromptProps) {
  if (!isOpen) return null

  const handleLogin = () => {
    onClose()
    onLogin()
  }

  const handleSkip = () => {
    onClose()
    onSkip()
  }

  return (
    <div
      className="fixed inset-0 z-[90] flex items-end justify-center bg-black/40 backdrop-blur-sm lg:items-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-prompt-title"
    >
      <div
        className="w-full max-w-md rounded-t-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 pb-8 lg:rounded-[24px]"
        onClick={e => e.stopPropagation()}
        style={{ paddingBottom: 'calc(2rem + env(safe-area-inset-bottom, 0px))' }}
      >
        <h3 id="save-prompt-title" className="text-lg font-semibold text-[var(--ink)]">
          保存您的报告
        </h3>
        <p className="mt-3 text-base leading-7 text-[var(--ink-soft)]">
          登录后可以保存报告到「我的报告」，方便在不同设备上随时查看分析结果。
        </p>

        <div className="mt-6 space-y-3">
          <button
            type="button"
            onClick={handleLogin}
            className="w-full rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
          >
            登录 / 注册
          </button>
          <button
            type="button"
            onClick={handleSkip}
            className="w-full rounded-full border border-[var(--border)] px-6 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-[var(--bg-muted)] hover:text-[var(--ink)]"
          >
            暂时跳过
          </button>
        </div>

        <p className="mt-4 text-xs text-[var(--ink-muted)] text-center">
          您的数据仅用于报告分析，不会用于其他用途
        </p>
      </div>
    </div>
  )
}
