import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import type { ChatSession } from '../types/chat'
import { useAuth } from '../auth/AuthProvider'
import { formatSidebarTimestamp } from '../utils'
import SessionMenu from './SessionMenu'

interface SessionSwitcherProps {
  sessions: ChatSession[]
  activeSessionId: string
  onSelectSession: (sessionId: string) => void
  onCreateSession: () => void
  onRenameSession: (id: string, title: string) => void
  onDeleteSession: (id: string) => void
  renamingSessionId: string | null
  onRenamingChange: (id: string | null) => void
  persistenceEnabled: boolean
  onTogglePersistence: () => void
  onClearAllSessions: () => void
}

const RECENT_LIMIT = 6

function ChevronDownIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className="h-4 w-4 transition-transform"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}

function PlusIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className="h-4 w-4"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}

function ArrowRightIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      className="h-3.5 w-3.5"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M5 12h14M13 5l7 7-7 7" />
    </svg>
  )
}

export default function SessionSwitcher({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onRenameSession,
  onDeleteSession,
  renamingSessionId,
  onRenamingChange,
  persistenceEnabled,
  onTogglePersistence,
  onClearAllSessions,
}: SessionSwitcherProps) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)

  const activeSession =
    sessions.find((s) => s.id === activeSessionId) ?? sessions[0] ?? null
  const recentSessions = useMemo(
    () => sessions.slice(0, RECENT_LIMIT),
    [sessions],
  )
  const hasMore = sessions.length > RECENT_LIMIT

  // Click outside to close
  useEffect(() => {
    if (!open) return
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  // Escape to close, return focus to trigger
  useEffect(() => {
    if (!open) return
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open])

  const handleSelect = useCallback(
    (id: string) => {
      onSelectSession(id)
      setOpen(false)
    },
    [onSelectSession],
  )

  const handleCreate = useCallback(() => {
    onCreateSession()
    setOpen(false)
  }, [onCreateSession])

  const handleNavigateAll = useCallback(() => {
    navigate('/reports')
    setOpen(false)
  }, [navigate])

  const handleClearAll = useCallback(() => {
    const message = user
      ? '这将从服务器删除所有对话，无法撤消。'
      : '清除所有历史记录？此操作无法撤消。'
    if (typeof window !== 'undefined' && window.confirm(message)) {
      onClearAllSessions()
      setOpen(false)
    }
  }, [user, onClearAllSessions])

  if (!activeSession) return null

  return (
    <div ref={containerRef} className="relative inline-block">
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className={clsx(
          'group inline-flex max-w-full items-center gap-3 rounded-2xl border bg-[var(--surface-strong)] px-4 py-2.5 text-left transition',
          'border-[var(--border)] hover:border-[var(--border-strong)] hover:bg-white',
          open && 'border-[var(--border-strong)] bg-white shadow-[0_8px_24px_rgba(45,125,143,0.10)]',
        )}
      >
        <span className="reading-copy truncate text-2xl font-medium tracking-tight text-[var(--ink)] md:text-[2rem]">
          {activeSession.title}
        </span>
        <span
          className={clsx(
            'flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[var(--ink-muted)] transition group-hover:text-[var(--ink-soft)]',
            open && 'rotate-180 text-[var(--ink-soft)]',
          )}
        >
          <ChevronDownIcon />
        </span>
      </button>

      {open && (
        <div
          role="menu"
          aria-label="切换会话"
          className="absolute left-0 top-[calc(100%+0.5rem)] z-40 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-[20px] border border-[var(--border)] bg-[var(--surface-strong)] shadow-[0_18px_48px_rgba(15,30,50,0.14)] backdrop-blur-md"
        >
          {/* Top action: new session */}
          <div className="px-2 pt-2">
            <button
              type="button"
              onClick={handleCreate}
              className="flex w-full items-center gap-3 rounded-[14px] px-3 py-2.5 text-left text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--accent-soft)] hover:text-[var(--accent)]"
              role="menuitem"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
                <PlusIcon />
              </span>
              新对话
            </button>
          </div>

          <div className="my-1 h-px bg-[var(--border)]" />

          {/* Recent sessions */}
          <div className="soft-scrollbar max-h-[min(60vh,360px)] overflow-y-auto px-2 pb-2">
            {recentSessions.length === 0 ? (
              <p className="px-3 py-4 text-sm text-[var(--ink-muted)]">
                暂无历史会话
              </p>
            ) : (
              <ul className="flex flex-col">
                {recentSessions.map((session) => {
                  const isActive = session.id === activeSessionId
                  const isRenaming = renamingSessionId === session.id
                  return (
                    <li key={session.id}>
                      <div
                        className={clsx(
                          'group/item flex items-start gap-2 rounded-[14px] px-3 py-2.5 transition',
                          isActive
                            ? 'bg-[var(--accent-soft)]'
                            : 'hover:bg-[var(--bg-muted)]',
                        )}
                      >
                        {isRenaming ? (
                          <div className="flex-1 min-w-0">
                            <SessionMenu
                              sessionId={session.id}
                              sessionTitle={session.title}
                              onRename={onRenameSession}
                              onDelete={onDeleteSession}
                              isRenaming={true}
                              onRenamingChange={onRenamingChange}
                            />
                          </div>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => handleSelect(session.id)}
                              className="flex-1 min-w-0 text-left"
                              role="menuitem"
                            >
                              <div className="flex items-center gap-2">
                                <span
                                  className={clsx(
                                    'h-1.5 w-1.5 shrink-0 rounded-full',
                                    isActive
                                      ? 'bg-[var(--accent)]'
                                      : 'bg-transparent',
                                  )}
                                  aria-hidden="true"
                                />
                                <p
                                  className={clsx(
                                    'truncate text-sm font-medium',
                                    isActive
                                      ? 'text-[var(--accent)]'
                                      : 'text-[var(--ink)]',
                                  )}
                                >
                                  {session.title}
                                </p>
                              </div>
                              <p className="mt-1 line-clamp-1 pl-3.5 text-xs leading-5 text-[var(--ink-muted)]">
                                {session.preview}
                              </p>
                            </button>
                            <div className="flex shrink-0 items-center gap-1">
                              <span className="hidden text-[11px] text-[var(--ink-muted)] sm:inline">
                                {formatSidebarTimestamp(session.updatedAt)}
                              </span>
                              <SessionMenu
                                sessionId={session.id}
                                sessionTitle={session.title}
                                onRename={onRenameSession}
                                onDelete={onDeleteSession}
                                isRenaming={false}
                                onRenamingChange={onRenamingChange}
                              />
                            </div>
                          </>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          {/* Footer: navigate to all reports + privacy controls */}
          <div className="border-t border-[var(--border)] bg-[var(--bg-muted)]/50 px-2 py-2">
            <button
              type="button"
              onClick={handleNavigateAll}
              className="flex w-full items-center justify-between rounded-[12px] px-3 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:bg-white hover:text-[var(--ink)]"
              role="menuitem"
            >
              <span>
                {hasMore
                  ? `查看全部 ${sessions.length} 个报告`
                  : '查看全部报告'}
              </span>
              <ArrowRightIcon />
            </button>

            {!user && (
              <div className="mt-1 rounded-[12px] px-3 py-2">
                <label className="flex items-center gap-2 text-xs text-[var(--ink-soft)]">
                  <input
                    type="checkbox"
                    checked={persistenceEnabled}
                    onChange={onTogglePersistence}
                    className="h-3.5 w-3.5 rounded border-[var(--border)]"
                  />
                  <span>在此设备上保存历史记录</span>
                </label>
                {!persistenceEnabled && (
                  <p className="mt-1 text-[11px] leading-4 text-[var(--ink-muted)]">
                    刷新后将清除所有对话
                  </p>
                )}
              </div>
            )}

            <button
              type="button"
              onClick={handleClearAll}
              className="mt-1 flex w-full items-center rounded-[12px] px-3 py-1.5 text-xs text-[var(--ink-muted)] transition hover:bg-white hover:text-[var(--danger)]"
              role="menuitem"
            >
              清除所有历史记录
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
