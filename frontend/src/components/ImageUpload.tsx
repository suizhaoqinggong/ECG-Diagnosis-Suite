import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import toast from 'react-hot-toast'
import { diagnosisApi, type DiagnosisResultData } from '../api'

interface ImageUploadProps {
  onResult: (result: DiagnosisResultData) => void
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
}

export default function ImageUpload({ onResult, isLoading, setIsLoading }: ImageUploadProps) {
  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return

    // 检查是否是图片上传（单文件）
    const imageFiles = acceptedFiles.filter(f => f.type.startsWith('image/'))
    if (imageFiles.length > 0) {
      // 处理图片上传
      const file = imageFiles[0]

      if (file.size > 10 * 1024 * 1024) {
        toast.error('文件大小不能超过10MB')
        return
      }

      await uploadFiles([file])
      return
    }

    // 检查是否是.dat/.hea文件上传
    const datFile = acceptedFiles.find(f => f.name.toLowerCase().endsWith('.dat'))
    const heaFile = acceptedFiles.find(f => f.name.toLowerCase().endsWith('.hea'))

    if (!datFile && !heaFile) {
      toast.error('请上传图片文件(.png, .jpg, .jpeg)或ECG数据文件(.dat + .hea)')
      return
    }

    // 如果只有.dat或只有.hea，提示用户
    if (datFile && !heaFile) {
      toast.error('请同时上传.dat和.hea文件')
      return
    }

    if (heaFile && !datFile) {
      toast.error('请同时上传.dat和.hea文件')
      return
    }

    // 检查文件名是否匹配
    const datName = datFile!.name.replace(/\.dat$/i, '')
    const heaName = heaFile!.name.replace(/\.hea$/i, '')

    if (datName !== heaName) {
      toast.error('.dat和.hea文件名必须相同')
      return
    }

    // 文件大小检查
    if (datFile!.size > 10 * 1024 * 1024 || heaFile!.size > 10 * 1024 * 1024) {
      toast.error('文件大小不能超过10MB')
      return
    }

    toast.loading('上传.dat和.hea文件中...', { duration: 2000 })
    await uploadFiles([datFile!, heaFile!])
  }, [onResult, setIsLoading])

  const uploadFiles = async (files: File[]) => {
    setIsLoading(true)

    try {
      const response = files.length === 1
        ? await diagnosisApi.diagnoseImage(files[0])
        : await diagnosisApi.diagnoseDatPair(files[0], files[1])

      onResult(response)
      toast.success('诊断完成！')
    } catch (error: any) {
      console.error('Upload error:', error)
      toast.error(error.response?.data?.detail || '上传失败，请重试')
    } finally {
      setIsLoading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/octet-stream': ['.dat', '.hea'],
      'text/plain': ['.hea'],
    },
    maxFiles: 2,
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
                {isDragActive ? '释放以上传文件' : '上传ECG心电图数据'}
              </p>
              <p className="text-gray-500 dark:text-gray-400">
                拖拽文件到此处，或点击选择文件
              </p>
              <div className="text-sm text-gray-400 dark:text-gray-500 space-y-1">
                <p>📸 图片格式: PNG, JPG, JPEG (单文件)</p>
                <p>📁 ECG数据: .dat + .hea (同时选择两个文件)</p>
                <p>📏 最大文件大小: 10MB</p>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400 space-y-1">
        <p>📱 支持手机拍照上传</p>
        <p>💡 .dat文件需同时上传对应的.hea文件</p>
        <p className="text-xs">提示: 在文件选择器中按住Ctrl/Cmd可多选</p>
      </div>
    </div>
  )
}
