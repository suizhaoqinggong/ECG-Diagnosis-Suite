import ChatComposer from '../components/ChatComposer'
import ConversationMessage from '../components/ConversationMessage'
import ConversationSidebar from '../components/ConversationSidebar'
import { useWorkspaceController } from '../controllers/useWorkspaceController'

export default function HomePage() {
  const { state, dispatch, activeSession, isSubmitting, submit } = useWorkspaceController()

  if (!activeSession) return null

  return (
    <div className="min-h-screen lg:flex">
      <ConversationSidebar
        sessions={state.persisted.sessions}
        activeSessionId={activeSession.id}
        onSelectSession={(id) => dispatch({ type: 'SWITCH_SESSION', id })}
        onCreateSession={() => dispatch({ type: 'CREATE_SESSION' })}
      />

      <main className="flex min-h-screen flex-1 flex-col">
        <header className="border-b border-[var(--border)] px-4 py-6 md:px-8">
          <div className="mx-auto max-w-4xl">
            <p className="text-[0.7rem] font-medium uppercase tracking-[0.3em] text-[var(--ink-muted)]">
              Writing-first interface
            </p>
            <div className="mt-3 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
              <div>
                <h2 className="reading-copy text-3xl tracking-tight text-[var(--ink)] md:text-[2.8rem]">
                  {activeSession.title}
                </h2>
                <p className="mt-3 max-w-2xl text-base leading-7 text-[var(--ink-soft)]">
                  A document-style conversation for ECG interpretation, designed to read like notes rather than chat bubbles.
                </p>
              </div>
              <p className="max-w-sm text-sm leading-7 text-[var(--ink-muted)] md:text-right">
                Keep image uploads, signal pair reviews, and follow-up notes in one calm workspace.
              </p>
            </div>
          </div>
        </header>

        <div className="flex-1">
          <div className="mx-auto max-w-4xl px-4 md:px-8">
            {activeSession.messages.map((message) => (
              <ConversationMessage key={message.id} message={message} />
            ))}
          </div>
        </div>

        <ChatComposer
          draft={state.composer.draft}
          attachedFiles={state.composer.attachments.map(a => a.summary)}
          isLoading={isSubmitting}
          onDraftChange={(value) => dispatch({ type: 'SET_DRAFT', value })}
          onImageFilesSelected={(files) => { if (files) dispatch({ type: 'ADD_FILES', files }) }}
          onDataFilesSelected={(files) => { if (files) dispatch({ type: 'ADD_FILES', files }) }}
          onRemoveFile={(id) => dispatch({ type: 'REMOVE_FILE', id })}
          onSubmit={submit}
        />
      </main>
    </div>
  )
}
