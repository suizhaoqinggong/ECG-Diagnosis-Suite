import { useState } from 'react'
import { useAuth } from '../auth/AuthProvider'
import { changePassword, deleteAccount } from '../auth/api'
import { getAuthErrorMessage } from '../auth/messages'
import toast from 'react-hot-toast'

export default function AccountPage() {
  const { user, logout } = useAuth()

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmNew, setConfirmNew] = useState('')
  const [pwLoading, setPwLoading] = useState(false)
  const [pwError, setPwError] = useState('')

  const [deleteConfirm, setDeleteConfirm] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  const [showDelete, setShowDelete] = useState(false)

  if (!user) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-8">
        <div className="max-w-md text-center">
          <p className="text-lg font-medium text-[var(--ink)]">请先登录</p>
          <p className="mt-2 text-sm text-[var(--ink-muted)]">登录后可查看账户信息</p>
        </div>
      </div>
    )
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError('')

    if (newPassword.length < 8) {
      setPwError('新密码至少需要8个字符')
      return
    }
    if (newPassword !== confirmNew) {
      setPwError('两次输入的新密码不一致')
      return
    }

    setPwLoading(true)
    try {
      await changePassword(currentPassword, newPassword)
      toast.success('密码已修改')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmNew('')
    } catch (err) {
      setPwError(getAuthErrorMessage(err, 'login'))
    } finally {
      setPwLoading(false)
    }
  }

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    setDeleteError('')

    if (deleteConfirm !== user.email) {
      setDeleteError('请输入您的邮箱以确认删除')
      return
    }

    setDeleteLoading(true)
    try {
      await deleteAccount(deletePassword)
      toast.success('账户已删除')
      logout()
    } catch (err) {
      setDeleteError(getAuthErrorMessage(err, 'login'))
    } finally {
      setDeleteLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-10 px-4 py-8 md:px-8 md:py-12">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-[var(--ink)]">账户管理</h1>
        <p className="mt-2 text-sm text-[var(--ink-muted)]">管理您的账户信息与安全设置</p>
      </div>

      <section aria-labelledby="user-info-heading" className="rounded-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6">
        <h2 id="user-info-heading" className="text-lg font-semibold text-[var(--ink)]">个人信息</h2>
        <div className="mt-4 space-y-3">
          <div className="flex items-baseline gap-3">
            <span className="text-sm font-medium text-[var(--ink-muted)] min-w-16">邮箱</span>
            <span className="text-base text-[var(--ink)]">{user.email}</span>
          </div>
          {user.display_name && (
            <div className="flex items-baseline gap-3">
              <span className="text-sm font-medium text-[var(--ink-muted)] min-w-16">名称</span>
              <span className="text-base text-[var(--ink)]">{user.display_name}</span>
            </div>
          )}
        </div>
        <p className="mt-4 text-xs text-[var(--ink-muted)]">
          登录后您可以跨设备访问保存的报告，您的数据仅用于报告分析。
        </p>
      </section>

      <section aria-labelledby="pw-heading" className="rounded-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6">
        <h2 id="pw-heading" className="text-lg font-semibold text-[var(--ink)]">修改密码</h2>
        <form onSubmit={handleChangePassword} className="mt-4 space-y-4">
          <div>
            <label htmlFor="current-pw" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">当前密码</label>
            <input id="current-pw" type="password" value={currentPassword} required
              onChange={e => setCurrentPassword(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
            />
          </div>
          <div>
            <label htmlFor="new-pw" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">新密码</label>
            <input id="new-pw" type="password" value={newPassword} required
              onChange={e => setNewPassword(e.target.value)} minLength={8}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              placeholder="至少8个字符"
            />
          </div>
          <div>
            <label htmlFor="confirm-new-pw" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">确认新密码</label>
            <input id="confirm-new-pw" type="password" value={confirmNew} required
              onChange={e => setConfirmNew(e.target.value)}
              className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
            />
          </div>
          {pwError && <p className="text-sm text-red-500" role="alert">{pwError}</p>}
          <button type="submit" disabled={pwLoading}
            className="rounded-full bg-[var(--accent)] px-6 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {pwLoading ? '修改中...' : '修改密码'}
          </button>
        </form>
      </section>

      <section aria-labelledby="danger-heading" className="rounded-[24px] border-2 border-red-200 bg-red-50/30 p-6">
        <h2 id="danger-heading" className="text-lg font-semibold text-red-700">危险操作</h2>
        <p className="mt-2 text-sm text-red-600/80">
          删除账户后将永久移除所有保存的报告和历史记录，此操作不可撤销。
        </p>
        {!showDelete ? (
          <button type="button" onClick={() => setShowDelete(true)}
            className="mt-4 rounded-full border-2 border-red-300 px-6 py-3 text-sm font-medium text-red-700 transition hover:bg-red-100"
          >
            删除账户
          </button>
        ) : (
          <form onSubmit={handleDeleteAccount} className="mt-4 space-y-4">
            <div>
              <label htmlFor="delete-email" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">
                输入您的邮箱以确认：<span className="font-semibold text-[var(--ink)]">{user.email}</span>
              </label>
              <input id="delete-email" type="email" value={deleteConfirm} required
                onChange={e => setDeleteConfirm(e.target.value)}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-red-500"
              />
            </div>
            <div>
              <label htmlFor="delete-password" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">输入密码以确认</label>
              <input id="delete-password" type="password" value={deletePassword} required
                onChange={e => setDeletePassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-red-500"
              />
            </div>
            {deleteError && <p className="text-sm text-red-500" role="alert">{deleteError}</p>}
            <div className="flex gap-3">
              <button type="submit" disabled={deleteLoading}
                className="rounded-full bg-red-600 px-6 py-3 text-sm font-medium text-white transition hover:bg-red-700 disabled:opacity-50"
              >
                {deleteLoading ? '删除中...' : '确认删除'}
              </button>
              <button type="button"
                onClick={() => { setShowDelete(false); setDeleteError('') }} disabled={deleteLoading}
                className="rounded-full border border-[var(--border)] px-6 py-3 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white"
              >
                取消
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
