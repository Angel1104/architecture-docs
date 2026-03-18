---
name: spec
description: Full spec stage for a CR — draft, multi-agent review, revise, approve. Use after /intake has produced a CR item. Accepts a CR-ID. Produces an approved spec proportional to the CR size and risk. Handles everything from a 3-section lean spec for a small fix to a full 10-section spec for a new feature.
allowed-tools: Read, Write, Edit, Bash(date:*), Bash(mkdir:*), Glob, Grep, Agent
metadata:
  version: 1.0.0
  stage: spec
  process: unified-cr-workflow
---

# Spec

**Role: Domain Analyst + Senior Software Architect**
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
- Read `.claude/references/unified_workflow.md`
- Read `.claude/references/technical_defaults.md`
- Read `.claude/references/hexagonal_architecture.md`
- Read `.claude/references/tenant_isolation.md`

**If Flutter or fullstack:**
- Read `.claude/references/flutter_defaults.md`
- Read `.claude/references/flutter_spec_template.md`

**Codebase scan:**
- Scan `specs/cr/` for related or dependent specs
- Scan `src/domain/models/` for existing entities this CR touches
- Scan `src/domain/ports/` for existing ports this CR might reuse or extend
- Scan `src/` or `lib/features/` for existing code related to this CR
- Identify which existing acceptance criteria (if any) are affected

---

## Phase 2: Proportionality Calibration (silent — no output)

Before drafting, decide the depth of each spec section based on the CR item:

| CR characteristic | Spec depth |
|---|---|
| New module, new domain concept | All sections fully populated |
| New endpoint on existing pattern | Problem statement, ports, adapter contracts, ACs, errors |
| Security fix, tenant isolation gap | Problem statement, tenant isolation, ACs, error scenarios |
| Refactor, structural improvement | Problem statement, bounded context, ACs only |
| Incident follow-up | Problem statement, root cause, ACs, errors |

A section that is not relevant to this CR should be marked `N/A — not applicable to this CR type` rather than left blank or padded with filler.

Apply all technical defaults from `technical_defaults.md` without asking. Mark them `(default)`.

---

## Phase 3: Draft the Spec

Create `specs/cr/<cr-id>.spec.md` using the standard template structure.

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
| Bounded Context | <inferred> |

## Changelog
| Date | Change | Author |
|------|--------|--------|
| <today> | Initial spec created from CR-<cr-id> | |

---

## 1. Problem Statement
<what the CR addresses, for whom, and why — from the CR item intent>

### Out of Scope
<what this spec explicitly does not cover>

## 2. Bounded Context
- **Owns**: <entities and data>
- **Depends on**: <other contexts>
- **Publishes**: <domain events, if any>

## 3. Inbound Ports
| Port Name | Type | Description | Auth Required | Roles Permitted | Read-RBAC |
|-----------|------|-------------|---------------|-----------------|-----------|

## 4. Outbound Ports
| Port Name | Type | Description | Bridge/Gateway? |
|-----------|------|-------------|-----------------|

## 5. Adapter Contracts

### Inbound Adapters
| Port | Adapter | Protocol | Endpoint/Trigger | Request Schema | Response Schema |
|------|---------|----------|------------------|----------------|-----------------|

### Outbound Adapters
| Port | Adapter | Technology | Gateway Concerns |
|------|---------|------------|------------------|

## 6. Tenant Isolation Strategy
<apply defaults from tenant_isolation.md — mark (default)>
<if N/A for this CR type, state why>

## 7. Acceptance Criteria
- [ ] AC-1: GIVEN ... WHEN ... THEN ...

## 8. Error Scenarios
| Error Condition | Domain Exception | HTTP | Retryable? | User Message |
|-----------------|-----------------|------|------------|--------------|

## 9. Side Effects
| Domain Event | Triggered By | Consumer | Sync/Async | Failure Policy |
|--------------|-------------|----------|------------|----------------|

## 10. Non-Functional Requirements
<apply defaults — mark (default). Flag BUSINESS DECISION REQUIRED where needed>
```

---

## Phase 4: Multi-Agent Review

Once the draft is complete, review it through three lenses. Run these in parallel:

**Domain Analyst lens:**
- Is the problem statement clear and complete?
- Are all acceptance criteria testable (GIVEN/WHEN/THEN)?
- Are there missing edge cases given the CR type and domain?
- Is anything ambiguous or open to interpretation?

**Software Architect lens:**
- Are ports defined as interfaces, not implementations?
- Does the dependency direction comply with hexagonal architecture?
- Are there boundary violations or missing ports?
- Is the bounded context correctly scoped?

**Security lens:**
- Is tenant isolation addressed for every data access path?
- Are all write endpoints authenticated?
- Are there injection risks or unvalidated inputs?
- Does the CR introduce any cross-tenant risk?

Consolidate findings. Classify each as:
- `BLOCKER` — must be resolved before approval
- `WARNING` — should be addressed, can be noted
- `SUGGESTION` — optional improvement

---

## Phase 5: Revise

Resolve all `BLOCKER` and `WARNING` findings autonomously using technical knowledge and the references.

**Ask the developer only if:**
- A blocker requires a business decision (e.g. "should admins be able to do X?")
- A warning involves a trade-off that only the developer can make (e.g. scope expansion)
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
> Next step: run `/plan CR-<cr-id>` to generate the implementation plan and tests.
