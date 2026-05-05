import { useState, useEffect, useCallback } from 'react'
import type { ChatSession } from '@/types/chat'
import { useWorkspace } from '@/controllers/WorkspaceProvider'
import ReportList from '@/components/ReportList'
import ReportDetail from '@/components/ReportDetail'
import EmptyReports from '@/components/EmptyReports'

function hasMeaningfulReport(session: ChatSession): boolean {
  return session.messages.some((m) => m.type !== 'intro')
}

export default function MyReportsPage() {
  const { state, renameSession, deleteSession } = useWorkspace()
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

  if (meaningfulSessions.length === 0) {
    return (
      <div className="flex min-h-0 flex-1">
        <EmptyReports />
      </div>
    )
  }

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
