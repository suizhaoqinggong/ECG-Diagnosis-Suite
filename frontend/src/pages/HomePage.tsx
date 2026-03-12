import { useState } from 'react'
import ImageUpload from '../components/ImageUpload'
import DiagnosisResult from '../components/DiagnosisResult'

export default function HomePage() {
  const [result, setResult] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <header className="text-center mb-12">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-4">
          ECG Diagnosis Suite
        </h1>
        <p className="text-lg text-gray-600 dark:text-gray-400">
          智能心电诊断系统 - AI-Powered ECG Analysis
        </p>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto">
        {!result ? (
          <ImageUpload
            onResult={setResult}
            isLoading={isLoading}
            setIsLoading={setIsLoading}
          />
        ) : (
          <DiagnosisResult
            result={result}
            onReset={() => setResult(null)}
          />
        )}
      </div>

      {/* Footer */}
      <footer className="text-center mt-16 text-gray-500 dark:text-gray-400 text-sm">
        <p>本系统仅供学术研究和教育目的，不用于临床诊断</p>
        <p className="mt-2">For academic research and educational purposes only</p>
      </footer>
    </div>
  )
}
