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
4. Locate `specs/cr/<cr-id>.spec.md` and `specs/cr/plans/<cr-id>.plan.md` — both must exist.

---

## Phase 1: Verification (silent — no output)

1. Read the CR item — load the original intent and assessment
2. Read the approved spec — load all acceptance criteria
3. Run the full test suite:
   ```bash
   npx jest --runInBand
   ```
4. For each AC in the spec, confirm:
   - Is there a test covering it?
   - Does the test pass?
   - Does the implementation match the AC description?
5. Confirm TypeScript compiles: `npx tsc --noEmit`
6. Confirm no new risks or issues are visible in the codebase

---

## Phase 2: Lessons Learned Assessment (silent — no output)

Ask yourself:
- Were there surprises during spec, plan, or build that the intake didn't anticipate?
- Did the risk assessment miss anything?
- Did tests catch something implementation missed?
- Did this CR reveal a pattern or gap that should be addressed elsewhere?
- Were there any RLS or tenant isolation gaps found during review?

Flag lessons learned only if they are genuine and actionable.

---

## Phase 3: Follow-up CR Identification (silent — no output)

Identify any work that surfaced during this CR that was deferred:
- Items noted as "follow-up CR" in the plan or build
- Risks that were documented and accepted
- Warnings from code review that were noted but not addressed
- Any adjacent issues discovered during implementation

---

## Phase 4: Present Closure Summary

---
**Closure Summary for CR-<cr-id>**

**Outcome:** [one sentence — what was delivered]

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|
| AC-1 | ✓ Passed | test name |
| AC-2 | ✓ Passed | test name |

**Decisions made during this CR:**
- [Key decision 1 — what was decided and why]

**Lessons learned:** [only if flagged]
- [Lesson — what happened and what it suggests]

**Follow-up CRs:** [only if any]
- [Item — brief description]

**Confirm closure?** Reply yes to close, or raise anything you want addressed first.

---

Wait for the developer's confirmation before closing.

---

## Phase 5: Append Closure to CR Item and Close

Update `specs/cr/<cr-id>.cr.md`:
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

**Outcome:** <one sentence>

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|
| AC-1 | ✓ Passed | test name |

**Decisions made during this CR:**
- <Key decision — what was decided and why>

**Lessons Learned:** <only if flagged>
**Follow-up CRs:** <only if any, otherwise omit>
```

---

## Phase 6: Create Follow-up CR Items

For each follow-up item identified, create a minimal CR item in `OPEN` state at `specs/cr/<new-cr-id>.cr.md`.

---

## Phase 7: Final Handoff

Tell the developer:

> **CR-<cr-id> is closed.**
>
> [Brief summary: what was delivered, AC count, any lessons learned flagged]
>
> [If follow-up CRs: "Follow-up CRs created: [list]. Run `/intake` on each when ready."]
