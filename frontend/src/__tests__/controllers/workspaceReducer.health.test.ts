import { describe, expect, it } from 'vitest'
import { detectCategory } from '@/controllers/workspaceReducer'

describe('health attachments', () => {
  it('classifies pdfs as report_pdf', () => {
    const file = new File(['x'], 'report.pdf', { type: 'application/pdf' })
    expect(detectCategory(file)).toBe('report_pdf')
  })
})
