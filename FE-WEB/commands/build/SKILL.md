---
name: build
description: Implements, tests, reviews, and approves a CR. Use after /plan has produced a confirmed plan. Accepts a CR-ID. Runs implementation layer by layer, tests at each layer, multi-agent code review, and final approval. For Critical incidents, handles containment first then fix.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
metadata:
  version: 1.0.0
  stage: build
  process: unified-cr-workflow
---

# Build

**Role: Senior Engineer + Code Reviewer**
**Stage: BUILD — fourth gate of the CR process**

You are responsible for implementing the plan, running tests at each layer, conducting a multi-agent code review, and approving the build. You work layer by layer, inside-out. You stop and engage the developer only when something unexpected surfaces that requires a decision. Everything technical is your call.

For Critical incidents, you lead the containment first, then the fix.

---

## Gate Check

**Requires:** A confirmed plan from `/plan`.

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found. Run `/intake` first."
3. Read the CR item — check status is `PLANNED`. If not:
   - Status is `OPEN` → "Run `/spec` then `/plan` first."
   - Status is `SPECCED` → "Plan not done yet. Run `/plan CR-<cr-id>` first."
4. Locate `specs/cr/plans/<cr-id>.plan.md` — verify it exists and option is confirmed.

**Exception — Critical track:**
If CR severity is `Critical`, gate check is relaxed. The CR item from `/intake` is sufficient. Proceed directly to Containment.

---

## Phase 0: Critical Track — Containment (Critical severity only)

If severity is Critical, do this before any implementation:

1. Read the CR item — understand what is broken, what is at risk
2. Scan the codebase for the affected components
3. Advise immediate containment steps:

> **Containment advice for CR-<cr-id>:**
>
> Based on what I can see, the fastest way to stop the bleeding is:
>
> 1. [Specific step — e.g. "Disable the affected route by adding a redirect in middleware.ts"]
> 2. [Specific step — e.g. "Remove the API key from the NEXT_PUBLIC_ variable immediately"]
>
> These are reversible. Confirm when done so I can proceed with the fix.

Wait for the developer to confirm containment. Then proceed to Phase 1.

---

## Phase 1: Context Loading (silent — no output)

1. Read the full plan `specs/cr/plans/<cr-id>.plan.md`
2. Read the full spec `specs/cr/<cr-id>.spec.md`
3. Read the full CR item `specs/cr/<cr-id>.cr.md`
4. Read `references/nextjs_defaults.md`
5. Read all existing test skeletons
6. Read existing code files that will be modified

---

## Phase 2: Implement Layer by Layer

Implement in strict inside-out order. Run tests after each layer before proceeding.

### Layer 1: Domain (src/features/<feature>/domain/)

Implement domain changes per the plan:
- New or modified entity interfaces
- New or modified repository interfaces
- New or modified use cases

Run tests:
```bash
npx vitest run src/features/<feature>/__tests__/domain/
```

If tests fail: diagnose and fix before proceeding. Do not move forward with a failing layer.

### Layer 2: Infrastructure (src/features/<feature>/infrastructure/)

Implement infrastructure changes:
- API response models + toDomain() mapping
- Repository implementations via ApiClient

Run tests:
```bash
npx vitest run src/features/<feature>/__tests__/infrastructure/
```

### Layer 3: Application (src/features/<feature>/application/)

Implement application hooks:
- TanStack Query hooks (useQuery / useMutation)
- Zustand store slices if needed

Run tests:
```bash
npx vitest run src/features/<feature>/__tests__/application/
```

### Layer 4: Presentation (src/features/<feature>/presentation/)

Implement UI layer:
- Page components (Server or Client per spec)
- Feature components
- Forms (react-hook-form + Zod)

Run all feature tests:
```bash
npx vitest run src/features/<feature>/
```

### Layer 5: Core (src/core/) — if applicable

Apply any core changes. Run the full test suite:
```bash
npx vitest run
```

**If any existing tests break:** Stop, diagnose, present to the developer before proceeding.

---

## Phase 3: Unexpected Risk Check

During implementation, if you discover:
- A risk not captured in the spec or plan
- A breaking change to existing routes or components
- A user isolation gap
- A Firebase auth issue

Stop. Present to the developer:

> "During implementation I found something unexpected: [description].
> This was not in the plan. Options:
> [A] Fix it now — adds scope to this CR
> [B] Create a follow-up CR and proceed with a documented known risk
> [C] Reassess — may need to revisit the plan
> Which do you prefer?"

---

## Phase 4: Multi-Agent Code Review

Once all layers are implemented and tests pass, run parallel code review.

**sw-architect agent:**
- Boundary violations — any domain file importing from infrastructure or presentation?
- Dependency direction — does application import only from domain?
- Server/Client Component split — is `'use client'` used correctly and only where needed?
- Firebase client SDK placement — only in `'use client'` files or core/auth/?

**security-engineer agent:**
- User isolation — are all authenticated routes protected?
- Auth — is Bearer token attached to all API calls?
- Input validation — are all forms validated with Zod?
- Secrets — any hardcoded credentials or secrets in NEXT_PUBLIC_ vars?
- XSS — any dangerouslySetInnerHTML with unvalidated user input?

**nextjs-engineer agent:**
- Code quality — is the implementation clean, readable, maintainable?
- Error handling — are ApiErrors handled correctly, no raw Error.message in UI?
- Test coverage — do the tests cover ACs, error states, and auth scenarios?
- Forms — react-hook-form + Zod used correctly, 422 fieldErrors mapped?

Consolidate findings. Classify each: `BLOCKER`, `WARNING`, or `SUGGESTION`.

---

## Phase 5: Resolve Review Findings

Fix all `BLOCKER` findings autonomously.

For any blocker requiring a business or scope decision:
> "Code review found a blocker I can't resolve on my own: [finding]. Options: [A / B]. Which do you prefer?"

Note all `WARNING` findings. Discard `SUGGESTION` findings.

Re-run tests after fixes:
```bash
npx vitest run
```

---

## Phase 6: Final Approval

All of the following must be true before approving:
- [ ] All CR test skeletons implemented and passing
- [ ] No existing tests broken
- [ ] No unresolved BLOCKER findings from code review
- [ ] No undocumented unexpected risks
- [ ] TypeScript compiles without errors: `npx tsc --noEmit`

Update `specs/cr/<cr-id>.cr.md`:
```
Status: PLANNED → BUILT
Changelog: | <today> | Build approved — all tests pass, code review clear | |
```

---

## Phase 7: Handoff

Tell the developer:

> **Build approved for CR-<cr-id>.**
>
> [Brief summary: layers implemented, tests passing, review findings resolved]
>
> Next step: run `/close CR-<cr-id>` to verify, document, and formally close the CR.
