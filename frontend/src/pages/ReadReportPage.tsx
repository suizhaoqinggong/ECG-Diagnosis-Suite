import { useRef } from 'react'
import type { NavigationDestination } from '@/types/navigation'

interface ReadReportPageProps {
  onNavigate: (dest: NavigationDestination) => void
}

function FileSearchIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
      <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
    </svg>
  )
}

function BrainIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2a3 3 0 00-3 3v1a3 3 0 003 3 3 3 0 003-3V5a3 3 0 00-3-3z" />
      <path d="M12 9v2M7.5 7.5l-.7-.7M16.5 7.5l.7-.7M12 16a2 2 0 100 4 2 2 0 000-4zM9 20a2 2 0 100 4 2 2 0 000-4zM15 20a2 2 0 100 4 2 2 0 000-4z" />
      <path d="M12 16v2M9 18h6" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-7 w-7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

function PrivacyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0110 0v4" />
    </svg>
  )
}

function DoctorIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M8 7h8M8 11h8M8 15h5M18 20l2-2-2-2M16 16l-2 2 2 2M3 21V5a2 2 0 012-2h14a2 2 0 012 2v16l-3-2-3 2-3-2-3 2-3-2-3 2z" />
    </svg>
  )
}

function ResultIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2l2 7h7l-5.5 4 2 7L12 16l-5.5 4 2-7L3 9h7z" />
    </svg>
  )
}

function AlertIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18l6-6-6-6" />
    </svg>
  )
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12" />
    </svg>
  )
}

export default function ReadReportPage({ onNavigate }: ReadReportPageProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handlePrimaryCTA = () => {
    fileInputRef.current?.click()
  }

  const handleFileSelected = () => {
    onNavigate('upload-ecg')
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 md:px-8 md:py-16">
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.dat,.hea,image/*,application/pdf"
        className="hidden"
        onChange={handleFileSelected}
      />

      {/* Hero Section */}
      <section className="text-center space-y-6 pb-12 md:pb-16">
        <h1 className="reading-copy text-4xl leading-tight tracking-tight text-[var(--ink)] md:text-5xl lg:text-[3.5rem]">
          读懂你的检查报告
        </h1>
        <p className="reading-copy mx-auto max-w-2xl text-lg leading-8 text-[var(--ink-soft)] md:text-xl md:leading-9">
          上传体检报告、化验单或心电图，智能解读各项指标和医学术语，帮你更好理解自己的健康状况。
        </p>

        <div className="flex flex-col items-center gap-4 pt-4 sm:flex-row sm:justify-center">
          <button
            type="button"
            onClick={handlePrimaryCTA}
            className="inline-flex items-center gap-2 rounded-full bg-[#2f2b26] px-8 py-4 text-base font-medium text-white shadow-[0_18px_40px_rgba(84,69,53,0.18)] transition hover:bg-[#1f1c18] hover:shadow-[0_22px_48px_rgba(84,69,53,0.24)]"
          >
            <UploadIcon />
            上传检查报告
          </button>
          <button
            type="button"
            onClick={() => onNavigate('upload-ecg')}
            className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--surface)] px-8 py-4 text-base font-medium text-[var(--ink-soft)] transition hover:border-[var(--border-strong)] hover:text-[var(--ink)] hover:bg-white/80"
          >
            上传 ECG / 健康资料
            <ChevronRightIcon />
          </button>
        </div>

        <p className="text-sm text-[var(--ink-muted)]">
          支持 PDF、PNG、JPG 格式的检查报告和化验单
        </p>
      </section>

      {/* Capability Cards */}
      <section className="grid gap-6 pb-12 md:grid-cols-3 md:pb-16">
        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_14px_36px_rgba(84,69,53,0.06)] md:p-7">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            <FileSearchIcon />
          </div>
          <h3 className="reading-copy text-xl font-medium text-[var(--ink)]">
            能看懂哪些报告
          </h3>
          <p className="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
            支持解读常规体检报告、血液生化检查、心电图报告、影像检查结论等常见检查单。特别擅长心血管相关指标的分析和解释。
          </p>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-[var(--ink-muted)]">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              心电图 (ECG) 解读与风险评估
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              血脂、血糖、肝肾功能等生化指标
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              体检报告综合分析与健康建议
            </li>
          </ul>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_14px_36px_rgba(84,69,53,0.06)] md:p-7">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            <BrainIcon />
          </div>
          <h3 className="reading-copy text-xl font-medium text-[var(--ink)]">
            怎么帮到你
          </h3>
          <p className="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
            用通俗易懂的语言解释专业的医学术语和检验数值，标注异常指标并说明临床意义，帮助你做好就医准备。
          </p>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-[var(--ink-muted)]">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              标注异常指标并解释其含义
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              提供后续检查和就诊建议
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              整理关键发现，方便与医生沟通
            </li>
          </ul>
        </div>

        <div className="rounded-[28px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 shadow-[0_14px_36px_rgba(84,69,53,0.06)] md:p-7">
          <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
            <ShieldIcon />
          </div>
          <h3 className="reading-copy text-xl font-medium text-[var(--ink)]">
            不能替代医生
          </h3>
          <p className="mt-3 text-sm leading-7 text-[var(--ink-soft)]">
            AI 解读仅供健康参考和教育目的，不能替代专业医疗诊断。最终的诊断和治疗方案需要由执业医师根据完整的临床资料做出。
          </p>
          <ul className="mt-4 space-y-2 text-sm leading-6 text-[var(--ink-muted)]">
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              不能替代面对面的医生诊疗
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              解读仅供参考，可能不完整
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-0.5 text-[var(--accent)]">-</span>
              有不适症状请及时就医
            </li>
          </ul>
        </div>
      </section>

      {/* Privacy & Trust Section */}
      <section className="rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[0_14px_36px_rgba(84,69,53,0.04)] md:p-8">
        <h2 className="reading-copy text-2xl font-medium tracking-tight text-[var(--ink)] md:text-3xl">
          数据安全与使用须知
        </h2>
        <p className="mt-4 text-sm leading-7 text-[var(--ink-soft)]">
          我们重视你的隐私和数据安全。请在使用前了解以下信息。
        </p>

        <div className="mt-8 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div className="flex gap-4">
            <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
              <PrivacyIcon />
            </div>
            <div>
              <h4 className="text-sm font-medium text-[var(--ink)]">数据如何使用</h4>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                你上传的报告仅用于生成分析结果。未登录用户的数据仅保存在本地浏览器中，不会上传到服务器长期存储。
              </p>
            </div>
          </div>

          <div className="flex gap-4">
            <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
              <ResultIcon />
            </div>
            <div>
              <h4 className="text-sm font-medium text-[var(--ink)]">结果仅供参考</h4>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                AI 分析结果仅供健康教育和参考，不能作为诊断、治疗或用药的依据。请结合临床医生的专业判断。
              </p>
            </div>
          </div>

          <div className="flex gap-4 md:col-span-2 lg:col-span-1">
            <div className="mt-0.5 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-[var(--accent-soft)] text-[var(--accent)]">
              <AlertIcon />
            </div>
            <div>
              <h4 className="text-sm font-medium text-[var(--ink)]">何时需要就医</h4>
              <p className="mt-2 text-sm leading-6 text-[var(--ink-muted)]">
                如果你有胸痛、心悸、呼吸困难、晕厥等急性症状，或报告中出现紧急提示，请立即就医，不要等待 AI 分析结果。
              </p>
            </div>
          </div>
        </div>

        <div className="mt-8 flex items-start gap-3 rounded-[18px] border border-[var(--border)] bg-[var(--accent-soft)]/50 p-4">
          <div className="mt-0.5 flex-shrink-0 text-[var(--accent)]">
            <DoctorIcon />
          </div>
          <p className="text-sm leading-6 text-[var(--ink-soft)]">
            <strong className="text-[var(--ink)]">温馨提示：</strong>
            本平台为 AI 辅助健康信息解读工具，不属于医疗器械。所有分析结果仅为教育目的，不应被视为医疗建议。如有健康问题，请咨询正规医疗机构。
          </p>
        </div>
      </section>
    </div>
  )
}
