# NestJS SDM Kit

This project uses the NestJS Spec-Driven Development Methodology Kit. These rules are always active. This kit is NestJS + TypeScript only.

## Methodology Flow

```
/intake → /spec → /plan → /build → /close
```

> Run `/init` once before anything else to set up the project context and folder structure.
> Run `/cr <cr-id>` to execute the full pipeline automatically after `/intake`. It stops only at mandatory human gates.

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
2. **Tests before code.** Test cases are derived from acceptance criteria BEFORE implementation begins.
3. **The domain layer is sacred.** `src/modules/<m>/domain/` has ZERO NestJS, Prisma, Firebase, or HTTP framework imports. Pure TypeScript only.
4. **Ports define contracts.** All data access and external interactions flow through abstract port interfaces. No concrete implementations in the domain layer.
5. **Infrastructure is replaceable.** Swapping a repository implementation (Prisma → another ORM) must never require touching domain or application code.
6. **Tenant isolation is mandatory.** Every data access operation is scoped to the tenant via RLS. The `tenant_id` comes from the authenticated user in Neon — never from the request body.
7. **Side effects are async.** Domain operations dispatch Cloud Tasks for side effects (email, notifications, webhooks). Direct calls to side-effect services from use cases are forbidden.
8. **CQRS mindset.** Use cases in `application/use-cases/` are single-responsibility — one per user action. Reads and writes are separate.
9. **Auth is infrastructure.** Firebase token verification, lazy user creation, and the `IUser` context in the request are infrastructure concerns (`interface/guards/`). Domain and application layers never touch tokens.
10. **Dependencies point inward.** `domain/` → nothing. `application/` → `domain/`. `infrastructure/` → `domain/` + external packages. `interface/` → `application/` + `domain/`.
11. **Explicit over implicit.** No global mutable state. Tenant context resolved from authenticated user, not from thread locals or ambient globals.
12. **Errors are RFC 7807.** Every HTTP error response uses RFC 7807 format: `type`, `title`, `status`, `detail`, `traceId`. Domain errors never reference HTTP codes.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** The Node.js hook blocks writes to `src/` if no reviewed spec exists.
15. **Name things precisely.** Specs use kebab-case (`user-registration`). Ports describe capabilities (`IUserRepository`), not implementations (`PrismaUserRepository`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in chat threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first.js` hook blocks writes to `src/` if no reviewed spec exists.
2. **No Prisma, Firebase, or HTTP framework imports in domain.** Any infrastructure import in `src/modules/<m>/domain/` is a boundary violation.
3. **No tenant query without RLS.** Every query to a multi-tenant table must run inside a transaction with `SET LOCAL app.tenant_id = :tenantId`. Never query without RLS context.
4. **No `tenant_id` from request body.** Tenant identity comes from the authenticated user in Neon only. Never trust the client to provide their own `tenant_id`.
5. **No secrets in code.** API keys, tokens, and credentials come from Secret Manager via environment variables. Never hardcoded.
6. **No HTTP exceptions in domain.** `domain/` and `application/` must not reference HTTP status codes or NestJS `HttpException`. Domain errors are plain `Error` subclasses.
7. **No unprotected write endpoints.** Every write endpoint requires the Firebase Auth guard. Every endpoint that returns tenant data requires RLS context.
8. **No unvalidated input.** All external input is validated with Zod at the controller boundary before reaching use cases.
9. **No cross-tenant data access.** Tests must include tenant isolation verification. A query that returns another tenant's data is a P0 incident.

## Architecture Quick Reference

```
src/
├── shared/                       # Cross-cutting concerns — never imports modules
│   ├── domain/                   # BaseEntity, DomainError, DomainEvent
│   ├── application/              # IUseCase interface
│   ├── infrastructure/
│   │   ├── prisma/               # PrismaService (with RLS transaction helper)
│   │   ├── redis/                # RedisService
│   │   ├── cloud-tasks/          # CloudTasksService
│   │   ├── r2/                   # R2Service (presigned URLs)
│   │   └── firebase/             # FirebaseAdminService
│   ├── interface/
│   │   ├── interceptors/         # TraceInterceptor, LoggingInterceptor
│   │   ├── filters/              # DomainExceptionFilter (maps domain errors → RFC 7807)
│   │   └── pipes/                # ZodValidationPipe
│   └── config/                   # Global NestJS module configuration
│
└── modules/
    └── <module>/
        ├── domain/               # ZERO framework dependencies. Pure TypeScript.
        │   ├── entities/         # Immutable TypeScript types / interfaces
        │   ├── ports/            # Abstract interfaces (IUserRepository, etc.)
        │   └── errors/           # Domain error classes (extend DomainError)
        ├── application/
        │   └── use-cases/        # Single-responsibility operations — one file per use case
        ├── infrastructure/
        │   └── adapters/         # Concrete implementations (Prisma repos, Firebase, R2)
        ├── interface/
        │   ├── controllers/      # HTTP controllers — execute use cases, no business logic
        │   ├── dtos/             # Zod schemas for request/response validation
        │   ├── guards/           # Firebase Auth guard, roles guard
        │   └── decorators/       # @CurrentUser, @Roles, @TenantId
        └── <module>.module.ts
```

### Dependency Rules (STRICT)

```
domain/          → nothing (pure TypeScript, no NestJS/Prisma/Firebase)
application/     → domain/ only
infrastructure/  → domain/ + external packages (Prisma, Firebase Admin, etc.)
interface/       → application/ + domain/ entities
shared/          → external packages only (never imports modules)
```

### RLS Transaction Pattern

```typescript
// PrismaService provides a helper — use this for ALL tenant-scoped queries
await prisma.withTenant(tenantId, async (tx) => {
  return tx.user.findMany({ where: { status: 'active' } })
})

// Under the hood:
// BEGIN
// SET LOCAL app.tenant_id = '<tenantId>'
// <query — Postgres RLS applies automatically>
// COMMIT
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
| `/help` | — | Prints this command reference |

## Available Agents

| Agent | Expertise | Can Help With |
|-------|-----------|---------------|
| `domain-analyst` | Requirements & specifications | Spec review, edge cases, acceptance criteria, scope |
| `sw-architect` | NestJS hexagonal architecture | Layer boundaries, port contracts, RLS patterns, dependency direction |
| `security-engineer` | Security & threat modeling | Firebase Auth guard, RLS, secrets, OIDC for Cloud Tasks |
| `qa-engineer` | Testing & quality | Fake repositories, Jest + Supertest, tenant isolation tests |
| `backend-engineer` | NestJS + TypeScript implementation | Feature implementation, Prisma, Cloud Tasks, auth flows |

> `/spec` and `/build` orchestrate multi-agent reviews automatically.
> All agents can also be invoked independently.

## References

All reference files are in `references/`:

- `nestjs_defaults.md` — NestJS Technical Constitution: every pre-decided default (hexagonal layers, auth guard, RLS pattern, error format, Cloud Tasks, pagination, testing, env vars). Applied automatically by commands.
- `nestjs_spec_template.md` — NestJS spec format (inbound ports, outbound ports, RLS strategy, Cloud Tasks side effects, acceptance criteria, error scenarios).

## Stack

- **API**: NestJS + TypeScript (hexagonal architecture)
- **AI/ML**: FastAPI + Python (Cloud Tasks only — no direct client calls)
- **Auth**: Firebase Admin SDK (verifyIdToken + lazy user creation in Neon)
- **Database**: Neon Postgres + Prisma (Row Level Security)
- **State**: Upstash Redis (caching, idempotency)
- **Storage**: Cloudflare R2 (presigned URLs)
- **Tasks**: Google Cloud Tasks (async side effects)
- **Observability**: OpenTelemetry → Cloud Trace + Logging + Monitoring
- **Infra**: Google Cloud Run

## Key Packages

| Package | Purpose |
|---------|---------|
| `@nestjs/core`, `@nestjs/common` | NestJS framework |
| `typescript` | Type safety |
| `@prisma/client`, `prisma` | Database ORM |
| `firebase-admin` | Auth token verification, lazy user creation |
| `zod` | Request/response validation (ZodValidationPipe) |
| `@google-cloud/tasks` | Async side effects via Cloud Tasks |
| `@opentelemetry/sdk-node` | Distributed tracing |
| `@nestjs/testing` | NestJS testing module |
| `jest`, `supertest` | Test runner + HTTP testing |
