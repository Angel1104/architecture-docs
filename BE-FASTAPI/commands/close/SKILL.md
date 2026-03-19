---
name: close
description: Verifies, documents, and formally closes a CR. Use after /build has approved the implementation. Accepts a CR-ID. Verifies all acceptance criteria are met, surfaces lessons learned, creates follow-up CRs if needed, and appends a closure section to the CR item. Human confirms before closing.
allowed-tools: Read, Write, Edit, Bash(date:*), Glob, Grep
metadata:
  version: 1.0.0
  stage: close
  process: unified-cr-workflow
---

# Close

**Role: Tech Lead**
**Stage: CLOSE — final gate of the CR process**

You are responsible for formally closing a CR. You verify all acceptance criteria are met, document what was done and why, surface lessons learned, create follow-up CRs if needed, and close the record. This is not a rubber stamp — it is a genuine review of the outcome against the intent.

---

## Gate Check

**Requires:** An approved build from `/build`.

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found. Run `/intake` first."
3. Read the CR item — check status is `BUILT`. If not:
   - Anything earlier → "Build not complete. Run `/build CR-<cr-id>` first."
4. For `feature`, `security`, `refactor` CRs: both spec and plan files must exist.
   For `bug` CRs: only the CR item is required.
   For `change` CRs: only the spec file is required.

---

## Phase 1: Verification (silent — no output)

Verify the build outcome against the CR intent:

1. Read the CR item — load the original intent and assessment
2. Read the approved spec — load all acceptance criteria
3. Run the full test suite:
   ```bash
   pytest tests/<cr-id>/ -v
   ```
4. For each AC in the spec, confirm:
   - Is there a test covering it?
   - Does the test pass?
   - Does the implementation match the AC description?
5. Confirm no new risks or issues are visible in the codebase

---

## Phase 2: Lessons Learned Assessment (silent — no output)

Ask yourself:

- Were there surprises during spec, plan, or build that the intake didn't anticipate?
- Did the risk assessment miss anything?
- Did the process slow things down unnecessarily for this CR type?
- Did tests catch something implementation missed, or did something slip through?
- Would a different approach have been better in hindsight?
- Did this CR reveal a pattern or gap that should be addressed elsewhere in the codebase?

Flag lessons learned only if they are genuine and actionable — not every CR needs a retro.

---

## Phase 3: Follow-up CR Identification (silent — no output)

Identify any work that surfaced during this CR that was deferred:
- Items noted as "follow-up CR" in the plan or build
- Risks that were documented and accepted
- Warnings from code review that were noted but not addressed
- Any adjacent issues discovered during implementation

---

## Phase 4: Present Closure Summary

Present the closure summary to the developer:

---
**Closure Summary for CR-<cr-id>**

**Outcome:** [one sentence — what was delivered]

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|
| AC-1 | ✓ Passed | test_xxx |
| AC-2 | ✓ Passed | test_yyy |

**Decisions made during this CR:**
- [Key decision 1 — what was decided and why]
- [Key decision 2]

**Lessons learned:** [only if flagged]
- [Lesson 1 — what happened and what it suggests]

**Follow-up CRs:** [only if any]
- [Item 1 — brief description]
- [Item 2 — brief description]

**Confirm closure?** Reply yes to close, or raise anything you want addressed first.

---

Wait for the developer's confirmation before closing.

If the developer raises something: address it, re-verify, then present closure again.

---

## Phase 5: Append Closure to CR Item and Close

Append a `## Closure` section to `specs/cr/<cr-id>.cr.md` and update the status:

```
Status: BUILT → CLOSED
Changelog: | <today> | CLOSED — all ACs verified | |
```

Append to the end of the file:

```markdown
## Closure

| Field  | Value |
|--------|-------|
| Closed | <today> |

**Outcome:** <one sentence — what was delivered>

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|
| AC-1 | ✓ Passed | test_xxx |

**Decisions made during this CR:**
- <Key decision 1 — what was decided and why>

**Lessons Learned:** <only if flagged>
- <Lesson — what happened and what it suggests>

**Follow-up CRs:** <only if any, otherwise omit>
- <Item — brief description>
```

---

## Phase 5b: Update specs/project.md Module Map (feature CRs only)

If CR type is `feature`, update `specs/project.md`:

1. Read `specs/project.md`
2. Find the `## Module Map` section
3. Update or add a row for the module just built using this exact format:

```markdown
| Module | Key files | Handlers/Commands | Endpoints |
|--------|-----------|-------------------|-----------|
| <module-name> | `src/domain/models/<name>.py`, `src/application/commands/<name>.py`, `src/adapters/outbound/<name>_repository.py`, `src/adapters/inbound/<name>_router.py` | `Create<Name>Command`, `Get<Name>Query` | `POST /internal/tasks/<name>`, `GET /internal/tasks/<name>/{id}` |
```

Use the **actual file paths and names** from the implementation — not templates. Include:
- Domain model file (`app/domain/models/`)
- Application command/query handler files (`app/application/commands/` or `queries/`)
- Outbound adapter — repository implementation (`app/adapters/outbound/`)
- Inbound adapter — FastAPI router (`app/adapters/inbound/`)
- Handler/command class names
- Exposed endpoint routes (e.g. `POST /internal/tasks/process-document`)

This keeps the project map current so future bug CRs can locate files without scanning the codebase.

---

## Phase 7: Create Follow-up CR Items

For each follow-up item identified, create a minimal CR item in `OPEN` state:

```markdown
# CR-<new-cr-id>

| Field    | Value |
|----------|-------|
| CR-ID    | <new-cr-id> |
| Date     | <today> |
| Status   | OPEN |
| Origin   | Follow-up from CR-<parent-cr-id> |
| Summary  | <one line> |
```

Tell the developer: "Follow-up CR-<new-cr-id> created. Run `/intake CR-<new-cr-id>` when ready to assess and prioritize it."

---

## Phase 8: Final Handoff

Tell the developer:

> **CR-<cr-id> is closed.**
>
> [Brief summary: what was delivered, AC count, any lessons learned flagged]
>
> [If follow-up CRs: "Follow-up CRs created: [list]. Run `/intake` on each when ready."]
>
> [If lessons learned: "Lessons learned documented in the closure report — worth reviewing before the next similar CR."]
