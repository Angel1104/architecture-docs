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
3. Read the CR item — load type, severity, intent, assessment
4. Determine the track:
   - **Critical** → skip spec and plan, go straight to build (containment + fix), then close
   - **High / Normal** → full pipeline: spec → plan → build → close
5. Report the starting state:
   > "CR-<cr-id> loaded. Track: <track>. Starting at: <stage>."

---

## Resume Logic

If the CR item already has a status beyond OPEN, resume from the appropriate stage:

| CR Status | Resume at |
|-----------|-----------|
| OPEN | spec |
| SPECCED | plan |
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

1. Read the CR item — load intent, type, severity, assessment
2. Load `references/nestjs_defaults.md` and `references/nestjs_spec_template.md`
3. Draft the spec proportional to the CR
4. Run multi-agent spec review (domain-analyst, sw-architect, security-engineer)
5. Resolve all blockers autonomously
6. **STOP** only if a business decision is needed → ask, wait, continue
7. Lock the approved spec at `specs/cr/<cr-id>.spec.md`
8. Update CR status: OPEN → SPECCED
9. Report: "Spec approved. Moving to plan."

---

## Stage 2: PLAN

1. Read the approved spec
2. Identify implementation options
3. If multiple valid approaches exist:
   - Present options with honest trade-offs
   - Give a clear recommendation
   - **STOP** → wait for human to confirm approach
4. Generate layered implementation blueprint
5. Generate proportional test skeletons in `src/modules/<module>/`
6. Re-assess risk at implementation level
7. **STOP** only if a new HIGH risk is found → present, ask how to proceed
8. Write `specs/cr/plans/<cr-id>.plan.md`
9. Update CR status: SPECCED → PLANNED
10. Report: "Plan confirmed. Moving to build."

---

## Stage 3: BUILD

**For Critical track — containment first:**
1. Advise immediate containment steps
2. Wait for human to confirm containment is in place
3. Then proceed with fix

**For all tracks:**
1. Read the plan and test skeletons
2. Implement layer by layer: domain → application → infrastructure → interface → module wiring
3. Run tests at each layer: `npx jest src/modules/<module>/ --runInBand`
4. If a layer fails: diagnose, fix, re-run — do not proceed with failing tests
5. Run multi-agent code review on completion
6. Resolve all review findings autonomously unless a finding requires a business decision
7. **STOP** only if an unexpected risk surfaces → state it, ask how to proceed
8. Verify TypeScript: `npx tsc --noEmit`
9. Update CR status: PLANNED → BUILT
10. Report: "Build complete. Moving to close."

---

## Stage 4: CLOSE

1. Verify all acceptance criteria are met
2. Confirm all tests pass: `npx jest --runInBand`
3. Assess lessons learned — flag only if genuine and actionable
4. Identify any follow-up CRs from deferred items
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

**Confirm closure?**

---

6. **STOP** → wait for human confirmation
7. On confirm:
   - Append `## Closure` section to `specs/cr/<cr-id>.cr.md`
   - Update CR status: BUILT → CLOSED
   - Create follow-up CR items if any
8. Report final handoff:
   > **CR-<cr-id> is closed.**
   > [Summary: what was delivered, AC count, lessons learned if any]
   > [Follow-up CRs if created: "Run `/cr <new-cr-id>` when ready."]
