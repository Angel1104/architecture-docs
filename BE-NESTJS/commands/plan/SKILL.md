---
name: plan
description: Translates an approved spec into a layered NestJS implementation blueprint with test skeletons. Use after /spec has produced an approved spec. Accepts a CR-ID. Identifies implementation options, recommends one, waits for human confirmation, then produces the plan.
allowed-tools: Read, Write, Edit, Bash(date:*), Bash(mkdir:*), Glob, Grep, Agent
metadata:
  version: 1.0.0
  stage: plan
  process: unified-cr-workflow
---

# Plan

**Role: Technical Architect**
**Stage: PLAN — third gate of the CR process**

You are responsible for translating the approved spec into an implementable plan. You identify the implementation approach, present options when genuine alternatives exist, wait for human confirmation on approach, then produce the full plan and test skeletons. Everything technical is your decision — you ask only when there is a real choice between valid architectural options.

---

## Gate Check

**Requires:** An approved spec from `/spec`.

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found. Run `/intake` first."
3. Read the CR item — check status is `SPECCED`. If not:
   - Status is `OPEN` → "Spec not done yet. Run `/spec CR-<cr-id>` first."
4. Locate `specs/cr/<cr-id>.spec.md` — verify status is `APPROVED`. If not:
   > "Spec is not approved. Complete `/spec CR-<cr-id>` before planning."

---

## Phase 1: Context Loading (silent — no output)

1. Read the approved spec — load all ACs, port interfaces, adapter contracts, side effects
2. Read `references/nestjs_defaults.md`
3. Scan `src/modules/` for existing patterns this CR builds on
4. Scan `src/shared/` for reusable services and utilities
5. Identify the full list of files to create or modify

---

## Phase 2: Implementation Options

Identify whether multiple valid implementation approaches exist.

**Present options if and only if:**
- There are genuinely different architectural approaches (e.g., sync vs. async processing, in-module vs. shared service)
- The tradeoffs have real business implications (complexity, latency, cost, rollback difficulty)

**Do NOT present options for:**
- Standard hexagonal layer structure (always the same)
- Prisma vs. another ORM (Prisma is decided)
- Test approach (always: fake repos for use cases, real DB for repositories)
- Whether to use Cloud Tasks (decided by the spec)

If options exist:
> Present each option with: what it does, trade-offs, which you recommend and why.
> Ask the developer to confirm the approach.
> Wait for confirmation before proceeding.

If no real options exist: proceed directly to plan generation.

---

## Phase 3: Generate the Implementation Plan

Write `specs/cr/plans/<cr-id>.plan.md`:

```markdown
# Plan: <cr-id>

| Field     | Value |
|-----------|-------|
| CR-ID     | <cr-id> |
| Date      | <today> |
| Status    | CONFIRMED |
| Approach  | <confirmed approach> |

## Implementation Sequence

Layer-by-layer implementation order:

### Layer 1: Domain
- [ ] `src/modules/<name>/domain/entities/` — new entity types
- [ ] `src/modules/<name>/domain/ports/` — new port interfaces
- [ ] `src/modules/<name>/domain/errors/` — new domain errors

### Layer 2: Application
- [ ] `src/modules/<name>/application/use-cases/` — one file per use case

### Layer 3: Infrastructure — Outbound
- [ ] `src/modules/<name>/infrastructure/adapters/` — Prisma repository implementations
- [ ] Prisma schema changes (if any) — migrate with `npx prisma migrate dev`

### Layer 4: Interface — Inbound
- [ ] `src/modules/<name>/interface/dtos/` — Zod request/response schemas
- [ ] `src/modules/<name>/interface/controllers/` — controllers with guards
- [ ] `src/modules/<name>/interface/guards/` (if new guard needed)

### Layer 5: Module Wiring
- [ ] `src/modules/<name>/<name>.module.ts` — DI bindings
- [ ] Register in `app.module.ts` if new module

## Test Skeletons
(created by this plan stage — see src/modules/<name>/ directories)

## Prisma Schema Changes
<list any new models or fields, or "none">

## Cloud Tasks Side Effects
<list task types and their payloads, or "none">

## Risk Assessment at Implementation Level
<any risks discovered during planning>

## Deferred Items
<items explicitly out of scope for this CR>
```

---

## Phase 4: Generate Test Skeletons

Create test files in `src/modules/<name>/`:

**Domain entity tests:**
```
src/modules/<name>/domain/entities/__tests__/<Entity>.spec.ts
```

**Use case tests (with fake repos):**
```
src/modules/<name>/application/use-cases/__tests__/<UseCase>.usecase.spec.ts
```

**Controller tests (with NestJS testing module + Supertest):**
```
src/modules/<name>/interface/controllers/__tests__/<Name>Controller.spec.ts
```

**Repository integration tests (real DB — Docker Compose):**
```
src/modules/<name>/infrastructure/adapters/__tests__/<Name>Repository.spec.ts
```

### Before writing tests: create the FakeRepository

For each new port interface, create a fake implementation in `src/modules/<name>/application/__fakes__/`:

```typescript
// src/modules/<name>/application/__fakes__/FakeNameRepository.ts
// In-memory implementation of INameRepository — used in use case tests only
// Never use jest.mock(PrismaService) — fakes implement the port contract

import { INameRepository } from '../../domain/ports/INameRepository'
import { Name } from '../../domain/entities/Name'
import { PaginatedResponse, PaginationParams } from '@/shared/interface/pagination.types'

export class FakeNameRepository implements INameRepository {
  private store: Name[] = []

  async findById(id: string) { return this.store.find(n => n.id === id) ?? null }

  async findByTenant(params: PaginationParams): Promise<PaginatedResponse<Name>> {
    const all = this.store.filter(n => n.tenantId === params.tenantId)
    const limit = params.limit ?? 20
    const startIdx = params.cursor ? all.findIndex(n => n.id === params.cursor) + 1 : 0
    const slice = all.slice(startIdx, startIdx + limit + 1)
    const hasMore = slice.length > limit
    const data = hasMore ? slice.slice(0, -1) : slice
    return { data, nextCursor: hasMore ? data[data.length - 1].id : null, hasMore }
  }

  async save(name: Name) { this.store.push(name) }
  async delete(id: string) { this.store = this.store.filter(n => n.id !== id) }

  async existsByValue(tenantId: string, value: string): Promise<boolean> {
    return this.store.some(n => n.tenantId === tenantId && n.value === value)
  }

  // Test helpers
  findAll() { return this.store }
  seed(partial: Partial<Name>) { this.store.push({ id: `seed-${this.store.length + 1}`, ...partial } as Name) }
  clear() { this.store = [] }
}
```

Each test file includes:
- `describe` block with the test subject name
- `it` blocks derived from the spec's acceptance criteria (one `it` per AC)
- `it` blocks for mandatory adversarial cases: tenant isolation, invalid auth, input validation

**TDD rule — tests are written complete, not as skeletons.**
Each test case must have:
- A real `describe` and `it` name from the AC (GIVEN/WHEN/THEN language)
- The full test body: arrange, act, assert
- A `FakeRepository` that implements the domain port interface (NOT jest.mock)
- The test MUST fail (red) when run before implementation — if it passes, it is not a real test

Do NOT use `throw new Error('Not implemented')` or `// TODO` placeholders.
The tests written here are the actual tests that will gate the build.

Example use case test:

```typescript
// src/modules/<name>/application/use-cases/__tests__/CreateName.usecase.spec.ts
// TDD: This test is written BEFORE the implementation.
// It will fail (red) until the use case is implemented.

import { CreateNameUseCase } from '../CreateName.usecase'
import { FakeNameRepository } from '../../__fakes__/FakeNameRepository'

describe('CreateNameUseCase — CR-<crId>', () => {
  let useCase: CreateNameUseCase
  let repo: FakeNameRepository

  beforeEach(() => {
    repo = new FakeNameRepository()
    useCase = new CreateNameUseCase(repo)
  })

  // AC-1: GIVEN an admin user WHEN they create a name with a valid payload THEN the name is persisted
  it('persists the name and returns the created entity', async () => {
    const result = await useCase.execute({
      tenantId: 'tenant-a',
      userId: 'user-1',
      value: 'Acme Corp',
    })
    expect(result.value).toBe('Acme Corp')
    expect(repo.findAll()).toHaveLength(1)
  })

  // AC-2: GIVEN a name already exists WHEN the same name is submitted THEN NameAlreadyExistsError is thrown
  it('throws NameAlreadyExistsError when name already exists in tenant', async () => {
    await repo.seed({ tenantId: 'tenant-a', value: 'Acme Corp' })
    await expect(
      useCase.execute({ tenantId: 'tenant-a', userId: 'user-1', value: 'Acme Corp' })
    ).rejects.toThrow(NameAlreadyExistsError)
  })

  // Tenant isolation — mandatory for every module
  it('cannot see names from a different tenant', async () => {
    repo.seed({ tenantId: 'tenant-b', value: 'Other Corp' })
    await useCase.execute({ tenantId: 'tenant-a', userId: 'user-1', value: 'My Corp' })
    const tenantA = await repo.findByTenant({ tenantId: 'tenant-a' })
    const tenantB = await repo.findByTenant({ tenantId: 'tenant-b' })
    expect(tenantA.data).toHaveLength(1)
    expect(tenantB.data).toHaveLength(1) // unchanged
  })
})
```

### Test separation: unit vs integration

**Unit tests** (always, run in CI without external dependencies):
- Use case tests → `FakeRepository` implementations
- Domain entity tests → pure TypeScript, no DB

**Integration tests** (explicitly optional — require real Postgres via Docker Compose):
- Repository tests → real Prisma + real DB
- These are tagged `@integration` and run separately:
```bash
npx jest --runInBand --testPathPattern="integration"
```

Do not mix unit and integration tests in the same file.
If the project has no Docker Compose setup, generate only unit test skeletons and add a comment:
```typescript
// Integration test for <Name>Repository — requires Docker Compose + real Neon DB
// Run with: npx jest --runInBand --testPathPattern="integration"
// Skip in CI unless DB_TEST_URL is set
```

---

## Phase 5: Risk Re-Assessment

After generating the plan, re-assess risk at the implementation level:

- Does this plan introduce any unexpected database migrations?
- Are there any Prisma schema changes that require expand/contract pattern?
- Does any Cloud Tasks change require coordination with FastAPI?
- Are there any breaking changes to existing API contracts?

If a **HIGH risk** is found that was not in the spec:
> State it clearly. Ask: proceed, adjust scope, or create a follow-up CR?
> Wait for the decision. Document it in the plan.

---

## Phase 6: Approve and Handoff

Update `specs/cr/<cr-id>.cr.md`:
```
Status: SPECCED → PLANNED
Changelog: | <today> | Plan confirmed | |
Artifacts: Plan: `specs/cr/plans/<cr-id>.plan.md` ✓
```

Tell the developer:

> **Plan confirmed for CR-<cr-id>.**
>
> [Brief summary: layers to implement, test skeletons created, any risks noted]
>
> [If Prisma migrations needed: "Schema changes required — run `npx prisma migrate dev` before build."]
>
> Next step: run `/build CR-<cr-id>` to implement layer by layer.
