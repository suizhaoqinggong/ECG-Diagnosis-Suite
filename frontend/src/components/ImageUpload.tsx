import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'
import toast from 'react-hot-toast'

interface ImageUploadProps {
  onResult: (result: any) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export default function ImageUpload({ onResult, isLoading, setIsLoading }: ImageUploadProps) {
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    // 文件大小检查
    if (file.size > 10 * 1024 * 1024) {
      toast.error('文件大小不能超过10MB')
      return
    }

    // 文件类型检查
    if (!file.type.startsWith('image/')) {
      toast.error('请上传图片文件')
      return
    }

    setIsLoading(true)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post('/api/diagnose', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000,
      })

      onResult(response.data)
      toast.success('诊断完成！')
    } catch (error: any) {
      console.error('Upload error:', error)
      toast.error(error.response?.data?.detail || '上传失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }, [onResult, setIsLoading])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
    },
    maxFiles: 1,
    disabled: isLoading,
  })

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center cursor-pointer
          transition-all duration-200
          ${isDragActive
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-primary-400'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="space-y-4">
          <div className="text-6xl">💓</div>

          {isLoading ? (
            <div>
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
              <p className="text-lg font-medium text-gray-700 dark:text-gray-300 mt-4">
                AI分析中...
              </p>
            </div>
          ) : (
            <>
              <p className="text-xl font-semibold text-gray-700 dark:text-gray-300">
                {isDragActive ? '释放以上传文件' : '上传ECG心电图图片'}
              </p>
              <p className="text-gray-500 dark:text-gray-400">
                拖拽图片到此处，或点击选择文件
              </p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                支持 PNG, JPG, JPEG 格式，最大 10MB
              </p>
            </>
          )}
        </div>
      </div>

      <div className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
        <p>📱 支持手机拍照上传</p>
      </div>
    </div>
  )
}
