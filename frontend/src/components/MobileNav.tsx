import { NavLink } from 'react-router-dom'
import { NAV_ITEMS } from '@/types/navigation'

function ReadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" aria-hidden="true">
      <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v15H6.5a2.5 2.5 0 0 0 0 5H20" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
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

export default function MobileNav() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-40 border-t border-[var(--border)] bg-[var(--surface-strong)]"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label="主导航"
    >
      <div className="flex items-center justify-around">
        {NAV_ITEMS.map((item) => {
          const Icon = iconMap[item.icon]
          return (
            <NavLink
              key={item.id}
              to={item.path}
              end={item.path === '/'}
              aria-current="page"
              className={({ isActive }) =>
                `flex min-h-[56px] min-w-[48px] flex-1 flex-col items-center justify-center gap-0.5 relative transition ${
                  isActive
                    ? 'text-[var(--accent)]'
                    : 'text-[var(--ink-muted)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon />
                  <span className="text-[11px] font-medium leading-none">
                    {item.shortLabel}
                  </span>
                  {isActive && (
                    <span className="absolute top-0 h-[3px] w-8 rounded-full bg-[var(--accent)]" />
                  )}
                </>
              )}
            </NavLink>
          )
        })}
      </div>
    </nav>
  )
}
