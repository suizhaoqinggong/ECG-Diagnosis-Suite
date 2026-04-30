import type { HealthRiskLevel } from '@/types/health'

export const COLORS = {
  bg: '#f4f7f9',
  bgMuted: '#eaf0f4',
  surface: 'rgba(255,255,255,0.88)',
  surfaceStrong: 'rgba(255,255,255,0.96)',
  border: 'rgba(100,130,150,0.16)',
  borderStrong: 'rgba(100,130,150,0.24)',
  ink: '#1a2330',
  inkSoft: '#3d5068',
  inkMuted: '#6b8299',
  accent: '#2d7d8f',
  accentSoft: '#d4e8ed',
  success: '#2d8f5e',
  danger: '#c0392b',
  warning: '#c9781b',
} as const

export const RISK_COLORS: Record<HealthRiskLevel, { bg: string; text: string; border: string }> = {
  low: { bg: '#f0faf5', text: '#1a6b3c', border: '#2d8f5e' },
  medium: { bg: '#fef9ee', text: '#8a5d1a', border: '#c9781b' },
  high: { bg: '#fef5f2', text: '#a82e1e', border: '#d4452f' },
  urgent: { bg: '#fef2f2', text: '#a41e1e', border: '#c0392b' },
} as const

export const SPACING = {
  xs: '0.25rem',
  sm: '0.5rem',
  md: '1rem',
  lg: '1.5rem',
  xl: '2rem',
  '2xl': '3rem',
} as const

export const RADIUS = {
  sm: '12px',
  md: '16px',
  lg: '20px',
  xl: '24px',
  full: '9999px',
} as const

export const FONTS = {
  heading: "'Lexend', 'Source Sans 3', -apple-system, sans-serif",
  body: "'Source Sans 3', -apple-system, 'Segoe UI', sans-serif",
} as const
