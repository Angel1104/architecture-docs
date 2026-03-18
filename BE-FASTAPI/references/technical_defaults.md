# Technical Defaults — comocom Technical Constitution

This document codifies every technical decision that applies to ALL comocom features. Both `/spec-init` and `/spec-revise` MUST read this file before writing or revising any spec. Defaults here are **not open questions** — they are settled decisions.

A default may only be overridden with an explicit, documented business reason recorded in the spec's Problem Statement or a dedicated "Architecture Decision" note.

---

## How Agents Must Use This Document

When `/spec-init` Phase 3 or `/spec-revise` Phase 2 encounters any decision listed below, apply the default and annotate it with `(default)`. Do **NOT** ask the user. Do **NOT** leave it as TBD.

Ask the user **only** for:
- Which roles exist and what each can/cannot do (authorization model)
- What a business-domain-specific entity contains (schema of "governance config", "behaviour rules", etc.)
- How many years data must be retained (compliance requirement)
- Which operations are explicitly out-of-scope for this version
- Feature-specific rate limit thresholds (e.g., "50 hires/day")
- Expected traffic/throughput scale

---

## 1. Authentication and JWT

| Decision | Default |
|----------|---------|
| Signing algorithm | RS256 mandatory. `alg: none` is explicitly rejected at the adapter boundary. |
| Required claims | `exp`, `iss`, `aud`, `sub`, `tenant_uid`, `tenant_role` |
| Access token expiry | **15 minutes** |
| Token revocation | Not implemented in v1. Mitigated by 15-minute expiry. Deferred to v2. |
| Role claim name | `tenant_role` extracted from JWT |
| Valid role values | Only `"admin"` and `"member"`. Any other value → 403. |
| Unprotected endpoints | None by default. All endpoints require auth unless explicitly listed as public. |

---

## 2. Tenant Isolation

| Decision | Default |
|----------|---------|
| Tenant resolution | JWT claim `tenant_uid`, extracted by `Depends(resolve_tenant)` |
| tenant_uid format | UUID v4, validated at adapter boundary before any query |
| Data scoping | Row-level security: `tenant_uid` column on every owned table + app-level filter on every query |
| PostgreSQL RLS | Enabled as defense-in-depth on all tenant-owned tables |
| RLS session setter | `SET LOCAL app.current_tenant_uid = :tid` — parameterized query only. Never f-string. |
| Cross-tenant access | Always returns 404, never 403. Do not reveal resource existence. |
| Cross-tenant joins | Forbidden. No join spans tenant boundaries. |
| Global tenant state | Forbidden. `tenant_uid` is always passed explicitly through every function signature. |
| port method first param | `tenant_uid: str` is the first positional parameter on every repository method (except explicitly documented shared catalogs). |

---

## 3. Pagination

| Decision | Default |
|----------|---------|
| Applied to | All list endpoints, always |
| Default page size | 20 |
| Maximum page size | 100 |
| Style | Offset-based: `page` (1-indexed), `page_size`, `total` |
| Response envelope | `{ items: [...], total: N, page: N, page_size: N }` |
| Port signature | `page: int, page_size: int` as final parameters; returns `tuple[list[Entity], int]` |

---

## 4. Idempotency

| Decision | Default |
|----------|---------|
| Required for | Any command that triggers a financial charge, provisions an external resource, or sends a notification |
| Mechanism | `Idempotency-Key` HTTP header — client-generated UUID v4, required |
| Missing key behavior | 400 "Idempotency-Key header is required" |
| Storage | Redis with 24-hour TTL |
| Uniqueness scope | `(tenant_uid, idempotency_key)` composite — never global |
| Check order | Before any external call, before any DB write |
| Duplicate behavior | Return original response; do not re-execute side effects |
| Outbound port | `IdempotencyStore` with `check_and_store(tenant_uid, key, ttl) -> bool` |

---

## 5. Optimistic Locking

| Decision | Default |
|----------|---------|
| Applied to | Any entity with a lifecycle state machine (`status` field with defined transitions) |
| Mechanism | `version: int` field, incremented on every state-changing write |
| Port method | `update_status(tenant_uid, entity_id, new_status, expected_version)` |
| Conflict exception | `OptimisticLockConflict` → HTTP 409, retryable = True |
| User message | "Resource was modified by another request. Please retry." |

---

## 6. Rate Limiting

| Decision | Default |
|----------|---------|
| Scope | Per-tenant (never global-only) |
| Storage | Redis — atomic INCR + EXPIRE in a single operation |
| Key format | `{context}:{tenant_uid}:{operation}:{time_window_bucket}` |
| Fallback — FINANCIAL operations | **Deny** (fail closed). If Redis unavailable, reject request. |
| Fallback — non-financial operations | **Allow** (fail open). If Redis unavailable, permit request. |
| Domain exception | `RateLimitExceeded` → HTTP 429, retryable = True |
| Outbound port | `RateLimitStore` with `increment_and_check(key, limit, window_seconds) -> bool` |
| Thresholds | **BUSINESS DECISION** — specified per feature by the user |

---

## 7. External API Resilience (Bridge/Gateway Pattern)

| Decision | Default |
|----------|---------|
| Required for | All outbound ports marked Bridge/Gateway = Yes |
| Pattern | Port (domain interface) → Adapter (translation) → Gateway (cross-cutting concerns) |
| Gateway responsibilities | Rate limiting, circuit breaking, retry, timeout |
| Circuit breaker — FINANCIAL | Fail-closed (deny request when open) |
| Circuit breaker — non-financial | Fail-open (allow degraded behavior when open) |
| Timeout | 10 seconds per external API call |
| Retry policy | Max 3 retries, exponential backoff (1s → 2s → 4s), 5xx and network errors only. Never retry 4xx. |
| Domain exception | `[ServiceName]ServiceUnavailable` → HTTP 503, retryable = True |
| User message | "[Service] is temporarily unavailable. Please try again shortly." |

---

## 8. Event Bus and Side Effects (NEL Pattern)

| Decision | Default |
|----------|---------|
| v1 transport | In-process (NEL). No external message broker in v1. |
| v2 transport | GCP Pub/Sub or outbox pattern. Upgrade when cross-service fan-out or crash durability is needed. |
| Event consumer retry | Max 3 retries, exponential backoff (1s → 2s → 4s) |
| Dead letter queue | One DLQ per consumer, named `failed-{context}-{operation}` |
| Synchronous operations | Billing/subscription calls; audit log writes; optimistic lock updates — all within the command handler |
| Asynchronous operations | Email, SMS, webhooks, agent provisioning, runtime config reloads, external notifications |
| Event required fields | `tenant_uid: str` as first field on every domain event |
| Event immutability | All domain events are `@dataclass(frozen=True)` |
| DomainEvent base | All events share a common base or Protocol with `tenant_uid: str` and `occurred_at: datetime` |

---

## 9. Audit Logging

| Decision | Default |
|----------|---------|
| Write timing | Synchronous within command handler, same DB transaction as entity write |
| Rollback behavior | If the entity write rolls back, the audit entry rolls back too |
| PII policy | No PII stored. Actor identified by opaque JWT `sub` claim only. |
| GDPR pseudonymization | Achievable by removing Identity & Auth mapping without modifying audit records |
| Repository | Append-only: no `update` or `delete` methods on the audit port |
| Retention period | **BUSINESS DECISION** — specified in years by the user |

---

## 10. Error Handling

| Decision | Default |
|----------|---------|
| HTTP codes in domain | Forbidden. Domain and application raise domain exceptions only. Adapters map to HTTP. |
| Universal errors (every spec) | `TenantContextMissing` (→ 403), `InsufficientPermissions` (→ 403), invalid UUID path param (→ 400) |
| Error message policy | Predefined message set only. Never `str(e)`, never raw DB errors, never stack traces. |
| Cross-tenant 404 | Access to another tenant's resource → 404, never 403 |
| Retryable | 429 (rate limit), 409 (optimistic lock), 503 (circuit breaker) |
| Non-retryable | 400, 401, 403, 404, 409 (invalid lifecycle transition), 422 |

---

## 11. Operation Ordering (Multi-Step Commands)

| Decision | Default |
|----------|---------|
| Order | Idempotency check → rate limit check → external API call → DB write → event publish |
| Rationale | If external call fails, no DB record is created. If DB write fails after a successful external call, a compensating action must be documented in §8. |
| Audit log | Same DB transaction as entity write — committed together or not at all |

---

## 12. Request / Response Schema

| Decision | Default |
|----------|---------|
| Decimal serialization | String in JSON to avoid float precision issues |
| Datetime serialization | ISO 8601 UTC (e.g., `2026-03-08T12:00:00Z`) |
| UUID path params | UUID v4 validated at adapter boundary → 400 on non-conforming value |
| Input validation | Pydantic at adapter boundary. Domain receives only valid inputs. |
| Free-text LLM input | Max length enforced; reject control chars (U+0000–U+001F except tab/LF/CR); reject bidi override chars; platform prompt always prepended and cannot be overridden by user content |
| Role-differentiated responses | Adapter constructs response based on `tenant_role` from JWT. Never pass role to domain for response construction. |
| Hidden fields | Omitted from response entirely — never returned as `null` |

---

## 13. Secrets and Configuration

| Decision | Default |
|----------|---------|
| API keys, tokens, credentials | Environment variables or GCP Secret Manager. Never hardcoded. |
| Configuration management | Pydantic `BaseSettings` in `src/config/settings.py` |
| Secret fields | `SecretStr` type from Pydantic |

---

## 14. CQRS Separation

| Decision | Default |
|----------|---------|
| Write operations | `src/application/commands/` only |
| Read operations | `src/application/queries/` only |
| Mixed read-write | Forbidden. A command handler may return the created entity as a convenience but may not perform a separate enriching query. |

---

## 15. Dependency Direction

| Layer | May import |
|-------|------------|
| `src/domain/` | Nothing (stdlib + typing only) |
| `src/application/` | `src/domain/` only |
| `src/adapters/` | `src/domain/`, `src/application/`, external libraries |
| `src/config/` | Everything (composition root) |
