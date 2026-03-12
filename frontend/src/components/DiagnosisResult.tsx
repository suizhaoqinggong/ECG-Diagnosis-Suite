interface DiagnosisResultProps {
  result: any
  onReset: () => void
}

export default function DiagnosisResult({ result, onReset }: DiagnosisResultProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-8 space-y-6">
      {/* 标题 */}
      <div className="text-center">
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          诊断结果
        </h2>
        <p className="text-gray-500 dark:text-gray-400 mt-2">
          Diagnosis Result
        </p>
      </div>

      {/* 主要结果 */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 dark:from-gray-700 dark:to-gray-700 rounded-xl p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">诊断结果</p>
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400 mt-1">
              {result.prediction}
            </p>
            {result.icd_code && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                ICD编码: {result.icd_code}
              </p>
            )}
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-600 dark:text-gray-400">置信度</p>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-1">
              {(result.confidence * 100).toFixed(1)}%
            </p>
          </div>
        </div>
      </div>

      {/* 详细信息 */}
      {result.description && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            症状说明
          </h3>
          <p className="text-gray-600 dark:text-gray-300 leading-relaxed">
            {result.description}
          </p>
        </div>
      )}

      {/* 健康建议 */}
      {result.recommendations && result.recommendations.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
            健康建议
          </h3>
          <ul className="space-y-2">
            {result.recommendations.map((rec: string, index: number) => (
              <li key={index} className="flex items-start">
                <span className="text-green-500 mr-2">✓</span>
                <span className="text-gray-600 dark:text-gray-300">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 操作按钮 */}
      <div className="flex gap-4 pt-4">
        <button
          onClick={onReset}
          className="flex-1 px-6 py-3 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          重新诊断
        </button>
        <button className="flex-1 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors">
          导出PDF报告
        </button>
      </div>

      {/* 免责声明 */}
      <div className="text-xs text-center text-gray-400 dark:text-gray-500 pt-4 border-t border-gray-200 dark:border-gray-700">
        <p>⚠️ 本结果仅供参考���不作为临床诊断依据</p>
        <p className="mt-1">如有疑虑，请及时就医咨询专业医生</p>
      </div>
    </div>
  )
}
