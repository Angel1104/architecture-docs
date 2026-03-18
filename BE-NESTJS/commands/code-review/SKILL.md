---
name: code-review
description: Discovery tool — multi-agent code review that surfaces security issues, architecture violations, and quality problems in existing NestJS code. Use when you want to audit the codebase, review a module, review a specific path, or produce a findings report. Findings feed into /intake to become CR items.
allowed-tools: Read, Bash, Glob, Grep, Agent
metadata:
  version: 1.0.0
  role: discovery
  feeds-into: intake
---

# Code Review

**Role: Technical Auditor**
**Purpose: Discovery — surfaces findings that feed into the CR process via `/intake`**

This skill reviews NestJS code and produces a findings report. It does not fix anything and does not create CR items — that is `/intake`'s job. The output of this skill is the input to `/intake`.

---

## Pre-Flight

Determine review scope from `$ARGUMENTS`:

**No argument — full codebase review:**
- Review all of `src/modules/` and `src/shared/`

**Path argument** (contains `/` or ends with a file extension):
- Review the specified path directly (e.g. `src/modules/auth/`)
- If the path does not exist, stop and tell the user

**Module name** (kebab-case, no slashes):
- Locate code matching the module name in `src/modules/<module>/`
- If a spec exists at `specs/cr/<module>.spec.md`, read it as the contract the code must satisfy

**CR-ID** (format `YYMMDD-HHMMSS`):
- Review code produced by that CR
- Load spec and plan from `specs/cr/`

---

## Review Orchestration

Launch all three reviewer agents in parallel.

### Agent 1: sw-architect

- Verify domain layer has no NestJS, Prisma, Firebase, or HTTP framework imports
- Verify `application/` imports only from `domain/` — no Prisma or infrastructure imports
- Verify `infrastructure/` implements domain port interfaces (not inheriting from concrete classes)
- Verify controllers do not contain business logic — only use case invocation
- Verify all multi-tenant queries use `prisma.withTenant()` in the infrastructure layer
- Verify Cloud Tasks side effects are dispatched from use cases (not from controllers)
- Check for missing port interfaces (concrete implementation without domain interface)

### Agent 2: security-engineer

- Check for hardcoded secrets, API keys, tokens in code
- Verify `@UseGuards(FirebaseAuthGuard)` on all write endpoints and tenant-data endpoints
- Verify `tenant_id` is NEVER taken from request body, params, or query — always from `req.user`
- Verify all multi-tenant Prisma queries are inside `prisma.withTenant()` (RLS enforcement)
- Verify Cloud Task handler endpoints use OIDC guard (not Firebase Auth guard)
- Verify `firebase.auth().verifyIdToken()` is used (not manual JWT decode)
- Check for missing Zod validation on controller inputs
- Check for exposed stack traces or internal error details in RFC 7807 error responses
- Check for PII in log statements

### Agent 3: backend-engineer

**Architecture Standards:**
- Verify TypeScript strict mode compliance — no implicit `any`, no unnecessary non-null assertions
- Verify RFC 7807 error format — all domain errors mapped in `DomainExceptionFilter`
- Verify cursor-based pagination (`PaginatedResponse<T>`) on all list endpoints
- Check for missing `traceId` in error responses
- Verify `withTenant()` wraps all tenant-scoped queries (double-check for sw-architect finding)

**Testing:**
- Check test coverage against acceptance criteria (if spec exists)
- Verify tenant isolation tests exist for authenticated modules
- Verify no `jest.mock()` of Prisma in use case tests — fake repository pattern should be used
- Check for TODO/FIXME comments that should be tracked

**Code Quality:**
- Check for missing error boundaries (unhandled promise rejections in async use cases)
- Check for direct `process.env` access outside `ConfigService`

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
<Hexagonal boundary violations, RLS gaps, Cloud Tasks misuse, missing port interfaces>

### Test Coverage
- ACs covered: X / Y (if spec exists)
- Missing: <list>
- Tenant isolation tests: present | missing
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
