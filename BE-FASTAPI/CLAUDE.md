# comocom — Python/FastAPI SDM Kit

This project uses the comocom Python/FastAPI SDM Kit. This kit provides the full Spec-Driven Development methodology pre-configured for Python/FastAPI backend services. No platform flags are needed — this kit IS the platform.

## Methodology Flow

```
/spec-init → Write spec → /spec-review → /plan → /test-gen → /implement → Validate
```

No stage may be skipped. Implementation without a reviewed spec is blocked by hook.

## 16 Principles

1. **Spec first, code second.** Every feature starts as a specification in `specs/`. No implementation without a reviewed spec.
2. **Tests before code.** Test cases are derived from acceptance criteria BEFORE implementation begins.
3. **The domain is sacred.** `src/domain/` has ZERO external dependencies. No framework imports, no database imports, no HTTP imports.
4. **Ports define contracts.** All external interaction flows through abstract ports in `src/domain/ports/`.
5. **Adapters are replaceable.** Swapping an adapter must never require touching domain or application code.
6. **Tenant isolation is mandatory.** Every data access operation is scoped to `tenant_uid`. No exceptions.
7. **Side effects are events.** Domain operations publish events. Side effects (email, notifications, webhooks) are handled by event consumers in adapters.
8. **CQRS separates reads and writes.** Commands in `src/application/commands/`, queries in `src/application/queries/`.
9. **Bridge external APIs.** External service calls go through Port → Adapter → Gateway. The Gateway handles rate limiting, circuit breaking, retries.
10. **Dependencies point inward.** domain/ → nothing. application/ → domain/. adapters/ → domain/ + application/.
11. **Explicit over implicit.** No global state, no ambient context, no magic. Tenant context, auth context, and dependencies are passed explicitly.
12. **Errors are domain concepts.** Domain and application layers raise domain exceptions. Adapters map them to HTTP responses.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** Hooks and linters catch violations automatically. Don't rely on memory.
15. **Name things precisely.** Specs use kebab-case (`user-registration`). Ports describe capabilities (`UserRepository`), not implementations (`PostgresUserRepo`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in Slack threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first` hook blocks writes to `src/` if no reviewed spec exists.
2. **No domain imports from adapters.** Any `from adapters` or `from application` import in `src/domain/` is a boundary violation.
3. **No query without tenant_uid.** Every repository method and every database query must filter by `tenant_uid`.
4. **No direct side effects.** Domain and application layers must not call email/notification/webhook services directly. Use domain events.
5. **No secrets in code.** Credentials, API keys, and tokens must come from environment variables or secret managers. Never hardcoded.
6. **No HTTP exceptions in domain.** `src/domain/` and `src/application/` must not reference HTTP status codes or framework-specific exceptions.
7. **No unprotected endpoints.** Every write endpoint requires authentication. Every endpoint requires tenant context.
8. **No unvalidated input.** All external input is validated at the adapter boundary using Pydantic models.
9. **No cross-tenant data access.** Tests must include cross-tenant isolation verification. A query that returns another tenant's data is a P0 incident.

## Architecture Quick Reference

```
src/
├── domain/           # Pure logic. Depends on NOTHING.
│   ├── models/       # Entities, Value Objects, Aggregates
│   ├── ports/        # Abstract interfaces (inbound + outbound)
│   ├── services/     # Domain services
│   ├── events/       # Domain event definitions
│   └── exceptions.py # Domain exceptions
├── application/      # Use cases. Depends on domain/ ONLY.
│   ├── commands/     # Write operations
│   └── queries/      # Read operations
├── adapters/         # Framework code. Implements ports.
│   ├── inbound/      # FastAPI routers, event handlers
│   └── outbound/     # Repositories, API clients, gateways
└── config/           # DI wiring, settings
```

## Stack

- **Backend**: Python 3.13 + FastAPI
- **Cloud**: Google Cloud Platform
- **Architecture**: Hexagonal + CQRS + Event-Driven
- **Multi-tenant**: Row-level security with tenant_uid scoping

## Available Commands

| Command | Stage | Description |
|---------|-------|-------------|
| `/spec-init <feature>` | 1 | Create spec from template via discovery conversation |
| `/spec-review <feature>` | 2 | Multi-agent spec review (domain, architecture, security) |
| `/spec-revise <feature>` | 3 | Revise spec to resolve all blockers and warnings |
| `/spec-auto <feature>` | 2–3 | Automated review-revise loop — repeats until APPROVED, pauses only for business decisions |
| `/plan <feature>` | 4 | Generate layered implementation plan |
| `/test-gen <feature>` | 5 | Generate test skeletons from acceptance criteria (TDD) |
| `/implement <feature>` | 6 | Implement from reviewed plan, inside-out |
| `/code-auto <feature>` | 6+ | Fully automated pipeline — implement, test, code-review, report |
| `/code-review <feature>` | 7 | Multi-agent code review: standards, security, performance |
| `/debug <feature>` | — | Root cause analysis on failing tests or runtime errors |

## Available Agents

| Agent | Focus |
|-------|-------|
| `domain-analyst` | Completeness, ambiguity, testability |
| `sw-architect` | Hexagonal compliance, boundaries, tenant isolation |
| `security-engineer` | Auth, validation, secrets, cross-tenant leakage |
| `qa-engineer` | Test strategy, adversarial thinking, coverage |
| `backend-engineer` | Python/FastAPI implementation, code review, debugging |

## References

Architecture patterns, spec templates, and tenant isolation rules are in `.claude/references/`:
- `technical_defaults.md` — Technical constitution: JWT, pagination, idempotency, rate limiting, events, errors
- `hexagonal_architecture.md` — Layer structure, Bridge, NEL, DAL patterns with code examples
- `tenant_isolation.md` — Multi-tenant data scoping rules and implementation patterns
- `spec_template.md` — Canonical spec format, required sections, and quality checklist
