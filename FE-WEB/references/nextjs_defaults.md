# Next.js Technical Constitution

> This file is the source of truth for all pre-decided Next.js defaults.
> Applied automatically by all commands in this kit. Do not ask about these — implement them.

---

## 1. Feature Folder Structure

Every feature lives under `src/features/<name>/`. No exceptions.

```
src/features/<name>/
├── domain/
│   ├── entities/         # Pure TypeScript interfaces — zero framework dependencies
│   ├── repositories/     # Abstract interfaces (IUserRepository, etc.)
│   └── use-cases/        # Single-responsibility operations — one per user action
├── application/
│   └── hooks/            # React hooks wrapping use cases (useUserProfile, etc.)
├── infrastructure/
│   ├── repositories/     # Concrete implementations via ApiClient
│   └── models/           # API response types + mappers to domain entities
└── presentation/
    ├── pages/            # Next.js page components (Server or Client)
    ├── components/       # Reusable feature UI components
    └── forms/            # react-hook-form + Zod forms
```

Shared, cross-feature code lives in:
```
src/core/
├── api/                  # ApiClient, Bearer token, X-Trace-ID, 401 handling
├── auth/                 # Firebase client SDK wrapper, useAuth hook
└── errors/               # ApiError type, isApiError, error mapping

src/components/
├── ui/                   # Pure visual atoms (Button, Input, Modal, Table)
└── shared/               # Product-level reusables (PageHeader, EmptyState)

src/entities/             # Shared domain types across features
src/theme/                # Token system (core → semantic → CSS vars)
```

### Dependency rules (STRICT)

```
domain/          → nothing (pure TypeScript, no React/Next.js/Firebase)
application/     → domain/ only
infrastructure/  → domain/ + external packages (ApiClient, etc.)
presentation/    → application/ + domain/ entities
core/            → external packages only (never imports features)
```

---

## 2. Server vs Client Components

**Default: Server Component.** Add `'use client'` only when explicitly required.

### When `'use client'` IS required

| Reason | Example |
|--------|---------|
| React hooks (`useState`, `useEffect`, `useRef`) | Any interactive component |
| Event handlers (`onClick`, `onChange`, `onSubmit`) | Buttons, form inputs |
| Browser APIs (`localStorage`, `window`, DOM) | Clipboard, scroll, resize |
| Firebase client SDK | `useAuth`, `getIdToken`, `onAuthStateChanged` |
| TanStack Query hooks | `useQuery`, `useMutation` |
| Zustand store reads | `useUserStore` |

### When `'use client'` is NOT needed

| Case | Reason |
|------|--------|
| Data fetching via `async` component | Runs on server |
| Static/display components | No interactivity |
| Layouts wrapping other components | Composition only |
| Server Actions | `'use server'` directive — not `'use client'` |

### Pattern: push `'use client'` to the leaves

```
app/(dashboard)/users/page.tsx         ← Server Component (fetch data)
  └── features/users/components/
        ├── UserList.tsx               ← Server Component (receives data as props)
        └── UserFilters.tsx            ← 'use client' (has filters + state)
```

A layout or page with `'use client'` forces ALL its children into client-side bundle. Avoid.

---

## 3. ApiClient — Full Contract

File: `src/core/api/client.ts` — the **only** file that can call `fetch`.

### Responsibilities

- Attach `Authorization: Bearer <token>` on every request — token obtained from `AuthService.getToken()`
- Generate and attach a UUID as `X-Trace-ID` on every request
- Parse RFC 7807 error responses into typed `ApiError`
- On 401: call `AuthService.refreshToken()` and retry the request **once**
- On second 401: call `AuthService.logout()` + redirect to `/auth/login`

### Design principle — auth provider agnostic

The `ApiClient` depends on an `AuthService` abstraction, not on any specific auth SDK. The auth provider (Firebase, Auth0, Cognito, custom JWT, etc.) is injected — the ApiClient does not import any auth SDK directly.

```typescript
// src/core/auth/AuthService.ts
export interface AuthService {
  getToken(): Promise<string | null>
  refreshToken(): Promise<string | null>
  logout(): Promise<void>
}
```

### Canonical implementation pattern

```typescript
// src/core/api/client.ts
import { AuthService } from '@/core/auth/AuthService'
import { ApiError } from '@/core/errors/ApiError'
import { v4 as uuidv4 } from 'uuid'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL

export function createApiClient(auth: AuthService) {
  async function request<T>(
    path: string,
    options: RequestInit = {},
    retry = false
  ): Promise<T> {
    const token = await auth.getToken()
    const traceId = uuidv4()

    const res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : '',
        'X-Trace-ID': traceId,
        ...options.headers,
      },
    })

    if (!res.ok) {
      if (res.status === 401 && !retry) {
        const freshToken = await auth.refreshToken()
        if (freshToken) return request<T>(path, options, true)
        await auth.logout()
        window.location.href = '/auth/login'
        throw new Error('Unauthenticated')
      }
      const body = await res.json().catch(() => ({}))
      throw {
        type: body.type ?? 'error/unknown',
        title: body.title ?? 'An error occurred',
        status: res.status,
        detail: body.detail ?? '',
        traceId: body.traceId ?? traceId,
      } satisfies ApiError
    }

    return res.json()
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
    put: <T>(path: string, body: unknown) =>
      request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) =>
      request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  }
}
```

### Rules

- `fetch` or `axios` are NEVER used outside `client.ts`
- Never manually attach `Authorization` in a feature
- Never import an auth SDK directly in `client.ts` — always through the `AuthService` interface
- Every API call goes through `apiClient.get/post/put/patch/delete`

---

## 4. Auth — Provider-Agnostic Design

File: `src/core/auth/AuthService.ts` — interface (always present)
File: `src/core/auth/useAuth.ts` — auth hook (always present)
File: `src/core/auth/<provider>.ts` — concrete implementation (project-specific)

### The contract — what the FE always needs

The FE needs exactly three things from auth:

```typescript
// src/core/auth/AuthService.ts
export interface AuthService {
  getToken(): Promise<string | null>       // Bearer token for ApiClient
  refreshToken(): Promise<string | null>   // Force-refresh on 401
  logout(): Promise<void>                  // Clear session + navigate to login
}

export interface AuthUser {
  id: string
  email: string | null
}

export interface AuthState {
  status: 'initializing' | 'authenticated' | 'unauthenticated'
  user: AuthUser | null
}
```

### Auth hook (always the same shape, regardless of provider)

```typescript
// src/core/auth/useAuth.ts — always 'use client'
'use client'

export function useAuth(): AuthState {
  // Implementation delegates to the injected provider
  // Returns: { status, user }
}
```

### Firebase implementation example

```typescript
// src/core/auth/providers/firebase.ts
// 'use client' — only used in client context
import { getAuth, onAuthStateChanged } from 'firebase/auth'

export class FirebaseAuthService implements AuthService {
  async getToken() {
    return getAuth().currentUser?.getIdToken() ?? null
  }
  async refreshToken() {
    return getAuth().currentUser?.getIdToken(true) ?? null
  }
  async logout() {
    await getAuth().signOut()
  }
}
```

### Rules

- The `AuthService` interface lives in `src/core/auth/` — it never changes between providers
- Auth SDK imports (`firebase/auth`, `@auth0/nextjs-auth0`, etc.) are ONLY in `src/core/auth/providers/`
- **Never import any auth SDK in a Server Component** — Firebase client SDK, Auth0 client, etc. are all client-only
- `getToken()` is called only inside `apiClient` — never in features or components directly
- Token refresh on 401 is handled by `apiClient` — never manually in features
- On second 401: `logout()` + redirect — no retry loops, no dialogs
- The 3-state auth model (`initializing` / `authenticated` / `unauthenticated`) is mandatory regardless of provider — it prevents flash of login screen on page load

### Form state preservation on re-auth

If a feature has a long form with unsaved data and the session expires mid-fill:
1. Store form values in the feature's Zustand slice before 401 redirect
2. After re-auth, hydrate the form from the slice
3. Clear the slice after successful submission or explicit discard
4. Only implement this if the feature spec explicitly calls for it

---

## 5. Forms — react-hook-form + Zod

### Standard form pattern

```typescript
'use client'

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { isApiError } from '@/core/errors/ApiError'

const schema = z.object({
  email: z.string().email('Invalid email'),
  name: z.string().min(2, 'Minimum 2 characters'),
})

type FormValues = z.infer<typeof schema>

export function ExampleForm() {
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormValues) => {
    try {
      await someApiFunction(data)
    } catch (err) {
      if (isApiError(err) && err.status === 422 && err.fieldErrors) {
        err.fieldErrors.forEach(({ field, message }) => {
          setError(field as keyof FormValues, { message })
        })
        return
      }
      // Generic error — show inline or toast
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
      <button type="submit" disabled={isSubmitting}>Save</button>
    </form>
  )
}
```

### Rules

- Every form uses `react-hook-form`. Never `useState` per field.
- Every form has a `z.object` schema. Client validation is for UX only — backend always validates too.
- 422 `fieldErrors` from backend are mapped to form fields with `setError`. Never shown as generic toast.
- `isSubmitting` disables the submit button to prevent double-submit.
- Zod schemas live in `features/<name>/types.ts` alongside the feature's TypeScript types.

---

## 6. ApiError Type

File: `src/core/errors/ApiError.ts`

```typescript
// src/core/errors/ApiError.ts
export type FieldError = {
  field: string
  message: string
}

export type ApiError = {
  type: string       // stable code for client logic (e.g., 'user/not-found')
  title: string      // human-readable — this is what gets shown to the user
  status: number     // HTTP status code
  detail: string     // additional detail — shown to user if helpful
  traceId: string    // include in error reports and logs
  fieldErrors?: FieldError[]  // present on 422 responses
}

export function isApiError(err: unknown): err is ApiError {
  return (
    typeof err === 'object' &&
    err !== null &&
    'type' in err &&
    'status' in err &&
    'traceId' in err
  )
}
```

### Error handling rules by layer

| Layer | Responsibility |
|-------|---------------|
| `ApiClient` | Parses HTTP error response → throws `ApiError` |
| TanStack Query `onError` / `catch` in hook | Captures `ApiError`, passes to component state |
| Component | Displays `error.title` or `error.detail` — never stack trace, never `error.type` |
| `ErrorBoundary` (root layout) | Catches unexpected render errors — shows generic fallback |

- Never `catch (e) { console.error(e) }` silently in features
- 5xx errors show generic message + `traceId` for user to report
- `ErrorBoundary` lives in `app/layout.tsx` — each dashboard section can add its own

---

## 7. State Management

### Zustand — global client state

```typescript
// features/<name>/store/useNameStore.ts
import { create } from 'zustand'

type NameState = {
  items: Item[]
  selected: Item | null
  setSelected: (item: Item | null) => void
  setItems: (items: Item[]) => void
}

export const useNameStore = create<NameState>((set) => ({
  items: [],
  selected: null,
  setSelected: (item) => set({ selected: item }),
  setItems: (items) => set({ items }),
}))
```

### TanStack Query — server state

```typescript
// features/<name>/application/hooks/useNameList.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { nameApi } from '@/features/<name>/infrastructure/repositories/nameApi'

export function useNameList() {
  return useQuery({
    queryKey: ['names'],
    queryFn: nameApi.list,
  })
}

export function useCreateName() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: nameApi.create,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['names'] }),
  })
}
```

### Rules

- Zustand for global UI state (auth status, selected item, form persistence on 401).
- TanStack Query for all server data (fetching, caching, invalidation).
- **Never mix**: don't store server data in Zustand, don't store UI state in TanStack Query cache.
- No `useEffect` to sync server state into local state — use `select` in `useQuery` for derivation.

---

## 8. Testing — msw + Vitest + React Testing Library

### Setup

```typescript
// src/mocks/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'
export const server = setupServer(...handlers)

// vitest.setup.ts
import { beforeAll, afterAll, afterEach } from 'vitest'
import { server } from './src/mocks/server'
beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

### msw handler pattern

```typescript
// src/mocks/handlers/names.ts
import { http, HttpResponse } from 'msw'

export const nameHandlers = [
  http.get('/v1/names', () => {
    return HttpResponse.json({ data: [{ id: '1', name: 'Alice' }] })
  }),
  http.post('/v1/names', async ({ request }) => {
    const body = await request.json()
    return HttpResponse.json({ id: '2', ...body }, { status: 201 })
  }),
]
```

### Test structure per feature

```
src/features/<name>/__tests__/
├── domain/          # Pure logic tests (entities, use-cases)
├── application/     # Hook tests with renderHook
├── infrastructure/  # API function tests (msw)
└── presentation/    # Component tests (RTL)
```

### Rules

- **Never mock ApiClient directly** — use msw to intercept at network level
- Test behavior the user sees — not internal implementation
- Every authenticated feature has at least one user isolation test (user A cannot see user B's data)
- Test file location: `src/features/<name>/__tests__/` (not scattered next to source files)
- Tests run with: `npx vitest run src/features/<name>/`
- Full suite: `npx vitest run`

---

## 9. Theme — CSS Custom Properties + Tailwind

### Token hierarchy

```
Core tokens (raw values) → Semantic tokens (roles) → CSS custom properties → Tailwind classes
```

### File structure

```
src/theme/
├── tokens/
│   ├── core.ts             # Full color palette, spacing scale, radii, typography
│   ├── semantic.light.ts   # Semantic roles for light mode
│   └── semantic.dark.ts    # Semantic roles for dark mode
└── web/
    ├── variables.css        # Tokens as CSS custom properties
    └── tailwind.config.ts   # Tailwind consumes CSS vars — defines no colors itself
```

### Required semantic token categories

| Category | Required tokens |
|----------|----------------|
| Background | `primary`, `secondary`, `tertiary` |
| Surface | `default`, `raised`, `overlay` |
| Text | `primary`, `secondary`, `disabled`, `inverse` |
| Border | `default`, `strong`, `focus` |
| Brand | `primary`, `primaryHover`, `primaryActive` |
| Status | `success`, `warning`, `error`, `info` |

### Usage rules

```tsx
// ✅ Semantic class names (correct)
<div className="bg-background-primary text-text-primary border-border-default">

// ❌ Literal Tailwind values (blocked)
<div className="bg-white text-gray-900 border-gray-200">
```

- Tailwind does not define any colors. It only references CSS custom properties.
- Components never use literal color values. Always semantic names.
- Dark mode via `@media (prefers-color-scheme: dark)` or `.dark` class on `<html>`.

---

## 10. Environment Variables

### What is always required (project-agnostic)

| Variable | Visibility | Purpose |
|----------|-----------|---------|
| `NEXT_PUBLIC_API_URL` | Client | Backend base URL — e.g. `https://api.example.com` |
| `NEXT_PUBLIC_APP_ENV` | Client | `production` / `staging` / `development` |

### Auth provider variables — added per project

These depend on the auth provider chosen for the project. Examples:

**Firebase Auth:**
| Variable | Visibility | Purpose |
|----------|-----------|---------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Client | Web API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Client | Auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Client | Project ID |
| `FIREBASE_ADMIN_PRIVATE_KEY` | Server only | Admin SDK — Server Actions only |
| `FIREBASE_ADMIN_CLIENT_EMAIL` | Server only | Admin SDK — Server Actions only |

**Auth0:**
| Variable | Visibility | Purpose |
|----------|-----------|---------|
| `NEXT_PUBLIC_AUTH0_DOMAIN` | Client | Auth0 domain |
| `NEXT_PUBLIC_AUTH0_CLIENT_ID` | Client | Auth0 client ID |
| `AUTH0_CLIENT_SECRET` | Server only | Never client-side |

> Document the actual variables used in `.env.example`. These tables are examples — not all are required.

### Rules

- `NEXT_PUBLIC_` variables are bundled into the client binary. Never put secrets or private keys there.
- Auth SDK server-side credentials (Admin SDK, client secrets) are server-only — never in `'use client'` files.
- All env vars documented in `.env.example` with empty values and a comment describing what they are.
- Missing required env vars cause a startup error — validate with `src/lib/env.ts` using Zod at boot.

---

## 11. Server Actions

File pattern: `src/features/<name>/application/actions/<name>.actions.ts`

### When to use Server Actions vs ApiClient

| Situation | Use |
|---|---|
| Mutation that only needs server-side Firebase Admin | Server Action |
| Reading or writing data from backend API | `apiClient` (fetch to NestJS) |
| Form submission that needs auth via Firebase Admin | Server Action |
| Any client-side data fetching | TanStack Query + `apiClient` |
| File upload to R2 (get presigned URL then upload) | `apiClient` |

**Default: use `apiClient` to call NestJS.** Server Actions are for operations that need Firebase Admin SDK directly (e.g., custom claims, token revocation) or for progressive enhancement of HTML forms.

### Server Action pattern

```typescript
// src/features/auth/application/actions/set-custom-claims.actions.ts
'use server'

import { adminAuth } from '@/core/auth/firebase-admin'
import { revalidatePath } from 'next/cache'

export async function setCustomClaims(userId: string, role: string) {
  await adminAuth.setCustomUserClaims(userId, { role })
  revalidatePath('/dashboard')
}
```

### Rules

- Always add `'use server'` directive at the top of the file — not just the function
- Server Actions run on the server — they have access to server-side env vars and Firebase Admin
- Never import Firebase client SDK in a Server Action file
- Use `revalidatePath` or `revalidateTag` after mutations to bust Next.js cache
- Server Actions that need auth must verify the token server-side — never trust client-passed identity
- For form validation: validate with Zod in the action before processing

---

## 12. Project Initialization Checklist

### Repository setup
- [ ] Next.js project created with `npx create-next-app@latest --typescript --tailwind --app`
- [ ] `tsconfig.json` has `"strict": true`
- [ ] `.env.local` for development, `.env.example` with all variables and comments
- [ ] `.gitignore` includes `.env.local`, `.next/`, `node_modules/`
- [ ] ESLint + Prettier configured

### Folder structure
- [ ] `src/core/api/client.ts` with ApiClient (Bearer, X-Trace-ID, 401 retry)
- [ ] `src/core/auth/firebase.ts` with Firebase initialization (no duplicate `initializeApp`)
- [ ] `src/core/auth/useAuth.ts` with `'use client'` hook
- [ ] `src/core/errors/ApiError.ts` with `ApiError` type and `isApiError` guard
- [ ] `src/theme/` with token structure (core → semantic → CSS vars → tailwind)
- [ ] `src/components/ui/` for atomic components (Button, Input, Modal)
- [ ] `src/components/shared/` for product-level reusables (PageHeader, EmptyState)

### Auth + routing
- [ ] Firebase client SDK initialized in `src/core/auth/firebase.ts`
- [ ] `useAuth` hook wraps `onAuthStateChanged` with loading state
- [ ] Auth guard middleware or layout checks auth before rendering protected routes
- [ ] `'use client'` directive on all files that use `useAuth` or Firebase client SDK
- [ ] Firebase Admin SDK (`firebase-admin`) installed for Server Actions — server-side only

### ApiClient
- [ ] `apiClient` exported from `src/core/api/client.ts`
- [ ] No `fetch` calls outside `client.ts`
- [ ] 401 retry: `getIdToken(forceRefresh: true)` → retry once → on second 401: `signOut()` + redirect
- [ ] `X-Trace-ID` attached to every request

### State and data
- [ ] `QueryClientProvider` wrapping app in `app/layout.tsx` (TanStack Query)
- [ ] `QueryClient` with appropriate `staleTime` configured
- [ ] Zustand stores only for global client state — no server data in Zustand

### Testing baseline
- [ ] `vitest` configured with `vitest.config.ts`
- [ ] `msw` server set up in `src/mocks/server.ts`
- [ ] `vitest.setup.ts` starts/resets/closes msw server
- [ ] At least one feature with full test structure (`domain/`, `application/`, `infrastructure/`, `presentation/`)
- [ ] At least one user isolation test

### Validation
- [ ] `npx tsc --noEmit` passes
- [ ] `npx vitest run` passes
- [ ] `npx next build` passes
- [ ] No `NEXT_PUBLIC_` variables contain secrets
- [ ] `'use client'` only where necessary (no unnecessary client boundaries)
