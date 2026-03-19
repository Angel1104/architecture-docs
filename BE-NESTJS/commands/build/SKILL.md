---
name: build
description: Implements, tests, reviews, and approves a CR. Use after /plan has produced a confirmed plan. Accepts a CR-ID. Implements NestJS layer by layer (domain → application → infrastructure → interface), runs Jest tests at each layer, multi-agent code review, final approval. For Critical incidents, handles containment first then fix.
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
3. Read the CR item — check Type and Status:

   **Bug track** (Type = `bug`):
   - Status must be `OPEN` — proceed directly to Bug Track phase
   - No plan required — bugs skip spec and plan

   **Full track** (Type = `feature`):
   - Status must be `PLANNED`
   - If status is `OPEN` → "Run `/spec` then `/plan` first."
   - If status is `SPECCED` → "Plan not done yet. Run `/plan CR-<cr-id>` first."
   - Locate `specs/cr/plans/<cr-id>.plan.md` — must exist

   **Lean track** (Type = `change`, `refactor`):
   - Status must be `SPECCED` (lean track skips plan)
   - If status is `OPEN` → "Run `/spec` first."
   - If status is `PLANNED` → proceed (plan exists, which is fine)
   - No plan file required — generate test skeletons inline in Phase 0c before building

   **Security / Incident track**:
   - Gate check relaxed — CR item from `/intake` is sufficient

**Exception — Critical track:**
If CR severity is `Critical`, gate check is relaxed. The CR item from `/intake` is sufficient. Proceed directly to the Containment phase.

---

## Phase 0: Critical Track — Containment (Critical severity only)

If severity is Critical, do this before any implementation:

1. Read the CR item — understand what is broken, what is at risk
2. Scan `src/modules/` for the affected components
3. Advise immediate containment steps:

> **Containment advice for CR-<cr-id>:**
>
> Based on what I can see, the fastest way to stop the bleeding is:
>
> 1. [Specific step — e.g. "Remove the auth guard bypass in module X at line Y"]
> 2. [Specific step — e.g. "Disable the affected endpoint in the controller with a feature flag"]
> 3. [Specific step — e.g. "Rotate the secret at Secret Manager > secret-name"]
>
> These are reversible. Confirm when done so I can proceed with the fix.

Wait for the developer to confirm containment is in place. Then proceed to Phase 1.

---

## Phase 0b: Bug Track (Type = `bug` only)

If CR type is `bug`, skip to this phase. Do not run Phases 1–2.

**Step 1 — Locate the file (silent)**

1. Read `specs/project.md` — find the feature map entry for the area described in the CR
2. Use the feature map to identify the exact file(s) most likely to contain the bug
3. Read only those files — do not scan the whole codebase

**Step 2 — Reproduce the bug (silent)**

4. Read the CR item description carefully — understand the exact symptom
5. Trace the code path that produces the bug
6. Identify the root cause — one specific line or logic error

**Step 3 — Write the regression test FIRST (TDD)**

7. Write a targeted test that:
   - Reproduces the exact failure described in the CR
   - Uses GIVEN/WHEN/THEN naming
   - Fails (red) before the fix
   - Lives in the existing test file for that module

```bash
npx jest <specific-test-file> --runInBand
```
Test must fail here. If it passes, the reproduction is wrong — revisit.

**Step 4 — Fix**

8. Apply the minimal fix — change only what is needed to make the regression test pass
9. Do not refactor surrounding code

**Step 5 — Verify (green)**

```bash
npx jest <specific-test-file> --runInBand
```
Regression test passes. Then run the full suite:
```bash
npx jest --runInBand
```
No existing tests broken.

**Step 6 — TypeScript check**

```bash
npx tsc --noEmit
```

**Step 7 — Update CR and close**

Update `specs/cr/<cr-id>.cr.md`:
```
Status: OPEN → BUILT
Changelog: | <today> | Bug fixed — regression test added and passing | |
```

Tell the developer:
> **Bug fix complete for CR-<cr-id>.**
>
> Root cause: [one sentence]
> Fix: [one sentence — what was changed]
> Test added: [test name]
>
> Next step: run `/close CR-<cr-id>` to formally close.

---

## Phase 0c: Lean Track — Test Skeletons (Type = `change` or `refactor` only)

If CR type is `change` or `refactor` and no plan file exists, generate test skeletons before building.

1. Read the spec `specs/cr/<cr-id>.spec.md` — extract the acceptance criteria and error scenarios
2. For each AC, write a complete test (`describe` / `it`, arrange/act/assert) that:
   - Derives the test name from the AC using GIVEN/WHEN/THEN language
   - Uses `FakeRepository` for use case tests, NestJS testing module + Supertest for controller tests
   - **Must fail (red) before implementation** — do not write tests that pass without code
3. Place test files in their standard locations:
   - Domain: `src/modules/<name>/domain/entities/__tests__/<Entity>.spec.ts`
   - Use case: `src/modules/<name>/application/use-cases/__tests__/<UseCase>.usecase.spec.ts`
   - Controller: `src/modules/<name>/interface/controllers/__tests__/<Name>Controller.spec.ts`
4. Confirm test files are written, then proceed to Phase 1.

---

## Phase 1: Context Loading (silent — no output)

1. Read the full plan `specs/cr/plans/<cr-id>.plan.md`
2. Read the full spec `specs/cr/<cr-id>.spec.md`
3. Read the full CR item `specs/cr/<cr-id>.cr.md`
4. Read `references/nestjs_defaults.md`
5. Read all existing test skeleton files in `src/modules/<name>/`
6. Read existing code files that will be modified

---

## Phase 2: Implement Layer by Layer

Implement in strict inside-out order. Run tests after each layer before proceeding.

### TDD Rule — Red → Green → Refactor

For every layer, the order is **always**:
1. **Read** the tests generated by `/plan` — understand what must be true
2. **Run** them first — they MUST fail (red). If they pass without implementation, the test is wrong — fix it before proceeding
3. **Write** the minimum code to make them pass (green)
4. **Refactor** if needed — tests must still pass after refactor
5. **Never** write implementation code before its test is red

This is non-negotiable. The test failure is the specification. The code is the proof.

### Layer 1: Domain (`src/modules/<name>/domain/`)

**Step 1 — Run tests first (expect RED):**
```bash
npx jest src/modules/<name>/domain/ --runInBand
```
Tests must fail here — if any pass before implementation, inspect them: either the test is wrong or the code already exists.

**Step 2 — Implement to make them green:**
- New entity types and factory functions
- Port interfaces (`INameRepository`, etc.)
- Domain error classes

**Step 3 — Run tests again (expect GREEN):**
```bash
npx jest src/modules/<name>/domain/ --runInBand
```
All tests for this layer must pass before proceeding to Layer 2.

### Layer 2: Application (`src/modules/<name>/application/`)

**Step 1 — Run tests first (expect RED):**
```bash
npx jest src/modules/<name>/application/ --runInBand
```
Tests must fail here — if any pass before implementation, inspect them: either the test is wrong or the code already exists.

**Step 2 — Implement to make them green:**
- Use cases — one file per use case, using only domain ports (no Prisma, no Firebase)

**Step 3 — Run tests again (expect GREEN):**
```bash
npx jest src/modules/<name>/application/ --runInBand
```
All tests for this layer must pass before proceeding to Layer 3.

### Layer 3: Infrastructure (`src/modules/<name>/infrastructure/`)

**Step 1 — Run tests first (expect RED):**
```bash
npx jest src/modules/<name>/infrastructure/ --runInBand
```
Tests must fail here — if any pass before implementation, inspect them: either the test is wrong or the code already exists.

Note: infrastructure tests require a running Postgres. Use Docker Compose for local testing.

**Step 2 — Implement to make them green:**
- Prisma repository implementations (using `prisma.withTenant()`)
- Firebase adapter, R2 adapter, Cloud Tasks payloads (if needed)
- Run Prisma migrations if schema changed: `npx prisma migrate dev`

**Step 3 — Run tests again (expect GREEN):**
```bash
npx jest src/modules/<name>/infrastructure/ --runInBand
```
All tests for this layer must pass before proceeding to Layer 4.

### Layer 4: Interface (`src/modules/<name>/interface/`)

**Step 1 — Run tests first (expect RED):**
```bash
npx jest src/modules/<name>/interface/ --runInBand
```
Tests must fail here — if any pass before implementation, inspect them: either the test is wrong or the code already exists.

**Step 2 — Implement to make them green:**
- Zod DTOs for request/response validation
- Controllers with `@UseGuards(FirebaseAuthGuard)` on all write endpoints
- Guards and decorators if new ones are needed

**Step 3 — Run tests again (expect GREEN):**
```bash
npx jest src/modules/<name>/ --runInBand
```
All tests for this layer must pass before proceeding to Layer 5.

### Layer 5: Module Wiring

Wire the NestJS module and run the full test suite:
```bash
npx jest --runInBand
```

**If any existing tests break:** stop, diagnose, present to the developer before proceeding.

---

## Phase 3: Unexpected Risk Check

During implementation, if you discover:
- A risk not captured in the spec or plan
- A breaking change to existing API contracts
- A missing RLS context on a tenant-scoped table
- A Prisma migration requiring expand/contract pattern

Stop. Present to the developer:

> "During implementation I found something unexpected: [description].
> This was not in the plan. Options:
> [A] Fix it now — adds scope to this CR
> [B] Create a follow-up CR and proceed with a documented known risk
> [C] Reassess — may need to revisit the plan
> Which do you prefer?"

Wait for the decision. Document it. Then proceed.

---

## Phase 4: Multi-Agent Code Review

Once all layers are implemented and tests pass, run a parallel code review.

Spawn three review agents simultaneously:

**sw-architect agent:**
- Boundary violations — does any domain file import from infrastructure?
- Dependency direction — does application import only from domain?
- Port compliance — are all external interactions going through port interfaces?
- RLS usage — does every tenant-scoped query use `withTenant()`?
- Controller purity — do controllers only call use cases?

**security-engineer agent:**
- Tenant isolation — is every tenant-scoped query inside `withTenant()`?
- Auth guard coverage — are all write endpoints and tenant-data endpoints guarded?
- `tenant_id` source — does it come from the authenticated user only (never from request body)?
- Input validation — is all external input validated with Zod at the controller boundary?
- Secrets — are credentials hardcoded anywhere?
- OIDC for Cloud Tasks — if Cloud Task handlers exist, do they use OIDC guard (not Firebase)?

**backend-engineer agent:**
- Code quality — is the implementation clean, readable, maintainable?
- Error handling — are domain errors used correctly (no HTTP exceptions in domain/application)?
- RFC 7807 — does `DomainExceptionFilter` cover all new domain errors?
- Test coverage — do the tests cover the ACs, edge cases, and tenant isolation?
- TypeScript strictness — no implicit `any`, no non-null assertions without justification

Consolidate findings. Classify each:
- `BLOCKER` — must be fixed before approval
- `WARNING` — should be noted, developer informed
- `SUGGESTION` — optional improvement

---

## Phase 5: Resolve Review Findings

Fix all `BLOCKER` findings autonomously.

For any blocker that requires a business or scope decision:
> "Code review found a blocker I can't resolve on my own: [finding]. Options: [A / B]. Which do you prefer?"

Note all `WARNING` findings in the closure report. Do not block on warnings.
Discard `SUGGESTION` findings — out of scope for this CR.

Re-run tests after fixes:
```bash
npx jest --runInBand
```

---

## Phase 6: TypeScript Check

```bash
npx tsc --noEmit
```

Fix any TypeScript errors before approving.

---

## Phase 7: Final Approval

All of the following must be true before approving:
- [ ] All CR test skeletons implemented and passing
- [ ] No existing tests broken
- [ ] `npx tsc --noEmit` passes with no errors
- [ ] No unresolved BLOCKER findings from code review
- [ ] No undocumented unexpected risks

Update `specs/cr/<cr-id>.cr.md`:
```
Status: PLANNED → BUILT   (feature track)
     or SPECCED → BUILT   (change/refactor lean track)
Changelog: | <today> | Build approved — all tests pass, code review clear | |
```

---

## Phase 8: Handoff

Tell the developer:

> **Build approved for CR-<cr-id>.**
>
> [Brief summary: layers implemented, tests passing, review findings resolved]
>
> [If warnings exist: "Review warnings noted: [brief list]. No action required now but worth considering."]
>
> Next step: run `/close CR-<cr-id>` to verify, document, and formally close the CR.
