import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ChatComposer from '@/components/ChatComposer'

const defaults = {
  draft: '',
  attachedFiles: [],
  isLoading: false,
  onDraftChange: vi.fn(),
  onImageFilesSelected: vi.fn(),
  onDataFilesSelected: vi.fn(),
  onRemoveFile: vi.fn(),
  onSubmit: vi.fn(),
}

beforeEach(() => {
  vi.clearAllMocks()
})

function pasteImage(imageType = 'image/png') {
  const onImageFilesSelected = vi.fn()
  render(<ChatComposer {...defaults} onImageFilesSelected={onImageFilesSelected} />)

  const textarea = screen.getByPlaceholderText(/attach files/i)
  const imageFile = new File(['fake-image'], 'pasted.png', { type: imageType })

  const clipboardData = {
    items: [{ kind: 'file', type: imageType, getAsFile: () => imageFile }],
    types: ['Files'],
    getData: () => '',
  }

  const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
  Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
  fireEvent(textarea, pasteEvent)

  return { onImageFilesSelected, pasteEvent }
}

describe('ChatComposer – clipboard image paste', () => {
  it('calls onImageFilesSelected when an image is pasted', () => {
    const { onImageFilesSelected } = pasteImage()

    expect(onImageFilesSelected).toHaveBeenCalledTimes(1)
    const [files] = onImageFilesSelected.mock.calls[0]
    expect(files).toHaveLength(1)
    expect(files![0].type).toBe('image/png')
    expect(files![0].name).toMatch(/^clipboard-\d+\.png$/)
  })

  it('prevents default when image is pasted (avoid inserting as text)', () => {
    const { pasteEvent } = pasteImage()

    expect(pasteEvent.defaultPrevented).toBe(true)
  })

  it('does not call onImageFilesSelected when pasting plain text', () => {
    const onImageFilesSelected = vi.fn()
    render(<ChatComposer {...defaults} onImageFilesSelected={onImageFilesSelected} />)

    const textarea = screen.getByPlaceholderText(/attach files/i)
    const clipboardData = {
      items: [],
      types: ['text/plain'],
      getData: (t: string) => (t === 'text/plain' ? 'hello' : ''),
    }

    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
    fireEvent(textarea, pasteEvent)

    expect(onImageFilesSelected).not.toHaveBeenCalled()
    expect(pasteEvent.defaultPrevented).toBe(false)
  })

  it('handles JPEG clipboard images', () => {
    const { onImageFilesSelected } = pasteImage('image/jpeg')

    const [files] = onImageFilesSelected.mock.calls[0]
    expect(files![0].type).toBe('image/jpeg')
    expect(files![0].name).toMatch(/^clipboard-\d+\.jpeg$/)
  })

  it('derives extension from MIME subtype for non-standard types', () => {
    const { onImageFilesSelected } = pasteImage('image/webp')

    const [files] = onImageFilesSelected.mock.calls[0]
    expect(files![0].type).toBe('image/webp')
    expect(files![0].name).toMatch(/^clipboard-\d+\.webp$/)
  })

  it('skips image items where getAsFile returns null without swallowing paste', () => {
    const onImageFilesSelected = vi.fn()
    render(<ChatComposer {...defaults} onImageFilesSelected={onImageFilesSelected} />)

    const textarea = screen.getByPlaceholderText(/attach files/i)
    const clipboardData = {
      items: [{ kind: 'file', type: 'image/png', getAsFile: () => null }],
      types: ['Files'],
      getData: () => '',
    }

    const pasteEvent = new Event('paste', { bubbles: true, cancelable: true })
    Object.defineProperty(pasteEvent, 'clipboardData', { value: clipboardData, writable: false })
    fireEvent(textarea, pasteEvent)

    expect(onImageFilesSelected).not.toHaveBeenCalled()
    expect(pasteEvent.defaultPrevented).toBe(false)
  })

  it('continues past broken items to find a valid image', () => {
    const onImageFilesSelected = vi.fn()
    render(<ChatComposer {...defaults} onImageFilesSelected={onImageFilesSelected} />)

    const textarea = screen.getByPlaceholderText(/attach files/i)
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

    expect(onImageFilesSelected).toHaveBeenCalledTimes(1)
    const [files] = onImageFilesSelected.mock.calls[0]
    expect(files![0].type).toBe('image/png')
    expect(files![0].name).toMatch(/^clipboard-\d+\.png$/)
    expect(pasteEvent.defaultPrevented).toBe(true)
  })
})
