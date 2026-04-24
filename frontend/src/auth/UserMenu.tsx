import { useState } from 'react'
import toast from 'react-hot-toast'

import { logout as logoutApi, changePassword, deleteAccount } from './api'
import { useAuth } from './AuthProvider'
import { getAuthErrorMessage } from './messages'

export function UserMenu() {
  const { user, logout: logoutState } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [showChangePassword, setShowChangePassword] = useState(false)
  const [showDeleteAccount, setShowDeleteAccount] = useState(false)
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [deletePassword, setDeletePassword] = useState('')
  const [changePasswordLoading, setChangePasswordLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [changePasswordError, setChangePasswordError] = useState('')
  const [deleteError, setDeleteError] = useState('')

  if (!user) return null

  const requestCloseChangePasswordModal = (force = false) => {
    if (changePasswordLoading && !force) return
    setShowChangePassword(false)
    setOldPassword('')
    setNewPassword('')
    setChangePasswordError('')
  }

  const requestCloseDeleteAccountModal = (force = false) => {
    if (deleteLoading && !force) return
    setShowDeleteAccount(false)
    setDeletePassword('')
    setDeleteError('')
  }

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
    setChangePasswordError('')
    setChangePasswordLoading(true)

    try {
      await changePassword(oldPassword, newPassword)
      requestCloseChangePasswordModal(true)
      logoutState()
      toast.success('密码已修改，请重新登录')
    } catch (error) {
      setChangePasswordError(getAuthErrorMessage(error, 'change-password'))
    } finally {
      setChangePasswordLoading(false)
    }
  }

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    setDeleteError('')
    setDeleteLoading(true)

    try {
      await deleteAccount(deletePassword)
      requestCloseDeleteAccountModal(true)
      logoutState()
      toast.success('账号已删除')
    } catch (error) {
      setDeleteError(getAuthErrorMessage(error, 'delete-account'))
    } finally {
      setDeleteLoading(false)
    }
  }

  const handleDeleteAccountClick = () => {
    setIsOpen(false)
    setDeleteError('')
    setDeletePassword('')
    setShowDeleteAccount(true)
  }

  const handleCloseChangePasswordModal = () => {
    requestCloseChangePasswordModal()
  }

  const handleCloseDeleteAccountModal = () => {
    requestCloseDeleteAccountModal()
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
                  setChangePasswordError('')
                  setShowChangePassword(true)
                }}
                className="w-full px-4 py-2 text-left text-sm text-[var(--ink-soft)] transition hover:bg-white/60"
              >
                修改密码
              </button>
              <button
                type="button"
                onClick={handleDeleteAccountClick}
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
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={handleCloseChangePasswordModal}
        >
          <form
            onSubmit={handleChangePassword}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-[24px] border border-[var(--border)] bg-[var(--bg)] p-8 shadow-[0_24px_48px_rgba(0,0,0,0.12)]"
          >
            <h3 className="mb-4 text-lg font-semibold text-[var(--ink)]">修改密码</h3>
            <div className="space-y-3">
              <label htmlFor="current-password" className="sr-only">
                当前密码
              </label>
              <input
                id="current-password"
                type="password"
                placeholder="当前密码"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
                className="w-full rounded-xl border border-[var(--border)] bg-white/60 px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              />
              <label htmlFor="new-password" className="sr-only">
                新密码
              </label>
              <input
                id="new-password"
                type="password"
                placeholder="新密码（至少8个字符）"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                className="w-full rounded-xl border border-[var(--border)] bg-white/60 px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-[var(--accent)]"
              />
            </div>
            {changePasswordError && <p className="mt-2 text-sm text-red-500">{changePasswordError}</p>}
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={handleCloseChangePasswordModal}
                disabled={changePasswordLoading}
                className="flex-1 rounded-full border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-white/60"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={changePasswordLoading}
                className="flex-1 rounded-full bg-[var(--accent)] px-4 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
              >
                {changePasswordLoading ? '处理中...' : '确认修改'}
              </button>
            </div>
          </form>
        </div>
      )}

      {showDeleteAccount && (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm"
          onClick={handleCloseDeleteAccountModal}
        >
          <form
            onSubmit={handleDeleteAccount}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-sm rounded-[24px] border border-red-200 bg-[var(--bg)] p-8 shadow-[0_24px_48px_rgba(0,0,0,0.12)]"
          >
            <h3 className="text-lg font-semibold text-[var(--ink)]">删除账号</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
              此操作会永久删除你的账号和云端会话记录，且不可撤销。请输入当前密码以确认。
            </p>
            <div className="mt-4">
              <label htmlFor="delete-account-password" className="mb-1 block text-sm font-medium text-[var(--ink-soft)]">
                当前密码
              </label>
              <input
                id="delete-account-password"
                type="password"
                value={deletePassword}
                onChange={(e) => setDeletePassword(e.target.value)}
                required
                className="w-full rounded-xl border border-[var(--border)] bg-white/60 px-4 py-3 text-sm text-[var(--ink)] outline-none transition focus:border-red-400"
              />
            </div>
            {deleteError && <p className="mt-2 text-sm text-red-500">{deleteError}</p>}
            <div className="mt-4 flex gap-3">
              <button
                type="button"
                onClick={handleCloseDeleteAccountModal}
                disabled={deleteLoading}
                className="flex-1 rounded-full border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-white/60"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={deleteLoading}
                className="flex-1 rounded-full bg-red-500 px-4 py-3 text-sm font-medium text-white transition hover:bg-red-600 disabled:opacity-50"
              >
                {deleteLoading ? '处理中...' : '确认删除'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
