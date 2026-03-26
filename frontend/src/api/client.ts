import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
)

export default apiClient
