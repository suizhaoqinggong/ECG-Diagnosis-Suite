import { describe, expect, it } from 'vitest'
import {
  createInitialState,
  detectCategory,
  workspaceReducer,
} from '@/controllers/workspaceReducer'

describe('health attachments', () => {
  it('classifies pdfs as report_pdf', () => {
    const file = new File(['x'], 'report.pdf', { type: 'application/pdf' })
    expect(detectCategory(file)).toBe('report_pdf')
  })

  it('classifies ecg keyword images as ecg_image', () => {
    const file = new File(['x'], 'ecg-lead.png', { type: 'image/png' })
    expect(detectCategory(file)).toBe('ecg_image')
  })

  it('accepts a mixed report image plus matched signal pair', () => {
    const state = createInitialState()
    const next = workspaceReducer(state, {
      type: 'ADD_FILES',
      files: [
        new File(['image'], 'bloodwork.png', { type: 'image/png' }),
        new File(['dat'], 'study.dat', { type: 'application/octet-stream' }),
        new File(['hea'], 'study.hea', { type: 'text/plain' }),
      ],
    })

    expect(next.composer.attachments).toHaveLength(3)
    expect(next.composer.validationErrors).toEqual([])
  })
})
