---
name: help
description: Print the full command reference for the NestJS SDM kit. Use when you want to see all available commands, the CR process flow, or how to get started.
allowed-tools: []
metadata:
  version: 1.0.0
---

Print the following reference exactly as shown — no additions, no commentary:

---

## NestJS SDM — Command Reference

### The CR Process

Everything is a Change Request. One process, no exceptions.

```
/code-review (optional discovery)
        ↓
/intake → /cr <cr-id>   ← automated pipeline (recommended)

         or step by step:
/intake → /spec → /plan → /build → /close

Critical incident fast track:
/intake → /build → /close
```

### Commands

| Command | Stage | What it does |
|---------|-------|--------------|
| `/intake` | Intake | Universal entry point. Bring anything — problem, bug, finding, request, incident, URL, file. Classifies, assesses risk, produces a CR item. |
| `/cr <cr-id>` | Pipeline | Automated pipeline — runs spec → plan → build → close in sequence. Stops only at mandatory human gates. |
| `/spec <cr-id>` | Spec | Full spec stage — draft, multi-agent review, revise, approve. Proportional to the CR. |
| `/plan <cr-id>` | Plan | Implementation blueprint + test skeletons. Presents options, recommends one, human confirms. |
| `/build <cr-id>` | Build | Implement layer by layer + code review + approve. Containment first for Critical CRs. |
| `/close <cr-id>` | Close | Verify ACs, document decisions, lessons learned, follow-up CRs, formal closure. |
| `/code-review` | Discovery | Multi-agent audit of existing NestJS code. Produces findings report. Feed output into `/intake`. |

### CR Severity & Tracks

| Severity | Meaning | Track |
|----------|---------|-------|
| Critical | Production down, data at risk, security breach | `/intake` → `/build` (contain + fix) → `/close` |
| High | Degraded, significant impact, time-sensitive | `/intake` → `/spec` (lean) → `/plan` → `/build` → `/close` |
| Normal | Everything else | `/intake` → `/spec` → `/plan` → `/build` → `/close` |

### CR-ID Format

Auto-generated at intake: `YYMMDD-HHMMSS` — e.g. `260311-143022`

### Key Principles

- **Bring anything to `/intake`** — plain text, file, URL, Jira ticket, error log, findings report
- **Skills decide depth** — proportional output based on CR classification, not developer preference
- **Infer technical, ask business** — skills handle all technical decisions, ask only for business intent
- **Each stage enforces the previous** — no stage runs without its predecessor gate being passed

### Artifacts produced

```
specs/cr/<cr-id>.cr.md              ← CR item (created by /intake, updated through lifecycle)
specs/cr/<cr-id>.spec.md            ← Spec (created by /spec)
specs/cr/plans/<cr-id>.plan.md      ← Plan (created by /plan)
src/modules/<m>/                    ← Test skeletons (created by /plan)
specs/reviews/<scope>-<date>.md     ← Review report (created by /code-review)
```
