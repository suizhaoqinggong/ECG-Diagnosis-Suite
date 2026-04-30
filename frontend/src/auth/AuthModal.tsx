import { useEffect, useState } from 'react'
import { login, register } from './api'
import { useAuth } from './AuthProvider'
import { getAuthErrorMessage } from './messages'

interface AuthModalProps {
  isOpen: boolean
  onClose: () => void
  defaultTab?: 'login' | 'register'
}

const BENEFITS = [
  '保存分析结果到「我的报告」',
  '在多台设备上安全访问历史记录',
  '方便随时回看和对比检查结果',
]

export function AuthModal({ isOpen, onClose, defaultTab = 'login' }: AuthModalProps) {
  const [tab, setTab] = useState<'login' | 'register'>(defaultTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setAuthenticated } = useAuth()

  useEffect(() => {
    if (isOpen) {
      setTab(defaultTab)
      setError('')
      return
    }

    setTab(defaultTab)
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setDisplayName('')
    setError('')
    setLoading(false)
  }, [defaultTab, isOpen])

  if (!isOpen) return null

  const requestClose = (force = false) => {
    if (loading && !force) return
    onClose()
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (tab === 'register') {
        if (password !== confirmPassword) {
          setError('两次输入的密码不一致')
          setLoading(false)
          return
        }
        if (password.length < 8) {
          setError('密码至少需要8个字符')
          setLoading(false)
          return
        }
        const response = await register({
          email,
          password,
          display_name: displayName || undefined,
        })
        setAuthenticated(response.user, response.access_token)
      } else {
        const response = await login({ email, password })
        setAuthenticated(response.user, response.access_token)
      }
      requestClose(true)
    } catch (error) {
      setError(getAuthErrorMessage(error, tab))
    } finally {
      setLoading(false)
    }
  }

  const handleCloseClick = () => {
    requestClose()
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/50 backdrop-blur-sm lg:items-center"
      onClick={handleCloseClick}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="w-full max-w-md rounded-t-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 pb-8 lg:rounded-[24px] lg:p-8 shadow-[0_24px_48px_rgba(0,0,0,0.12)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="auth-modal-title" className="text-lg font-semibold text-[var(--ink)]">
          {tab === 'login' ? '登录以保存报告' : '注册以保存报告'}
        </h3>
        <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
          {tab === 'login'
            ? '登录后可保存分析结果到「我的报告」，跨设备安全访问'
            : '注册后可保存分析结果到「我的报告」，跨设备安全访问'
          }
        </p>

        <div className="mt-4 space-y-1.5 rounded-[16px] bg-[var(--bg-muted)]/70 px-4 py-3">
          {BENEFITS.map((benefit, i) => (
            <div key={i} className="flex items-center gap-2 text-sm text-[var(--ink-soft)]">
              <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4 shrink-0 text-[var(--accent)]" aria-hidden="true">
                <path d="M5 13l4 4L19 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              {benefit}
            </div>
          ))}
        </div>

        <div className="mt-6 mb-4 flex gap-6">
          <button
            type="button"
            onClick={() => { setTab('login'); setError('') }}
            className={`pb-2 text-sm font-medium transition ${
              tab === 'login'
                ? 'border-b-2 border-[var(--accent)] text-[var(--ink)]'
                : 'text-[var(--ink-muted)]'
            }`}
          >
            登录
          </button>
          <button
            type="button"
            onClick={() => { setTab('register'); setError('') }}
            className={`pb-2 text-sm font-medium transition ${
              tab === 'register'
                ? 'border-b-2 border-[var(--accent)] text-[var(--ink)]'
                : 'text-[var(--ink-muted)]'
            }`}
          >
            注册
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {tab === 'register' && (
            <div>
              <label
                htmlFor="auth-display-name"
                className="mb-1 block text-sm font-medium text-[var(--ink-soft)]"
              >
                显示名称（可选）
              </label>
              <input
                id="auth-display-name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
                placeholder="你希望怎么被称呼"
              />
            </div>
          )}

          <div>
            <label htmlFor="auth-email" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">
              邮箱
            </label>
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              placeholder="your@email.com"
            />
          </div>

          <div>
            <label htmlFor="auth-password" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">
              密码
            </label>
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={tab === 'register' ? 8 : undefined}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              placeholder={tab === 'register' ? '至少8个字符' : ''}
            />
          </div>

          {tab === 'register' && (
            <div>
              <label
                htmlFor="auth-confirm-password"
                className="mb-1 block text-sm font-medium text-[var(--ink-soft)]"
              >
                确认密码
              </label>
              <input
                id="auth-confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
                placeholder="再次输入密码"
              />
            </div>
          )}

          <div aria-live="polite">
            {error && (
              <p className="text-sm text-red-500" role="alert">{error}</p>
            )}
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={handleCloseClick}
              disabled={loading}
              className="flex-1 rounded-full border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-[var(--bg-muted)] hover:text-[var(--ink)]"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {loading ? '处理中...' : tab === 'login' ? '登录' : '注册'}
            </button>
          </div>
        </form>

        <p className="mt-4 text-center text-xs text-[var(--ink-muted)]">
          您的数据仅用于报告分析，不会用于其他用途
        </p>
      </div>
    </div>
  )
}
