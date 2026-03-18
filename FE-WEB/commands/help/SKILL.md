---
name: help
description: Print the full command reference for the Next.js SDM kit. Use when you want to see all available commands, the CR process flow, or how to get started.
allowed-tools: []
metadata:
  version: 1.0.0
---

Print the following reference exactly as shown — no additions, no commentary:

---

## Next.js SDM — Command Reference

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
| `/init` | Setup | One-time project setup. Creates specs/project.md, scaffolds src/. Run once before anything else. |
| `/intake` | Intake | Universal entry point. Bring anything — problem, bug, finding, request, incident, URL, file. Classifies into 6 CR types, produces a CR item. |
| `/cr <cr-id>` | Pipeline | Automated pipeline — routes by CR type. Stops only at mandatory human gates. |
| `/spec <cr-id>` | Spec | Full or lean spec — 10 sections for features, 3 sections for changes/refactors. Multi-agent review. |
| `/plan <cr-id>` | Plan | Implementation blueprint + TDD tests written before code. Human confirms approach. |
| `/build <cr-id>` | Build | TDD: red → green per layer. Code review. Containment for Critical/Security. Direct fix for bugs. |
| `/close <cr-id>` | Close | Verify ACs, update project map, document decisions, formal closure. |
| `/code-review` | Discovery | Multi-agent audit of existing Next.js code. Produces findings report. |

### CR Types & Tracks

| Type | When to use | Track |
|------|-------------|-------|
| `feature` | New capability, new screen, new user-facing behavior | `/intake` → `/spec` (10 sections) → `/plan` → `/build` → `/close` |
| `bug` | Existing behavior is broken | `/intake` → `/build` (locate → regression test → fix) → `/close` |
| `change` | Small modification — copy, style, config, limit | `/intake` → `/spec` (3 sections) → `/build` → `/close` |
| `security` | Auth gap, XSS, token storage, secrets exposed | `/intake` → `/spec` → `/plan` → `/build` → `/close` |
| `incident` | Production crash or data at risk | `/intake` → `/build` (contain first) → `/close` |
| `refactor` | Internal restructure, no behavior change | `/intake` → `/spec` (3 sections) → `/build` → `/close` |

### CR-ID Format

Auto-generated at intake: `YYMMDD-HHMMSS` — e.g. `260311-143022`

### Key Principles

- **Bring anything to `/intake`** — plain text, file, URL, Jira ticket, error log, findings report
- **Skills decide depth** — proportional output based on CR classification, not developer preference
- **Infer technical, ask business** — skills handle all technical decisions, ask only for business intent
- **Each stage enforces the previous** — no stage runs without its predecessor gate being passed

### Artifacts produced

```
specs/project.md                    ← Project memory (created by /init, updated by /close)
specs/cr/<cr-id>.cr.md              ← CR item (created by /intake, updated through lifecycle)
specs/cr/<cr-id>.spec.md            ← Spec (created by /spec — full or lean)
specs/cr/plans/<cr-id>.plan.md      ← Plan (created by /plan — features only)
src/features/<f>/__tests__/         ← TDD tests written before code (created by /plan)
specs/reviews/<scope>-<date>.md     ← Review report (created by /code-review)
```
