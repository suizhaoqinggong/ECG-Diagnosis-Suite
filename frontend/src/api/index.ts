import apiClient from './client'

export interface PredictionProbability {
  class: string
  class_en?: string
  probability: number
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
}

export interface DiagnosisHistoryResponse {
  items: Array<{
    id: number
    image_path: string
    prediction: string
    confidence: number
    severity?: string | null
    icd_code?: string | null
    description?: string | null
    recommendations?: string[] | null
    created_at?: string | null
    updated_at?: string | null
  }>
  count: number
}

async function postFormData<T>(url: string, formData: FormData): Promise<T> {
  const response = await apiClient.post<T>(url, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

export const diagnosisApi = {
  diagnoseImage(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return postFormData<DiagnosisResultData>('/api/diagnose', formData)
  },

  diagnoseDatPair(datFile: File, heaFile: File) {
    const formData = new FormData()
    formData.append('files', datFile)
    formData.append('files', heaFile)
    return postFormData<DiagnosisResultData>('/api/diagnose-dat', formData)
  },

  async getHistory(limit = 20) {
    const response = await apiClient.get<DiagnosisHistoryResponse>('/api/history', {
      params: { limit },
    })
    return response.data
  },
}

export { apiClient }
