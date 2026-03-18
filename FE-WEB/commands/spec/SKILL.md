---
name: spec
description: Full spec stage for a CR — draft, multi-agent review, revise, approve. Use after /intake has produced a CR item. Accepts a CR-ID. Produces an approved spec proportional to the CR size and risk.
allowed-tools: Read, Write, Edit, Bash(date:*), Bash(mkdir:*), Glob, Grep, Agent
metadata:
  version: 1.0.0
  stage: spec
  process: unified-cr-workflow
---

# Spec

**Role: Domain Analyst + Software Architect**
**Stage: SPEC — second gate of the CR process**

You are responsible for producing an approved specification for this CR. You draft it, review it through multiple lenses, revise it autonomously, and lock it when approved. You ask the developer only when a genuine business decision cannot be inferred from the CR item, the codebase, or the technical references.

The depth of what you produce is proportional to the CR. You decide how much each section needs. The template is always the same — the content scales.

---

## Gate Check

**Requires:** A confirmed CR item from `/intake`.

1. Read `$ARGUMENTS` — extract the CR-ID (e.g. `CR-260311-143022` or `260311-143022`)
2. Locate `specs/cr/<cr-id>.cr.md` — if it does not exist, stop and tell the developer:
   > "No CR item found for [input]. Run `/intake` first to create a CR item before speccing."
3. Read the full CR item — load type, severity, track, intent, assessment, business decisions already made
4. Check if `specs/cr/<cr-id>.spec.md` already exists:
   - If it exists with status `APPROVED` — tell the developer the spec is already approved and suggest `/plan`
   - If it exists with another status — continue from where it left off

---

## Phase 1: Context Loading (silent — no output)

Load all relevant context before writing anything:

**Always:**
- Read `references/nextjs_defaults.md`
- Read `references/nextjs_spec_template.md`

**Codebase scan:**
- Scan `specs/cr/` for related or dependent specs
- Scan `src/features/` for existing code this CR touches
- Scan `src/core/` for existing utilities or patterns to reuse
- Identify which existing acceptance criteria (if any) are affected

---

## Phase 2: Proportionality Calibration (silent — no output)

Before drafting, decide the depth of each spec section based on the CR item:

| CR type | Sections required | Notes |
|---------|------------------|-------|
| `feature` (Normal) | All 10 sections | Full spec |
| `feature` (High) | All 10 sections, leaner content | Same sections, less detail where obvious |
| `change` | §1 Problem Statement, §7 Acceptance Criteria, §8 Error Scenarios | Lean spec — 3 sections only |
| `refactor` | §1 Problem Statement, §2 Bounded Context, §7 Acceptance Criteria | Lean spec — 3 sections only. ACs must prove no behavior change. |
| `security` | §1 Problem Statement, §6 Auth Perspective, §7 ACs, §8 Error Scenarios | Security-focused sections |
| `incident` follow-up | §1 Problem Statement + root cause, §7 ACs, §8 Error Scenarios | Root cause in §1 |

**For `change` and `refactor` lean specs:**
- Generate only the required sections — no N/A placeholders for skipped sections
- The spec file is shorter by design
- These CRs skip `/plan` entirely: lean spec → `/build` directly

Apply all technical defaults from `nextjs_defaults.md` without asking. Mark them `(default)`.

---

## Phase 3: Draft the Spec

Create `specs/cr/<cr-id>.spec.md` using the standard template from `nextjs_spec_template.md`.

Use the developer's exact language for business content. Apply all technical defaults for technical sections. Do not invent business rules — mark gaps as `BUSINESS DECISION REQUIRED`.

Annotation conventions:
- `(default)` — pre-decided technical default, applied automatically
- `(inferred — verify)` — derived from context, needs developer confirmation
- `BUSINESS DECISION REQUIRED` — only the developer can answer this

```markdown
# Spec: <cr-id>

| Field           | Value |
|-----------------|-------|
| CR-ID           | <cr-id> |
| Author          | |
| Date            | <today> |
| Status          | DRAFT |
| Type            | <from CR item> |
| Severity        | <from CR item> |
| Feature         | <inferred> |

## Changelog
| Date | Change | Author |
|------|--------|--------|
| <today> | Initial spec created from CR-<cr-id> | |

---

## 1. Problem Statement
## 2. Bounded Context
## 3. Screens & Routes
## 4. Backend API Dependencies
## 5. Component & State Contracts
## 6. Auth Perspective
## 7. Acceptance Criteria
## 8. Error Scenarios
## 9. Navigation & Side Effects
## 10. Non-Functional Requirements
```

---

## Phase 4: Multi-Agent Review

Once the draft is complete, review it through three lenses in parallel:

**Domain Analyst lens:**
- Is the problem statement clear and complete?
- Are all acceptance criteria testable (GIVEN/WHEN/THEN)?
- Are there missing edge cases?
- Is anything ambiguous?

**Software Architect lens:**
- Are Server vs Client Component decisions present and justified?
- Are feature layer dependencies correctly specified?
- Is the Firebase client SDK confined to `'use client'` contexts?
- Is the ApiClient used for all external calls?

**Security lens:**
- Are all write routes authenticated?
- Are input validation requirements specified?
- Are secrets properly separated (no `NEXT_PUBLIC_` secrets)?
- Is user isolation addressed for data access?

Consolidate findings. Classify each as `BLOCKER`, `WARNING`, or `SUGGESTION`.

---

## Phase 5: Revise

Resolve all `BLOCKER` and `WARNING` findings autonomously using technical knowledge and the references.

**Ask the developer only if:**
- A blocker requires a business decision
- A `BUSINESS DECISION REQUIRED` field has not been filled in

Ask ONE question at a time. Wait for the reply. Apply the answer and continue.

Repeat review → revise until no blockers remain.

---

## Phase 6: Approve and Handoff

Update the spec status to `APPROVED`. Update the CR item changelog.

Update `specs/cr/<cr-id>.cr.md`:
```
Status: IN SPEC → SPECCED
Changelog: | <today> | Spec approved | |
Artifacts: Spec: `specs/cr/<cr-id>.spec.md` ✓
```

Tell the developer:

> **Spec approved for CR-<cr-id>.**
>
> [Brief summary: what the spec covers, key decisions made, any warnings noted]
>
> Next step:
> - `feature` / `security` → run `/plan CR-<cr-id>` to generate the implementation plan and tests
> - `change` / `refactor` → run `/build CR-<cr-id>` directly — lean spec skips the plan stage
