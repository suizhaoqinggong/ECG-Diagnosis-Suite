import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatComposer from '@/components/ChatComposer'

const defaults = {
  draft: '',
  attachedFiles: [],
  isLoading: false,
  onDraftChange: vi.fn(),
  onAttachFiles: vi.fn(),
  onRemoveFile: vi.fn(),
  onSubmit: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

function pasteImage(imageType = 'image/png') {
  const onAttachFiles = vi.fn()
  render(<ChatComposer {...defaults} onAttachFiles={onAttachFiles} />)

  const textarea = screen.getByPlaceholderText(/attach health files/i)
  const imageFile = new File(['fake-image'], 'pasted.png', { type: imageType })

  const clipboardData = {
    items: [{ kind: 'file', type: imageType, getAsFile: () => imageFile }],
    types: ['Files'],
    getData: () => '',
  }

  const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
  Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
  fireEvent(textarea, pasteEvent)

  return { onAttachFiles, pasteEvent }
}

describe('ChatComposer – clipboard image paste', () => {
  it('calls onAttachFiles when an image is pasted', () => {
    const { onAttachFiles } = pasteImage()

    expect(onAttachFiles).toHaveBeenCalledTimes(1)
    const [files] = onAttachFiles.mock.calls[0]
    expect(files).toHaveLength(1)
    expect(files![0].type).toBe('image/png')
    expect(files![0].name).toMatch(/^clipboard-\d+\.png$/)
  })

  it('prevents default when image is pasted (avoid inserting as text)', () => {
    const { pasteEvent } = pasteImage()

    expect(pasteEvent.defaultPrevented).toBe(true)
  })

  it('does not call onAttachFiles when pasting plain text', () => {
    const onAttachFiles = vi.fn()
    render(<ChatComposer {...defaults} onAttachFiles={onAttachFiles} />)

    const textarea = screen.getByPlaceholderText(/attach health files/i)
    const clipboardData = {
      items: [],
      types: ['text/plain'],
      getData: (t: string) => (t === 'text/plain' ? 'hello' : ''),
    }

    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
    fireEvent(textarea, pasteEvent)

    expect(onAttachFiles).not.toHaveBeenCalled()
    expect(pasteEvent.defaultPrevented).toBe(false)
  })

  it('handles JPEG clipboard images', () => {
    const { onAttachFiles } = pasteImage('image/jpeg')

    const [files] = onAttachFiles.mock.calls[0]
    expect(files![0].type).toBe('image/jpeg')
    expect(files![0].name).toMatch(/^clipboard-\d+\.jpeg$/)
  })

  it('derives extension from MIME subtype for non-standard types', () => {
    const { onAttachFiles } = pasteImage('image/webp')

    const [files] = onAttachFiles.mock.calls[0]
    expect(files![0].type).toBe('image/webp')
    expect(files![0].name).toMatch(/^clipboard-\d+\.webp$/)
  })

  it('skips image items where getAsFile returns null without swallowing paste', () => {
    const onAttachFiles = vi.fn()
    render(<ChatComposer {...defaults} onAttachFiles={onAttachFiles} />)

    const textarea = screen.getByPlaceholderText(/attach health files/i)
    const clipboardData = {
      items: [{ kind: 'file', type: 'image/png', getAsFile: () => null }],
      types: ['Files'],
      getData: () => '',
    }

    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
    fireEvent(textarea, pasteEvent)

    expect(onAttachFiles).not.toHaveBeenCalled()
    expect(pasteEvent.defaultPrevented).toBe(false)
  })

  it('continues past broken items to find a valid image', () => {
    const onAttachFiles = vi.fn()
    render(<ChatComposer {...defaults} onAttachFiles={onAttachFiles} />)

    const textarea = screen.getByPlaceholderText(/attach health files/i)
    const validFile = new File(['valid-image'], 'ok.png', { type: 'image/png' })
    const clipboardData = {
      items: [
        { kind: 'file', type: 'image/png', getAsFile: () => null },
        { kind: 'file', type: 'image/png', getAsFile: () => validFile },
      ],
      types: ['Files'],
      getData: () => '',
    }

    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
    fireEvent(textarea, pasteEvent)

    expect(onAttachFiles).toHaveBeenCalledTimes(1)
    const [files] = onAttachFiles.mock.calls[0]
    expect(files![0].type).toBe('image/png')
    expect(files![0].name).toMatch(/^clipboard-\d+\.png$/)
    expect(pasteEvent.defaultPrevented).toBe(true)
  })
})
