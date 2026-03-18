# Specification Template Reference

This document defines the canonical format for feature specifications at comocom. Every feature MUST have a spec in `specs/<feature-name>.spec.md` before any implementation code is written.

## Spec Lifecycle

```
DRAFT → REVIEWED → APPROVED → IMPLEMENTING → DONE
```

- **DRAFT**: Author is writing/filling in the spec
- **REVIEWED**: Multi-agent review completed (`/spec-review`), revisions addressed
- **APPROVED**: All blockers resolved, ready for implementation
- **IMPLEMENTING**: `/implement` is in progress
- **DONE**: All acceptance criteria pass, feature is shipped

## Required Sections

Every spec MUST contain all 10 sections (plus §6.5). A spec missing any section is incomplete and cannot be REVIEWED.

### 1. Problem Statement
- What specific problem does this solve?
- Who experiences this problem? (user persona, role)
- What is the impact of NOT solving it?
- **Out of Scope**: what this feature does NOT do (mandatory subsection)

### 2. Bounded Context
- Which domain does this feature live in?
- What entities/aggregates does this context OWN?
- What does it DEPEND ON from other contexts?
- What domain events does it PUBLISH for others to consume?

### 3. Inbound Ports
Every operation exposed to the outside world. For each:
- Port name (as it would appear in code)
- Type: HTTP endpoint, event handler, CLI command, scheduled job
- Description of what it does
- Whether auth is required
- **Roles Permitted**: which roles can invoke this port
- **Read-RBAC**: for read ports or ports that return data, which response fields each role receives. Use "all fields" if the response is role-homogeneous, or list omitted fields per role. Hidden fields must be omitted entirely — never returned as `null`.

| Port Name | Type | Description | Auth Required | Roles Permitted | Read-RBAC |
|-----------|------|-------------|---------------|-----------------|-----------|

> Rule: If a write port has field-level restrictions (e.g., member cannot submit `system_prompt`),
> document it in the Read-RBAC column as: "admin: write [field_a, field_b] — member: write [field_a] only".

### 4. Outbound Ports
Every external dependency the feature needs. For each:
- Port name
- Type: repository, API client, event publisher, file storage, rate limit store, idempotency store
- Description and full Python method signatures (with `tenant_uid: str` as first parameter on all repository methods)
- Whether Bridge/Gateway pattern applies (yes for all external APIs)

### 5. Adapter Contracts
Concrete implementation details for each port:
- Inbound: protocol, endpoint path, **Request Schema** (fields, types, validation constraints), **Response Schema** (fields, types, per-role variations)
- Outbound: technology (PostgreSQL, Redis, Stripe API), connection details, Gateway concerns
- For multi-step commands: **Operation Ordering** table (step, operation, port, on-failure behavior)
- For free-text user input fields: **Sanitization Rules** (max length, prohibited characters, platform prefix rules)

### 6. Tenant Isolation Strategy
- How is `tenant_uid` resolved? (always: JWT claim via `Depends(resolve_tenant)`)
- How is data scoped? (always: row-level security + PostgreSQL RLS)
- Where is tenant context validated? (always: adapter layer)
- JWT validation: algorithm, required claims, expiry duration
- What happens if `tenant_uid` is missing or invalid?

### 6.5 Security Defaults
This section is mandatory. Every field must have a concrete value — no "TBD".

**Rate Limit Fallback Policy**

| Endpoint / Port | Rate Limit | Window | Scope | Fallback on Store Failure |
|-----------------|------------|--------|-------|--------------------------|
| (list each write endpoint) | (threshold) | (window) | per tenant_uid | deny-on-failure (financial) / allow-on-failure (non-financial) |

> `deny-on-failure`: request rejected with 503 when rate-limit store is unreachable.
> Required for any operation that creates a financial commitment.
>
> `allow-on-failure`: request proceeds when store is unreachable.
> Acceptable only for non-financial operations. State the accepted risk.

**JWT Expiry**
- Access token expiry: `___ minutes` (default: 15)
- Token revocation: short expiry only (default) / revocation list in Redis / other

**Read-RBAC Summary**

| Port | Role | Fields Visible | Fields Hidden | Enforcement Point |
|------|------|---------------|---------------|-------------------|
| (every read port with role-differentiated output) | admin | all fields | none | adapter, before response serialisation |
| | member | (list visible fields) | (list hidden fields) | adapter, before response serialisation |

> Every read port that returns a document must have at least one row here.
> Hidden fields are omitted from the response body — never returned as `null`.

**Operation Ordering** (for every command that calls more than one outbound port)

| Command | Step | Operation | Port | On Failure |
|---------|------|-----------|------|------------|
| | 1 | Idempotency check | IdempotencyStore | Return original response if duplicate |
| | 2 | Rate limit check | RateLimitStore | 429 if exceeded |
| | 3 | External API call | (e.g. SubscriptionClient) | Domain exception; do not proceed to DB write |
| | 4 | DB write + Audit log (same transaction) | Repository + AuditLogRepository | Compensate step 3 if applicable |
| | 5 | Publish domain event | EventBus | Log warning; do NOT roll back DB write |

> Standard order: idempotency → rate limit → external API → DB write → event publish.
> External call BEFORE DB write. If external call fails, no DB record is created.

### 7. Acceptance Criteria
GIVEN/WHEN/THEN format. Each criterion must be:
- **Specific**: no vague terms
- **Measurable**: has a pass/fail condition
- **Testable**: can be verified with an automated test
- **Independent**: does not depend on other criteria's order

### 8. Error Scenarios

#### 8.1 Auth Failures (mandatory — applies to every JWT-authenticated feature)

| Error | HTTP | User Message | Log Level |
|-------|------|--------------|-----------|
| Expired token (`exp` in past) | 401 | "Authentication token has expired. Please sign in again." | WARN |
| Invalid signature | 401 | "Authentication token is invalid." | WARN |
| Wrong audience (`aud` mismatch) | 401 | "Authentication token is not valid for this service." | WARN |
| Missing required claim | 401 | "Authentication token is missing required information." | ERROR |
| `alg: none` or unexpected algorithm | 401 | "Authentication token is invalid." | ERROR (potential attack) |

> Messages must never reveal which specific validation step failed.

#### 8.2 Domain & Application Errors

For EVERY domain error condition:
- What triggers it
- Domain Exception name (no HTTP codes in domain/application layer)
- HTTP status code (adapter mapping)
- Whether it's retryable
- User-facing error message (from a predefined set — never `str(e)`)

| Error Condition | Domain Exception | HTTP | Retryable? | User Message |
|-----------------|-----------------|------|------------|--------------|
| Missing tenant context | `TenantContextMissing` | 403 | No | "Tenant context required" |
| Insufficient role | `InsufficientPermissions` | 403 | No | "You do not have permission" |
| Invalid UUID path param | (adapter validation) | 400 | No | "Invalid identifier format" |
| (feature-specific errors) | | | | |

### 9. Side Effects (NEL)
For every side effect:
- Domain event name (`@dataclass(frozen=True)`, includes `tenant_uid: str` and `occurred_at: datetime`)
- What triggers it
- Who consumes it
- Sync or async (billing/audit = sync in command handler; notifications = async consumers)
- Failure policy: max retries, backoff, dead-letter destination

| Domain Event | Triggered By | Consumer | Sync/Async | Failure Policy |
|--------------|-------------|----------|------------|----------------|
| | | | | max 3 retries, exp backoff 1s→2s→4s, DLQ: failed-{context}-{op} |

### 10. Non-Functional Requirements
- Latency target (p95 per operation type)
- Throughput (requests/sec, events/sec)
- Data volume (rows/day, storage growth)
- Rate limit thresholds (per-tenant, per-agent, etc.)
- Idempotency TTL
- Audit log retention period (years)

---

## Quality Checklist

A spec is ready for review when:

- [ ] No placeholder text remains (no "TBD", "TODO", "fill in later", "BUSINESS DECISION REQUIRED")
- [ ] No ambiguous language ("appropriate", "as needed", "etc.", "relevant", "handle gracefully")
- [ ] All ports defined as interfaces, not implementations
- [ ] Tenant isolation addressed for every data access path
- [ ] Every acceptance criterion follows GIVEN/WHEN/THEN
- [ ] Every error scenario has an explicit behavior
- [ ] Side effects are domain events, not direct calls
- [ ] §6.5 Security Defaults fully populated (no blanks)
- [ ] §8.1 Auth failures present (all 5 rows)
- [ ] Read-RBAC defined for every port that returns data
- [ ] Operation ordering defined for every multi-step command
- [ ] All technical defaults applied (see `.claude/references/technical_defaults.md`)

---

## Naming Convention

Spec files: `specs/<feature-name>.spec.md` — kebab-case, descriptive name.

Good: `user-registration.spec.md`, `invoice-pdf-generation.spec.md`, `tenant-onboarding.spec.md`

Bad: `feature1.spec.md`, `new-stuff.spec.md`, `update.spec.md`

---

## Annotation Conventions

- `(default)` — technical default from `technical_defaults.md`; pre-decided, do not change without documented justification
- `(inferred — verify)` — derived from conversation; needs author confirmation
- `BUSINESS DECISION REQUIRED` — only the user can fill this in; spec cannot be reviewed until resolved
