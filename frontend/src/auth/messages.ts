import axios from 'axios'

import { extractErrorMessage } from '@/api/client'

type AuthAction = 'login' | 'register' | 'change-password' | 'delete-account'

const FALLBACK_MESSAGES: Record<AuthAction, string> = {
  login: '登录失败，请稍后重试',
  register: '注册失败，请稍后重试',
  'change-password': '密码修改失败，请稍后重试',
  'delete-account': '删除账号失败，请稍后重试',
}

function getCommonMessage(status: number | undefined, detail: string): string | null {
  if (status === 403 || detail === 'Invalid origin') {
    return '当前页面已失效，请刷新后重试'
  }

  if (status === 429) {
    return '尝试次数过多，请稍后再试'
  }

  return null
}

export function getAuthErrorMessage(error: unknown, action: AuthAction): string {
  const detail = extractErrorMessage(error)

  if (!axios.isAxiosError(error) || !error.response) {
    if (detail === 'Network Error') {
      return '网络异常，请检查连接后重试'
    }
    return detail || FALLBACK_MESSAGES[action]
  }

  const { status } = error.response
  const commonMessage = getCommonMessage(status, detail)
  if (commonMessage) {
    if (status === 429) {
      switch (action) {
        case 'login':
          return '登录尝试过多，请稍后再试'
        case 'register':
          return '注册尝试过多，请稍后再试'
        default:
          return commonMessage
      }
    }
    return commonMessage
  }

  switch (action) {
    case 'login':
      if (status === 401 || detail === 'Invalid credentials') {
        return '邮箱或密码错误'
      }
      if (status === 422) {
        return '请输入有效的邮箱和密码'
      }
      break
    case 'register':
      if (status === 400 || detail === 'Registration failed') {
        return '该邮箱已被注册'
      }
      if (status === 422) {
        return '请输入有效的邮箱和至少 8 位密码'
      }
      break
    case 'change-password':
      if (status === 400 || detail === 'Invalid old password') {
        return '当前密码错误'
      }
      if (status === 401) {
        return '登录状态已失效，请重新登录'
      }
      if (status === 422) {
        return '新密码至少需要 8 个字符'
      }
      break
    case 'delete-account':
      if (detail === 'Invalid password') {
        return '当前密码错误，无法删除账号'
      }
      if (status === 401) {
        return '登录状态已失效，请重新登录'
      }
      if (status === 422) {
        return '请输入当前密码以删除账号'
      }
      break
  }

  if (status >= 500) {
    return FALLBACK_MESSAGES[action]
  }

  return detail || FALLBACK_MESSAGES[action]
}
