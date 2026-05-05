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
  expect(screen.getByText('建议尽快就医')).toBeInTheDocument()
  expect(screen.getByText('尽快门诊复查')).toBeInTheDocument()
})

it('renders an ECG section when ECG analysis is present', () => {
  render(
    <HealthReport
      result={{
        jobId: 'job-2',
        status: 'completed',
        summary: '需要结合 ECG 结果继续判断。',
        overallRisk: 'medium',
        findings: [],
        nextSteps: ['两周后复查'],
        limitations: ['仅基于上传资料解释'],
        disclaimer: '本结果仅供参考',
        ecgResult: {
          prediction: '正常',
          confidence: 0.91,
          timestamp: '2026-04-29T00:00:00Z',
          disclaimer: '本结果仅供参考',
          report: {
            source: 'template',
            summary: 'ECG 未见急性异常',
            clinical_interpretation: '节律基本规则。',
            key_findings: [],
            recommendations: [],
            follow_up: [],
            limitations: [],
          },
        },
      }}
    />,
  )

  expect(screen.getByText('ECG 详细分析')).toBeInTheDocument()
  expect(screen.getByText('正常')).toBeInTheDocument()
  expect(screen.getByText('ECG 未见急性异常')).toBeInTheDocument()
})
