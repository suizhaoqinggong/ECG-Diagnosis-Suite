import { useState, useEffect, useCallback } from 'react'
import type { NavigationDestination } from '@/types/navigation'
import type { ChatSession } from '@/types/chat'
import { useWorkspaceController } from '@/controllers/useWorkspaceController'
import ReportList from '@/components/ReportList'
import ReportDetail from '@/components/ReportDetail'
import EmptyReports from '@/components/EmptyReports'

interface MyReportsPageProps {
  onNavigate: (dest: NavigationDestination) => void
}

function hasMeaningfulReport(session: ChatSession): boolean {
  return session.messages.some((m) => m.type !== 'intro')
}

export default function MyReportsPage({ onNavigate }: MyReportsPageProps) {
  const { state, renameSession, deleteSession } = useWorkspaceController()
  const sessions = state.persisted.sessions
  const meaningfulSessions = sessions.filter(hasMeaningfulReport)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [isMobile, setIsMobile] = useState(false)
  const [showDetailMobile, setShowDetailMobile] = useState(false)

  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [])

  // Auto-select first meaningful session when the list first populates
  useEffect(() => {
    if (meaningfulSessions.length > 0 && !selectedId) {
      setSelectedId(meaningfulSessions[0].id)
    }
  }, [meaningfulSessions, selectedId])

  const selectedSession =
    sessions.find((s) => s.id === selectedId) ?? null

  const handleSelect = useCallback(
    (id: string) => {
      setSelectedId(id)
      if (isMobile) setShowDetailMobile(true)
    },
    [isMobile],
  )

  const handleBack = useCallback(() => {
    setShowDetailMobile(false)
  }, [])

  const handleRename = useCallback(
    (id: string, title: string) => {
      renameSession(id, title)
    },
    [renameSession],
  )

  const handleDelete = useCallback(
    (id: string) => {
      deleteSession(id)
      if (selectedId === id) {
        const remaining = sessions
          .filter((s) => s.id !== id)
          .filter(hasMeaningfulReport)
        setSelectedId(remaining[0]?.id ?? null)
      }
    },
    [deleteSession, selectedId, sessions],
  )

  // Empty state
  if (meaningfulSessions.length === 0) {
    return (
      <div className="flex min-h-0 flex-1">
        <EmptyReports onNavigate={onNavigate} />
      </div>
    )
  }

  // Mobile: toggle between list and detail
  if (isMobile) {
    if (showDetailMobile && selectedSession) {
      return (
        <div className="flex min-h-0 flex-1 flex-col">
          <ReportDetail
            session={selectedSession}
            onRename={handleRename}
            onDelete={handleDelete}
            onBack={handleBack}
          />
        </div>
      )
    }

    return (
      <div className="flex min-h-0 flex-1 flex-col">
        <ReportList
          sessions={sessions}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
      </div>
    )
  }

  // Desktop: master/detail layout
  return (
    <div className="flex min-h-0 flex-1">
      <div className="w-80 shrink-0">
        <ReportList
          sessions={sessions}
          selectedId={selectedId}
          onSelect={handleSelect}
        />
      </div>
      <div className="min-w-0 flex-1">
        <ReportDetail
          session={selectedSession}
          onRename={handleRename}
          onDelete={handleDelete}
        />
      </div>
    </div>
  )
}
