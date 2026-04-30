import { useState, useMemo } from 'react'
import type { ChatSession } from '@/types/chat'
import ReportListItem from './ReportListItem'

export function hasMeaningfulReport(session: ChatSession): boolean {
  return session.messages.some((m) => m.type !== 'intro')
}

interface ReportListProps {
  sessions: ChatSession[]
  selectedId: string | null
  onSelect: (id: string) => void
}

export default function ReportList({
  sessions,
  selectedId,
  onSelect,
}: ReportListProps) {
  const [search, setSearch] = useState('')

  const filtered = useMemo(() => {
    const meaningful = sessions.filter(hasMeaningfulReport)
    if (!search.trim()) return meaningful
    const q = search.toLowerCase()
    return meaningful.filter(
      (s) =>
        s.title.toLowerCase().includes(q) ||
        s.preview.toLowerCase().includes(q),
    )
  }, [sessions, search])

  return (
    <div className="flex h-full flex-col border-r border-[var(--border)]">
      <div className="space-y-3 border-b border-[var(--border)] p-4">
        <h2 className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
          报告列表
        </h2>
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="搜索报告..."
          className="w-full rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--ink)] placeholder:text-[var(--ink-muted)] focus:border-[var(--accent)] focus:outline-none"
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-sm text-[var(--ink-muted)]">
              {search.trim() ? '未找到匹配的报告' : '暂无报告'}
            </p>
          </div>
        ) : (
          filtered.map((session) => (
            <ReportListItem
              key={session.id}
              session={session}
              isSelected={session.id === selectedId}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </div>
  )
}
