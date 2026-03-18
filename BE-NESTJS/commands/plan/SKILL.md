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

Create test skeleton files in `src/modules/<name>/`:

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

Each skeleton includes:
- `describe` block with the test subject name
- `it` blocks derived from the spec's acceptance criteria (one `it` per AC)
- `it` blocks for mandatory adversarial cases: tenant isolation, invalid auth, input validation
- `// TODO: implement` comments

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
