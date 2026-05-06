import { useState } from 'react'
import wechatQR from '../assets/wechat-qr.jpg'
import alipayQR from '../assets/alipay-qr.jpg'

interface DonationModalProps {
  isOpen: boolean
  onClose: () => void
}

type Tab = 'wechat' | 'alipay'

const QR_IMAGES: Record<Tab, string> = {
  wechat: wechatQR,
  alipay: alipayQR,
}

const TABS: { key: Tab; label: string }[] = [
  { key: 'wechat', label: '微信打赏' },
  { key: 'alipay', label: '支付宝打赏' },
]

export default function DonationModal({ isOpen, onClose }: DonationModalProps) {
  const [tab, setTab] = useState<Tab>('wechat')

  if (!isOpen) return null

  const handleCloseClick = () => {
    onClose()
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end justify-center bg-black/50 backdrop-blur-sm lg:items-center"
      onClick={handleCloseClick}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="donation-modal-title"
        className="w-full max-w-md rounded-t-[24px] border border-[var(--border)] bg-[var(--surface-strong)] p-6 pb-8 lg:rounded-[24px] lg:p-8 shadow-[0_24px_48px_rgba(0,0,0,0.12)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h3
          id="donation-modal-title"
          className="text-lg font-semibold text-[var(--ink)]"
        >
          支持我们
        </h3>
        <p className="mt-2 text-sm leading-6 text-[var(--ink-soft)]">
          如果您觉得这个工具对您有帮助，欢迎扫码打赏，支持我们持续改进。
        </p>

        <div className="mt-6 mb-5 flex gap-6">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              className={`pb-2 text-sm font-medium transition ${
                tab === t.key
                  ? 'border-b-2 border-[var(--accent)] text-[var(--ink)]'
                  : 'text-[var(--ink-muted)]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col items-center rounded-[20px] border border-[var(--border)] bg-[var(--bg-muted)]/40 py-7 px-4">
          <div className="rounded-[16px] bg-white p-3 shadow-sm">
            <img
              src={QR_IMAGES[tab]}
              alt={tab === 'wechat' ? '微信收款码' : '支付宝收款码'}
              className="h-48 w-48 object-contain"
            />
          </div>
          <p className="mt-4 text-xs text-[var(--ink-muted)]">
            {tab === 'wechat' ? '请使用微信扫描二维码' : '请使用支付宝扫描二维码'}
          </p>
        </div>

        <p className="mt-5 text-center text-xs text-[var(--ink-muted)] leading-relaxed">
          感谢您的支持！每一份心意都是我们前进的动力 ❤️
        </p>

        <button
          type="button"
          onClick={handleCloseClick}
          className="mt-5 w-full rounded-full border border-[var(--border)] px-4 py-3 text-sm font-medium text-[var(--ink-muted)] transition hover:bg-[var(--bg-muted)] hover:text-[var(--ink)]"
        >
          关闭
        </button>
      </div>
    </div>
  )
}
