# Architecture Overview

> Quick reference for what we have and what we're building. Full details live in each dedicated doc.

---

## What We Have

A **full-stack, multi-tenant SaaS architecture** covering web, mobile, backend, and infrastructure — all decisions are made and documented as source of truth for scaffolding new projects.

### Stack at a Glance

| Layer | Technology |
|---|---|
| Web | Next.js 14+ · TypeScript · Tailwind · TanStack Query · Zustand |
| Mobile | Flutter · Riverpod · GoRouter · Dio |
| Backend (primary) | NestJS · Prisma · Neon Postgres · Upstash Redis |
| Backend (AI/ML) | FastAPI · Cloud Tasks (OIDC-authenticated) |
| Auth | Firebase (client auth) → backend authorization |
| Infrastructure | Vercel · Google Cloud Run · Cloudflare · Neon · Cloudflare R2 |
| Observability | OpenTelemetry · GCP Logging |

---

## What We're Doing

Five architecture documents define our standards across every layer:

### [ARCHITECTURE.md](ARCHITECTURE.md) — Master Document
The source of truth. Defines the full system, auth contract, multi-tenancy model, data flows, API contract, and 15 non-negotiable rules. Start here.

**Key decisions:**
- Firebase authenticates → backend authorizes (no exceptions)
- Multi-tenancy via Postgres Row Level Security (RLS)
- Async operations via Google Cloud Tasks
- Cursor-based pagination on all list endpoints
- No business logic in the UI layer

---

### [ARCHITECTURE_BACKEND.md](ARCHITECTURE_BACKEND.md) — NestJS + FastAPI
Hexagonal architecture with a strict module structure. FastAPI is scoped exclusively to AI/ML tasks triggered by Cloud Tasks.

**Key decisions:**
- Interface → Application → Domain ← Infrastructure layering
- Auth: Firebase token verification + lazy user creation in Neon
- Prisma migrations follow expand/contract pattern
- Error responses follow RFC 7807
- Tests hit a real database — no mocks for repository tests

---

### [ARCHITECTURE_WEB.md](ARCHITECTURE_WEB.md) — Next.js Frontend
Feature-based folder structure. One HTTP exit point (ApiClient). Server Components by default.

**Key decisions:**
- `ApiClient` is the only place HTTP calls happen
- Auth token refresh + 401 retry handled in ApiClient interceptor
- Forms use react-hook-form + Zod, with server-side validation as fallback
- `'use client'` only when strictly necessary
- Tests use Vitest + RTL + MSW — ApiClient is never mocked

---

### [ARCHITECTURE_MOBILE.md](ARCHITECTURE_MOBILE.md) — Flutter
Clean architecture with feature-based folders. Online-first (no local persistence by default).

**Key decisions:**
- Data flow: Screen → Controller → UseCase → Repository → DataSource → ApiClient
- Sealed `AppError` class for typed error handling
- State management with Riverpod (AsyncNotifier / StateNotifier)
- GoRouter with auth guards and splash screen handling
- Tests: fake repositories for use cases, mocktail for controllers, patrol for integration

---

### [ARCHITECTURE_DEVOPS.md](ARCHITECTURE_DEVOPS.md) — Infrastructure & CI/CD
Three environments (dev / staging / prod). GitHub Actions for CI and deployment. Fastlane for mobile store delivery.

**Key decisions:**
- Cloudflare handles DNS, WAF, and Turnstile CAPTCHA
- GCP Workload Identity Federation — no long-lived service account keys
- Staging deploys automatically on merge to main; prod requires manual approval
- Mobile: Android → Play Store, iOS → TestFlight via Fastlane
- Rollback: Cloud Run traffic shifting, Vercel instant promotion

---

## Folder Structure

```
Architecture/
├── ARCHITECTURE.md          # Master — start here
├── ARCHITECTURE_BACKEND.md  # NestJS + FastAPI
├── ARCHITECTURE_WEB.md      # Next.js
├── ARCHITECTURE_MOBILE.md   # Flutter
├── ARCHITECTURE_DEVOPS.md   # Infra & CI/CD
├── BE-FASTAPI/              # FastAPI reference/scaffold
├── BE-NESTJS/               # NestJS reference/scaffold
├── FE-MOBILE/               # Flutter reference/scaffold
└── FE-WEB/                  # Next.js reference/scaffold
```

---

## Core Principles (Non-Negotiable)

1. No business logic in the UI
2. Auth always validated server-side — never trust the client
3. Every tenant is isolated via RLS — no cross-tenant data leaks
4. No hardcoded secrets or environment values
5. All async work goes through Cloud Tasks
6. One HTTP exit point per client (ApiClient)
7. Errors follow RFC 7807 (backend) and typed sealed classes (mobile)
8. No mocking the database in repository tests
