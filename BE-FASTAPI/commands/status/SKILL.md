---
name: status
description: Shows all CRs in this project — what's open, in progress, blocked, and recently closed. No arguments needed. Use to get a quick overview of what's in flight before starting new work.
allowed-tools: Read, Glob, Bash(date:*)
metadata:
  version: 1.0.0
  stage: utility
  process: unified-cr-workflow
---

# Status

**Role: Tech Lead**
**Stage: UTILITY — project overview, no gate**

You generate a complete status report of all CRs in this project. Silent phase first, then one clean output.

---

## Phase 1: Collect (silent — no output)

1. Get today's date
2. Read `specs/project.md` — extract the project name
   - If not found, use "this project"
3. Glob `specs/cr/*.cr.md` — read each file, extract:
   - CR-ID
   - Type
   - Severity
   - Status
   - Summary (first line of the `## Summary` section)
   - Closed date (from `## Closure` section, if present)
4. For each CR, check for missing artifacts:
   - Status is `SPECCED` but `specs/cr/<cr-id>.spec.md` does not exist → **BLOCKED**
   - Status is `PLANNED` but `specs/cr/plans/<cr-id>.plan.md` does not exist → **BLOCKED**
5. Sort CRs into groups:
   - **In Progress**: Status is `SPECCED`, `PLANNED`, or `BUILT`
   - **Blocked**: Any CR where a required artifact is missing
   - **Open**: Status is `OPEN`
   - **Closed**: Status is `CLOSED` — keep only the 5 most recently closed
6. Determine suggested next CR: highest severity open CR, or oldest open if tied

---

## Phase 2: Present

Output the status report:

```
## Project Status — <name>
<today>

### In Progress
| CR-ID | Type | Severity | Status | Summary |
|-------|------|----------|--------|---------|
| ...   | ...  | ...      | ...    | ...     |

*(empty: no CRs in progress)*

### Blocked
| CR-ID | Status | Missing artifact |
|-------|--------|-----------------|
| ...   | ...    | ...             |

*(empty: no blocked CRs)*

### Open (not started)
| CR-ID | Type | Severity | Summary |
|-------|------|----------|---------|
| ...   | ...  | ...      | ...     |

*(empty: no open CRs)*

### Recently Closed (last 5)
| CR-ID | Type | Closed | Summary |
|-------|------|--------|---------|
| ...   | ...  | ...    | ...     |

*(empty: nothing closed yet)*

---
**Total:** X open · Y in progress · Z blocked · W closed

**Suggested next:** CR-<id> — <reason: "Critical severity" / "oldest open" / "unblocked and ready">
```

If `specs/cr/` is empty or does not exist:
> "No CRs found. Run `/intake <description>` to create the first CR."
