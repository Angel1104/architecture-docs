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

**5. Firebase** — after scope:
> "Is a Firebase project already configured for this? If yes, what's the project ID?"

**6. Backend** — after Firebase:
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
- Firebase: configured yes/no + project ID if yes
- Backend URL or placeholder
- File uploads: yes/no
- Billing: yes/no

Then present a brief summary and ask for confirmation before writing anything:

> "Here's what I've got — [product name]: [one sentence description]. v1 features: [list]. Out of scope: [summary]. Firebase: [status]. Backend: [url or TBD]. Uploads: [yes/no]. Billing: [yes/no].
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

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Firebase Auth | Autenticación de usuarios (JWT) | <Sí — project ID: X / Pendiente> |
| NestJS Backend | API REST (/v1/) | <URL o Pendiente> |
| Cloudflare R2 | File uploads | <Sí / No aplica en v1> |
| Billing | Suscripciones | <En scope / No en scope> |

## Decisiones tomadas en este proyecto
<project-specific decisions that deviate from nextjs_defaults.md defaults, or "Ninguna — seguir todos los defaults de nextjs_defaults.md">

## Feature Map (se actualiza con cada /build completado)
| Feature | Archivos clave | Hooks/Componentes principales | Endpoints que consume |
|---------|---------------|-------------------------------|----------------------|
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

**`src/core/api/client.ts`** — minimal ApiClient skeleton:

```typescript
// src/core/api/client.ts
// ApiClient — injects Firebase Bearer token into every request
// Full implementation: references/nextjs_defaults.md § ApiClient

import { ApiError } from '@/core/errors/ApiError';

const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function apiClient<T>(
  path: string,
  options: RequestInit & { getToken: () => Promise<string> }
): Promise<T> {
  const { getToken, ...fetchOptions } = options;
  const token = await getToken();

  const res = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...fetchOptions.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw ApiError.fromResponse(res.status, body);
  }

  return res.json();
}
```

**`src/core/auth/firebase.ts`** — Firebase client SDK init skeleton:

```typescript
// src/core/auth/firebase.ts
// Firebase client SDK initialization — use only in 'use client' files
// Full config: references/nextjs_defaults.md § Firebase

import { initializeApp, getApps } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

**`src/core/auth/useAuth.ts`** — useAuth hook skeleton:

```typescript
// src/core/auth/useAuth.ts
// useAuth — wraps Firebase onAuthStateChanged
// Full implementation: references/nextjs_defaults.md § Auth

'use client';

import { useEffect, useState } from 'react';
import { onAuthStateChanged, User } from 'firebase/auth';
import { auth } from './firebase';

type AuthState = 'loading' | 'authenticated' | 'unauthenticated';

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [state, setState] = useState<AuthState>('loading');

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
      setUser(u);
      setState(u ? 'authenticated' : 'unauthenticated');
    });
  }, []);

  return { user, state };
}
```

**`src/core/errors/ApiError.ts`** — ApiError type:

```typescript
// src/core/errors/ApiError.ts
// Typed API error — infrastructure maps all fetch errors to this type
// Domain and application layers never see raw Error or fetch responses

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }

  static fromResponse(status: number, body: Record<string, unknown>): ApiError {
    return new ApiError(
      status,
      String(body['code'] ?? 'UNKNOWN'),
      String(body['message'] ?? `HTTP ${status}`)
    );
  }
}
```

**`.env.example`** — all environment variables from `references/nextjs_defaults.md` § 10:

```bash
# .env.example — copy to .env.local and fill in values
# Never commit .env.local

# ── Client-visible (NEXT_PUBLIC_) ──────────────────────────────────────────
# Non-sensitive config only. These are bundled into the client bundle.

NEXT_PUBLIC_API_URL=                   # Backend base URL (e.g. https://api.example.com)
NEXT_PUBLIC_FIREBASE_API_KEY=          # Firebase web API key
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=      # Firebase auth domain
NEXT_PUBLIC_FIREBASE_PROJECT_ID=       # Firebase project ID
NEXT_PUBLIC_FIREBASE_APP_ID=           # Firebase app ID

# ── Server-side only ────────────────────────────────────────────────────────
# Never use NEXT_PUBLIC_ for these. Only available in Server Actions and API routes.

FIREBASE_ADMIN_PRIVATE_KEY=            # Firebase Admin SDK private key
FIREBASE_ADMIN_CLIENT_EMAIL=           # Firebase Admin SDK client email
DATABASE_URL=                          # DB connection string (if Server Actions use DB directly)
```

---

## Phase 5: Handoff

Tell the developer what was done and what comes next:

> **[Product name] is initialized.**
>
> Created:
> - `specs/project.md` — project memory (update it as the project evolves)
> - `src/core/` — ApiClient, Firebase auth init, useAuth hook, ApiError
> - `src/features/<feature>/` — empty clean architecture folders for each v1 feature
> - `src/theme/` — empty, ready for your token and component files
> - `.env.example` — all required environment variables
>
> Before your first feature:
> - Copy `.env.example` → `.env.local` and fill in the Firebase and API values
> - Run `npm install` (or `pnpm install`) to make sure dependencies are in place
>
> When you're ready to build: run `/intake <description of your first feature>` to start the process.
