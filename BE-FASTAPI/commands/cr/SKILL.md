---
name: cr
description: Fully automated CR pipeline — spec through close. Use after /intake has produced a CR item. Accepts a CR-ID. Runs spec, plan, build, and close in sequence. Stops only at mandatory human decision gates. Everything else runs automatically.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
metadata:
  version: 1.0.0
  stage: pipeline
  process: unified-cr-workflow
---

# CR — Automated Pipeline

**Role: Technical Lead**
**Stage: PIPELINE — spec → plan → build → close**

You are responsible for running the full CR pipeline automatically from spec to close. You stop only when a genuine human decision is required. You do not ask for confirmations the human doesn't need to make. You do not ask technical questions you can answer yourself.

---

## Gate Check

1. Read `$ARGUMENTS` — extract the CR-ID
2. Locate `specs/cr/<cr-id>.cr.md` — if missing, stop:
   > "No CR item found for <cr-id>. Run `/intake` first to create the CR item."
3. Read the CR item — load **type**, severity, intent, assessment
4. Determine the track from CR **type**:

| CR Type | Track | Stages |
|---------|-------|--------|
| `feature` | Full | spec (10 sections) → plan → build → close |
| `bug` | Minimal | build only (locate → regression test → fix) → close |
| `change` | Lean | spec (3 sections) → build → close (no plan) |
| `security` | Full | spec → plan → build → close |
| `incident` | Containment-first | build (containment first) → close |
| `refactor` | Lean | spec (3 sections) → build → close (no plan) |

5. Report the starting state:
   > "CR-<cr-id> loaded. Type: <type> | Track: <track>. Starting at: <stage>."

---

## Resume Logic

If the CR item already has a status beyond OPEN, resume from the appropriate stage:

| CR Status | Resume at |
|-----------|-----------|
| OPEN | first stage for this type (see track table above) |
| SPECCED | plan (if `feature`/`security`) or build (if `change`/`refactor`) |
| PLANNED | build |
| BUILT | close |
| CLOSED | nothing — tell the developer the CR is already closed |

---

## Mandatory Human Gates

Stop and wait for human confirmation at these points only:

| Gate | When | What to ask |
|------|------|-------------|
| **Spec business decision** | A spec review surfaces a question only the human can answer | Ask the specific question, nothing else |
| **Implementation option** | Plan identifies multiple valid approaches | Present options with trade-offs, give a clear recommendation, ask human to confirm |
| **Unexpected risk** | Build surfaces a risk not in the spec or plan | State the risk clearly, ask: proceed, adjust scope, or create follow-up CR? |
| **Closure confirmation** | Before formally closing | Present closure summary, ask for confirm |

All other decisions are made automatically.

---

## Stage 1: SPEC

**Skip this stage for `bug` and `incident` types — go directly to Stage 3: BUILD.**

1. Read the CR item — load intent, type, severity, assessment
2. Load `references/technical_defaults.md` and the spec template
3. Draft the spec proportional to the CR type:
   - `feature` / `security` → full 10-section spec
   - `change` / `refactor` → lean 3-section spec (§1 Problem Statement, §7 ACs, §8 Error Scenarios)
4. Run multi-agent spec review (domain-analyst, sw-architect, security-engineer)
5. Resolve all blockers autonomously
6. **STOP — Spec approval required.**
   Present the complete spec, then ask:
   > "Spec ready for CR-<cr-id>. Before you confirm, check:
   > - [ ] Acceptance criteria match your intent exactly — not vague, not missing cases
   > - [ ] Out-of-scope section is correct — nothing over-engineered, nothing missing
   > - [ ] Error scenarios cover your real edge cases
   > - [ ] No open business questions remain
   >
   > Reply **'approved'** to proceed, or tell me what to change."

   Wait. Apply any corrections. Re-present if changed.
7. Lock the approved spec at `specs/cr/<cr-id>.spec.md`
8. Update CR status: OPEN → SPECCED
9. Report: "Spec approved. Moving to [plan / build]."
   - `feature` / `security` → move to Stage 2: PLAN
   - `change` / `refactor` → skip to Stage 3: BUILD

---

## Stage 2: PLAN

**Skip this stage for `bug`, `change`, `refactor`, and `incident` types — go directly to Stage 3: BUILD.**

1. Read the approved spec
2. Identify implementation options
3. If multiple valid approaches exist:
   - Present options with honest trade-offs
   - Give a clear recommendation with reasoning
   - **STOP** → wait for human to confirm approach
4. Generate layered implementation blueprint
5. Generate test skeletons (FakeRepository + unit tests)
6. Re-assess risk at implementation level
7. **STOP** only if a new HIGH risk is found → present, ask how to proceed
8. Write `specs/cr/plans/<cr-id>.plan.md`
9. Update CR status: SPECCED → PLANNED
10. Report: "Plan confirmed. Moving to build."

---

## Stage 3: BUILD

**For `incident` type — containment first:**
1. Advise immediate containment steps based on code and infrastructure knowledge
2. **STOP** → wait for human to confirm containment is in place
3. Then proceed with fix

**For `bug` type — TDD regression fix:**
1. Read `specs/project.md` Module Map — locate the affected file(s)
2. Reproduce the bug from the CR description
3. Write regression test first (TDD red) — GIVEN/WHEN/THEN naming
4. Run test: `pytest <specific-test-file> -v` — must FAIL
5. Apply minimal fix — change only what is needed
6. Run test again — must PASS (green)
7. Run full suite: `pytest`
8. Type check: `mypy src/`
9. Update CR status: OPEN → BUILT

**For `feature`, `change`, `refactor`, `security` — layer by layer:**
1. Read the plan and test skeletons
2. For each layer — TDD: run tests (RED) → implement → run tests (GREEN)
3. Layer order: domain → application → adapters outbound → adapters inbound → config
4. Run: `pytest src/<layer>/ -v` per layer
5. If a layer fails: diagnose, fix, re-run — do not proceed with failing tests
6. Run multi-agent code review on completion
7. Resolve all review findings autonomously unless a finding requires a business decision
8. **STOP** only if an unexpected risk surfaces → state it, ask how to proceed
9. Type check: `mypy src/`
10. Update CR status: PLANNED → BUILT (or OPEN → BUILT for `change`/`refactor`)
11. Report: "Build complete. Moving to close."

---

## Stage 4: CLOSE

Run the close stage for CR-<cr-id>:

1. Verify all acceptance criteria are met
2. Confirm all tests pass
3. Assess lessons learned — flag only if genuine and actionable
4. Identify any follow-up CRs from deferred items or discovered issues
5. Present closure summary:

---
**Closure Summary — CR-<cr-id>**

**Outcome:** [one sentence]

**Acceptance Criteria:**
| AC | Status | Test |
|----|--------|------|

**Decisions made:** [key decisions with reasoning]

**Lessons learned:** [only if flagged]

**Follow-up CRs:** [only if any]

---

6. **STOP — Closure confirmation required.**
   > "Ready to close CR-<cr-id>. Before you confirm:
   > - [ ] You've manually tested the happy path in your environment
   > - [ ] The AC table above matches what was actually built
   > - [ ] Any follow-up CRs are noted and you know who owns them
   >
   > Reply **'close it'** to formally close, or raise anything you want addressed first."

   Wait for confirmation.
7. On confirm:
   - Append `## Closure` section to `specs/cr/<cr-id>.cr.md`
   - Update CR status: BUILT → CLOSED
   - Create follow-up CR items if any
8. Report final handoff:
   > **CR-<cr-id> is closed.**
   > [Summary: what was delivered, AC count, lessons learned if any]
   > [Follow-up CRs if created: "Run `/cr <new-cr-id>` when ready."]
