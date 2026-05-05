import DesktopNav from './DesktopNav'
import MobileNav from './MobileNav'

export default function Navigation() {
  return (
    <>
      <div className="hidden lg:block">
        <DesktopNav />
      </div>
      <div className="lg:hidden">
        <MobileNav />
      </div>
    </>
  )
}
