import clsx from 'clsx'
import type { ChatSession } from '../types/chat'
import { useAuth } from '../auth/AuthProvider'
import { formatSidebarTimestamp } from '../utils'
import SessionMenu from './SessionMenu'

interface ConversationSidebarProps {
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
  isOpen: boolean
  onClose: () => void
}

export default function ConversationSidebar({
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
  isOpen,
  onClose,
}: ConversationSidebarProps) {
  const { user } = useAuth()
  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={clsx(
          'fixed inset-y-0 left-0 z-50 w-[320px] border-r border-[var(--border)] bg-[rgba(247,243,236,0.97)] transition-transform duration-300 lg:static lg:z-auto lg:flex lg:w-[320px] lg:translate-x-0 lg:bg-[rgba(247,243,236,0.82)]',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between gap-4 px-5 py-5 lg:px-6 lg:py-6">
            <div>
              <p className="text-[0.68rem] font-medium uppercase tracking-[0.28em] text-[var(--ink-muted)]">
                ECG Workspace
              </p>
              <h1 className="mt-2 text-lg font-semibold tracking-tight text-[var(--ink)]">
                Diagnosis Studio
              </h1>
            </div>
            <button
              type="button"
              onClick={onCreateSession}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-2 text-sm font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)]"
            >
              New chat
            </button>
          </div>

          <div className="soft-scrollbar flex-1 overflow-y-auto px-4 pb-5 lg:pb-6">
            <div className="flex flex-col gap-3">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  type="button"
                  onClick={() => {
                    onSelectSession(session.id)
                    onClose()
                  }}
                  className={clsx(
                    'rounded-[24px] border px-4 py-4 text-left transition',
                    session.id === activeSessionId
                      ? 'border-[var(--border-strong)] bg-[var(--surface-strong)] shadow-[0_16px_40px_rgba(84,69,53,0.08)]'
                      : 'border-transparent bg-transparent hover:border-[var(--border)] hover:bg-[rgba(255,252,247,0.65)]',
                  )}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      {renamingSessionId === session.id ? (
                        <SessionMenu
                          sessionId={session.id}
                          sessionTitle={session.title}
                          onRename={onRenameSession}
                          onDelete={onDeleteSession}
                          isRenaming={true}
                          onRenamingChange={onRenamingChange}
                        />
                      ) : (
                        <>
                          <p className="truncate text-sm font-semibold text-[var(--ink)]">
                            {session.title}
                          </p>
                          <p className="mt-2 overflow-hidden text-sm leading-6 text-[var(--ink-soft)]">
                            {session.preview}
                          </p>
                        </>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-xs text-[var(--ink-muted)]">
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
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Privacy toggle & clear history */}
          <div className="border-t border-[var(--border)] px-5 py-5 lg:px-6">
            {!user && (
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={persistenceEnabled}
                  onChange={onTogglePersistence}
                  className="h-4 w-4 rounded border-[var(--border)]"
                />
                <span className="text-sm text-[var(--ink-soft)]">
                  Save history on this device
                </span>
              </label>
            )}

            {!user && !persistenceEnabled && (
              <p className="mt-2 text-xs text-[var(--ink-muted)]">
                History will not be saved. Refreshing the page will clear sessions.
              </p>
            )}

            {user && (
              <p className="text-xs text-[var(--ink-muted)]">
                Conversations are saved to your account.
              </p>
            )}

            <button
              type="button"
              onClick={() => {
                const message = user
                  ? 'This will delete all conversations from the server. This cannot be undone.'
                  : 'Clear all history? This cannot be undone.'
                if (confirm(message)) {
                  onClearAllSessions()
                }
              }}
              className="mt-4 w-full rounded-full border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-white/60 hover:text-[var(--ink)]"
            >
              Clear all history
            </button>
          </div>
        </div>
      </aside>
    </>
  )
}
