import { render, screen } from '@testing-library/react'

import ConversationMessage from '@/components/ConversationMessage'

it('shows pending health-report processing state', () => {
  render(
    <ConversationMessage
      message={{
        id: 'msg-1',
        role: 'assistant',
        type: 'health_report',
        content: 'Analyzing...',
        createdAt: '2026-04-29T00:00:00Z',
        status: 'pending',
      }}
      submissionPhase="processing"
    />,
  )

  expect(screen.getByText(/AI 正在分析健康数据/i)).toBeInTheDocument()
})
