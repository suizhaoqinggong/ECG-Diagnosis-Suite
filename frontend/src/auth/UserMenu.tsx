import { useState } from 'react'
import { logout as logoutApi, changePassword, deleteAccount } from './api'
import { useAuth } from './AuthProvider'

export function UserMenu() {
  const { user, logout: logoutState } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  if (!user) return null

  const handleLogout = async () => {
    setIsOpen(false)
    try {
      await logoutApi()
    } finally {
      logoutState()
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      await changePassword(oldPassword, newPassword)
      setSuccess('密码已更改，其他设备需要重新登录')
      setOldPassword('')
      setNewPassword('')
    } catch {
      setError('密码修改失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteAccount = async () => {
    setIsOpen(false)
    if (!confirm('确定要删除账号吗？所有数据将被永久删除，此操作不可撤销。')) {
      return
    }
    try {
      await deleteAccount()
      logoutState()
    } catch {
      alert('删除账号失败，请重试')
    }
  }

  const initial = (user.display_name || user.email).charAt(0).toUpperCase()

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-full px-3 py-2 transition hover:bg-[var(--surface-strong)]"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-medium text-white">
          {initial}
        </span>
        <span className="hidden text-sm font-medium text-[var(--ink)] sm:inline">
          {user.display_name || user.email}
        </span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-full z-50 mt-1 min-w-[220px] rounded-[18px] border border-[var(--border)] bg-[var(--bg)] shadow-[0_16px_40px_rgba(0,0,0,0.1)]">
            <div className="border-b border-[var(--border)] px-4 py-3">
              <p className="text-sm font-medium text-[var(--ink)]">
                {user.display_name || user.email}
              </p>
              <p className="text-xs text-[var(--ink-muted)]">{user.email}</p>
            </div>
            <div className="py-1">
              <button
                type="button"
                onClick={() => {
                  setIsOpen(false)
                  setShowChangePassword(true)
                }}
                className="w-full px-4 py-2 text-left text-sm text-[var(--ink-soft)] transition hover:bg-white/60"
              >
                修改密码
              </button>
              <button
                type="button"
                onClick={handleDeleteAccount}
                className="w-full px-4 py-2 text-left text-sm text-red-500 transition hover:bg-white/60"
              >
                删除账号
              </button>
            </div>
            <div className="border-t border-[var(--border)] py-1">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full px-4 py-2 text-left text-sm text-[var(--ink-soft)] transition hover:bg-white/60"
              >
                退出登录
              </button>
            </div>
          </div>
        </>
      )}

      {showChangePassword && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <form
            onSubmit={handleChangePassword}
            className="w-full max-w-sm rounded-[24px] border border-[var(--border)] bg-[var(--bg)] p-8 shadow-[0_24px_48px_rgba(0,0,0,0.12)]"
          >
            <h3 className="mb-4 text-lg font-semibold text-[var(--ink)]">修改密码</h3>
            <div className="space-y-3">
              <input
                type="password"
                placeholder="当前密码"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                className="w-full rounded-xl border border-[var(--border)] bg-white/60 px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              />
              <input
                type="password"
                placeholder="新密码（至少8个字符）"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-xl border border-[var(--border)] bg-white/60 px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              />
            </div>
            {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
            {success && <p className="mt-2 text-sm text-green-600">{success}</p>}
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={() => setShowChangePassword(false)}
                className="flex-1 rounded-full border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-white/60"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
              >
                {loading ? '处理中...' : '确认修改'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
