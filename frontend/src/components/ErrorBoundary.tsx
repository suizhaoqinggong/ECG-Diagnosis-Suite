import { Component, type ReactNode } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  message: string
}

export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, message: '' }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message || '未知错误' }
  }

  handleReset = () => {
    this.setState({ hasError: false, message: '' })
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center px-6">
          <div className="max-w-md space-y-6 text-center">
            <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
              Something went wrong
            </p>
            <p className="reading-copy text-2xl leading-tight tracking-tight text-[var(--ink)]">
              页面遇到了意外错误
            </p>
            <p className="text-sm leading-7 text-[var(--ink-soft)]">
              {this.state.message}
            </p>
            <button
              onClick={this.handleReset}
              className="rounded-full border border-[var(--border)] bg-[var(--surface-strong)] px-6 py-2.5 text-sm font-medium text-[var(--ink)] transition-colors hover:bg-[var(--accent-soft)]"
            >
              重试
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
