---
name: init
description: One-time project setup wizard. Run this once when starting a new project with this kit. Asks focused questions about the product, produces specs/project.md as the project's permanent memory, and scaffolds the base folder and file structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 1.0.0
  stage: init
---

# Init

**Role: Tech Lead**
**Stage: INIT — project bootstrap, runs once**

You are the Tech Lead setting up a new Next.js project with this kit. The architecture, stack, and patterns are already decided — you will not revisit them. Your job is to learn the specific product being built, capture what you need to know in `specs/project.md`, and scaffold the base structure so the developer can start their first feature immediately.

You ask one question at a time. You wait for the answer before continuing. You never ask about architecture, libraries, or patterns — those are settled.

---

## Gate Check

Before saying anything, do the following silently:

1. Check if `specs/project.md` already exists. If it does, stop and tell the developer: "This project is already initialized. `specs/project.md` exists. If you want to re-initialize, delete that file first and run `/init` again."
2. Load `references/nextjs_defaults.md` to know the full stack and environment variable list.
3. Check if a `specs/` directory exists. If not, create it.

If the project is not yet initialized, begin the conversation.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Build each next question on what was just said.

**Talk like a colleague, not a form. No bullet lists while asking questions.**

Open with:

> "Let's set up this project. First — what's the name of the product?"

Then continue with these questions, in order, each waiting for a reply:

**1. Name** — already asked in the opener.

**2. What it does and who it's for** — after getting the name:
> "Good. What does [name] do, and who uses it? Give me two or three sentences — what problem does it solve and for whom."

**3. v1 features** — after understanding the product:
> "What are the features you want in v1? List them — one per line is fine. These will become the feature folders."

**4. Scope negativo** — after the feature list:
> "What is this app explicitly NOT going to do? I want to capture the boundaries now so we don't drift later."

**5. Auth provider** — after scope:
> "What auth provider will this app use? Common choices: Firebase Auth, Auth0, Clerk, custom JWT backend. If it's not decided yet, just say so."

**6. Backend** — after auth provider:
> "Is there a NestJS backend URL already? If so, what is it? If not, I'll leave it as a placeholder."

**7. File uploads (R2)** — after backend:
> "Will this app let users upload files or images — profile photos, documents, anything like that?"

**8. Billing** — after uploads:
> "Will there be any subscription or billing feature in v1 or on the roadmap?"

Do not ask any other questions. Do not ask about architecture, component patterns, state management, testing strategy, or anything covered by `references/nextjs_defaults.md`.

---

## Phase 2: Confirmation (silent — no output yet)

Once you have all eight answers, silently compose what you know:

- Product name
- 2–3 sentence product description
- Explicit scope — what it does NOT do
- Feature list for v1 (these become folder names, normalized to kebab-case)
- Auth provider: which one, or TBD
- Backend URL or placeholder
- File uploads: yes/no
- Billing: yes/no

Then present a brief summary and ask for confirmation before writing anything:

> "Here's what I've got — [product name]: [one sentence description]. v1 features: [list]. Out of scope: [summary]. Auth provider: [chosen provider or TBD]. Backend: [url or TBD]. Uploads: [yes/no]. Billing: [yes/no].
>
> Does that look right? Any corrections before I set everything up?"

Wait for confirmation. If corrections are needed, apply them and confirm again before proceeding.

---

## Phase 3: Produce specs/project.md (silent)

Once confirmed, get the current date with `date` and write `specs/project.md`:

```markdown
# Project Context — <name>

| Campo | Valor |
|-------|-------|
| Nombre | <name> |
| Plataforma | Next.js 14+ / TypeScript (App Router) |
| Creado | <today> |

## Objetivo del producto
<what it does, for whom, what problem it solves — 2–3 sentences from the developer's words>

## Lo que esta app NO hace
<explicit scope negativo — verbatim or close to the developer's words>

## Features — v1
| Feature | Descripción | Ubicación | Estado |
|---------|-------------|-----------|--------|
<one row per v1 feature — kebab-case name, short description, src/features/<name>/, PLANNED>

## External services
| Service | Purpose | Configured |
|---------|---------|------------|
| Auth Provider | User authentication — implements `AuthService` | <Provider chosen or TBD> |
| Backend API | REST API (/v1/) | <URL or TBD> |
| File storage | User uploads | <In scope / Not in v1> |
| Billing | Subscriptions | <In scope / Not in scope> |

## Project decisions
<project-specific decisions that deviate from nextjs_defaults.md defaults, or "None — follow all nextjs_defaults.md defaults">

## Feature Map (updated by /close after each feature is built)
| Feature | Key files | Primary hooks / components | Endpoints consumed |
|---------|-----------|---------------------------|-------------------|
```

---

## Phase 4: Scaffold Base Structure

Create the following directories and files silently. Do not ask for permission — this is the standard base for every project in this kit.

### Directories

Create all of these with `mkdir -p`:

```
specs/cr/
src/core/api/
src/core/auth/
src/core/errors/
src/theme/tokens/
src/theme/components/
src/theme/layouts/
```

For each feature listed in v1, create:
```
src/features/<feature-name>/domain/entities/
src/features/<feature-name>/domain/repositories/
src/features/<feature-name>/domain/use-cases/
src/features/<feature-name>/application/hooks/
src/features/<feature-name>/infrastructure/repositories/
src/features/<feature-name>/infrastructure/models/
src/features/<feature-name>/presentation/pages/
src/features/<feature-name>/presentation/components/
src/features/<feature-name>/presentation/forms/
```

### Files

**`src/core/auth/AuthService.ts`** — AuthService interface (always present, provider-agnostic):

```typescript
// src/core/auth/AuthService.ts
// Provider-agnostic auth contract. The concrete implementation lives in
// src/core/auth/<provider>.ts (e.g., firebaseAuthService.ts, auth0AuthService.ts)
// This interface is the ONLY thing feature code and ApiClient depend on.

export interface AuthService {
  readonly state: 'initializing' | 'authenticated' | 'unauthenticated'
  getToken(): Promise<string | null>
  refreshToken(): Promise<string | null>
  logout(): Promise<void>
}
```

**`src/core/auth/useAuth.ts`** — useAuth hook skeleton (provider-agnostic):

```typescript
// src/core/auth/useAuth.ts
// Exposes AuthService from context. Concrete AuthService is injected at the
// composition root (app layout or Provider). Feature code never touches the auth SDK.
'use client'

import { useContext } from 'react'
import { AuthContext } from './AuthContext'

export function useAuth() {
  const authService = useContext(AuthContext)
  if (!authService) throw new Error('useAuth must be used within AuthProvider')
  return authService
}
// TODO: add src/core/auth/<provider>.ts implementing AuthService for your chosen provider
// See references/nextjs_defaults.md §4 for Firebase and Auth0 examples
```

**`src/core/api/client.ts`** — ApiClient skeleton (canonical pattern from §3):

```typescript
// src/core/api/client.ts
// createApiClient(auth) — token injected at construction, never passed per call
// Full implementation: references/nextjs_defaults.md §3

import type { AuthService } from '@/core/auth/AuthService'
import type { ApiError } from '@/core/errors/ApiError'
import { v4 as uuidv4 } from 'uuid'

export type ApiClient = ReturnType<typeof createApiClient>

export function createApiClient(auth: AuthService) {
  // Full implementation in nextjs_defaults.md §3
  // Handles: Bearer token, X-Trace-ID, 401 retry, RFC 7807 errors
  async function request<T>(path: string, options: RequestInit = {}, retry = false): Promise<T> {
    const token = await auth.getToken()
    const traceId = uuidv4()
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}${path}`, {
      ...options,
      headers: { 'Content-Type': 'application/json', 'Authorization': token ? `Bearer ${token}` : '',
                  'X-Trace-ID': traceId, ...options.headers },
    })
    if (!res.ok) {
      if (res.status === 401 && !retry) {
        const fresh = await auth.refreshToken()
        if (fresh) return request<T>(path, options, true)
        await auth.logout()
        throw { type: 'error/unauthenticated', title: 'Session expired', status: 401, detail: '', traceId } satisfies ApiError
      }
      const body = await res.json().catch(() => ({}))
      throw { type: body.type ?? 'error/unknown', title: body.title ?? 'An error occurred',
              status: res.status, detail: body.detail ?? '', traceId: body.traceId ?? traceId } satisfies ApiError
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

**`src/core/errors/ApiError.ts`** — ApiError type (RFC 7807):

```typescript
// src/core/errors/ApiError.ts
// RFC 7807 error shape — all API errors use this type
// Never throw raw Error from infrastructure. Never render Error.message in UI.

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

**`.env.example`** — environment variables:

```bash
# .env.example — copy to .env.local and fill in values
# Never commit .env.local

# ── Always required ──────────────────────────────────────────────────────────
NEXT_PUBLIC_API_URL=                   # Backend base URL (e.g. https://api.example.com)
APP_ENV=development                    # production / staging / development

# ── Auth provider config (add entries for your chosen provider) ──────────────
# Firebase example:
#   NEXT_PUBLIC_FIREBASE_API_KEY=
#   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
#   NEXT_PUBLIC_FIREBASE_PROJECT_ID=
#   NEXT_PUBLIC_FIREBASE_APP_ID=
#
# Auth0 example:
#   NEXT_PUBLIC_AUTH0_DOMAIN=
#   NEXT_PUBLIC_AUTH0_CLIENT_ID=
#
# Server-side (never NEXT_PUBLIC_):
#   AUTH_SECRET=           # e.g. for NextAuth.js or JWT signing
#   DATABASE_URL=          # DB connection string for Server Actions

# Never expose secrets via NEXT_PUBLIC_ — those are bundled into the client.
```

---

## Phase 5: Handoff

Tell the developer what was done and what comes next:

> **[Product name] is initialized.**
>
> Created:
> - `specs/project.md` — project memory (update it as the project evolves)
> - `src/core/auth/` — `AuthService.ts` interface + `useAuth.ts` hook (add your provider implementation)
> - `src/core/api/client.ts` — `createApiClient(auth)` skeleton
> - `src/core/errors/ApiError.ts` — RFC 7807 error type
> - `src/features/<feature>/` — clean architecture folders for each v1 feature
> - `src/theme/` — ready for your token and component files
> - `.env.example` — required variables (auth provider section is template — fill in for your provider)
>
> Next steps:
> - Add `src/core/auth/<provider>.ts` implementing `AuthService` for your chosen provider (see `references/nextjs_defaults.md §4` for examples)
> - Copy `.env.example` → `.env.local` and fill in values
> - Run `npm install` (or `pnpm install`) to install dependencies
>
> When you're ready to build: run `/intake <description of your first feature>` to start the process.
