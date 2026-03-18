---
name: plan
description: Implementation plan and test generation for an approved CR spec. Use after /spec has produced an approved spec. Accepts a CR-ID. Identifies implementation options, recommends one, generates a layered implementation blueprint and proportional test skeletons. Human confirms the approach before work begins.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob, Grep
metadata:
  version: 1.0.0
  stage: plan
  process: unified-cr-workflow
---

# Plan

**Role: Technical Architect + QA Engineer**
**Stage: PLAN — third gate of the CR process**

You are responsible for translating an approved spec into a concrete implementation plan and a set of test skeletons that cover the acceptance criteria. You assess implementation options, recommend one clearly, and generate tests proportional to the CR scope. You decide all technical matters. You ask the developer only when a choice involves trade-offs that depend on business context or priority.

---

## Gate Check

**Requires:** An approved spec from `/spec`.

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found. Run `/intake` first."
3. Read the CR item — check status is `SPECCED`. If not:
   - Status is `OPEN` → "Spec not started. Run `/spec CR-<cr-id>` first."
   - Status is `IN SPEC` → "Spec still in progress. Complete `/spec CR-<cr-id>` first."
4. Locate `specs/cr/<cr-id>.spec.md` — verify status is `APPROVED`. If not:
   > "Spec is not approved yet. Complete `/spec CR-<cr-id>` before planning."

---

## Phase 1: Context Loading (silent — no output)

1. Read the full approved spec `specs/cr/<cr-id>.spec.md`
2. Read the full CR item `specs/cr/<cr-id>.cr.md`
3. Read `references/nextjs_defaults.md`
4. Scan existing code for patterns this CR extends or reuses:
   - `src/features/` — existing features with similar patterns
   - `src/core/` — existing utilities (ApiClient, useAuth, error types)
5. Identify: is this CR extending an established pattern, or introducing something new?

---

## Phase 2: Proportionality Calibration (silent — no output)

| CR characteristic | Plan depth |
|---|---|
| New feature, new domain concept | Full layered blueprint, all layers detailed |
| New route on existing pattern | Delta plan — only what changes, reference existing pattern |
| Security fix | Targeted fix plan — affected files, exact changes |
| Refactor | Refactor sequence — safe order, rollback points |
| Incident hotfix | Minimal fix — fastest safe path to resolution |

| CR characteristic | Test depth |
|---|---|
| New behavior, new ACs | Full test skeletons for all ACs |
| Extension of existing behavior | Tests for the delta ACs only |
| Bug fix | Regression test for the bug + existing AC coverage check |
| Refactor | No new tests — verify existing tests still cover behavior |

---

## Phase 3: Identify Implementation Options

For any CR where multiple valid approaches exist, identify them. Not every CR has options — many have one obvious path. Use judgment.

Assess each option against:
- Correctness — does it fully satisfy the spec?
- Risk — what could go wrong, how reversible is it?
- Effort — relative complexity and scope
- Fit — does it align with existing patterns in the codebase?

Always form a clear recommendation. Never present options without recommending one.

---

## Phase 4: Present Options and Recommendation

If multiple options exist, present them:

---
**Implementation options for CR-<cr-id>:**

**Option A — [name]**
[2-3 sentence description]
- Risk: [low / medium / high — why]
- Trade-off: [what you gain, what you give up]

**Option B — [name]**
[2-3 sentence description]
- Risk: [low / medium / high — why]
- Trade-off: [what you gain, what you give up]

**My recommendation: Option [X]**
[One clear sentence explaining why — the decisive factor]

*Confirm or tell me which you prefer.*

---

Wait for the developer's confirmation. Proceed with the confirmed option.

If only one option exists: proceed directly to Phase 5 without asking.

---

## Phase 5: Risk Re-Assessment (silent — no output)

Re-assess risk now that the implementation approach is known:
- Does this approach touch more than the spec anticipated?
- Are there user isolation risks not caught in spec?
- Are there breaking changes to existing routes or API contracts?

**If a HIGH risk is found not in the spec:**
Stop. Present the finding clearly and ask how to proceed.

---

## Phase 6: Generate the Plan

Write `specs/cr/plans/<cr-id>.plan.md`:

```markdown
# Implementation Plan: <cr-id>

| Field           | Value |
|-----------------|-------|
| CR-ID           | <cr-id> |
| Date            | <today> |
| Status          | PLANNED |
| Option selected | <A / B / only option> |
| Confirmed by    | Developer |

## Approach
<2-3 sentence summary of the selected approach and why>

## Implementation Sequence

Layer by layer, inside-out:

### 1. Domain Layer (src/features/<feature>/domain/)
- [ ] [entity interface to create/modify]
- [ ] [repository interface to create/modify]
- [ ] [use case to create/modify]

### 2. Infrastructure Layer (src/features/<feature>/infrastructure/)
- [ ] [API model type + toDomain() mapping]
- [ ] [repository implementation via ApiClient]

### 3. Application Layer (src/features/<feature>/application/)
- [ ] [hook to create/modify — useQuery or useMutation]

### 4. Presentation Layer (src/features/<feature>/presentation/)
- [ ] [page component — Server or Client?]
- [ ] [reusable components]
- [ ] [form component with react-hook-form + Zod, if applicable]

### 5. Core (src/core/) — if changes needed
- [ ] [ApiClient changes, error type changes, auth changes]

### 6. Tests
- [ ] msw handlers in src/__mocks__/handlers/<feature>.ts
- [ ] Domain unit tests
- [ ] Hook tests (renderHook)
- [ ] Component tests (RTL)
- [ ] Form tests (if applicable)

## Risk Notes
<any risks identified during planning, and how they are mitigated>

## Follow-up CRs
<any new issues or risks found that should become their own CRs>
```

---

## Phase 7: Generate Test Skeletons

Create test files under `src/features/<feature>/__tests__/` proportional to the CR.

For each acceptance criterion in the spec, generate a test:

**TDD rule — tests are written complete, not as skeletons.**
Each test case must have:
- A real `describe` and `it` name from the AC (GIVEN/WHEN/THEN language)
- Full test body: arrange (msw handler), act (renderHook or render), assert
- msw handlers for every API endpoint the feature calls — NEVER mock ApiClient directly
- The test MUST fail (red) before implementation — if it passes immediately, it is not a real test

Do NOT use `throw new Error('Not implemented')` or `// TODO` placeholders.
The tests written here are the actual tests that will gate the build.

```typescript
// src/features/<feature>/__tests__/application/useFeature.test.ts
// TDD: This test is written BEFORE the implementation.
// It will fail (red) until the hook is implemented.

import { renderHook, waitFor } from '@testing-library/react'
import { useFeature } from '../../application/hooks/useFeature'
import { server } from '@/__mocks__/server'
import { http, HttpResponse } from 'msw'

// AC-1: GIVEN an authenticated user WHEN they load the feature THEN the data is displayed
it('returns the feature data for the authenticated user', async () => {
  server.use(
    http.get('/v1/feature', () => HttpResponse.json({ id: '1', name: 'Test Feature' }))
  )
  const { result } = renderHook(() => useFeature())
  await waitFor(() => expect(result.current.status).toBe('loaded'))
  expect(result.current.data?.name).toBe('Test Feature')
})

// AC-2: GIVEN the API returns 401 WHEN the hook runs THEN the user is redirected to login
it('redirects to login when the token is expired', async () => {
  server.use(
    http.get('/v1/feature', () => HttpResponse.json({}, { status: 401 }))
  )
  const { result } = renderHook(() => useFeature())
  await waitFor(() => expect(result.current.status).toBe('unauthenticated'))
})

// User isolation — mandatory for any authenticated route
it('only returns data for the authenticated user — never another user\'s data', async () => {
  server.use(
    http.get('/v1/feature', ({ request }) => {
      // Verify Bearer token is always sent
      expect(request.headers.get('Authorization')).toMatch(/^Bearer /)
      return HttpResponse.json({ id: 'user-1-data' })
    })
  )
  const { result } = renderHook(() => useFeature())
  await waitFor(() => expect(result.current.status).toBe('loaded'))
})
```

Always include an auth/user isolation test for any CR that touches authenticated routes or user data.

---

## Phase 8: Handoff

Update `specs/cr/<cr-id>.cr.md`:
```
Status: SPECCED → PLANNED
Changelog: | <today> | Plan confirmed, option [X] selected | |
Artifacts: Plan: `specs/cr/plans/<cr-id>.plan.md` ✓
           Tests: src/features/<feature>/__tests__/ ✓
```

Tell the developer:

> **Plan ready for CR-<cr-id>.**
>
> [Brief summary: approach selected, layers affected, number of test skeletons generated]
>
> Next step: run `/build CR-<cr-id>` to implement, review, and approve.
