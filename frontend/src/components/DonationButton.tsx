import { useState } from 'react'
import DonationModal from './DonationModal'

function HeartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="h-5 w-5" aria-hidden="true">
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" />
    </svg>
  )
}

export default function DonationButton() {
  const [isModalOpen, setModalOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        aria-label="支持我们"
        title="支持我们"
        className="fixed bottom-24 right-6 z-50 flex h-12 w-12 items-center justify-center rounded-full bg-[var(--accent)] text-white shadow-lg transition hover:scale-110 hover:shadow-xl active:scale-95 lg:bottom-8"
        style={{
          boxShadow: '0 4px 16px rgba(45, 125, 143, 0.35)',
        }}
      >
        <HeartIcon />
      </button>

      <DonationModal
        isOpen={isModalOpen}
        onClose={() => setModalOpen(false)}
      />
    </>
  )
}
