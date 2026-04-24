import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthModal } from '@/auth/AuthModal'

const { loginMock, registerMock, setAuthenticatedMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  registerMock: vi.fn(),
  setAuthenticatedMock: vi.fn(),
}))

vi.mock('@/auth/api', () => ({
  login: loginMock,
  register: registerMock,
}))

vi.mock('@/auth/AuthProvider', () => ({
  useAuth: () => ({
    setAuthenticated: setAuthenticatedMock,
  }),
}))

function createDeferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolver) => {
    resolve = resolver
  })
  return { promise, resolve }
}

function makeAxiosError(status: number, detail: string) {
  return {
    isAxiosError: true,
    message: detail,
    response: {
      status,
      data: { detail },
    },
  }
}

describe('AuthModal', () => {
  beforeEach(() => {
    loginMock.mockReset()
    registerMock.mockReset()
    setAuthenticatedMock.mockReset()
  })

  it('shows a rate-limit message for failed logins', async () => {
    loginMock.mockRejectedValueOnce(makeAxiosError(429, 'Too many requests'))

    render(<AuthModal isOpen onClose={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('邮箱'), {
      target: { value: 'doctor@example.com' },
    })
    fireEvent.change(screen.getByLabelText('密码'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: '登录' })[1])

    await waitFor(() => {
      expect(screen.getByText('登录尝试过多，请稍后再试')).toBeInTheDocument()
    })
  })

  it('resets fields when reopened and honors the default tab', () => {
    const { rerender } = render(<AuthModal isOpen onClose={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('邮箱'), {
      target: { value: 'doctor@example.com' },
    })

    rerender(<AuthModal isOpen={false} onClose={vi.fn()} />)
    rerender(<AuthModal isOpen onClose={vi.fn()} defaultTab="register" />)

    expect(screen.getByLabelText('邮箱')).toHaveValue('')
    expect(screen.getByLabelText('确认密码')).toBeInTheDocument()
  })

  it('does not close while an auth request is still pending', async () => {
    const deferred = createDeferred<{
      user: { id: number; email: string; display_name: string }
      access_token: string
    }>()
    loginMock.mockImplementationOnce(() => deferred.promise)
    const onClose = vi.fn()

    render(<AuthModal isOpen onClose={onClose} />)

    fireEvent.change(screen.getByLabelText('邮箱'), {
      target: { value: 'doctor@example.com' },
    })
    fireEvent.change(screen.getByLabelText('密码'), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getAllByRole('button', { name: '登录' })[1])

    await waitFor(() => {
      expect(screen.getByRole('button', { name: '处理中...' })).toBeDisabled()
    })

    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    expect(onClose).not.toHaveBeenCalled()

    deferred.resolve({
      user: {
        id: 1,
        email: 'doctor@example.com',
        display_name: 'Doctor',
      },
      access_token: 'token',
    })

    await waitFor(() => {
      expect(setAuthenticatedMock).toHaveBeenCalledWith(
        {
          id: 1,
          email: 'doctor@example.com',
          display_name: 'Doctor',
        },
        'token',
      )
      expect(onClose).toHaveBeenCalledTimes(1)
    })
  })
})
