# comocom Flutter SDM Kit

This project uses the comocom Flutter Spec-Driven Development Methodology Kit. These rules are always active. This kit is Flutter/Dart only — no `--platform` flag is needed.

## Methodology Flow

```
/spec-init → /spec-review → /spec-revise → /spec-review → /plan → /test-gen → /implement → Validate
```

> If `/spec-review` returns REVISIONS NEEDED, run `/spec-revise` to resolve all blockers, then re-review. Repeat until APPROVED.

No stage may be skipped. Implementation without a reviewed spec is blocked by the Dart hook.

## 16 Principles

1. **Spec first, code second.** Every feature starts as a specification in `specs/`. No implementation without a reviewed spec.
2. **Tests before code.** Test cases (BLoC tests, widget tests, use case tests) are derived from acceptance criteria BEFORE implementation begins.
3. **The domain layer is sacred.** `lib/features/<f>/domain/` has ZERO Flutter SDK, Dio, Hive, or Firebase imports. Pure Dart only.
4. **Repositories define contracts.** All data access flows through abstract repository interfaces in `domain/repositories/`. No concrete implementations in the domain layer.
5. **Infrastructure is replaceable.** Swapping a repository implementation (e.g., Dio → GraphQL) must never require touching domain or application code.
6. **User isolation is mandatory.** Every data access operation passes `userId` (from JWT). Every local storage key is scoped by `userId`. No exceptions.
7. **State is sealed.** Every BLoC has `@freezed` sealed states: `initial`, `loading`, `loaded(data)`, `error(message)`. No raw strings, no mutable state.
8. **CQRS mindset.** BLoC events = commands or queries. Use cases in `domain/use_cases/` are single-responsibility — one per BLoC event type.
9. **Auth is infrastructure.** Token storage, token refresh, and Authorization header injection are infrastructure concerns (`core/network/`, `core/auth/`). The domain and application layers never touch tokens.
10. **Dependencies point inward.** `domain/` → nothing. `application/` → `domain/`. `infrastructure/` → `domain/` + external packages. `presentation/` → `application/` + `domain/` entities.
11. **Explicit over implicit.** No global state, no ambient context. `userId` and dependencies are passed explicitly through constructors and `get_it`.
12. **Errors are typed Failures.** Domain and application layers return `Either<Failure, T>`. Infrastructure maps `DioException` → typed `Failure`. `DioException` never crosses the infrastructure boundary.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** The Dart hook blocks writes to `lib/features/` if no reviewed spec exists. `flutter analyze` catches boundary violations.
15. **Name things precisely.** Specs use kebab-case (`user-profile`). Repositories describe capabilities (`UserRepository`), not implementations (`DioUserRepository`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in chat threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first.dart` hook blocks writes to `lib/features/` if no reviewed spec exists.
2. **No Flutter/Dio/Hive imports in domain.** Any external package import in `lib/features/<f>/domain/` is a boundary violation.
3. **No data access without userId.** Every repository method must accept `userId` as a parameter. No query or cache operation executes without user scoping.
4. **No tokens in SharedPreferences.** Access and refresh tokens must be stored in `FlutterSecureStorage` only. Never SharedPreferences. Never in-memory across sessions.
5. **No secrets in code.** API keys, tokens, and credentials must come from environment variables or build-time constants. Never hardcoded.
6. **No business logic in presentation.** Widgets fire BLoC events and render BLoC states. No `if` statements on business rules in widget `build()` methods.
7. **No unguarded routes.** Every route that displays user-specific data must have an auth guard in GoRouter. Role-restricted routes must have a role guard.
8. **No unvalidated input.** All external input is validated at the infrastructure boundary before it reaches the domain layer.
9. **No cross-user data access.** Tests must include user isolation verification. A query that returns another user's data is a P0 incident.

## Architecture Quick Reference

```
lib/
├── core/                         # Shared utilities — depends on everything
│   ├── di/                       # get_it service locator, injection.dart
│   ├── network/                  # Dio client, auth interceptor, error handler
│   ├── auth/                     # Token storage (FlutterSecureStorage), refresh logic
│   └── errors/                   # Failure types, exception hierarchy
└── features/
    └── <feature>/
        ├── domain/               # ZERO external dependencies. Pure Dart.
        │   ├── entities/         # Immutable @freezed data classes
        │   ├── repositories/     # Abstract interfaces (no implementation)
        │   └── use_cases/        # Single-responsibility business operations
        ├── application/          # State management. Depends on domain only.
        │   └── blocs/            # BLoC classes, events, sealed @freezed states
        ├── infrastructure/       # Concrete implementations. Depends on domain + packages.
        │   ├── repositories/     # Implements domain repositories via Dio
        │   ├── models/           # JSON models (freezed + json_serializable)
        │   └── data_sources/     # API data sources, Hive local cache
        └── presentation/         # Widgets and screens. Depends on application layer.
            ├── screens/          # Full-page widgets (BlocBuilder/BlocListener)
            ├── widgets/          # Reusable components (skeleton, error, empty state)
            └── router/           # GoRouter route definitions for this feature
```

### Dependency Rules (STRICT)

```
domain/          → nothing (pure Dart, no Flutter/Dio/Hive/Firebase)
application/     → domain/ only
infrastructure/  → domain/ + external packages (Dio, Hive, etc.)
presentation/    → application/ + domain/ (entities for display)
core/            → everything (composition root)
```

## Available Commands

| Command | Role | Stage | Description |
|---------|------|-------|-------------|
| `/spec-init <feature>` | Domain Analyst | Spec | Interactive wizard — draws out Flutter feature requirements, adds domain intelligence, generates spec |
| `/spec-review <feature>` | — (orchestrator) | Review | Runs domain-analyst, sw-architect, and security-engineer on the spec; produces consolidated verdict |
| `/spec-revise <feature>` | Senior Software Architect | Revise | Resolves all blockers and warnings from the review; asks user only for business decisions |
| `/spec-auto <feature>` | — (orchestrator) | Review | Automated review-revise loop — repeats until APPROVED, pauses only for business decisions |
| `/plan <feature>` | Technical Architect | Plan | Translates reviewed spec into layered Flutter implementation blueprint |
| `/test-gen <feature>` | QA Engineer | Test | Generates BLoC tests, use case tests, widget tests, integration tests (TDD — before code) |
| `/implement <feature>` | Flutter Engineer | Build | Implements feature from plan, inside-out Clean Architecture order |
| `/code-auto <feature>` | Technical Lead | Build | Fully automated pipeline — implement, test each layer, code-review, report |
| `/code-review <feature>` | — (orchestrator) | Review | Multi-agent code review: standards, security, performance |
| `/debug <feature>` | — (orchestrator) | Debug | Root cause analysis on failing tests, Dart errors, or BLoC issues |

## Available Agents

| Agent | Expertise | Can Help With |
|-------|-----------|---------------|
| `domain-analyst` | Requirements & specifications | Review spec; draft/refine specs; detect edge cases; write acceptance criteria |
| `sw-architect` | System design & Clean Architecture | Review architecture; verify BLoC contracts; validate repository interfaces; plan features |
| `security-engineer` | Security & threat modeling | Token storage review; auth interceptor design; user isolation audit; input validation |
| `qa-engineer` | Testing & quality | BLoC test generation; widget test generation; user isolation tests; adversarial thinking |
| `flutter-engineer` | Flutter + Dart implementation | Feature implementation; code review; state management design; auth flows; debugging |

> `/spec-review` orchestrates `domain-analyst` + `sw-architect` + `security-engineer` for spec review.
> All agents can also be invoked independently for any task within their expertise.

## References

All reference files are in `.claude/references/`:

- `flutter_defaults.md` — Flutter Technical Constitution: every pre-decided Flutter default (auth, storage, BLoC patterns, navigation, error handling, testing). Applied automatically by commands.
- `flutter_spec_template.md` — Flutter spec format (screens, BLoC contracts, offline behavior, permissions, auth context, navigation flows).

## Stack

- **Mobile**: Flutter / Dart
- **Auth**: Firebase Authentication (JWT with custom claims)
- **Backend**: GCP (API calls via Dio; backend enforces tenant/user isolation server-side)
- **Architecture**: Clean Architecture + BLoC + Event-Driven UI
- **User isolation**: `userId` from JWT claim scopes all data access; local cache keyed by `userId`

## Key Packages

| Package | Purpose |
|---------|---------|
| `freezed` + `freezed_annotation` | Immutable entities and sealed BLoC states |
| `json_serializable` | JSON serialization for API models |
| `dio` | HTTP client |
| `flutter_secure_storage` | JWT token storage (Keychain / Keystore) |
| `go_router` | Navigation with auth and role guards |
| `flutter_bloc` | State management (BLoC / Cubit) |
| `get_it` | Dependency injection service locator |
| `dartz` | `Either<Failure, T>` for typed error handling |
| `bloc_test` | BLoC unit testing |
| `mockito` + `build_runner` | Mocking for tests |
| `shimmer` | Skeleton loading screens |
| `hive` | Local structured cache (user-scoped) |
| `firebase_crashlytics` | Error reporting |
