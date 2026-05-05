import { useCallback, useRef } from 'react'
import toast from 'react-hot-toast'
import { extractErrorMessage } from '@/api/client'
import { chatApi } from '@/api/chat'
import { healthApi } from '@/api/health'
import type { ChatSession, ConversationMessage } from '@/types/chat'
import type { HealthAnalysisResult } from '@/types/health'
import {
  createId,
  detectCategory,
  validateAttachments,
} from '../reducers/helpers'
import type { WorkspaceState, WorkspaceAction, PendingAttachment } from '../reducers/types'
import { mapLocalMessageToRemote } from '../messageMappers'

interface AuthLike {
  isLoading: boolean
  user?: { id: number } | null
}

interface SubmissionFlowDeps {
  state: WorkspaceState
  dispatch: React.Dispatch<WorkspaceAction>
  auth: AuthLike
  activeSession: ChatSession | null
  composerRef: React.MutableRefObject<WorkspaceState['composer']>
  ensureRemoteSession: (session: ChatSession) => Promise<void>
}

function buildPendingAttachments(files: File[]): PendingAttachment[] {
  return files.flatMap((file) => {
    const category = detectCategory(file)
    if (!category) return []

    const id = createId()
    return [{
      id,
      file,
      summary: {
        id,
        name: file.name,
        size: file.size,
        category,
      },
    }]
  })
}

export function useSubmissionFlow({
  state,
  dispatch,
  auth,
  activeSession,
  composerRef,
  ensureRemoteSession,
}: SubmissionFlowDeps) {
  const lastFilesRef = useRef<File[] | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const isSubmitting = state.submission.phase === 'uploading' || state.submission.phase === 'processing'

  const submit = useCallback(async (attachmentOverride?: PendingAttachment[]) => {
    if (!activeSession || isSubmitting) return

    const attachments = attachmentOverride ?? composerRef.current.attachments
    const draft = composerRef.current.draft.trim()
    const validationErrors = attachmentOverride
      ? validateAttachments(attachments)
      : composerRef.current.validationErrors
    const hasDraft = draft.length > 0
    const hasAttachments = attachments.length > 0

    if (!hasDraft && !hasAttachments) {
      toast.error('请添加备注或上传健康文件。')
      return
    }

    if (!hasAttachments && hasDraft) {
      const userMessage: ConversationMessage = {
        id: createId(),
        role: 'user',
        type: 'prompt',
        title: '临床备注',
        content: draft,
        createdAt: new Date().toISOString(),
        status: 'completed',
      }
      const guidanceMessage: ConversationMessage = {
        id: createId(),
        role: 'assistant',
        type: 'guidance',
        content: '我可以在此工作区中保存备注和发现，但分析需要先上传文件。准备好后请上传 PDF、PNG、JPG 或匹配的 .dat + .hea 信号对。',
        createdAt: new Date().toISOString(),
        status: 'completed',
      }
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: guidanceMessage })
      dispatch({ type: 'CLEAR_COMPOSER' })

      if (auth.user) {
        try {
          await ensureRemoteSession(activeSession)
          await chatApi.createMessages(activeSession.id, [
            mapLocalMessageToRemote(userMessage),
            mapLocalMessageToRemote(guidanceMessage),
          ])
        } catch (error) {
          toast.error(extractErrorMessage(error))
        }
      }
      return
    }

    if (validationErrors.length > 0) {
      toast.error(validationErrors[0])
      return
    }

    const userMessage: ConversationMessage = {
      id: createId(),
      role: 'user',
      type: 'prompt',
      title: attachments.length > 0 ? '已提交健康文件待分析' : '临床备注',
      content: draft || '请分析附件中的健康文件。',
      createdAt: new Date().toISOString(),
      attachments: attachments.map(attachment => attachment.summary),
      status: 'completed',
    }
    dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })

    const pendingMessageId = createId()
    const pendingMessage: ConversationMessage = {
      id: pendingMessageId,
      role: 'assistant',
      type: 'health_report',
      content: '分析中...',
      createdAt: new Date().toISOString(),
      status: 'pending',
    }
    dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: pendingMessage })
    dispatch({ type: 'SUBMIT_STARTED', messageId: pendingMessageId })

    lastFilesRef.current = attachments.map(attachment => attachment.file)
    abortControllerRef.current = new AbortController()
    const currentAbortController = abortControllerRef.current

    try {
      if (auth.user) {
        await ensureRemoteSession(activeSession)
        await chatApi.createMessages(activeSession.id, [mapLocalMessageToRemote(userMessage)])
      }

      const files = attachments.map(attachment => attachment.file)
      const job = await healthApi.createJob(
        files,
        composerRef.current.draft,
        auth.user ? activeSession.id : undefined,
      )
      dispatch({ type: 'UPDATE_MESSAGE', sessionId: activeSession.id, messageId: pendingMessageId, updates: { type: 'health_report' } })
      dispatch({ type: 'SUBMIT_PROCESSING' })

      let latestResult: HealthAnalysisResult | undefined
      const MAX_POLLS = 120
      let pollCount = 0
      for (;;) {
        if (currentAbortController.signal.aborted) return
        const latest = await healthApi.getJob(job.id)
        if (latest.status === 'completed') {
          latestResult = latest.result ?? undefined
          break
        }
        if (latest.status === 'failed') {
          throw new Error(latest.error ?? '健康分析失败')
        }
        pollCount += 1
        if (pollCount >= MAX_POLLS) {
          throw new Error('分析超时，请重试。')
        }
        await new Promise((resolve) => setTimeout(resolve, 1500))
      }

      if (!currentAbortController.signal.aborted) {
        const result = latestResult!
        const completedMessage: Partial<ConversationMessage> = {
          status: 'completed',
          content: '分析完成',
          result,
        }
        dispatch({
          type: 'UPDATE_MESSAGE',
          sessionId: activeSession.id,
          messageId: pendingMessageId,
          updates: completedMessage,
        })
        dispatch({ type: 'SUBMIT_SUCCEEDED', result })
        dispatch({ type: 'CLEAR_COMPOSER' })

        toast.success('分析完成。')
      }
    } catch (error: unknown) {
      if (currentAbortController.signal.aborted) return
      const errorMessage = extractErrorMessage(error)
      dispatch({
        type: 'UPDATE_MESSAGE',
        sessionId: activeSession.id,
        messageId: pendingMessageId,
        updates: { status: 'error', errorDetail: errorMessage, content: '分析失败' },
      })
      dispatch({ type: 'SUBMIT_FAILED', error: errorMessage })

      toast.error(errorMessage)
    }
  }, [activeSession, auth.user, composerRef, dispatch, ensureRemoteSession, isSubmitting])

  const cancelSubmission = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (state.submission.activeMessageId && activeSession) {
      dispatch({
        type: 'UPDATE_MESSAGE',
        sessionId: activeSession.id,
        messageId: state.submission.activeMessageId,
        updates: { status: 'error', errorDetail: '分析已取消', content: '分析已取消' },
      })
    }
    dispatch({ type: 'SUBMIT_CANCEL' })
  }, [activeSession, dispatch, state.submission.activeMessageId])

  const retry = useCallback(async () => {
    if (!lastFilesRef.current || !activeSession) {
      toast.error('请重新选择文件后重试。')
      return
    }
    const retryAttachments = buildPendingAttachments(lastFilesRef.current)
    dispatch({ type: 'ADD_FILES', files: lastFilesRef.current })
    await submit(retryAttachments)
  }, [activeSession, dispatch, submit])

  return {
    submit,
    retry,
    cancelSubmission,
    isSubmitting,
  }
}
