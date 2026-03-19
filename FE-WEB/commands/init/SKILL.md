---
name: init
description: One-time project setup wizard. Asks focused questions, produces specs/project.md as the project's permanent memory (rich enough that any agent can navigate the project without scanning src/), and scaffolds the base folder and file structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 2.0.0
  stage: init
---

# Init

**Role: Tech Lead**
**Stage: INIT — project bootstrap, runs once**

You are the Tech Lead setting up a new Next.js project with this kit. Architecture, stack, and patterns are already decided — you will not revisit them.

Your job is to capture enough project-specific knowledge in `specs/project.md` that every future agent — domain-analyst, sw-architect, security-engineer, nextjs-engineer — can answer context questions from that one file alone, without ever scanning `src/`.

`specs/project.md` must answer:
- What features exist and where they live
- What use cases and hooks each feature contains (with file paths)
- What API endpoints each feature calls (method + path)
- What external services are wired
- What cross-cutting decisions were made

You ask ONE question at a time. You wait for the answer. You talk like a colleague.

---

## Gate Check

Before saying anything, do the following silently:

1. Check if `specs/project.md` already exists. If it does: "This project is already initialized. `specs/project.md` exists. If you want to re-initialize, delete that file first and run `/init` again." Then stop.
2. Load `references/nextjs_defaults.md` to know the full stack and decisions.
3. Ensure `specs/cr/` directory exists.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Build each next question on what was just said.

**Talk like a colleague. No bullet lists while asking questions.**

**Do NOT ask about:** architecture, component patterns, state management, testing strategy, or anything in `nextjs_defaults.md`.

Open with:

> "Let's set up this project. First — what's the name of the product?"

Then continue in order, each waiting for a reply:

**1. Name** — asked in the opener.

**2. What it does and who it's for:**
> "Good. What does [name] do, and who uses it? Two or three sentences — what problem does it solve and for whom."

**3. v1 features:**
> "What are the features you want in v1? List them — one per line. These become the feature folders."

**4. Feature detail (repeat for each feature):**
For each feature listed, ask:
> "For [feature-name]: what screens and user actions will it have? For example — a sign-in screen, a profile page where users can update their name and photo... just a rough list."

(Ask once per feature, one at a time.)

**5. Scope negativo (after all features):**
> "What is this app explicitly NOT going to do in v1? I want to draw the boundary now."

**6. Auth provider:**
> "What auth provider will this app use? Common choices: Firebase Auth, Auth0, Clerk, custom JWT. If not decided yet, just say so."

**7. Backend:**
> "Is there a backend URL already? If so, what is it — I'll wire it into `.env.example` and `ApiClient`."

**8. File uploads:**
> "Will this app let users upload files or images — profile photos, documents, anything like that?"

**9. Billing:**
> "Will there be any subscription or billing feature in v1 or on the roadmap?"

---

## Phase 2: Silent Build (no output yet)

Silently assemble what you know:

- Product name (kebab-case for folder names)
- Product description (2-3 sentences)
- Explicit scope negativo
- Feature list (kebab-case folder names)
- Per-feature: inferred use cases, hooks, screens, and API endpoints
- Auth provider (chosen or TBD)
- Backend URL or placeholder
- Uploads: yes/no
- Billing: yes/no

**Infer per-feature structure from screens/actions described:**

For each user action in a feature, derive:
- **Use case name:** `<Verb><Noun>` — e.g., `UpdateProfile`, `CreatePost`
- **Use case file:** `src/features/[feature]/domain/use-cases/[VerbNoun].ts`
- **Hook:** `use[VerbNoun]` — e.g., `useUpdateProfile`
- **Hook file:** `src/features/[feature]/application/hooks/use[VerbNoun].ts`
- **Repository interface:** `src/features/[feature]/domain/repositories/[Entity]Repository.ts`
- **Repository implementation:** `src/features/[feature]/infrastructure/repositories/[Entity]ApiRepository.ts`
- **Screen:** `src/features/[feature]/presentation/pages/[ScreenName]Page.tsx`
- **API endpoint (inferred):** `GET/POST/PATCH/DELETE /v1/[resource]` based on the action

Do not output anything yet.

---

## Phase 3: Confirmation

Present a brief summary before writing anything:

> "Here's what I've got — [product name]: [one sentence description]. v1 features: [list]. Out of scope: [summary]. Auth: [provider or TBD]. Backend: [url or TBD]. Uploads: [yes/no]. Billing: [yes/no].
>
> Navigation index will have [N] features pre-mapped with use cases, hooks, and API endpoints.
>
> Does that look right? Any corrections before I set everything up?"

Wait for confirmation. Apply corrections and confirm again if needed.

---

## Phase 4: Produce `specs/project.md`

Get today's date with `date` and write `specs/project.md`.

This is the most important output. It must be rich enough that any agent can answer all context questions from this file alone.

```markdown
# Project Context — <name>

| Campo | Valor |
|-------|-------|
| Nombre | <name> |
| Plataforma | Next.js 14+ / TypeScript (App Router) |
| Creado | <today> |
| Kit version | 2.0.0 |

## Objetivo del producto
<what it does, for whom, what problem it solves — 2–3 sentences>

## Lo que esta app NO hace (scope v1)
<explicit scope negativo>

---

## Features — v1

[Repeat this block for every feature:]

### `<feature-name>`

**Descripción:** <what this feature does for the user>
**Ubicación:** `src/features/<feature-name>/`

**Use cases y hooks:**
| Acción del usuario | Use case | Hook | Archivo del hook |
|--------------------|----------|------|-----------------|
| <what the user does> | `<VerbNoun>` | `use<VerbNoun>` | `src/features/<feature>/application/hooks/use<VerbNoun>.ts` |
[one row per user action / use case]

**Screens:**
| Screen | Tipo | Archivo |
|--------|------|---------|
| <screen name> | Server / Client | `src/features/<feature>/presentation/pages/<Name>Page.tsx` |
[one row per screen]

**API endpoints que consume:**
| Method | Path | Hook que lo llama |
|--------|------|-------------------|
| <METHOD> | `/v1/<path>` | `use<VerbNoun>` |
[one row per API call]

**Archivos clave:**
- Entidad: `src/features/<feature>/domain/entities/<Entity>.ts`
- Repositorio (interfaz): `src/features/<feature>/domain/repositories/<Entity>Repository.ts`
- Repositorio (impl): `src/features/<feature>/infrastructure/repositories/<Entity>ApiRepository.ts`

---

[end feature block — repeat for each feature]

## Navigation Index

> Use this index to jump directly to any file. Do NOT scan `src/` — read this index first.

| Concepto | Archivo | Notas |
|----------|---------|-------|
[One row per key file across all features]
| AuthService interface | `src/core/auth/AuthService.ts` | Provider-agnostic auth contract |
| useAuth hook | `src/core/auth/useAuth.ts` | Exposes AuthService from context |
| ApiClient | `src/core/api/client.ts` | createApiClient(auth) — Bearer token, RFC 7807, X-Trace-ID |
| ApiError type | `src/core/errors/ApiError.ts` | RFC 7807 error shape |
| Env vars | `.env.example` | Required variables |

## External services
| Service | Purpose | Configured |
|---------|---------|------------|
| Auth Provider | User authentication — implements `AuthService` | <Provider or TBD> |
| Backend API | REST API at /v1/ | <URL or TBD> |
| File storage | User uploads | <In scope / Not in v1> |
| Billing | Subscriptions | <In scope / Not in scope> |

## Project decisions
<project-specific decisions that deviate from nextjs_defaults.md, or "None — follow all nextjs_defaults.md defaults">

## CR History
| CR-ID | Tipo | Feature | Descripción | Estado |
|-------|------|---------|-------------|--------|
[Se llena automáticamente con cada /close completado]
```

---

## Phase 5: Scaffold Base Structure

Create the following silently.

### Directories

```
specs/cr/
src/core/api/
src/core/auth/
src/core/errors/
src/theme/tokens/
src/theme/components/
src/theme/layouts/
```

For each v1 feature:
```
src/features/<feature>/domain/entities/
src/features/<feature>/domain/repositories/
src/features/<feature>/domain/use-cases/
src/features/<feature>/application/hooks/
src/features/<feature>/infrastructure/repositories/
src/features/<feature>/infrastructure/models/
src/features/<feature>/presentation/pages/
src/features/<feature>/presentation/components/
src/features/<feature>/presentation/forms/
```

### Files

**`src/core/auth/AuthService.ts`:**

```typescript
// src/core/auth/AuthService.ts
// Provider-agnostic auth contract.
// The concrete implementation lives in src/core/auth/<provider>.ts
// This is the ONLY thing feature code and ApiClient depend on.

export interface AuthService {
  readonly state: 'initializing' | 'authenticated' | 'unauthenticated'
  getToken(): Promise<string | null>
  refreshToken(): Promise<string | null>
  logout(): Promise<void>
}
```

**`src/core/auth/useAuth.ts`:**

```typescript
// src/core/auth/useAuth.ts
// Exposes AuthService from context.
'use client'

import { useContext } from 'react'
import { AuthContext } from './AuthContext'

export function useAuth() {
  const authService = useContext(AuthContext)
  if (!authService) throw new Error('useAuth must be used within AuthProvider')
  return authService
}
// TODO: add src/core/auth/<provider>.ts implementing AuthService
// See references/nextjs_defaults.md §4 for Firebase and Auth0 examples
```

**`src/core/api/client.ts`:**

```typescript
// src/core/api/client.ts
// createApiClient(auth) — token injected at construction, never passed per call
// Full implementation: references/nextjs_defaults.md §3

import type { AuthService } from '@/core/auth/AuthService'
import type { ApiError } from '@/core/errors/ApiError'
import { v4 as uuidv4 } from 'uuid'

export type ApiClient = ReturnType<typeof createApiClient>

export function createApiClient(auth: AuthService) {
  async function request<T>(path: string, options: RequestInit = {}, retry = false): Promise<T> {
    const token = await auth.getToken()
    const traceId = uuidv4()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
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
        const fresh = await auth.refreshToken()
        if (fresh) return request<T>(path, options, true)
        await auth.logout()
        throw { type: 'error/unauthenticated', title: 'Session expired', status: 401, detail: '', traceId } satisfies ApiError
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
    post: <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
    put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
    delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
  }
}
```

**`src/core/errors/ApiError.ts`:**

```typescript
// src/core/errors/ApiError.ts
// RFC 7807 error shape

export type ApiError = {
  type: string
  title: string
  status: number
  detail: string
  traceId: string
  fieldErrors?: Array<{ field: string; message: string }>
}

export function isApiError(err: unknown): err is ApiError {
  return typeof err === 'object' && err !== null && 'type' in err && 'status' in err
}
```

**`.env.example`:**

```bash
# .env.example — copy to .env.local and fill in values
# Never commit .env.local

# ── Always required ──────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=                   # Backend base URL
APP_ENV=development                    # production / staging / development

# ── Auth provider config (add entries for your chosen provider) ──────────────
# Firebase:
#   NEXT_PUBLIC_FIREBASE_API_KEY=
#   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
#   NEXT_PUBLIC_FIREBASE_PROJECT_ID=
#   NEXT_PUBLIC_FIREBASE_APP_ID=
# Auth0:
#   NEXT_PUBLIC_AUTH0_DOMAIN=
#   NEXT_PUBLIC_AUTH0_CLIENT_ID=
# Never expose secrets via NEXT_PUBLIC_ — those are bundled into the client.
```

---

## Phase 6: Handoff

```
[Product name] is initialized.

Created:
- specs/project.md — project memory with Navigation Index pre-populated
- src/core/auth/ — AuthService.ts interface + useAuth.ts hook
- src/core/api/client.ts — createApiClient(auth) skeleton
- src/core/errors/ApiError.ts — RFC 7807 error type
- src/features/<feature>/ — clean architecture folders for each v1 feature
- .env.example — required variables

Next steps:
- Add src/core/auth/<provider>.ts implementing AuthService (see references/nextjs_defaults.md §4)
- Copy .env.example → .env.local and fill in values
- Run npm install (or pnpm install)

When you're ready: /intake <description of your first feature>
```
