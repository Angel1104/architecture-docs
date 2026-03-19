# Next.js SDM Kit

This project uses the Next.js Spec-Driven Development Methodology Kit. These rules are always active. This kit is Next.js / TypeScript only.

## Methodology Flow

```
/intake → /spec → /plan → /build → /close
```

> Run `/init` once before anything else to set up the project context and folder structure.
> Run `/cr <cr-id>` to execute the full pipeline automatically after `/intake`. It stops only at mandatory human gates.

No stage may be skipped. Implementation without a reviewed spec is blocked by the hook.

## CR Types & Tracks

| Type | Track | Stages |
|------|-------|--------|
| `feature` | Full | spec (10 sections) → plan → build → close |
| `bug` | Minimal | build only (locate → regression test → fix) → close |
| `change` | Lean | spec (3 sections) → build → close |
| `security` | Full | spec → plan → build → close |
| `incident` | Containment-first | build (containment first) → close |
| `refactor` | Lean | spec (3 sections) → build → close |

## 16 Principles

1. **Spec first, code second.** Every feature starts as a specification in `specs/`. No implementation without a reviewed spec.
2. **Tests before code.** Test cases are derived from acceptance criteria BEFORE implementation begins.
3. **The domain layer is sacred.** `src/features/<f>/domain/` has ZERO Next.js, browser API, or third-party imports. Pure TypeScript only.
4. **Repositories define contracts.** All data access flows through abstract repository interfaces. No concrete implementations in the domain layer.
5. **Infrastructure is replaceable.** Swapping an API client (REST → GraphQL) must never require touching domain or application code.
6. **User isolation is mandatory.** Every data access operation is scoped to the authenticated user. The Bearer token from `AuthService` identifies the user. No exceptions.
7. **State is typed.** Every hook and store has explicit TypeScript types: `idle | loading | loaded | error`. No implicit `any`.
8. **CQRS mindset.** Hooks for reads, mutations for writes. Use cases in `domain/use-cases/` are single-responsibility.
9. **Auth is infrastructure.** Token retrieval, Authorization header injection, and 401 handling are infrastructure concerns (`core/api/`, `core/auth/`). Domain and application layers never touch tokens.
10. **Dependencies point inward.** `domain/` → nothing. `application/` → `domain/`. `infrastructure/` → `domain/` + external packages. `presentation/` → `application/` + `domain/`.
11. **Explicit over implicit.** No global mutable state. Dependencies injected through hooks and context. No ambient auth state outside of the auth provider.
12. **Errors are typed.** Every API error maps to `ApiError`. Infrastructure maps fetch errors → typed `ApiError`. Raw `Error` objects never cross the infrastructure boundary into the UI.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** The Node.js hook blocks writes to `src/features/` if no reviewed spec exists.
15. **Name things precisely.** Specs use kebab-case (`user-profile`). Hooks describe capability (`useUserProfile`), not implementation (`useFetchFromAPI`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in chat threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first.js` hook blocks writes to `src/features/` if no reviewed spec exists.
2. **No Next.js / browser API imports in domain.** Any framework import in `src/features/<f>/domain/` is a boundary violation.
3. **No data access without authenticated user.** Every API call includes the Bearer token from `AuthService`. No request executes without auth unless the endpoint is explicitly public.
4. **No tokens in localStorage.** Tokens are managed by the `AuthService` implementation. Never extract and store tokens in localStorage, sessionStorage, or cookies manually.
5. **No secrets in code or NEXT_PUBLIC_ vars.** API keys and server-side secrets go in server-side env vars only. `NEXT_PUBLIC_` is for non-sensitive config only.
6. **No business logic in Server Components or pages.** Components render state and fire actions. No `if` statements on business rules in JSX.
7. **No unguarded routes.** Every route that displays user-specific data must check auth. Unauthenticated users are redirected.
8. **No unvalidated input.** All form input validated with Zod before submission. All external API responses validated at the infrastructure boundary.
9. **No `'use client'` in Server Components unnecessarily.** Default to Server Components. Add `'use client'` only when browser APIs, event handlers, or client-side auth SDK calls are required.

## Architecture Quick Reference

```
src/
├── core/                         # Shared utilities — never imports features
│   ├── api/                      # ApiClient, Bearer token injection, 401 handling
│   ├── auth/                     # AuthService interface + useAuth hook + provider implementations (core/auth/<provider>.ts)
│   └── errors/                   # ApiError type, error mapping
└── features/
    └── <feature>/
        ├── domain/               # ZERO framework dependencies. Pure TypeScript.
        │   ├── entities/         # Immutable TypeScript interfaces / types
        │   ├── repositories/     # Abstract interfaces (no implementation)
        │   └── use-cases/        # Single-responsibility business operations
        ├── application/          # State management. Depends on domain only.
        │   └── hooks/            # React hooks wrapping use cases
        ├── infrastructure/       # Concrete implementations. Depends on domain + packages.
        │   ├── repositories/     # Implements domain repositories via ApiClient
        │   └── models/           # API response types + mapping to domain entities
        └── presentation/         # Components and pages. Depends on application layer.
            ├── pages/            # Next.js page components (Server or Client)
            ├── components/       # Reusable feature components
            └── forms/            # react-hook-form + Zod form components
```

### Dependency Rules (STRICT)

```
domain/          → nothing (pure TypeScript, no React/Next.js/auth SDK)
application/     → domain/ only
infrastructure/  → domain/ + external packages (ApiClient, etc.)
presentation/    → application/ + domain/ (entities for display)
core/            → everything (composition root)
```

### Server vs Client Components

```
Server Component (default):
  - Data fetching at build/request time
  - No useState, useEffect, event handlers
  - No client-side auth SDK
  - No browser APIs

Client Component ('use client'):
  - Event handlers (onClick, onChange, onSubmit)
  - useState, useEffect, custom hooks
  - AuthService calls (getToken, onAuthStateChanged)
  - Browser APIs (localStorage, window, etc.)
```

## Available Commands

| Command | Stage | Description |
|---------|-------|-------------|
| `/init` | Setup | One-time project setup. Creates `specs/project.md`, scaffolds folder structure. Run once before anything else. |
| `/intake <description>` | Intake | Universal entry point — classifies any issue and produces a CR item |
| `/spec <cr-id>` | Spec | Drafts spec → multi-agent review → revise → approve |
| `/plan <cr-id>` | Plan | Translates spec into layered implementation blueprint + test skeletons |
| `/build <cr-id>` | Build | Implements plan layer by layer, runs tests, code review, approves |
| `/close <cr-id>` | Close | Verifies ACs, documents outcome, formally closes CR |
| `/code-review [scope]` | Discovery | Multi-agent code audit → produces findings report → offers to create CR items |
| `/cr <cr-id>` | Pipeline | Automated full pipeline: spec → plan → build → close |
| `/status` | — | Shows all CRs: open, in progress, blocked, recently closed. No arguments. |
| `/help` | — | Prints this command reference |

## Available Agents

| Agent | Expertise | Can Help With |
|-------|-----------|---------------|
| `domain-analyst` | Requirements & specifications | Spec review, edge cases, acceptance criteria, scope |
| `sw-architect` | Next.js App Router architecture | Feature boundaries, Server/Client split, dependency direction |
| `security-engineer` | Security & threat modeling | XSS, CSRF, Firebase auth, secrets, SSR security |
| `qa-engineer` | Testing & quality | msw handlers, React Testing Library, user isolation tests |
| `nextjs-engineer` | Next.js + TypeScript implementation | Feature implementation, ApiClient, forms, auth flows |

> `/spec` and `/build` orchestrate multi-agent reviews automatically.
> All agents can also be invoked independently.

## References

All reference files are in `references/`:

- `nextjs_defaults.md` — Next.js Technical Constitution: every pre-decided default (ApiClient, AuthService abstraction, forms, SSR, testing, theme, env vars). Applied automatically by commands.
- `nextjs_spec_template.md` — Next.js spec format (screens/routes, Server/Client split, API dependencies, form contracts, auth perspective, error scenarios).

## Stack

- **Web**: Next.js 14+ / TypeScript (App Router)
- **Auth**: Provider-agnostic — `AuthService` abstraction in `core/auth/`. Concrete implementation chosen per project (Firebase, Auth0, custom JWT, etc.). Client SDK used in `'use client'` only.
- **Backend**: Any REST backend — contract: Bearer token, RFC 7807 errors, X-Trace-ID, cursor pagination
- **Architecture**: Feature-based Clean Architecture + React hooks
- **User isolation**: Bearer token from `AuthService` scopes all API requests; backend enforces RLS

## Key Packages

| Package | Purpose |
|---------|---------|
| `next` | Framework (App Router, SSR, SSG) |
| `typescript` | Type safety |
| `tailwindcss` | Styling (CSS custom properties + utility classes) |
| Auth provider SDK | Chosen per project — implements `AuthService` (e.g., `firebase`, `@auth0/nextjs-auth0`) — `'use client'` only |
| `react-hook-form` | Form state management |
| `zod` | Schema validation (forms + API responses) |
| `zustand` | Global client state |
| `@tanstack/react-query` | Server state management and caching |
| `msw` | API mocking for tests |
| `@testing-library/react` | Component testing |
| `vitest` | Test runner |
