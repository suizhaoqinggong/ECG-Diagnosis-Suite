import { useWorkspace } from '../controllers/WorkspaceProvider'
import ResultPage from './ResultPage'
import type { ConversationMessage } from '../types/chat'

function findLatestResult(messages: ConversationMessage[]) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const msg = messages[i]
    if (msg.result && (msg.type === 'health_report' || msg.type === 'diagnosis')) {
      return msg
    }
  }
  return null
}

export default function ResultPageRoute() {
  const { state } = useWorkspace()
  const sessions = state.persisted.sessions
  const activeId = state.persisted.activeSessionId
  const activeSession = sessions.find(s => s.id === activeId)

  if (!activeSession) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-8">
        <p className="text-lg text-[var(--ink-muted)]">暂无分析结果</p>
      </div>
    )
  }

  const resultMessage = findLatestResult(activeSession.messages)

  if (!resultMessage?.result) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center p-8">
        <div className="max-w-md text-center space-y-4">
          <p className="text-lg font-medium text-[var(--ink)]">暂无分析结果</p>
          <p className="text-sm text-[var(--ink-muted)]">
            完成一次健康分析后，可在此查看详细结果。
          </p>
        </div>
      </div>
    )
  }

  return (
    <ResultPage
      result={resultMessage.result}
      timestamp={resultMessage.createdAt}
    />
  )
}
