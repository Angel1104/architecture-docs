---
name: code-review
description: Discovery tool — multi-agent code review that surfaces security issues, architecture violations, and quality problems in existing code. Use when you want to audit the codebase, review a feature, review a specific path, or produce a findings report before deciding what to fix. Findings feed into /intake to become CR items. Spawns sw-architect, security-engineer, and backend/flutter-engineer in parallel.
allowed-tools: Read, Bash, Glob, Grep, Agent
metadata:
  version: 1.0.0
  role: discovery
  feeds-into: intake
---

# Code Review

**Role: Technical Auditor**
**Purpose: Discovery — surfaces findings that feed into the CR process via `/intake`**

This skill reviews code and produces a findings report. It does not fix anything and does not create CR items — that is `/intake`'s job. The output of this skill is the input to `/intake`.

---

## Pre-Flight

1. **Auto-detect the stack** from the project structure:
   - `src/` exists → **backend** (Python/FastAPI). Agents: sw-architect, security-engineer, backend-engineer.
   - `lib/features/` exists → **flutter**. Agents: sw-architect, security-engineer, flutter-engineer.
   - Both exist → **fullstack**. Run both sets of agents.
   - `infra/` exists (and no `src/` or `lib/`) → **infra**. Agents: sw-architect, security-engineer, gcp-engineer.

2. Determine review scope from `$ARGUMENTS`:

   **No argument — full codebase review:**
   - backend: review all of `src/`
   - flutter: review all of `lib/features/` and `lib/core/`
   - infra: review all of `infra/`

   **Path argument** (contains `/` or ends with a file extension):
   - Review the specified path directly (e.g. `src/adapters/inbound/`, `lib/features/auth/`)
   - If the path does not exist, stop and tell the user

   **Feature name** (kebab-case, no slashes):
   - Locate code matching the feature name
   - If a spec exists at `specs/cr/<feature>.spec.md`, read it — it's the contract the code must satisfy
   - If a plan exists at `specs/cr/plans/<feature>.plan.md`, read it — the code must follow the plan's structure

   **CR-ID** (format `YYMMDD-HHMMSS`):
   - Review code produced by that CR
   - Load spec and plan from `specs/cr/<cr-id>.spec.md` and `specs/cr/plans/<cr-id>.plan.md`

---

## Review Orchestration

Launch all three reviewer agents in parallel. Each gets the code files plus any spec/plan as context.

### Agent 1: sw-architect

**Backend/Fullstack:**
- Run `python .claude/scripts/validate_architecture.py src/` — include full output
- Verify CQRS: commands mutate state, queries are read-only
- Verify domain events used for all side effects — no direct service calls from domain/application
- Check for anemic domain models — business logic in application services instead of domain entities
- Verify gateway pattern: external API calls go through Port → Adapter → Gateway
- Verify paginated results use standard `Page[T]` shape
- Check that error types are domain exceptions, not HTTP exceptions

**Flutter/Fullstack:**
- Verify BLoC state is `@freezed` sealed with `initial/loading/loaded/error`
- Verify use cases are single-responsibility
- Verify `Either<Failure, T>` used consistently — no throwing across layer boundaries
- Check that presentation layer has no business rule logic

**Infra:**
- Verify Terraform module structure and naming conventions
- Verify no hardcoded project IDs or region strings
- Verify all resources have labels block

### Agent 2: security-engineer

**All platforms:**
- Check for hardcoded secrets, tokens, or credentials
- Verify all endpoints require authentication
- Verify tenant/user context is passed explicitly, never from global state

**Backend/Fullstack:**
- Verify every repository query filters by `tenant_uid`
- Verify all external input validated by Pydantic at the adapter boundary
- Verify domain and application layers do not import HTTP exceptions
- Check for SQL injection risks
- Verify rate limiting on write endpoints
- Check for IDOR vulnerabilities

**Flutter/Fullstack:**
- Verify JWT stored in `FlutterSecureStorage` only
- Verify auth interceptor handles 401 with silent token refresh
- Verify local cache keys scoped by `userId`
- Check for deep link injection risks

**Infra:**
- Verify no public IP on Cloud SQL
- Verify IAM least-privilege
- Verify secrets from Secret Manager, not environment variables
- Verify Cloud Run services do not allow unauthenticated access unless justified

### Agent 3: backend-engineer / flutter-engineer / gcp-engineer

**Performance (all platforms):**
- Check for N+1 query patterns
- Verify all list endpoints have pagination
- Check for missing indexes on WHERE clause fields
- Verify async/await used correctly

**Backend performance:**
- Verify gateway calls have timeouts and circuit breakers
- Check for repeated DB calls within the same request context

**Flutter performance:**
- Verify `const` constructors used where possible
- Check for `setState` or BLoC emits inside `build()`
- Verify `ListView.builder` used for dynamic lists

**Standards (all platforms):**
- Check for obvious bugs: null safety, missing error handling, off-by-one
- Verify error paths handled — no swallowed exceptions
- Check test coverage against acceptance criteria
- Verify tenant isolation tests exist
- Flag copy-paste duplication
- Check TODO/FIXME comments are tracked

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

### Architecture Validator Output
<output from validate_architecture.py or "No violations found">

### Test Coverage
- ACs covered: X / Y
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
