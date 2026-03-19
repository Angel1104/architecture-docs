# NestJS Technical Constitution

> This file is the source of truth for all pre-decided NestJS defaults.
> Applied automatically by all commands in this kit. Do not ask about these — implement them.

---

## TL;DR — Critical Defaults (read this first if context is compressed)

| # | Rule | Detail |
|---|------|--------|
| 1 | Domain layer: pure TypeScript | No NestJS, no Prisma, no Firebase, no HTTP imports in `domain/`. Zero framework dependencies. |
| 2 | RLS on every tenant query | Every query to a multi-tenant table inside `prisma.withTenant(tenantId, async (tx) => {...})` — never query without it. `withTenant()` lives in the repository, **not the controller**. |
| 3 | `tenant_id` from auth only | Comes from authenticated user in Neon — never from request body or query params |
| 4 | RFC 7807 errors | `type/title/status/detail/traceId` — never plain strings, never raw `Error`, never NestJS `HttpException` in domain |
| 5 | Cloud Tasks for side effects | Never call email/notification/webhook services directly from use cases — always dispatch a Cloud Task |
| 6 | Fake repos for use case tests | `FakeUserRepository implements IUserRepository` — never mock Prisma directly in unit tests |
| 7 | Cursor pagination | `PaginatedResponse<T>` with Prisma `take+1` pattern — never offset/skip pagination |
| 8 | OIDC for Cloud Tasks → FastAPI | Use GCP OIDC service account token — never Firebase Auth for this boundary |
| 9 | Expand/contract migrations | Never drop a column in the same deploy that removes the code using it — always two deploys |
| 10 | Auth guard on every write endpoint | Every `@Post`, `@Put`, `@Patch`, `@Delete` must have `@UseGuards(FirebaseAuthGuard)`. OIDC guard (not Firebase) for `/internal/tasks/` endpoints. |

> Full rules below. TL;DR is a summary — the sections below are authoritative.

---

## 1. Hexagonal Layer Rules

Every NestJS module follows this four-layer structure:

```
src/modules/<name>/
├── domain/               # ZERO framework imports. Pure TypeScript.
│   ├── entities/         # Immutable TypeScript types + factory functions with invariant checks
│   ├── ports/            # Abstract interfaces (INameRepository, IEmailService, etc.)
│   └── errors/           # Domain error classes (extend DomainError from shared/)
├── application/
│   └── use-cases/        # Single-responsibility. One file per use case.
│                         # Depends on domain ports ONLY. No Prisma, no Firebase, no HTTP.
├── infrastructure/
│   └── adapters/         # Implements domain port interfaces.
│                         # Uses Prisma, Firebase Admin, Cloud Tasks, R2.
│                         # All tenant-scoped queries use prisma.withTenant().
├── interface/
│   ├── controllers/      # HTTP entry points. Calls one use case per handler.
│   │                     # No business logic. Uses @UseGuards, @Body, @Param.
│   ├── dtos/             # Zod schemas for request/response validation.
│   ├── guards/           # Firebase Auth guard, OIDC guard, Roles guard.
│   └── decorators/       # @CurrentUser, @Roles, @TenantId
└── <name>.module.ts      # NestJS module — binds interfaces to implementations.
```

Shared cross-cutting concerns:
```
src/shared/
├── domain/               # BaseEntity, DomainError, DomainEvent
├── application/          # IUseCase interface
├── infrastructure/
│   ├── prisma/           # PrismaService with withTenant() helper
│   ├── redis/            # RedisService
│   ├── cloud-tasks/      # CloudTasksService
│   ├── r2/               # R2Service (presigned URLs)
│   └── firebase/         # FirebaseAdminService
├── interface/
│   ├── interceptors/     # TraceInterceptor (generates traceId per request)
│   ├── filters/          # DomainExceptionFilter (domain errors → RFC 7807)
│   └── pipes/            # ZodValidationPipe
└── config/               # Global configuration and composition root
```

### Dependency rules (STRICT)

```
domain/          → nothing (pure TypeScript, no NestJS/Prisma/Firebase)
application/     → domain/ only (no infrastructure, no interface)
infrastructure/  → domain/ + external packages
interface/       → application/ + domain/ entities (no infrastructure directly)
shared/          → external packages only (never imports modules)
```

---

## 2. Auth Guard — Firebase + Lazy User Creation

### Guard implementation

```typescript
// src/shared/interface/guards/FirebaseAuthGuard.ts
@Injectable()
export class FirebaseAuthGuard implements CanActivate {
  constructor(
    private readonly firebase: FirebaseAdminService,
    private readonly userRepo: UserRepository,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const req = context.switchToHttp().getRequest()
    const token = req.headers.authorization?.slice(7)
    if (!token) throw new UnauthorizedException()

    const decoded = await this.firebase.auth().verifyIdToken(token)

    // Lazy user creation — upsert into Neon on first request
    const user = await this.userRepo.findOrCreateByFirebaseUid({
      firebaseUid: decoded.uid,
      email: decoded.email ?? '',
    })

    req.user = user
    return true
  }
}
```

### Rules

- **Always use `verifyIdToken()`** — never manually decode a JWT without verification
- **Apply to all write endpoints** with `@UseGuards(FirebaseAuthGuard)`
- **Lazy user creation**: If a user authenticates for the first time, create their Neon record automatically — do not reject
- **`req.user`** is the Neon user record (with `id`, `tenantId`, `role`) — not the Firebase decoded token

### OIDC Guard — for Cloud Tasks / FastAPI endpoints

```typescript
// src/shared/interface/guards/OidcGuard.ts
// Validates GCP OIDC tokens (NOT Firebase JWT) on /internal/* endpoints
// Never use FirebaseAuthGuard on Cloud Task handler endpoints
```

---

## 3. Multi-Tenancy RLS — Transaction Pattern

Every query to a multi-tenant table MUST run inside `prisma.withTenant()`.

### PrismaService helper

```typescript
// src/shared/infrastructure/prisma/PrismaService.ts
@Injectable()
export class PrismaService extends PrismaClient implements OnModuleInit {
  async onModuleInit() {
    await this.$connect()
  }

  async withTenant<T>(tenantId: string, fn: (tx: Prisma.TransactionClient) => Promise<T>): Promise<T> {
    return this.$transaction(async (tx) => {
      await tx.$executeRaw`SET LOCAL app.tenant_id = ${tenantId}`
      return fn(tx)
    })
  }
}
```

### Usage in repository

```typescript
// Always wrap tenant-scoped queries:
await this.prisma.withTenant(tenantId, async (tx) => {
  return tx.user.findMany({ where: { status: 'active' } })
  // Postgres RLS automatically filters to tenantId rows
})
```

### Rules

- **Never query multi-tenant tables without `withTenant()`** — even for reads
- **`tenant_id` source**: Always from `req.user.tenantId` (the authenticated Neon user) — never from request body or params
- **RLS policies** must be applied to Postgres tables from the first migration
- **Non-tenant tables** (system configs, catalogs) do not need `withTenant()`

---

## 4. Error Format — RFC 7807

All HTTP error responses use this format. No exceptions.

```typescript
// RFC 7807 response shape:
{
  type: string       // stable error code (e.g., 'user/not-found')
  title: string      // human-readable message
  status: number     // HTTP status code
  detail: string     // additional context
  traceId: string    // correlation ID — always include
  timestamp: string  // ISO 8601
  fieldErrors?: Array<{ field: string; message: string }>  // 422 only
}
```

### DomainExceptionFilter

Maps all domain errors to RFC 7807 responses. Lives in `src/shared/interface/filters/`.

```typescript
// Error map — add all domain errors here:
const ERROR_MAP: Record<string, { status: number; type: string; title: string }> = {
  NameNotFoundError:       { status: 404, type: 'name/not-found',       title: 'Name not found' },
  NameAlreadyExistsError:  { status: 409, type: 'name/already-exists',  title: 'Name already exists' },
  InsufficientPermissions: { status: 403, type: 'auth/forbidden',       title: 'You do not have permission' },
  TenantContextMissing:    { status: 403, type: 'auth/tenant-required',  title: 'Tenant context required' },
}
```

### Rules

- Domain errors (`DomainError` subclasses) are NEVER coupled to HTTP status codes
- Only `DomainExceptionFilter` maps domain errors to HTTP
- `detail` field: include the error message for domain errors, "An unexpected error occurred" for 500s
- **Never** include stack traces or internal error details in responses
- `traceId` is always present — generated by `TraceInterceptor` per request

---

## 5. Cloud Tasks — Async Side Effects

Side effects from use cases go through `CloudTasksService`. Never call email/notification/webhook services directly from use cases.

### Payload pattern

```typescript
// src/shared/infrastructure/cloud-tasks/CloudTasksService.ts
type TaskPayload<T extends string, D> = {
  taskType: T
  tenantId: string
  triggeredBy: string  // userId
  data: D
}

// Example task type
type ProcessDocumentTask = TaskPayload<'process-document', {
  documentId: string
  fileKey: string
}>
```

### Dispatching from a use case

```typescript
// In a use case:
await this.cloudTasks.enqueue<ProcessDocumentTask>('process-document', {
  taskType: 'process-document',
  tenantId: input.tenantId,
  triggeredBy: input.userId,
  data: { documentId, fileKey },
})
```

### FastAPI handler endpoint

```
POST /internal/tasks/process-document
Auth: GCP OIDC token (NOT Firebase JWT)
```

FastAPI validates OIDC token using `ALLOWED_SERVICE_ACCOUNT` env var. Never Firebase Auth.

### Rules

- Cloud Tasks are for side effects the client does NOT need for the response
- For side effects the client NEEDS synchronously: call FastAPI via HTTP directly at `/internal/sync/<operation>`
- Never use `FirebaseAuthGuard` on `/internal/tasks/` endpoints — use OIDC guard
- All task payloads include `tenantId` and `triggeredBy`

---

## 6. Cursor Pagination

All list endpoints return `PaginatedResponse<T>`. Never return raw arrays without pagination.

```typescript
// src/shared/interface/pagination.types.ts
export type PaginatedResponse<T> = {
  data: T[]
  nextCursor: string | null  // null = no more pages
  hasMore: boolean
}

export type PaginationParams = {
  cursor?: string   // absent = first page
  limit?: number    // default: 20, max: 100
}
```

### Prisma query pattern

```typescript
const limit = Math.min(params.limit ?? 20, 100)
const rows = await tx.item.findMany({
  where: {
    ...(params.cursor ? { id: { gt: params.cursor } } : {}),
  },
  orderBy: { createdAt: 'asc' },  // stable order required
  take: limit + 1,
})
const hasMore = rows.length > limit
const data = hasMore ? rows.slice(0, -1) : rows
return {
  data,
  nextCursor: hasMore ? data[data.length - 1].id : null,
  hasMore,
}
```

### Rules

- Default limit: 20. Maximum: 100. Return 400 if client requests > 100.
- Order must be stable: use a unique field (`id`) in `orderBy` to prevent cursor drift
- The cursor is opaque to the client (an ID string) — never a page number

---

## 7. Prisma — Migrations

- Use `prisma migrate dev` in development, `prisma migrate deploy` in CI/CD
- **Expand/contract pattern**: never drop a column in the same migration that adds its replacement
  1. Expand: add new column (nullable or with default)
  2. Migrate data (if needed)
  3. Contract: remove old column in a separate deploy
- RLS is activated from the first migration for all multi-tenant tables
- Every multi-tenant table has `tenant_id UUID NOT NULL` with an index

---

## 8. FastAPI Integration

### Rules

- FastAPI only receives requests from Cloud Tasks (OIDC) or from NestJS direct HTTP calls (OIDC)
- **Never expose FastAPI endpoints to clients** (web, mobile)
- **Never use Firebase Auth in FastAPI** — only GCP OIDC token validation
- NestJS contains all business logic. FastAPI is for AI/ML processing only.
- FastAPI endpoints: `/internal/tasks/<name>` (async) and `/internal/sync/<name>` (sync)

---

## 9. Observability — OpenTelemetry

### Setup in `main.ts`

```typescript
// Initialize OpenTelemetry BEFORE any other import
import './instrumentation'  // OpenTelemetry SDK init

async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  // ...
}
bootstrap()
```

### TraceInterceptor

Generates a `traceId` (UUID) for each request and:
- Attaches to `req.traceId`
- Adds `X-Trace-ID` header to response
- Includes in all log statements

### Rules

- `traceId` is in EVERY log statement — no log without it
- `traceId` is in EVERY RFC 7807 error response
- Logs are structured JSON — no `console.log` in production code

---

## 10. Environment Variables

### NestJS Backend

| Variable | Secret | Description |
|----------|--------|-------------|
| `NODE_ENV` | No | `production` / `staging` / `development` |
| `PORT` | No | `8080` on Cloud Run |
| `DATABASE_URL` | Yes | Neon Postgres connection string |
| `FIREBASE_PROJECT_ID` | No | Firebase project ID |
| `FIREBASE_CLIENT_EMAIL` | Yes | Firebase Admin service account email |
| `FIREBASE_PRIVATE_KEY` | Yes | Firebase Admin private key |
| `REDIS_URL` | Yes | Upstash Redis URL |
| `R2_ACCOUNT_ID` | No | Cloudflare account ID |
| `R2_ACCESS_KEY_ID` | Yes | R2 access key |
| `R2_SECRET_ACCESS_KEY` | Yes | R2 secret key |
| `R2_BUCKET_NAME` | No | R2 bucket name |
| `GOOGLE_CLOUD_PROJECT` | No | GCP project ID |
| `CLOUD_TASKS_QUEUE_LOCATION` | No | Cloud Tasks queue region |
| `FASTAPI_INTERNAL_URL` | No | FastAPI internal Cloud Run URL |

### Rules

- All secrets come from Secret Manager mounted as env vars — never hardcoded
- Use `ConfigService` for all env var access in application code — never `process.env` directly
- All env vars documented in `.env.example` with empty values and a comment
- Validate required env vars at startup using a Zod schema in `src/shared/config/`

---

## 11. API Versioning

### Default strategy: URL prefix versioning (`/v1/`)

All public-facing endpoints are prefixed with `/v1/`. Internal endpoints (Cloud Tasks, FastAPI) use `/internal/` and are never versioned.

```
/v1/users            ← public, versioned
/v1/documents        ← public, versioned
/internal/tasks/<name>   ← Cloud Tasks handler, not versioned
/internal/sync/<name>    ← FastAPI sync call, not versioned
```

### When to create `/v2/`

Create a new version ONLY when the contract change is breaking and cannot be expressed as additive:

| Additive change (no version bump needed) | Breaking change (requires /v2/) |
|---|---|
| New optional field in response | Removing a field from response |
| New optional query parameter | Changing a field type or name |
| New endpoint | Changing error codes clients depend on |
| Adding enum values | Changing pagination shape |

### Rules

- New projects start at `/v1/` — never `/v0/` or no prefix
- Versioning is at the route level, not per-module
- Old versions stay alive for 1 full release cycle after the migration guide is published
- Never use Accept-header versioning or query param versioning

---

## 12. Sync Side Effects — Cloud Tasks vs HTTP Sync

Two patterns for side effects from use cases:

### Pattern A: Async (Cloud Tasks) — default

Use when the client does NOT need the result to complete the request:

```typescript
// In a use case — dispatch and continue:
await this.cloudTasks.enqueue<ProcessDocumentTask>('process-document', {
  taskType: 'process-document',
  tenantId: input.tenantId,
  triggeredBy: input.userId,
  data: { documentId, fileKey },
})
// Response returns immediately — task runs in background
```

Endpoint receives task: `POST /internal/tasks/process-document` (OIDC guard).

### Pattern B: Sync HTTP call to FastAPI — when result is needed immediately

Use when the client needs the AI/ML result synchronously (e.g., document classification that determines next UI step):

```typescript
// In a use case — wait for FastAPI result:
const result = await this.fastApiService.post<ClassifyResult>(
  '/internal/sync/classify-document',
  { documentId, fileKey, tenantId: input.tenantId }
)
```

Endpoint at FastAPI: `POST /internal/sync/classify-document` (OIDC guard).

### Decision table

| Situation | Use |
|---|---|
| Email, notification, webhook after save | Cloud Tasks (async) |
| AI/ML result that blocks the response | FastAPI sync HTTP |
| Heavy processing user doesn't need to wait for | Cloud Tasks (async) |
| Validation by AI before confirming to client | FastAPI sync HTTP |

### Rules

- Never call FastAPI endpoints directly from controllers — always from use cases
- Both patterns use OIDC authentication — never Firebase Auth on `/internal/` endpoints
- Cloud Task handlers in FastAPI are idempotent — Cloud Tasks retries on failure

---

## 13. Project Initialization Checklist

### Repository setup
- [ ] NestJS project created with `nest new`
- [ ] TypeScript strict mode enabled in `tsconfig.json` (`"strict": true`)
- [ ] `.env.example` with all required variables and comments
- [ ] `.gitignore` includes `.env`, `node_modules/`, `dist/`
- [ ] ESLint + Prettier configured

### Folder structure
- [ ] `src/shared/` created with: `domain/`, `application/`, `infrastructure/`, `interface/`, `config/`
- [ ] `src/modules/` folder created (empty, ready for first module)
- [ ] `src/shared/infrastructure/prisma/PrismaService.ts` with `withTenant()` helper
- [ ] `src/shared/infrastructure/firebase/FirebaseAdminService.ts`
- [ ] `src/shared/infrastructure/cloud-tasks/CloudTasksService.ts`
- [ ] `src/shared/interface/interceptors/TraceInterceptor.ts`
- [ ] `src/shared/interface/filters/DomainExceptionFilter.ts`
- [ ] `src/shared/interface/pipes/ZodValidationPipe.ts`
- [ ] `src/shared/interface/guards/FirebaseAuthGuard.ts`
- [ ] `src/shared/interface/guards/OidcGuard.ts`

### Auth + security
- [ ] `FirebaseAuthGuard` uses `verifyIdToken()` — never manual JWT decode
- [ ] Lazy user creation in guard: `findOrCreateByFirebaseUid()`
- [ ] `OidcGuard` for all `/internal/` endpoints
- [ ] No Firebase Auth guard on Cloud Tasks endpoints

### Database
- [ ] Prisma initialized: `npx prisma init`
- [ ] `DATABASE_URL` points to Neon Postgres
- [ ] RLS enabled on all multi-tenant tables from first migration
- [ ] Every multi-tenant table has `tenant_id UUID NOT NULL` with index
- [ ] `prisma.withTenant()` used for all tenant-scoped queries

### Observability
- [ ] OpenTelemetry SDK initialized in `src/instrumentation.ts` before any other import
- [ ] `TraceInterceptor` generates `traceId` per request
- [ ] `traceId` present in all log statements
- [ ] `traceId` present in all RFC 7807 error responses
- [ ] No `console.log` — structured JSON logging

### Error handling
- [ ] `DomainExceptionFilter` registered globally
- [ ] `ZodValidationPipe` registered globally
- [ ] All domain errors extend `DomainError` from `shared/domain/`
- [ ] All HTTP errors use RFC 7807 format
- [ ] No stack traces in error responses

### Testing baseline
- [ ] At least one module with fake repository pattern (no `jest.mock(PrismaService)`)
- [ ] At least one tenant isolation test
- [ ] `jest.config.ts` with separate unit and integration test suites
- [ ] `npx jest --testPathPattern=unit` runs without database
- [ ] `npx jest --testPathPattern=integration` hits real test database

### Validation
- [ ] `npx tsc --noEmit` passes
- [ ] `npx jest --testPathPattern=unit` passes
- [ ] `npx nest build` passes
- [ ] App starts and health check endpoint returns 200
