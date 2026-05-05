import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import QCWarning from '@/components/QCWarning'
import type { PerLeadQC } from '@/types/chat'

const mockPerLeadQC: PerLeadQC[] = [
  { lead_index: 0, quality: 'good', flatness: 0.1, coverage: 0.95 },
  { lead_index: 1, quality: 'warn', flatness: 0.3, coverage: 0.75 },
  { lead_index: 2, quality: 'poor', flatness: 0.5, coverage: 0.55 },
  { lead_index: 3, quality: 'fail', flatness: 0.6, coverage: 0.45 },
]

describe('QCWarning', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('quality_warning display', () => {
    it('displays quality_warning string when present', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Signal quality is marginal']}
        />
      )

      expect(screen.getByText('Signal quality is marginal')).toBeInTheDocument()
    })

    it('displays multiple pipeline warnings', () => {
      const warnings = ['Warning 1', 'Warning 2', 'Warning 3']
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={warnings}
        />
      )

      warnings.forEach(warning => {
        expect(screen.getByText(warning)).toBeInTheDocument()
      })
    })

    it('displays warning without pipeline_warnings', () => {
      render(<QCWarning quality_warning="warn" />)

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })
  })

  describe('severity level styles', () => {
    it('renders minimal UI when quality is good/pass', () => {
      const { container } = render(
        <QCWarning
          quality_warning="pass"
          pipeline_warnings={[]}
        />
      )

      expect(container.firstChild).toBeNull()
    })

    it('renders null when quality_warning is undefined', () => {
      const { container } = render(<QCWarning />)

      expect(container.firstChild).toBeNull()
    })

    it('renders null when quality_warning is null', () => {
      const { container } = render(<QCWarning quality_warning={null} />)

      expect(container.firstChild).toBeNull()
    })

    it('still renders pipeline warnings when quality_warning is pass', () => {
      render(
        <QCWarning
          quality_warning="pass"
          pipeline_warnings={['Collapsed signal detected']}
        />
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
      expect(screen.getByText('Collapsed signal detected')).toBeInTheDocument()
    })

    it('applies yellow warning styles for "warn" severity', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
        />
      )

      const alert = screen.getByRole('alert')
      expect(alert).toHaveClass('border-amber-200', 'bg-amber-50', 'text-amber-800')
    })

    it('applies red error styles for "fail" severity', () => {
      render(
        <QCWarning
          quality_warning="fail"
          pipeline_warnings={['Quality failed']}
        />
      )

      const alert = screen.getByRole('alert')
      expect(alert).toHaveClass('border-red-200', 'bg-red-50', 'text-red-800')
    })

    it('displays correct badge label for "warn" severity', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
        />
      )

      expect(screen.getByText('需复查')).toBeInTheDocument()
    })

    it('displays correct badge label for "fail" severity', () => {
      render(
        <QCWarning
          quality_warning="fail"
          pipeline_warnings={['Quality failed']}
        />
      )

      expect(screen.getByText('低可靠性')).toBeInTheDocument()
    })
  })

  describe('per-lead QC details expand/collapse', () => {
    it('does not show per-lead details by default', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      expect(screen.queryByText('导联 0')).not.toBeInTheDocument()
      expect(screen.queryByText('导联 1')).not.toBeInTheDocument()
      expect(screen.queryByText('导联 2')).not.toBeInTheDocument()
      expect(screen.queryByText('导联 3')).not.toBeInTheDocument()
    })

    it('shows expand button when per_lead_qc is provided', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      expect(screen.getByText('查看详情')).toBeInTheDocument()
    })

    it('does not show expand button when per_lead_qc is empty', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={[]}
        />
      )

      expect(screen.queryByText('查看详情')).not.toBeInTheDocument()
    })

    it('does not show expand button when per_lead_qc is undefined', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
        />
      )

      expect(screen.queryByText('查看详情')).not.toBeInTheDocument()
    })

    it('expands to show per-lead details when clicked', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      const expandButton = screen.getByText('查看详情')
      fireEvent.click(expandButton)

      expect(screen.getByText('导联 0')).toBeInTheDocument()
      expect(screen.getByText('导联 1')).toBeInTheDocument()
      expect(screen.getByText('导联 2')).toBeInTheDocument()
      expect(screen.getByText('导联 3')).toBeInTheDocument()
    })

    it('displays lead quality badges with correct styles', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))

      const lead0 = screen.getByText('导联 0').closest('[data-lead-index]')
      const lead1 = screen.getByText('导联 1').closest('[data-lead-index]')
      const lead2 = screen.getByText('导联 2').closest('[data-lead-index]')
      const lead3 = screen.getByText('导联 3').closest('[data-lead-index]')

      expect(lead0).toHaveAttribute('data-quality', 'good')
      expect(lead1).toHaveAttribute('data-quality', 'warn')
      expect(lead2).toHaveAttribute('data-quality', 'poor')
      expect(lead3).toHaveAttribute('data-quality', 'fail')
    })

    it('applies orange styles for "poor" lead quality', () => {
      const poorLeadQC: PerLeadQC[] = [
        { lead_index: 0, quality: 'poor', flatness: 0.5, coverage: 0.55 },
      ]

      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={poorLeadQC}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))

      const lead0 = screen.getByText('导联 0').closest('[data-lead-index]')
      expect(lead0).toHaveClass('bg-orange-100', 'text-orange-800', 'border-orange-200')
    })

    it('displays coverage and flatness metrics for each lead', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))

      // Use function matcher since text may be split across elements
      expect(screen.getByText((content) => content.includes('95') && content.includes('%'))).toBeInTheDocument()
      expect(screen.getByText((content) => content.includes('75') && content.includes('%'))).toBeInTheDocument()
      expect(screen.getByText((content) => content.includes('45') && content.includes('%'))).toBeInTheDocument()
    })

    it('collapses details when clicking collapse button', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))
      expect(screen.getByText('导联 0')).toBeInTheDocument()

      fireEvent.click(screen.getByText('隐藏详情'))
      expect(screen.queryByText('导联 0')).not.toBeInTheDocument()
    })

    it('toggles expand/collapse button text', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Quality warning']}
          per_lead_qc={mockPerLeadQC}
        />
      )

      expect(screen.getByText('查看详情')).toBeInTheDocument()

      fireEvent.click(screen.getByText('查看详情'))
      expect(screen.getByText('隐藏详情')).toBeInTheDocument()

      fireEvent.click(screen.getByText('隐藏详情'))
      expect(screen.getByText('查看详情')).toBeInTheDocument()
    })
  })

  describe('edge cases', () => {
    it('handles empty pipeline_warnings array', () => {
      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={[]}
        />
      )

      expect(screen.getByRole('alert')).toBeInTheDocument()
    })

    it('handles single lead QC data', () => {
      const singleLead: PerLeadQC[] = [
        { lead_index: 0, quality: 'good', flatness: 0.1, coverage: 0.95 }
      ]

      render(
        <QCWarning
          quality_warning="warn"
          pipeline_warnings={['Warning']}
          per_lead_qc={singleLead}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))
      expect(screen.getByText('导联 0')).toBeInTheDocument()
    })

    it('handles all leads failing', () => {
      const allFailing: PerLeadQC[] = Array.from({ length: 12 }, (_, i) => ({
        lead_index: i,
        quality: 'fail',
        flatness: 0.8,
        coverage: 0.3
      }))

      render(
        <QCWarning
          quality_warning="fail"
          pipeline_warnings={['All leads failed']}
          per_lead_qc={allFailing}
        />
      )

      fireEvent.click(screen.getByText('查看详情'))

      for (let i = 0; i < 12; i++) {
        expect(screen.getByText(`导联 ${i}`)).toBeInTheDocument()
      }
    })
  })
})
