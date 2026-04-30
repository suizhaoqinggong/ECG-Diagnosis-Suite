import { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import ErrorBoundary from './components/ErrorBoundary'
import HomePage from './pages/HomePage'
import { AuthProvider } from './auth/AuthProvider'
import type { NavigationDestination } from './types/navigation'

function App() {
  const [destination, setDestination] = useState<NavigationDestination>('read-report')

  return (
    <ErrorBoundary>
      <AuthProvider>
        <div className="min-h-screen bg-transparent text-[var(--ink)]">
          <HomePage destination={destination} onNavigate={setDestination} />
        </div>
        <Toaster
          position="top-center"
          toastOptions={{
            duration: 3200,
            style: {
              borderRadius: '18px',
              background: 'rgba(255, 252, 247, 0.96)',
              color: '#2e2a26',
              boxShadow: '0 18px 40px rgba(84, 69, 53, 0.12)',
            },
          }}
        />
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
