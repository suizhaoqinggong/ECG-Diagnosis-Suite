import type { NavigationDestination } from '@/types/navigation'
import { NAV_ITEMS } from '@/types/navigation'

interface DesktopNavProps {
  active: NavigationDestination
  onChange: (dest: NavigationDestination) => void
}

function ReadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v15H6.5a2.5 2.5 0 0 0 0 5H20" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M8 6h8M8 9.5h6M8 13h7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
      <path d="M12 3v12m0-12 4 4m-4-4-4 4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M3 16v3a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

function ReportsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
      <rect x="3" y="3" width="7" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
      <rect x="14" y="3" width="7" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
      <rect x="3" y="14" width="7" height="7" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
      <rect x="14" y="11" width="7" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.6"/>
    </svg>
  )
}

function AccountIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
      <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M4 21c0-4.418 3.582-8 8-8s8 3.582 8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  )
}

const iconMap: Record<string, () => JSX.Element> = {
  read: ReadIcon,
  upload: UploadIcon,
  reports: ReportsIcon,
  account: AccountIcon,
}

export default function DesktopNav({ active, onChange }: DesktopNavProps) {
  return (
    <nav
      className="flex h-screen w-64 shrink-0 flex-col border-r border-[var(--border)] bg-[var(--surface-strong)]"
      aria-label="主导航"
    >
      <div className="px-6 py-7">
        <p className="text-sm font-semibold tracking-wide text-[var(--accent)]">
          ECG Diagnosis
        </p>
        <p className="mt-1 text-xs text-[var(--ink-muted)]">
          患者阅读工作台
        </p>
      </div>

      <div className="flex-1 space-y-1 px-3">
        {NAV_ITEMS.map((item) => {
          const Icon = iconMap[item.icon]
          const isActive = active === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onChange(item.id)}
              aria-current={isActive ? 'page' : undefined}
              className={`flex w-full items-center gap-3 rounded-[16px] px-4 py-3 text-left text-sm font-medium transition ${
                isActive
                  ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
                  : 'text-[var(--ink-soft)] hover:bg-[var(--bg-muted)] hover:text-[var(--ink)]'
              }`}
            >
              <Icon />
              <span>{item.label}</span>
            </button>
          )
        })}
      </div>

      <div className="px-6 py-5">
        <p className="text-xs text-[var(--ink-muted)]">
          结果仅供参考，不构成医疗诊断
        </p>
      </div>
    </nav>
  )
}
