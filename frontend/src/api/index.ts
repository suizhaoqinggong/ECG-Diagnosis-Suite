import apiClient from './client'

export interface PredictionProbability {
  class: string
  class_en?: string
  probability: number
}

export interface EnhancedDiagnosisReport {
  source: 'template' | 'llm'
  model?: string | null
  summary: string
  clinical_interpretation: string
  key_findings: string[]
  recommendations: string[]
  follow_up: string[]
  limitations: string[]
}

export interface DiagnosisResultData {
  prediction: string
  confidence: number
  severity?: string | null
  icd_code?: string | null
  description?: string | null
  recommendations?: string[] | null
  timestamp: string
  disclaimer: string
  all_probabilities?: Record<string, number> | null
  top3_predictions?: PredictionProbability[] | null
  report: EnhancedDiagnosisReport
}

async function postFormData<T>(
  url: string,
  formData: FormData,
  onUploadProgress?: (progress: number) => void,
  signal?: AbortSignal,
): Promise<T> {
  const config: Parameters<typeof apiClient.post>[2] = {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }

  if (onUploadProgress) {
    config.onUploadProgress = (event: { loaded: number; total?: number }) => {
      if (event.total) {
        onUploadProgress(Math.round((event.loaded / event.total) * 100))
      }
    }
  }

  if (signal) {
    config.signal = signal
  }

  const response = await apiClient.post<T>(url, formData, config)
  return response.data
}

export const diagnosisApi = {
  diagnoseImage(
    file: File,
    onUploadProgress?: (progress: number) => void,
    signal?: AbortSignal,
  ) {
    const formData = new FormData()
    formData.append('file', file)
    return postFormData<DiagnosisResultData>('/api/diagnose', formData, onUploadProgress, signal)
  },

  diagnoseDatPair(
    datFile: File,
    heaFile: File,
    onUploadProgress?: (progress: number) => void,
    signal?: AbortSignal,
  ) {
    const formData = new FormData()
    formData.append('files', datFile)
    formData.append('files', heaFile)
    return postFormData<DiagnosisResultData>('/api/diagnose-dat', formData, onUploadProgress, signal)
  },
}

export { apiClient }
