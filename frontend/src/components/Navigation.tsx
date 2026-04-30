import type { NavigationDestination } from '@/types/navigation'
import DesktopNav from './DesktopNav'
import MobileNav from './MobileNav'

interface NavigationProps {
  active: NavigationDestination
  onChange: (dest: NavigationDestination) => void
}

export default function Navigation({ active, onChange }: NavigationProps) {
  return (
    <>
      {/* Desktop: visible on lg+ */}
      <div className="hidden lg:block">
        <DesktopNav active={active} onChange={onChange} />
      </div>

      {/* Mobile: visible below lg */}
      <div className="lg:hidden">
        <MobileNav active={active} onChange={onChange} />
      </div>
    </>
  )
}
