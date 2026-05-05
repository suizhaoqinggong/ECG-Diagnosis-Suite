import { useState, useRef, useEffect } from 'react'

interface SessionMenuProps {
  sessionId: string
  sessionTitle: string
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
  isRenaming: boolean
  onRenamingChange: (id: string | null) => void
}

export default function SessionMenu({
  sessionId,
  sessionTitle,
  onRename,
  onDelete,
  isRenaming,
  onRenamingChange,
}: SessionMenuProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [editTitle, setEditTitle] = useState(sessionTitle)
  const inputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isRenaming])

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleRenameSubmit = () => {
    if (editTitle.trim()) {
      onRename(sessionId, editTitle.trim())
    }
    onRenamingChange(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit()
    } else if (e.key === 'Escape') {
      setEditTitle(sessionTitle)
      onRenamingChange(null)
    }
  }

  if (isRenaming) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editTitle}
        onChange={(e) => setEditTitle(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleRenameSubmit}
        className="w-full rounded border border-[var(--border)] px-2 py-1 text-sm text-[var(--ink)]"
        aria-label="编辑对话标题"
      />
    )
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        onClick={() => setMenuOpen(!menuOpen)}
        className="rounded p-1 text-[var(--ink-muted)] hover:bg-white/60"
        aria-label="对话选项"
        aria-expanded={menuOpen}
      >
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
          <circle cx="12" cy="6" r="2" />
          <circle cx="12" cy="12" r="2" />
          <circle cx="12" cy="18" r="2" />
        </svg>
      </button>

      {menuOpen && (
        <div className="absolute right-0 top-full z-10 mt-1 w-32 rounded-lg border border-[var(--border)] bg-[var(--surface-strong)] py-1 shadow-lg">
          <button
            onClick={() => {
              onRenamingChange(sessionId)
              setMenuOpen(false)
            }}
            className="w-full px-4 py-2 text-left text-sm text-[var(--ink)] hover:bg-white/60"
          >
            重命名
          </button>
          <button
            onClick={() => {
              if (confirm('删除此对话？')) {
                onDelete(sessionId)
              }
              setMenuOpen(false)
            }}
            className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
          >
            删除
          </button>
        </div>
      )}
    </div>
  )
}
