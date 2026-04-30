import type { HealthRiskLevel, ClinicalFindingView } from '@/types/health'

const RISK_LABELS: Record<HealthRiskLevel, string> = {
  low: '建议常规随访',
  medium: '建议近期复诊',
  high: '建议尽快就医',
  urgent: '建议立即就医',
}

const RISK_REASONS: Record<HealthRiskLevel, string> = {
  low: '本次分析未发现明显高风险指标，建议按常规计划定期随访。',
  medium: '本次分析发现一些值得关注的指标，建议在近期安排复诊。',
  high: '本次分析发现较明显的异常指标，建议尽快咨询医生进行评估。',
  urgent: '本次分析发现需要紧急关注的指标，建议立即就医，不要延误。',
}

export function mapRiskToPatientLabel(risk: HealthRiskLevel): string {
  return RISK_LABELS[risk] || risk
}

export function mapRiskToReason(risk: HealthRiskLevel): string {
  return RISK_REASONS[risk] || ''
}

const TERM_EXPLANATIONS: Record<string, string> = {
  '心肌梗死': '心脏血管阻塞导致心肌缺血坏死，俗称"心脏病发作"',
  'ST-T改变': '心电图ST段和T波的形态变化，可能提示心肌供血异常',
  '传导障碍': '心脏电信号传导出现延迟或阻断，可能影响心跳节律',
  '心室肥大': '心室肌肉增厚，通常与长期高血压或心脏负荷过重有关',
  '窦性心律': '正常的心脏节律，由窦房结正常发放电信号',
  '房颤': '心房快速不规则收缩，可能导致心悸和血栓风险',
  'QT间期': '心电图上表示心室除极和复极的时间，延长或缩短都可能异常',
  'PR间期': '心电图上从心房激动到心室激动的时间',
  'QRS波': '心电图上代表心室除极的波形',
  'T波': '心电图上代表心室复极的波形',
  'ST段': 'QRS波结束到T波开始的段落，抬高或压低都可能异常',
}

export function explainMedicalTerm(term: string): string {
  // Check exact match
  if (TERM_EXPLANATIONS[term]) {
    return TERM_EXPLANATIONS[term]
  }
  // Check if any key is contained in the term
  for (const [key, explanation] of Object.entries(TERM_EXPLANATIONS)) {
    if (term.includes(key)) {
      return `${key}：${explanation}`
    }
  }
  return ''
}

export function generateDoctorQuestions(findings: ClinicalFindingView[]): string[] {
  const questions: string[] = []

  if (findings.length === 0) {
    questions.push('这次检查结果整体情况如何，需要特别关注哪些方面？')
    return questions
  }

  const hasHighSeverity = findings.some(f => f.severity === 'high' || f.severity === 'urgent')

  if (hasHighSeverity) {
    questions.push('根据这次检查结果，我需要尽快进行哪些进一步检查？')
    questions.push('这些异常指标对我的长期健康有什么影响？')
  } else {
    questions.push('这次检查结果中，哪些指标需要我持续关注？')
  }

  const ecgFindings = findings.filter(f => f.sourceType === 'ecg_ai')
  if (ecgFindings.length > 0) {
    questions.push('心电图的这些发现对我的日常活动有什么限制吗？')
  }

  const nonEcgFindings = findings.filter(f => f.sourceType !== 'ecg_ai')
  if (nonEcgFindings.length > 0) {
    questions.push('其他检查指标与心电图结果之间有什么关系？')
  }

  questions.push('在日常生活中，我应该注意哪些症状变化？')
  questions.push('建议多久复查一次，复查时应该重点检查什么项目？')

  return questions.slice(0, 5)
}
