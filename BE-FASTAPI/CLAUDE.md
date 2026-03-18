# FastAPI SDM Kit

This project uses the FastAPI Spec-Driven Development Methodology Kit. These rules are always active. This kit is FastAPI + Python 3.13 only.

## Methodology Flow

```
/intake → /spec → /plan → /build → /close
```

> Run `/cr <cr-id>` to execute the full pipeline automatically after `/intake`. It stops only at mandatory human gates.
> Run `/init` once before anything else to set up the project context and folder structure.

No stage may be skipped. Implementation without a reviewed spec is blocked by the hook.

## CR Types & Tracks

| Type | Track | Stages |
|------|-------|--------|
| `feature` | Full | spec (10 sections) → plan → build → close |
| `bug` | Minimal | build only (locate → regression test → fix) → close |
| `change` | Lean | spec (3 sections) → build → close |
| `security` | Full | spec → plan → build → close |
| `incident` | Containment-first | build (containment first) → close |
| `refactor` | Lean | spec (3 sections) → build → close |

## 16 Principles

1. **Spec first, code second.** Every feature starts as a specification in `specs/`. No implementation without a reviewed spec.
2. **Tests before code.** Test cases are derived from acceptance criteria BEFORE implementation begins. Tests run RED before any implementation code is written.
3. **The domain is sacred.** `app/domain/` has ZERO external dependencies. No framework imports, no database imports, no HTTP imports.
4. **Ports define contracts.** All external interaction flows through abstract ports in `app/domain/ports/`.
5. **Adapters are replaceable.** Swapping an adapter must never require touching domain or application code.
6. **Tenant isolation is mandatory.** Every data access operation is scoped to `tenant_id` via OIDC context. No exceptions.
7. **Side effects are async.** Domain operations dispatch Cloud Tasks for side effects. Direct calls to notification/webhook services are forbidden.
8. **CQRS separates reads and writes.** Commands in `app/application/commands/`, queries in `app/application/queries/`.
9. **Auth is OIDC only.** This service accepts requests from Cloud Tasks only. Every endpoint validates the GCP OIDC token. No Firebase, no API keys.
10. **Dependencies point inward.** `domain/` → nothing. `application/` → `domain/`. `adapters/` → `domain/` + external packages.
11. **Explicit over implicit.** No global state, no ambient context, no magic. Tenant context and dependencies are passed explicitly.
12. **Errors are domain concepts.** Domain and application layers raise domain exceptions. Adapters map them to HTTP responses.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** The Node.js hook blocks writes to `app/` if no reviewed spec exists.
15. **Name things precisely.** Specs use kebab-case (`process-document`). Ports describe capabilities (`DocumentRepository`), not implementations (`PostgresDocumentRepo`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in chat threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first.js` hook blocks writes to `app/` if no reviewed spec exists.
2. **No external imports in domain.** Any `from adapters` or `from application` import in `app/domain/` is a boundary violation.
3. **No unvalidated input.** All external input is validated at the inbound adapter boundary using Pydantic models.
4. **No direct side effects.** Domain and application layers must not call external services directly. Use Cloud Tasks.
5. **No secrets in code.** Credentials, API keys, and tokens must come from Secret Manager via environment variables. Never hardcoded.
6. **No HTTP exceptions in domain.** `app/domain/` and `app/application/` must not reference HTTP status codes or FastAPI exceptions.
7. **No unprotected endpoints.** Every endpoint validates the GCP OIDC token. No endpoint is callable without OIDC context.
8. **No cross-tenant data access.** Tests must include tenant isolation verification. A query that returns another tenant's data is a P0 incident.
9. **No Firebase auth.** This service is called by NestJS via Cloud Tasks only. Firebase token validation belongs in NestJS, not here.

## Architecture Quick Reference

```
app/
├── domain/           # Pure logic. Depends on NOTHING.
│   ├── models/       # Entities, Value Objects
│   ├── ports/        # Abstract interfaces (inbound + outbound)
│   └── exceptions.py # Domain exceptions
├── application/      # Use cases. Depends on domain/ ONLY.
│   ├── commands/     # Write operations
│   └── queries/      # Read operations
├── adapters/         # Framework code. Implements ports.
│   ├── inbound/      # FastAPI routers (OIDC-protected)
│   └── outbound/     # Repositories, R2 adapter, Postgres adapter
└── core/             # Config, security (OIDC), logging, DI wiring
```

### Dependency Rules (STRICT)

```
domain/          → nothing (pure Python, no FastAPI/SQLAlchemy/boto3)
application/     → domain/ only
adapters/        → domain/ + external packages (FastAPI, SQLAlchemy, boto3, etc.)
core/            → external packages only (never imports domain or application)
```

## Available Commands

| Command | Stage | Description |
|---------|-------|-------------|
| `/init` | Setup | One-time project setup. Creates `specs/project.md`, scaffolds folder structure. Run once before anything else. |
| `/intake <description>` | Intake | Universal entry point — classifies any issue and produces a CR item |
| `/spec <cr-id>` | Spec | Drafts spec → multi-agent review → revise → approve |
| `/plan <cr-id>` | Plan | Translates spec into layered implementation blueprint + test skeletons |
| `/build <cr-id>` | Build | Implements plan layer by layer, runs tests, code review, approves |
| `/close <cr-id>` | Close | Verifies ACs, documents outcome, formally closes CR |
| `/code-review [scope]` | Discovery | Multi-agent code audit → produces findings report → offers to create CR items |
| `/cr <cr-id>` | Pipeline | Automated full pipeline: spec → plan → build → close |
| `/status` | — | Shows all CRs: open, in progress, blocked, recently closed. No arguments. |
| `/help` | — | Prints this command reference |

## Available Agents

| Agent | Expertise | Can Help With |
|-------|-----------|---------------|
| `domain-analyst` | Requirements & specifications | Spec review, edge cases, acceptance criteria, scope |
| `sw-architect` | FastAPI hexagonal architecture | Layer boundaries, port contracts, OIDC auth, dependency direction |
| `security-engineer` | Security & threat modeling | OIDC validation, tenant isolation, secrets, input validation |
| `qa-engineer` | Testing & quality | FakeRepository pattern, pytest, tenant isolation tests |
| `backend-engineer` | FastAPI + Python implementation | Feature implementation, Pydantic, Cloud Tasks, OIDC flows |

> `/spec` and `/build` orchestrate multi-agent reviews automatically.
> All agents can also be invoked independently.

## References

All reference files are in `references/`:

- `technical_defaults.md` — FastAPI Technical Constitution: every pre-decided default (OIDC auth, Pydantic, R2, Cloud Tasks, pagination, testing, env vars). Applied automatically by commands.
- `spec_template.md` — FastAPI spec format (inbound ports, outbound ports, OIDC strategy, Cloud Tasks side effects, acceptance criteria, error scenarios).

## Stack

- **API**: FastAPI + Python 3.13 (hexagonal architecture)
- **Auth**: GCP OIDC (Cloud Tasks service account — no Firebase)
- **Database**: Neon Postgres (SQLAlchemy async)
- **Storage**: Cloudflare R2 (boto3)
- **Tasks**: Google Cloud Tasks (async side effects from NestJS)
- **Infra**: Google Cloud Run

## Key Packages

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn[standard]` | ASGI server |
| `pydantic`, `pydantic-settings` | Validation and config |
| `google-auth` | OIDC token validation |
| `google-cloud-tasks` | Cloud Tasks client |
| `sqlalchemy` | Database ORM (async) |
| `asyncpg` | Async Postgres driver |
| `boto3` | Cloudflare R2 (S3-compatible) |
| `pytest`, `pytest-asyncio` | Test runner |
