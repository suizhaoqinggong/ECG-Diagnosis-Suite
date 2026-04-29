import { describe, expect, it } from 'vitest'
import type { HealthAnalysisResult } from '@/types/health'
import type { ConversationMessage } from '@/types/chat'

describe('health contracts', () => {
  it('supports health-report messages', () => {
    const message: ConversationMessage = {
      id: '1',
      role: 'assistant',
      type: 'health_report',
      content: 'done',
      createdAt: '2026-04-29T00:00:00Z',
    }
    expect(message.type).toBe('health_report')
  })

  it('defines unified health result shape', () => {
    const result: HealthAnalysisResult = {
      jobId: 'job-1',
      status: 'completed',
      summary: '需要先复查血脂并关注心电图结果。',
      overallRisk: 'medium',
      findings: [],
      nextSteps: ['两周内复查血脂'],
      limitations: ['仅基于上传资料解释'],
      disclaimer: '本结果仅供参考',
    }
    expect(result.overallRisk).toBe('medium')
  })
})
