---
name: code-review
description: Discovery tool — multi-agent code review that surfaces security issues, architecture violations, and quality problems in existing Next.js code. Use when you want to audit the codebase, review a feature, review a specific path, or produce a findings report. Findings feed into /intake to become CR items.
allowed-tools: Read, Bash, Glob, Grep, Agent
metadata:
  version: 1.0.0
  role: discovery
  feeds-into: intake
---

# Code Review

**Role: Technical Auditor**
**Purpose: Discovery — surfaces findings that feed into the CR process via `/intake`**

This skill reviews Next.js code and produces a findings report. It does not fix anything and does not create CR items — that is `/intake`'s job. The output of this skill is the input to `/intake`.

---

## Pre-Flight

Determine review scope from `$ARGUMENTS`:

**No argument — full codebase review:**
- Review all of `src/features/` and `src/core/`

**Path argument** (contains `/` or ends with a file extension):
- Review the specified path directly (e.g. `src/features/auth/`)
- If the path does not exist, stop and tell the user

**Feature name** (kebab-case, no slashes):
- Locate code matching the feature name in `src/features/<feature>/`
- If a spec exists at `specs/cr/<feature>.spec.md`, read it as the contract the code must satisfy

**CR-ID** (format `YYMMDD-HHMMSS`):
- Review code produced by that CR
- Load spec and plan from `specs/cr/`

---

## Review Orchestration

Launch all three reviewer agents in parallel.

### Agent 1: sw-architect

- Verify domain layer has no framework imports (React, Next.js, Firebase, fetch)
- Verify `'use client'` is used only when required — not as default
- Verify Server Components do not use Firebase client SDK, useState, or event handlers
- Verify application hooks import only from domain layer
- Verify all API calls go through ApiClient — no raw fetch in hooks or components
- Verify presentation components have no business logic (no if/else on business rules in JSX)
- Check for missing repository interfaces (concrete impl without domain interface)

### Agent 2: security-engineer

- Check for hardcoded secrets, API keys, tokens in code
- Verify no secrets in `NEXT_PUBLIC_` environment variables
- Verify all authenticated routes have auth guards
- Verify Firebase client SDK is not used in Server Components
- Check for `dangerouslySetInnerHTML` with unvalidated user input (XSS risk)
- Verify all forms validate with Zod before submission
- Check for exposed stack traces or internal errors in error UI
- Check for hardcoded HTTP URLs (should be HTTPS in production)

### Agent 3: nextjs-engineer

**Performance:**
- Check for missing `loading.tsx` on data-fetching routes
- Check for missing error boundaries on routes
- Verify `const` used for static components where possible
- Verify images use `next/image` with proper sizing
- Check for missing Suspense boundaries around async components

**Standards:**
- Check for obvious TypeScript issues: missing types, `any` usage, non-null assertions
- Verify error paths are handled — no swallowed errors, no empty catch blocks
- Check test coverage against acceptance criteria (if spec exists)
- Verify user isolation tests exist for authenticated features
- Verify react-hook-form + Zod used for all forms (no uncontrolled inputs)
- Check for TODO/FIXME comments that should be tracked

---

## Synthesis

Produce a consolidated findings report:

```
## Code Review: <scope>
Date: <today>

### Overall Verdict: APPROVED | REVISIONS NEEDED | CRITICAL ISSUES

### Summary
- Critical: X findings (block work)
- High: Y findings (fix before next release)
- Medium/Low: Z findings (track in backlog)

### Critical Findings
<finding> — <file:line if known> — [Security | Architecture | Quality]

### High Findings
<finding> — <file:line if known> — [Security | Architecture | Quality]

### Medium / Low Findings
<finding> — <file:line if known>

### Architecture Notes
<Server/Client split issues, dependency violations, missing abstractions>

### Test Coverage
- ACs covered: X / Y (if spec exists)
- Missing: <list>
- Auth/isolation tests: present | missing
```

---

## Handoff — Create CR Items

After the report, if there are any findings that require action:

1. **Save the report** — always save to `specs/reviews/<scope>-<date>.md`

2. **Offer to create CR items immediately:**

> "I found **X critical** and **Y high** findings. Want me to create CR items for these now?
>
> I'll run `/intake` on the report and produce a prioritized set of CR items ready for the process — you confirm or adjust before I write anything.
>
> Just say **yes** to proceed, or **skip** to handle it manually later."

3. **If the developer says yes:**
   - Run `/intake specs/reviews/<scope>-<date>.md`
   - `/intake` will classify each finding, group related ones, assess risk and priority, and produce CR items
   - Present the full CR assessment before writing any CR files — wait for confirmation

4. **If the verdict is APPROVED** and no findings require action:
   - State this clearly: "No CR items needed — codebase is clean."
   - Do not offer to create CRs.
