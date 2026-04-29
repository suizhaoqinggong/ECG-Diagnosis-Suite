import { render, screen } from '@testing-library/react'
import HealthReport from '@/components/HealthReport'

it('renders overall risk and next steps', () => {
  render(
    <HealthReport
      result={{
        jobId: 'job-1',
        status: 'completed',
        summary: '关注 LDL 与 ECG 结果',
        overallRisk: 'high',
        findings: [],
        nextSteps: ['尽快门诊复查'],
        limitations: ['仅基于上传资料解释'],
        disclaimer: '本结果仅供参考',
      }}
    />,
  )
  expect(screen.getByText(/high/)).toBeInTheDocument()
  expect(screen.getByText('尽快门诊复查')).toBeInTheDocument()
})
