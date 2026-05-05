export type NavigationDestination = 'read-report' | 'upload-ecg' | 'my-reports' | 'account'

export interface NavItem {
  id: NavigationDestination
  label: string
  shortLabel: string
  icon: string
  path: string
}

export const ROUTES: Record<NavigationDestination, string> = {
  'read-report': '/',
  'upload-ecg': '/upload',
  'my-reports': '/reports',
  'account': '/account',
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: 'read-report',
    label: '读懂报告',
    shortLabel: '读报告',
    icon: 'read',
    path: '/',
  },
  {
    id: 'upload-ecg',
    label: '上传ECG',
    shortLabel: '上传',
    icon: 'upload',
    path: '/upload',
  },
  {
    id: 'my-reports',
    label: '我的报告',
    shortLabel: '报告',
    icon: 'reports',
    path: '/reports',
  },
  {
    id: 'account',
    label: '账户',
    shortLabel: '账户',
    icon: 'account',
    path: '/account',
  },
]
