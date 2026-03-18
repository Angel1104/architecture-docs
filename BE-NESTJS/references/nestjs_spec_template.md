# NestJS Module Specification Template

This document defines the canonical format for **NestJS module** specifications.
Use this template when the primary deliverable is a NestJS module, endpoint, use case, or backend capability.

For web/mobile features consuming these endpoints, use the respective frontend spec template.
For full-stack features (new NestJS module + web/mobile UI), use both templates and link them.

---

## Spec Lifecycle

```
DRAFT → REVIEWED → APPROVED → IMPLEMENTING → DONE
```

## Required Sections

Every NestJS spec MUST contain all 10 sections. A spec missing any section cannot be REVIEWED.

---

### 1. Problem Statement

- What specific problem does this solve?
- Who experiences this problem? (user persona, role: owner / admin / member)
- What is the impact of NOT solving it?
- **Out of Scope**: what this feature does NOT do (mandatory subsection)

---

### 2. Bounded Context

- Which NestJS module does this belong to? (`src/modules/<name>/`)
- What entities/aggregates does this module OWN?
- What does it DEPEND ON from other modules?
- What domain events does it PUBLISH for side effects?
- What shared services does it use? (`PrismaService`, `CloudTasksService`, `R2Service`, etc.)

---

### 3. Inbound Ports

Every operation exposed to the outside world:

| Port Name | Type | Method + Route | Auth Required | Roles Permitted | Description |
|-----------|------|---------------|---------------|-----------------|-------------|
| CreateName | HTTP endpoint | `POST /v1/names` | Yes (Firebase JWT) | admin, owner | Create a new name record |
| ListNames | HTTP endpoint | `GET /v1/names` | Yes (Firebase JWT) | admin, owner, member | List names with cursor pagination |
| ProcessDocument | Cloud Task handler | `POST /internal/tasks/process-document` | Yes (OIDC) | — | Process document async via FastAPI |

**Input validation** — for each endpoint, specify the Zod schema shape:

```typescript
// POST /v1/names
z.object({
  value: z.string().min(1).max(255).trim(),
  // ...
})
```

> **Role rules**: Hidden fields must be omitted from response entirely — never returned as `null`.
> If a write endpoint has field-level role restrictions, document them here.

---

### 4. Outbound Ports

Every external dependency this module needs. Define TypeScript interfaces:

```typescript
// src/modules/<name>/domain/ports/INameRepository.ts
export interface INameRepository {
  findById(id: string): Promise<Name | null>
  findByTenant(params: PaginationParams): Promise<PaginatedResponse<Name>>
  save(name: Name): Promise<void>
  delete(id: string): Promise<void>
  existsByValue(value: string): Promise<boolean>
}

// src/modules/<name>/domain/ports/IDocumentProcessor.ts
// (if this module calls FastAPI)
export interface IDocumentProcessor {
  processAsync(payload: ProcessDocumentPayload): Promise<void>
}
```

| Port Name | Type | Technology | Description |
|-----------|------|-----------|-------------|
| INameRepository | Repository | Prisma + Neon | CRUD for Name entities — all queries via RLS transaction |
| IDocumentProcessor | Event publisher | Cloud Tasks | Dispatches async processing to FastAPI |

---

### 5. Adapter Contracts

Concrete implementation details:

#### Inbound — HTTP endpoints

For each endpoint:
- **Request schema** (fields, types, Zod constraints)
- **Response schema** (fields, types)
- **Error responses** (which domain errors map to which HTTP codes)

```typescript
// POST /v1/names — request
{ value: string }  // validated by Zod

// POST /v1/names — response (201)
{ id: string; value: string; createdAt: string }

// Error responses
// 409 — NameAlreadyExistsError
// 422 — Zod validation failure (fieldErrors)
// 401 — missing/invalid Firebase JWT
// 403 — insufficient role
```

#### Inbound — Cloud Task handlers (if any)

```typescript
// POST /internal/tasks/process-document — payload
{
  taskType: 'process-document'
  tenantId: string
  triggeredBy: string  // userId
  data: {
    documentId: string
    fileKey: string
  }
}
```

#### Outbound — Prisma schema delta

```prisma
model Name {
  id        String   @id @default(uuid())
  tenantId  String   @map("tenant_id")
  value     String
  createdAt DateTime @default(now()) @map("created_at")
  updatedAt DateTime @updatedAt @map("updated_at")

  @@index([tenantId])
  @@map("names")
}
```

> RLS policy (must be added in migration):
> ```sql
> ALTER TABLE names ENABLE ROW LEVEL SECURITY;
> CREATE POLICY tenant_isolation ON names
>   USING (tenant_id = current_setting('app.tenant_id')::uuid);
> ```

#### Operation ordering (for multi-step commands)

| Step | Operation | Port | On Failure |
|------|-----------|------|------------|
| 1 | Validate input (Zod) | — | 422 with fieldErrors |
| 2 | Check duplicate exists | INameRepository.existsByValue | 409 NameAlreadyExistsError |
| 3 | Save entity | INameRepository.save | 500 (rollback transaction) |
| 4 | Dispatch side effect | IDocumentProcessor (Cloud Tasks) | Log warning, do NOT rollback step 3 |

---

### 6. Auth & Tenant Isolation Strategy

- **Token validation**: `FirebaseAuthGuard` calls `firebase.auth().verifyIdToken(token)`. On success, lazy user creation in Neon.
- **`tenant_id` resolution**: From `req.user.tenantId` (Neon user record) — never from request body or params
- **RLS enforcement**: All tenant-scoped queries run inside `prisma.withTenant(tenantId, ...)` which sets `SET LOCAL app.tenant_id = :tenantId` before each query
- **What happens on invalid token**: `verifyIdToken` throws → `UnauthorizedException` → 401 RFC 7807 response
- **What happens on missing `tenant_id`**: Guard throws `ForbiddenException` → 403 RFC 7807 response
- **Cloud Task handlers**: Use OIDC guard (not Firebase). Validate `ALLOWED_SERVICE_ACCOUNT` from env.

---

### 7. Acceptance Criteria

GIVEN / WHEN / THEN format. Each criterion must be:
- **Specific**: no vague terms ("it works", "it saves correctly")
- **Measurable**: clear pass/fail condition
- **Testable**: verifiable with a Jest test (use case test or controller test)
- **Independent**: does not depend on other criteria's execution order

- [ ] **AC-1**: GIVEN an authenticated admin user WHEN they POST `/v1/names` with a valid payload THEN a 201 response is returned with the created name's `id`, `value`, and `createdAt`
- [ ] **AC-2**: GIVEN an admin user WHEN they POST `/v1/names` with a name that already exists in their tenant THEN a 409 RFC 7807 response is returned
- [ ] **AC-3**: GIVEN an unauthenticated request WHEN any endpoint is called THEN a 401 RFC 7807 response is returned
- [ ] **AC-4**: GIVEN a user from tenant-A WHEN they request data THEN only tenant-A's data is returned (tenant isolation)

---

### 8. Error Scenarios

#### 8.1 Auth Failures (mandatory — applies to every Firebase-authenticated module)

| Error | HTTP | User Message | Log Level |
|-------|------|--------------|-----------|
| Expired token (`exp` in past) | 401 | "Authentication token has expired. Please sign in again." | WARN |
| Invalid signature | 401 | "Authentication token is invalid." | WARN |
| Wrong audience (`aud` mismatch) | 401 | "Authentication token is not valid for this service." | WARN |
| Missing required claim | 401 | "Authentication token is missing required information." | ERROR |
| `alg: none` or unexpected algorithm | 401 | "Authentication token is invalid." | ERROR (potential attack) |

> Messages must never reveal which specific validation step failed.

#### 8.2 Domain & Application Errors

| Error Condition | Domain Error Class | HTTP | Retryable? | User Message |
|----------------|-------------------|------|------------|--------------|
| Name not found | `NameNotFoundError` | 404 | No | "Name not found" |
| Duplicate name | `NameAlreadyExistsError` | 409 | No | "A name with this value already exists" |
| Insufficient role | `InsufficientPermissions` | 403 | No | "You do not have permission to perform this action" |
| Tenant context missing | `TenantContextMissing` | 403 | No | "Tenant context required" |
| (feature-specific errors) | | | | |

---

### 9. Side Effects (Cloud Tasks)

For every async side effect:

| Task Type | Triggered By | Consumer | Retry Policy | DLQ |
|-----------|-------------|----------|-------------|-----|
| `process-document` | `CreateName` use case | FastAPI `/internal/tasks/process-document` | max 3 retries, exp backoff 1s→2s→4s | `failed-names-process` |

**Sync side effects** (if any — FastAPI direct call):

| Operation | Endpoint | When | Failure Behavior |
|-----------|---------|------|-----------------|
| `generate-thumbnail` | `POST /internal/sync/generate-thumbnail` | On document upload | If fails: log WARN, return without thumbnail; enqueue retry via Cloud Tasks |

---

### 10. Non-Functional Requirements

- **Latency target**: p95 < 200ms for read endpoints, p95 < 500ms for write endpoints
- **Pagination**: cursor-based with default limit 20, max 100
- **Idempotency**: [specify if any endpoint should be idempotent and the TTL]
- **Data retention**: [specify retention policy if applicable]
- **Throughput**: [requests/sec expected if known]
- **Observability**: all errors include `traceId`; all logs are structured JSON with `traceId`

---

## Quality Checklist

A NestJS spec is ready for review when:

- [ ] No "TBD", "TODO", or "BUSINESS DECISION REQUIRED" remains unresolved
- [ ] All endpoints listed in §3 with HTTP method, route, and auth decision
- [ ] All domain port interfaces defined in §4 as TypeScript interfaces
- [ ] Prisma schema delta specified in §5
- [ ] Operation ordering specified for all multi-step commands
- [ ] `tenant_id` resolution path documented in §6 (from `req.user.tenantId` only)
- [ ] RLS `withTenant()` usage confirmed for all tenant-scoped queries
- [ ] All 8.1 mandatory auth error scenarios covered
- [ ] Every domain error has an explicit HTTP status mapping
- [ ] Cloud Tasks payloads typed in §9 (or "none" if no async side effects)
- [ ] Every AC follows GIVEN/WHEN/THEN with measurable conditions
- [ ] No HTTP status codes in domain error classes
- [ ] Technical defaults applied (see `nestjs_defaults.md`)

---

## Annotation Conventions

- `(default)` — NestJS technical default from `nestjs_defaults.md`
- `(inferred — verify)` — derived from context; needs author confirmation
- `BUSINESS DECISION REQUIRED` — only the product owner can fill this in
- `(pending — frontend spec: <cr-id>)` — frontend consuming this endpoint not yet specced
