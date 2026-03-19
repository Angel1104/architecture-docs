# Next.js Feature Specification Template

This document defines the canonical format for **Next.js web feature** specifications.
Use this template when the primary deliverable is a Next.js screen, flow, or web capability.

For backend NestJS features, use the NestJS spec template instead.
For full-stack features (new backend API + web UI), use both templates and link them.

---

## Spec Lifecycle

```
DRAFT → REVIEWED → APPROVED → IMPLEMENTING → DONE
```

## Required Sections

Every Next.js spec MUST contain all 10 sections. A spec missing any section cannot be REVIEWED.

---

### 1. Problem Statement

- What specific user problem does this solve?
- Who experiences this problem? (user persona, role: admin / member / viewer)
- What is the impact of NOT solving it?
- **Out of Scope**: what this feature does NOT cover (backend logic already specced separately, unrelated screens, etc.)

---

### 2. Bounded Context

- Which feature domain does this belong to? (`src/features/<name>/`)
- What screens / routes does this feature OWN?
- What does it DEPEND ON from the backend? (which API endpoints — listed in §4)
- What does it DEPEND ON from other features? (shared hooks, shared store slices, shared components)
- What cache invalidations or state changes does it trigger for other features?
  (e.g., successful hire → invalidate `['agents']` query)

---

### 3. Screens & Routes

Every UI surface this feature introduces or modifies. For each:

| Screen Name | Route Path | Component Type | Auth Required | Role | Data Source |
|-------------|------------|----------------|---------------|------|-------------|
| User List | `/dashboard/users` | Server Component | Yes | admin | `GET /v1/users` — server fetch |
| User Detail | `/dashboard/users/[id]` | Server Component | Yes | admin | `GET /v1/users/:id` — server fetch |
| Edit User Form | `/dashboard/users/[id]/edit` | `'use client'` | Yes | admin | hydrated from parent |

**Columns:**
- **Component Type**: `Server Component` / `'use client'`
- **Data Source**: `server fetch` (async component) / `TanStack Query` (client hook) / `props` / `Zustand`

> Every screen displaying user-specific data must have auth protection. Unauthenticated users redirect to `/auth/login`.

**Route guard pattern:**

```typescript
// middleware.ts or app/(dashboard)/layout.tsx
// Check auth session — redirect unauthenticated users to /auth/login
// During 'initializing' auth state: show loading skeleton, never redirect
```

---

### 4. Backend API Dependencies

Every backend endpoint this feature calls:

| Endpoint | Method | Purpose | Auth | Owned By Hook/Action |
|----------|--------|---------|------|---------------------|
| `/v1/users` | GET | List users with pagination | Bearer JWT | `useUserList` |
| `/v1/users/:id` | GET | Get user by ID | Bearer JWT | `useUser` |
| `/v1/users/:id` | PATCH | Update user | Bearer JWT | `useUpdateUser` |

**Rules:**
- All calls go through `apiClient` in `src/core/api/client.ts`. Never raw `fetch` in features.
- `Authorization: Bearer <token>` attached by ApiClient automatically.
- If no backend endpoint exists yet, note it as `(pending — NestJS spec: <cr-id>)`.

---

### 5. Component & State Contracts

For each hook and store slice introduced by this feature:

#### Hooks (TanStack Query)

```typescript
// features/<name>/application/hooks/useNameList.ts

// Query key
const QUERY_KEY = ['names'] as const

// Return type
type UseNameListResult = {
  data: Name[] | undefined
  isLoading: boolean
  error: ApiError | null
  refetch: () => void
}

// Mutation
type CreateNameInput = {
  name: string
  // ...
}
```

#### Store (Zustand — only if global state needed)

```typescript
// features/<name>/store/useNameStore.ts
type NameState = {
  selectedId: string | null
  // formDraft: Partial<CreateNameInput> | null  — ONLY add if §6 Auth Perspective explicitly
  //   specifies "preserve form state on 401". Do not add by default.
  setSelectedId: (id: string | null) => void
}
```

#### Domain Entity

```typescript
// features/<name>/domain/entities/Name.ts
type Name = {
  id: string
  name: string
  createdAt: string
  // ...
}
```

#### API Model (infrastructure — matches backend response)

```typescript
// features/<name>/infrastructure/models/NameResponse.ts
type NameResponse = {
  id: string
  name: string
  created_at: string  // snake_case from backend
}

// Mapper: NameResponse → Name
function toName(r: NameResponse): Name { ... }
```

---

### 6. Auth Perspective

- **Route protection**: describe which middleware or layout guard is used
- **Token**: `AuthService.getToken()` called by `ApiClient` automatically — auth provider SDK is isolated in `src/core/auth/`
- **Auth SDK location**: only in `'use client'` components or `src/core/auth/` — never imported directly in feature code
- **401 handling**: `ApiClient` calls `AuthService.refreshToken()` once, then `AuthService.logout()` + redirect
- **Form state on 401**: [describe if any form should preserve state in Zustand during re-auth]
- **Role-based UI**: [describe which UI elements are hidden/shown based on role, if any]

---

### 7. Acceptance Criteria

GIVEN / WHEN / THEN format. Each criterion must be:
- **Specific**: no vague terms ("it works", "it shows data")
- **Measurable**: has a clear pass/fail condition
- **Testable**: verifiable with RTL component test, hook test, or E2E test
- **Independent**: does not depend on other criteria's execution order

- [ ] **AC-1**: GIVEN an authenticated admin user WHEN they navigate to `/dashboard/users` THEN they see a paginated list of all users
- [ ] **AC-2**: GIVEN an unauthenticated user WHEN they navigate to any `/dashboard/*` route THEN they are redirected to `/auth/login`
- [ ] **AC-3**: GIVEN a filled form WHEN the user submits and the backend returns 422 THEN each `fieldError` is shown under the corresponding input field

---

### 8. Error Scenarios

#### 8.1 Network & Auth Errors (mandatory — applies to all authenticated Next.js features)

| Error | Trigger | User-Visible Behavior | Retryable? |
|-------|---------|----------------------|------------|
| No network | `fetch` throws `TypeError: Failed to fetch` | Show "Connection error" message | Yes — retry button |
| Request timeout | `fetch` rejects after timeout | Show "Request timed out" | Yes — retry button |
| 401 — expired token | ApiClient refresh fails | Silent refresh attempted; if fails → `/auth/login` redirect | No — requires re-auth |
| 403 — insufficient role | Backend returns 403 | Show "You don't have permission" message in-page | No |
| 404 — resource missing | Backend returns 404 | Show "Not found" state with navigation back | No |
| 422 — validation error | Backend returns `fieldErrors` | Map to form fields with `setError` | Yes — user corrects form |
| 500 — server error | Backend returns 5xx | Show "Something went wrong" + `traceId` | Yes — retry button |

#### 8.2 Feature-Specific Errors

| Error Condition | User-Visible Behavior | Component State |
|-----------------|----------------------|-----------------|
| (e.g., duplicate email) | "Email already in use" under email field | 422 fieldError mapped |
| (e.g., org at user limit) | "User limit reached" inline message | error state in hook |

---

### 9. Navigation & Side Effects

**Navigation Flow**

```
[Entry] → [Screen A] → [Screen B on success]
                     → [Error state on failure]
[Back]: [describe expected back behavior]
[Deep link]: [URL if applicable — direct navigation support]
```

**Query Invalidations on Mutation**

| Action | Query Invalidated | Reason |
|--------|------------------|--------|
| Create user | `['users']` | Stale list |
| Update user | `['users', id]` | Stale detail |
| Delete user | `['users']` | Stale list |

**Cross-feature side effects**

| Event | Consumed By | Purpose |
|-------|------------|---------|
| (e.g., user created) | `useOrgMemberCount` | Refresh member count badge |

---

### 10. Non-Functional Requirements

- **Rendering strategy**: [SSR / SSG / ISR / Client-side — specify per route and why]
- **Loading states**: Use skeleton screens (not spinner) for initial data load. Skeleton matches final layout.
- **Initial render**: First meaningful content within 300ms of navigation. No blank/flash.
- **Pagination**: Cursor-based pagination with `PaginatedResponse<T>` from backend (if list exceeds 20 items).
- **Accessibility**: All interactive elements have ARIA labels. Forms have associated `<label>`. Tab order is logical.
- **SEO**: [specify `<title>`, `<meta description>`, OG tags if public-facing route]
- **Performance**: No large images without `next/image`. No layout shift (CLS).
- **Error logging**: Unexpected errors logged to monitoring with `traceId` (no PII).

---

## Quality Checklist

A Next.js spec is ready for review when:

- [ ] No "TBD", "TODO", or "BUSINESS DECISION REQUIRED" remains unresolved
- [ ] All routes listed in §3 with component type (Server/Client) specified
- [ ] Every backend endpoint called is listed in §4
- [ ] Hook return types and store shape defined in §5
- [ ] Auth guard specified — no route without explicit auth decision
- [ ] Firebase SDK location confirmed (`'use client'` only)
- [ ] Navigation flow diagrammed in §9
- [ ] All 8.1 mandatory error scenarios covered
- [ ] Every AC follows GIVEN/WHEN/THEN with measurable conditions
- [ ] No business logic described in presentation/component terms
- [ ] Technical defaults applied (see `nextjs_defaults.md`)

---

## Annotation Conventions

- `(default)` — Next.js technical default from `nextjs_defaults.md`
- `(inferred — verify)` — derived from context; needs author confirmation
- `BUSINESS DECISION REQUIRED` — only the product owner can fill this in
- `(pending — NestJS spec: <cr-id>)` — backend endpoint not yet implemented
