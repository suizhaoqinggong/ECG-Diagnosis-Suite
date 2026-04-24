import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { UserMenu } from '@/auth/UserMenu'

const {
  authState,
  logoutMock,
  changePasswordMock,
  deleteAccountMock,
  toastSuccessMock,
} = vi.hoisted(() => ({
  authState: {
    user: {
      id: 1,
      email: 'doctor@example.com',
      display_name: 'Doctor',
    },
  },
  logoutMock: vi.fn(),
  changePasswordMock: vi.fn(),
  deleteAccountMock: vi.fn(),
  toastSuccessMock: vi.fn(),
}))

vi.mock('@/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: authState.user,
    logout: logoutMock,
  }),
}))

vi.mock('@/auth/api', () => ({
  logout: vi.fn(),
  changePassword: changePasswordMock,
  deleteAccount: deleteAccountMock,
}))

vi.mock('react-hot-toast', () => ({
  default: {
    success: toastSuccessMock,
  },
}))

describe('UserMenu', () => {
  beforeEach(() => {
    logoutMock.mockReset()
    changePasswordMock.mockReset()
    deleteAccountMock.mockReset()
    toastSuccessMock.mockReset()
  })

  it('logs the current device out after a successful password change', async () => {
    changePasswordMock.mockResolvedValueOnce(undefined)

    render(<UserMenu />)

    fireEvent.click(screen.getByRole('button', { name: /Doctor/i }))
    fireEvent.click(screen.getByRole('button', { name: '修改密码' }))
    fireEvent.change(screen.getByLabelText('当前密码'), {
      target: { value: 'old-password' },
    })
    fireEvent.change(screen.getByLabelText('新密码'), {
      target: { value: 'new-password123' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认修改' }))

    await waitFor(() => {
      expect(changePasswordMock).toHaveBeenCalledWith('old-password', 'new-password123')
      expect(logoutMock).toHaveBeenCalledTimes(1)
      expect(toastSuccessMock).toHaveBeenCalledWith('密码已修改，请重新登录')
    })
  })

  it('sends the current password when deleting an account', async () => {
    deleteAccountMock.mockResolvedValueOnce(undefined)

    render(<UserMenu />)

    fireEvent.click(screen.getByRole('button', { name: /Doctor/i }))
    fireEvent.click(screen.getByRole('button', { name: '删除账号' }))
    fireEvent.change(screen.getByLabelText('当前密码'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByRole('button', { name: '确认删除' }))

    await waitFor(() => {
      expect(deleteAccountMock).toHaveBeenCalledWith('password123')
      expect(logoutMock).toHaveBeenCalledTimes(1)
      expect(toastSuccessMock).toHaveBeenCalledWith('账号已删除')
    })
  })
})
