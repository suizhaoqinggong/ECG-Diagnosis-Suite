/**
 * Tests for frontend performance and type architecture fixes.
 *
 * Covers:
 * - P1-6: submit callback should be stable across draft changes
 * - P1-7: PerLeadQC type should live in shared types, not component layer
 * - P2-10: ChatComposer should be memoized
 */

import { describe, it, expect } from 'vitest'

// ---------------------------------------------------------------------------
// P1-7: PerLeadQC type lives in shared types
// ---------------------------------------------------------------------------

describe('PerLeadQC type location', () => {
  it('should be exported from @/types/chat, not from components', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const indexPath = path.resolve(__dirname, '../../api/index.ts')
    const source = fs.readFileSync(indexPath, 'utf-8')

    // After fix: should import from types, not from components
    expect(source).not.toContain("from '@/components/QCWarning'")
    expect(source).toContain('PerLeadQC')
  })

  it('should be defined in @/types/chat.ts', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const typesPath = path.resolve(__dirname, '../../types/chat.ts')
    const source = fs.readFileSync(typesPath, 'utf-8')

    expect(source).toContain('PerLeadQC')
  })
})

// ---------------------------------------------------------------------------
// P1-6: submit callback stability
// ---------------------------------------------------------------------------

describe('submit callback stability', () => {
  it('submit should not depend on state.composer.draft', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const controllerPath = path.resolve(
      __dirname,
      '../../controllers/useWorkspaceController.ts',
    )
    const source = fs.readFileSync(controllerPath, 'utf-8')

    const submitMatch = source.match(
      /const submit = useCallback\(async[\s\S]*?\},\s*\[([^\]]+)\]\)/,
    )
    expect(submitMatch).not.toBeNull()

    const deps = submitMatch![1]
    expect(deps).not.toContain('state.composer.draft')
  })

  it('submit should not depend on state.composer.validationErrors', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const controllerPath = path.resolve(
      __dirname,
      '../../controllers/useWorkspaceController.ts',
    )
    const source = fs.readFileSync(controllerPath, 'utf-8')

    const submitMatch = source.match(
      /const submit = useCallback\(async[\s\S]*?\},\s*\[([^\]]+)\]\)/,
    )
    expect(submitMatch).not.toBeNull()

    const deps = submitMatch![1]
    expect(deps).not.toContain('state.composer.validationErrors')
  })
})

// ---------------------------------------------------------------------------
// P2-10: ChatComposer memoization
// ---------------------------------------------------------------------------

describe('ChatComposer memoization', () => {
  it('should be wrapped with React.memo', async () => {
    const fs = await import('fs')
    const path = await import('path')
    const componentPath = path.resolve(
      __dirname,
      '../../components/ChatComposer.tsx',
    )
    const source = fs.readFileSync(componentPath, 'utf-8')

    // After fix: the component should use memo() wrapper
    // Pattern: `const X = memo(function ...)` + separate `export default X`
    expect(source).toMatch(/const\s+\w+\s*=\s*memo\s*\(/)
    expect(source).toMatch(/export\s+default/)
  })
})
