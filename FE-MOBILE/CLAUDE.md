# Flutter SDM Kit

This project uses the Flutter Spec-Driven Development Methodology Kit. These rules are always active. This kit is Flutter/Dart only.

## Methodology Flow

```
/intake → /spec → /plan → /build → /close
```

> Run `/cr <cr-id>` to execute the full pipeline automatically after `/intake`. It stops only at mandatory human gates.
> Run `/init` once before anything else to set up the project context and folder structure.

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
2. **Tests before code.** Test cases (use case tests, controller tests, widget tests) are derived from acceptance criteria BEFORE implementation begins. Tests run RED before any implementation code is written.
3. **The domain layer is sacred.** `lib/features/<f>/domain/` has ZERO Flutter SDK, Dio, or Firebase imports. Pure Dart only.
4. **Repositories define contracts.** All data access flows through abstract repository interfaces in `domain/repositories/`. No concrete implementations in the domain layer.
5. **Infrastructure is replaceable.** Swapping a repository implementation (e.g., Dio → GraphQL) must never require touching domain or application code.
6. **User isolation is mandatory.** Every data access operation passes `userId` (from JWT). No exceptions.
7. **State is sealed.** Every controller has `@freezed` sealed states: `initial`, `loading`, `loaded(data)`, `error(AppError)`. No raw strings, no mutable state.
8. **CQRS mindset.** Use cases in `domain/usecases/` are single-responsibility — one per user action.
9. **Auth is infrastructure.** Token injection and refresh are infrastructure concerns (`core/network/`, `core/auth/`). The domain layer never touches tokens.
10. **Dependencies point inward.** `domain/` → nothing. `data/` → `domain/` + external packages. `presentation/` → `domain/` + Riverpod controllers.
11. **Explicit over implicit.** No global state, no ambient context. Dependencies registered in `app/providers/app_providers.dart` via Riverpod ProviderScope.
12. **Errors are typed.** Infrastructure maps `DioException` → `AppError` (sealed class). `AppError` is propagated through Riverpod state. `DioException` never crosses the data layer boundary.
13. **Review before merge.** Multi-agent review (spec, architecture, security) catches issues before code reaches production.
14. **Automate enforcement.** The hook blocks writes to `lib/features/` if no reviewed spec exists. `flutter analyze` catches boundary violations.
15. **Name things precisely.** Specs use kebab-case (`user-profile`). Repositories describe capabilities (`UserRepository`), not implementations (`DioUserRepository`).
16. **Document decisions.** Architecture decisions, trade-offs, and rejected alternatives are captured in specs, not lost in chat threads.

## 9 Non-Negotiables

These are HARD blockers. Code violating any of these must not proceed.

1. **No implementation without a spec.** The `enforce-spec-first.js` hook blocks writes to `lib/features/` if no reviewed spec exists.
2. **No Flutter/Dio/Firebase imports in domain.** Any external package import in `lib/features/<f>/domain/` is a boundary violation.
3. **No data access without userId.** Every repository method that returns user data must be scoped to `userId`. No exceptions.
4. **No tokens stored manually.** Tokens are managed by the `AuthService` implementation — never extract and store them in SharedPreferences, Hive, or any manual store.
5. **No secrets in code.** API keys and credentials must come from `--dart-define` build-time constants or `AppConfig`. Never hardcoded.
6. **No business logic in presentation.** Widgets consume Riverpod state and fire controller methods. No `if` statements on business rules in widget `build()` methods.
7. **No unguarded routes.** Every route that displays user-specific data must have an auth guard in GoRouter. The guard must respect the `initializing` state.
8. **No unvalidated input.** All external input is validated at the data layer boundary before it reaches the domain layer.
9. **No cross-user data access.** Tests must include user isolation verification. A query that returns another user's data is a P0 incident.

## Architecture Quick Reference

```
lib/
├── core/                         # Shared infrastructure — imported by features
│   ├── network/                  # Dio client, auth interceptor, trace interceptor
│   ├── auth/                     # AuthService, AppAuthState enum
│   ├── errors/                   # sealed class AppError, FieldError
│   ├── config/                   # AppConfig (dart-define constants)
│   └── utils/                    # Extensions, formatters, permission_utils
├── ui/                           # Reusable UI components
│   ├── primitives/               # AppButton, AppInput, AppCard
│   ├── components/               # EmptyState, ErrorView, LoadingOverlay
│   └── layouts/                  # ScaffoldWithNav, AuthLayout
├── theme/                        # Token system: core → semantic → ThemeData extensions
├── app/
│   ├── router/                   # GoRouter — all routes + auth guard
│   ├── providers/                # app_providers.dart — all Riverpod providers registered
│   └── bootstrap/                # app_bootstrap.dart — Firebase init + runApp
└── features/
    └── <feature>/
        ├── domain/               # ZERO external dependencies. Pure Dart.
        │   ├── entities/         # Immutable @freezed data classes
        │   ├── repositories/     # Abstract interfaces (no implementation)
        │   └── usecases/         # Single-responsibility — one per user action
        ├── data/                 # Concrete implementations. Depends on domain + packages.
        │   ├── datasources/      # HTTP calls via ApiClient
        │   ├── models/           # JSON models (freezed + json_serializable)
        │   └── repositories/     # Implements domain repository interfaces
        └── presentation/         # Widgets and screens. Consumes Riverpod providers.
            ├── controllers/      # StateNotifier / AsyncNotifier
            ├── screens/          # Full-page widgets
            └── widgets/          # Feature-specific components
```

### Dependency Rules (STRICT)

```
domain/          → nothing (pure Dart, no Flutter/Dio/Firebase)
data/            → domain/ + external packages (Dio, Firebase, etc.)
presentation/    → domain/ + Riverpod providers (controllers)
core/            → external packages only (never imports features)
app/             → everything (composition root)
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
| `/help` | — | Prints this command reference |

## Available Agents

| Agent | Expertise | Can Help With |
|-------|-----------|---------------|
| `domain-analyst` | Requirements & specifications | Spec review, edge cases, acceptance criteria, scope |
| `sw-architect` | Flutter Clean Architecture | Layer boundaries, Riverpod patterns, repository interfaces, dependency direction |
| `security-engineer` | Security & threat modeling | Firebase auth, Dio interceptors, user isolation, input validation |
| `qa-engineer` | Testing & quality | FakeRepository pattern, controller tests, widget tests, user isolation tests |
| `flutter-engineer` | Flutter + Dart implementation | Feature implementation, Riverpod, Dio, auth flows, debugging |

> `/spec` and `/build` orchestrate multi-agent reviews automatically.
> All agents can also be invoked independently.

## References

All reference files are in `references/`:

- `flutter_defaults.md` — Flutter Technical Constitution: every pre-decided default (Riverpod patterns, auth, ApiClient, AppError, navigation, offline strategy, permissions, testing). Applied automatically by commands.
- `flutter_spec_template.md` — Flutter spec format (screens, Riverpod contracts, offline behavior, permissions, auth context, navigation flows).

## Stack

- **Mobile**: Flutter / Dart
- **Auth**: Provider-agnostic — `AuthService` abstraction in `core/auth/`. Concrete implementation chosen per project (Firebase, Auth0, custom JWT, etc.)
- **Backend**: Any REST backend reachable via Dio — contract: Bearer token, RFC 7807 errors, X-Trace-ID, cursor pagination
- **Architecture**: Clean Architecture + Riverpod
- **User isolation**: `userId` from JWT scopes all data access; backend enforces RLS

## Key Packages

| Package | Purpose |
|---------|---------|
| `flutter_riverpod` + `riverpod_annotation` | State management (StateNotifier, AsyncNotifier) |
| `freezed` + `freezed_annotation` | Immutable entities and sealed state classes |
| `json_serializable` + `build_runner` | JSON serialization for API models |
| `dio` | HTTP client |
| `go_router` | Navigation with auth guard (respects `initializing` state) |
| Auth provider SDK | Chosen per project — implements `AuthService` (e.g., `firebase_auth`, `auth0_flutter`) |
| Push notifications SDK | Chosen per project (e.g., `firebase_messaging` if using FCM) |
| `connectivity_plus` | Offline detection |
| `permission_handler` | Runtime permissions (just-in-time) |
| `cached_network_image` | Network image caching |
| `shimmer` | Skeleton loading screens |
| `mocktail` | Controller unit tests (mock use cases) |
| `integration_test` + `patrol` | E2E tests for critical flows |
