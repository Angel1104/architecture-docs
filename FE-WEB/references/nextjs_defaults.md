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

- Attach `Authorization: Bearer <token>` on every request
- Generate and attach a UUID as `X-Trace-ID` on every request
- Parse RFC 7807 error responses into typed `ApiError`
- On 401: call `getIdToken(forceRefresh: true)` and retry the request **once**
- On second 401: call `signOut()` + redirect to `/auth/login`

### Canonical implementation pattern

```typescript
// src/core/api/client.ts
import { getAuth } from 'firebase/auth'
import { ApiError } from '@/core/errors/ApiError'
import { v4 as uuidv4 } from 'uuid'

const BASE_URL = process.env.NEXT_PUBLIC_API_URL

async function request<T>(
  path: string,
  options: RequestInit = {},
  retry = false
): Promise<T> {
  const auth = getAuth()
  const token = await auth.currentUser?.getIdToken()
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
      const freshToken = await auth.currentUser?.getIdToken(true)
      if (freshToken) return request<T>(path, options, true)
      await auth.signOut()
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

export const apiClient = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
}
```

### Rules

- `fetch` or `axios` are NEVER used outside `client.ts`
- Never manually attach `Authorization` in a feature
- Never store or read the Firebase token in feature code
- Every API call goes through `apiClient.get/post/put/patch/delete`

---

## 4. Auth — Firebase Client SDK

File: `src/core/auth/firebase.ts` — initialization
File: `src/core/auth/useAuth.ts` — auth hook

### Firebase initialization

```typescript
// src/core/auth/firebase.ts
import { initializeApp, getApps } from 'firebase/app'
import { getAuth } from 'firebase/auth'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
}

const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0]
export const auth = getAuth(app)
```

### Auth hook

```typescript
// src/core/auth/useAuth.ts
'use client'

import { useEffect, useState } from 'react'
import { onAuthStateChanged, User } from 'firebase/auth'
import { auth } from './firebase'

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
      setUser(u)
      setLoading(false)
    })
  }, [])

  return { user, loading }
}
```

### Rules

- Firebase client SDK imports are ONLY in files marked `'use client'` or in `src/core/auth/`
- **Never import Firebase client SDK in a Server Component**
- `getIdToken()` is called only inside `apiClient` — never in features or components
- Token refresh on 401 is handled by `apiClient` — never manually in features
- On second 401: `signOut()` + redirect — no retry loops, no dialogs

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

### NEXT_PUBLIC_ — client-visible (non-sensitive only)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL (e.g., `https://api.example.com`) |
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase web API key |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase auth domain |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase project ID |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase app ID |

### Server-side only (never NEXT_PUBLIC_)

| Variable | Purpose |
|----------|---------|
| `FIREBASE_ADMIN_PRIVATE_KEY` | Firebase Admin SDK private key (Server Actions / API routes only) |
| `FIREBASE_ADMIN_CLIENT_EMAIL` | Firebase Admin SDK client email |
| `DATABASE_URL` | DB connection string (if Server Actions use DB directly) |

### Rules

- `NEXT_PUBLIC_` variables are bundled into the client. Never put secrets there.
- Firebase Admin SDK is server-side only — never in `'use client'` files.
- All env vars documented in `.env.example` with empty values and a comment.
- Missing required env vars cause a startup error — validate with `src/lib/env.ts` using Zod.
