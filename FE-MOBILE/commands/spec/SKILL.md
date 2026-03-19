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
- Read `references/flutter_defaults.md`
- Read `references/flutter_spec_template.md`

**Codebase scan:**
- Scan `specs/cr/` for related or dependent specs
- Scan `lib/features/` for existing code related to this CR
- Scan `lib/core/` for shared utilities this CR may depend on
- Identify which existing acceptance criteria (if any) are affected

---

## Phase 2: Proportionality Calibration (silent — no output)

Before drafting, decide the depth of each spec section based on the CR item:

| CR type | Sections required | Notes |
|---------|------------------|-------|
| `feature` (Normal) | All 10 sections | Full spec |
| `feature` (High) | All 10 sections, leaner content | |
| `change` | §1 Problem Statement, §7 Acceptance Criteria, §8 Error Scenarios | Lean — 3 sections only |
| `refactor` | §1 Problem Statement, §2 Bounded Context, §7 Acceptance Criteria | Lean — ACs must prove no behavior change |
| `security` | §1 Problem Statement, §6 Auth Perspective, §7 ACs, §8 Error Scenarios | |
| `incident` follow-up | §1 Problem Statement + root cause, §7 ACs, §8 Error Scenarios | |

**For `change` and `refactor`:** generate only required sections. These CRs skip `/plan` — lean spec → `/build` directly.

A section that is not relevant to this CR should be marked `N/A — not applicable to this CR type` rather than left blank or padded with filler.

Apply all technical defaults from `flutter_defaults.md` without asking. Mark them `(default)`.

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
| Feature         | <lib/features/<name>/> |

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
- **Feature folder**: `lib/features/<name>/`
- **Entities owned**: <domain entities this feature owns>
- **Depends on**: <other features or core services>
- **Backend endpoints consumed**: <list API routes>

## 3. Screens & Entry Points
| Screen | Route | Entry Point | Auth Required |
|--------|-------|-------------|---------------|

## 4. Backend API Dependencies
| Endpoint | Method | Request | Response | Error Codes |
|----------|--------|---------|----------|-------------|

## 5. Controller & State Contracts
| Controller | State Type | States | Actions |
|------------|-----------|--------|---------|

```dart
// Sealed state — freezed
@freezed
class <Feature>State with _$<Feature>State {
  const factory <Feature>State.initial() = _Initial;
  const factory <Feature>State.loading() = _Loading;
  const factory <Feature>State.loaded(<Entity> data) = _Loaded;
  const factory <Feature>State.error(AppError error) = _Error;
}
```

## 6. Auth & User Context
- **Auth state required**: `authenticated` (guard blocks `initializing` + `unauthenticated`)
- **userId source**: `AuthService` → JWT → passed to all repository methods
- **Token injection**: `AuthInterceptor` via `AuthService.getToken()` — (default)
- **401 handling**: `AuthInterceptor` calls `AuthService.refreshToken()`, retries once; on failure calls `AuthService.logout()` — (default)

## 7. Acceptance Criteria
- [ ] AC-1: GIVEN ... WHEN ... THEN ...

## 8. Error Scenarios
| Error Condition | AppError | User Message | Retryable? |
|-----------------|----------|--------------|------------|

## 9. Navigation & Side Effects
| Trigger | Action | Notes |
|---------|--------|-------|

## 10. Non-Functional Requirements
<apply defaults from flutter_defaults.md — mark (default). Flag BUSINESS DECISION REQUIRED where needed>
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
- Do screens/routes map cleanly to a feature folder in Clean Architecture?
- Are domain entities pure Dart — no Flutter SDK, Dio, or auth SDK imports?
- Are repository interfaces abstract (domain layer) with concrete implementations in data/?
- Does the dependency direction comply: `domain/ → nothing`, `data/ → domain/`, `presentation/ → domain/`?
- Is the controller state sealed with `AppError` in the error variant?

**Security lens:**
- Is every data access scoped to `userId` from the authenticated user?
- Does the GoRouter guard block `initializing` + `unauthenticated` states for all new routes?
- Are tokens managed by `AuthService` — never stored manually?
- Are there input validation gaps at the data layer boundary?
- Does the CR introduce any cross-user data access risk?

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
> Next step:
> - `feature` / `security` → run `/plan CR-<cr-id>` to generate the implementation plan and tests
> - `change` / `refactor` → run `/build CR-<cr-id>` directly — lean spec skips the plan stage
