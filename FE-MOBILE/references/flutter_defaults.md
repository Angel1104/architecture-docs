# Flutter Technical Constitution

> This file is the source of truth for all pre-decided Flutter defaults.
> Applied automatically by all commands in this kit. Do not ask about these — implement them.

---

## TL;DR — Critical Defaults (read this first if context is compressed)

| # | Rule | Detail |
|---|------|--------|
| 1 | Domain layer: pure Dart | No Flutter SDK, no Dio, no auth SDK imports anywhere in `domain/` |
| 2 | AuthService abstraction | Auth interceptor calls `authService.getToken()` / `refreshToken()` / `logout()` — never calls auth SDK directly |
| 3 | AppError sealed class | No `Either`, no `dartz`. `DioException` never crosses the data layer boundary — always map to `AppError` |
| 4 | 3-state auth | `initializing / authenticated / unauthenticated` — GoRouter guard must handle all 3, never redirect during `initializing` |
| 5 | FakeRepository for use case tests | `FakeRepository implements IRepository` for domain/use case tests — `mocktail` ONLY for controller tests (mocking use cases) |
| 6 | StateNotifier error state | Error state uses `AppError`, never `String`. `@freezed` sealed states: `initial / loading / loaded(data) / error(AppError)` |
| 7 | Online-first | No Hive/sqflite/Drift in v1. Show `ConnectivityError` state when offline — never silently fail |
| 8 | HTTP contract | Bearer token via `AuthService.getToken()`, `X-Trace-ID: <uuid>` per request, RFC 7807 errors from backend |
| 9 | Cursor pagination | `{data, nextCursor, hasMore}` — never offset/page number |
| 10 | Just-in-time permissions | Request at the moment of use — never at app start, never pre-emptively |

> Full rules below. TL;DR is a summary — the sections below are authoritative.

---

## 1. Architecture — Clean Architecture + Riverpod

| Decision | Default |
|----------|---------|
| Pattern | Clean Architecture: domain → data → presentation |
| State management | Riverpod (StateNotifier / AsyncNotifier) |
| DI | Riverpod ProviderScope — registered in `app/providers/app_providers.dart` |
| Immutable data | All entities and models use `freezed` |
| Error handling | `sealed class AppError` — no `Either`, no `dartz` |
| Navigation | `go_router` with auth guard that respects the `initializing` state |

### Layer structure per feature

```
lib/features/<name>/
├── domain/
│   ├── entities/       # Pure Dart — zero external dependencies
│   ├── repositories/   # Abstract interfaces (INameRepository)
│   └── usecases/       # Single-responsibility — one per user action
├── data/
│   ├── datasources/    # HTTP calls via ApiClient (Dio)
│   ├── models/         # freezed + json_serializable JSON models
│   └── repositories/   # Implements domain repository interfaces
└── presentation/
    ├── controllers/    # StateNotifier / AsyncNotifier (Riverpod)
    ├── screens/        # Full-page widgets
    └── widgets/        # Feature-specific components
```

### Dependency rules (STRICT)

```
domain/          → nothing (pure Dart, no Flutter SDK, no Dio, no Firebase)
data/            → domain/ + external packages (Dio, Firebase, etc.)
presentation/    → domain/ + Riverpod controllers
core/            → external packages only (never imports features)
```

---

## 2. Auth — Provider-Agnostic Design

| Decision | Default |
|----------|---------|
| Auth state | `AppAuthState` enum: `initializing`, `authenticated`, `unauthenticated` |
| Token injection | Dio auth interceptor: `Authorization: Bearer <token>` via `AuthService.getToken()` |
| Token refresh | On 401: `AuthService.refreshToken()` + retry once. On second failure: emit logout. |
| Logout | `AuthService.logout()` + navigate to login |
| Token storage | Managed by the auth provider SDK — never extract or store tokens manually |
| Auth SDK placement | Only imported in `data/` and `core/` layers — never in `domain/` |

### The contract — what the FE always needs

```dart
// core/auth/auth_service.dart
abstract class AuthService {
  AppAuthState get state;
  Stream<AppAuthState> get stateChanges;

  Future<String?> getToken();          // Bearer token for ApiClient
  Future<String?> refreshToken();      // Force-refresh on 401
  Future<void> logout();               // Clear session + navigate to login
}
```

### Three-state auth (mandatory — regardless of provider)

```dart
// core/auth/auth_state.dart
enum AppAuthState {
  initializing,    // Auth SDK has not yet emitted the first value
  authenticated,   // User is signed in
  unauthenticated  // User is signed out (we know with certainty)
}
```

The `initializing` state prevents the GoRouter guard from flashing `/auth/login` before the auth SDK is ready.

### Firebase implementation example

```dart
// core/auth/providers/firebase_auth_service.dart
class FirebaseAuthService implements AuthService {
  @override
  Future<String?> getToken() =>
    FirebaseAuth.instance.currentUser?.getIdToken();

  @override
  Future<String?> refreshToken() =>
    FirebaseAuth.instance.currentUser?.getIdToken(true);

  @override
  Future<void> logout() => FirebaseAuth.instance.signOut();
}
```

### GoRouter guard pattern (same regardless of provider)

```dart
redirect: (context, state) {
  final authState = ref.read(authServiceProvider).state;

  if (authState == AppAuthState.initializing) return '/splash';

  final isAuthenticated = authState == AppAuthState.authenticated;
  final isGoingToAuth = state.matchedLocation.startsWith('/auth');
  final isOnSplash = state.matchedLocation == '/splash';

  if (!isAuthenticated && !isGoingToAuth) return '/auth/login';
  if (isAuthenticated && (isGoingToAuth || isOnSplash)) return '/home';
  return null;
},
```

### Rules

- `AuthService` interface lives in `core/auth/` — the concrete implementation lives in `core/auth/providers/`
- Never import any auth SDK (`firebase_auth`, `amplify_auth_cognito`, etc.) directly in the auth interceptor — always through `AuthService`
- Never navigate from the splash screen programmatically — GoRouter handles redirection
- The `initializing` state must never persist longer than 3 seconds. If the auth SDK takes longer, treat as `NetworkError(isOffline: true)`
- JWT claims are read server-side — the mobile app never decodes claims for authorization decisions

---

## 3. ApiClient — Dio

File: `core/network/api_client.dart` — the **only** file that calls HTTP.

| Decision | Default |
|----------|---------|
| HTTP client | Dio with typed interceptors |
| Auth interceptor | Adds `Authorization: Bearer <token>` via `AuthService.getToken()` — provider-agnostic |
| Trace interceptor | Generates UUID and adds `X-Trace-ID` header per request |
| Timeouts | Connect: 10s, Receive: 30s |
| Error mapping | `DioException` → `AppError` in repository `catch` blocks. Never let `DioException` cross the data layer boundary. |
| JSON serialization | `freezed` + `json_serializable`. No manual `fromJson`. |

### Interceptor files

```
core/network/
├── api_client.dart           # Dio instance with interceptors registered
├── interceptors/
│   ├── auth_interceptor.dart # Adds Authorization: Bearer header
│   └── trace_interceptor.dart # Adds X-Trace-ID: <uuid>
```

### 401 retry logic

1. Intercept the 401 response.
2. Call `authService.refreshToken()`.
3. Retry the original request once with the new token.
4. If the retry also returns 401: call `authService.logout()` to emit logout.

### Rules

- `Dio` is never instantiated directly in a datasource or controller — always inject through `core/network/`
- Every request has `X-Trace-ID` — no exceptions
- `DioException` never reaches the presentation layer

---

## 4. Error Handling — `sealed class AppError`

File: `core/errors/app_error.dart`

```dart
sealed class AppError {
  const AppError();
}

// 4xx domain errors from backend (RFC 7807 responses)
class DomainError extends AppError {
  final String type;         // stable code: 'user/not-found'
  final String title;        // show to user
  final int status;
  final String detail;
  final String traceId;
  final List<FieldError> fieldErrors; // only on 422
  const DomainError({required this.type, required this.title, required this.status, required this.detail, required this.traceId, this.fieldErrors = const []});
}

// 5xx, timeout, no connection
class NetworkError extends AppError {
  final String? traceId;
  final bool isOffline;
  const NetworkError({this.traceId, this.isOffline = false});
}

// Unexpected bug — not for user display
class UnknownError extends AppError {
  final Object cause;
  const UnknownError(this.cause);
}
```

### Error handling rules by layer

| Layer | Responsibility |
|-------|---------------|
| `ApiClient` | Catches `DioException`, converts to `AppError`, rethrows |
| Repository | Catches `AppError` from datasource, propagates it |
| Controller | Catches `AppError`, emits it into Riverpod state |
| Screen | Displays `error.title` or `error.detail`. Never shows `type`, stack trace, or raw exception |

- `NetworkError(isOffline: true)` → show connectivity banner
- `DomainError` with `status == 422` and `fieldErrors` → map to form field errors
- `DomainError` with `status == 5xx` → generic message + `traceId` visible for user to report
- Never `catch` silently in controllers

---

## 5. State Management — Riverpod

| Case | Pattern |
|------|---------|
| Async state (loading/data/error) | `AsyncNotifier` |
| Business state with actions | `StateNotifier` |
| Derived/computed state | `Provider` / `FutureProvider` |
| Local UI state (toggle, animation) | `StateProvider` (UI-only, never for business state) |

### StateNotifier pattern

```dart
// features/auth/presentation/controllers/auth_controller.dart
class AuthController extends StateNotifier<AuthState> {
  final LoginUseCase _loginUseCase;

  AuthController(this._loginUseCase) : super(const AuthState.initial());

  Future<void> login(String email, String password) async {
    state = const AuthState.loading();
    try {
      final user = await _loginUseCase.execute(LoginParams(email, password));
      state = AuthState.authenticated(user);
    } on AppError catch (e) {
      state = AuthState.error(e);
    }
  }
}
```

### Rules

- All business state lives in Riverpod. `setState` is only for ephemeral local UI (animations, focus nodes).
- Register all providers in `app/providers/app_providers.dart`.
- Controllers only consume use cases from the domain layer — never call datasources directly.
- State classes use `freezed` sealed classes: `initial`, `loading`, `loaded(data)`, `error(AppError)`.

---

## 6. Navigation — GoRouter

| Decision | Default |
|----------|---------|
| Router | `go_router` |
| Route definitions | All in `app/router/app_router.dart` — no ad-hoc `Navigator.push` in features |
| Auth guard | `redirect` callback observes `AuthService` state — respects `initializing` |
| Deep links | Registered in `AndroidManifest.xml`, `Info.plist`, and `app_router.dart` |
| Push notification taps | `FirebaseMessaging.onMessageOpenedApp` → `context.go(route)` |

### Rules

- Never use `Navigator.push` or `Navigator.pushNamed` in feature screens — always `context.go()` or `context.push()`
- The splash screen has no navigation logic — the guard handles everything
- Deep links must be tested before release

---

## 7. Offline and Connectivity

**The app is online-first. No local persistence in v1.**

| Decision | Default |
|----------|---------|
| Detection | `connectivity_plus` |
| Offline banner | Persistent banner when `isOffline: true` — disable action buttons that need network |
| Local cache | None in v1. No Hive, no sqflite, no Drift, no Isar. |
| Offline queue | Not supported in v1. |

### Optimistic updates

Not used by default. The only exception is low-consequence UI actions (e.g., favorite/unfavorite) where failure is extremely rare. If implemented:

1. Update local state immediately.
2. Call backend.
3. If backend fails: revert local state + show snackbar.

The revert path must be implemented before enabling optimistic update. If revert is not implemented, do not use optimistic updates.

---

## 8. Permissions — `permission_handler`

| Decision | Default |
|----------|---------|
| Package | `permission_handler` |
| Request timing | Just-in-time — never on app launch |
| Permanently denied | Show bottom sheet explaining why → "Open Settings" button → `openAppSettings()` |
| Permission logic | In controllers or use cases — never directly in widgets |

### Standard permission request pattern

```dart
// core/utils/permission_utils.dart
Future<bool> requestCameraPermission() async {
  final status = await Permission.camera.status;
  if (status.isGranted) return true;
  if (status.isPermanentlyDenied) {
    await openAppSettings();
    return false;
  }
  final result = await Permission.camera.request();
  return result.isGranted;
}
```

### Push notification permissions

- Request at first login, after explaining the value to the user
- Get push token from the push notifications SDK (e.g., `FirebaseMessaging.instance.getToken()` for FCM) and send to backend

---

## 9. Testing Strategy

| What to test | Tool | Type |
|---|---|---|
| Use cases + domain logic | `flutter_test` | Unit |
| Controllers (mock use cases with mocktail) | `flutter_test` + `mocktail` | Unit |
| Widget screens (loading, data, error states) | `flutter_test` widget tests | Integration |
| Critical end-to-end flows | `integration_test` + `patrol` | E2E |

### Fake repository pattern

```dart
// test/fakes/fake_user_repository.dart
// Implements domain interface — guarantees contract compliance
// Use seed() in setUp() — never constructor injection
class FakeUserRepository implements IUserRepository {
  final Map<String, User> _store = {};

  @override
  Future<User?> findById(String id) async => _store[id];

  @override
  Future<void> save(User user) async => _store[user.id] = user;

  // Test helpers
  void seed(User user) => _store[user.id] = user;
  void clear() => _store.clear();
}
```

**Layer → Test tool rule:**
- Use case tests → `FakeRepository` (implements domain interface, no HTTP, no mocks)
- Controller tests → `mocktail` (mocks use cases, NOT repositories)
- Never use `mocktail` to mock domain repository interfaces — FakeRepository guarantees contract compliance

### Rules

- Tests live in `test/` mirroring `lib/`: `test/features/auth/domain/usecases/login_usecase_test.dart`
- Every authenticated feature has at least one user isolation test: user A's data must not appear when user B is authenticated
- Never mock `ApiClient` or `Dio` directly — use a fake repository
- Test naming: `test('<action> when <condition> should <result>')`
- Run unit tests: `flutter test test/features/<name>/`
- Full suite: `flutter test`
- Static analysis: `flutter analyze`

---

## 10. Theme Architecture

### Token hierarchy

```
Core tokens → Semantic tokens → ThemeData extensions → Widget usage
```

### File structure

```
theme/
├── tokens/
│   ├── core.dart             # Full palette, spacing scale, radii, typography
│   ├── semantic.light.dart   # Semantic roles for light mode
│   └── semantic.dark.dart    # Semantic roles for dark mode
└── flutter/
    ├── color_scheme.dart     # ColorScheme from semantic tokens
    ├── text_theme.dart       # TextTheme from semantic tokens
    ├── extensions.dart       # AppColorsExtension, AppTextExtension
    └── app_theme.dart        # ThemeData light + dark
```

### Correct usage

```dart
// ✅ Correct — semantic extension
final colors = Theme.of(context).extension<AppColors>()!;
Container(color: colors.backgroundPrimary)

// ❌ Wrong — literal color
Container(color: Colors.white)
Container(color: Color(0xFFFFFFFF))
```

### Minimum required semantic tokens

| Category | Tokens |
|---|---|
| Background | `backgroundPrimary`, `backgroundSecondary`, `backgroundTertiary` |
| Surface | `surfaceDefault`, `surfaceRaised`, `surfaceOverlay` |
| Text | `textPrimary`, `textSecondary`, `textDisabled`, `textInverse` |
| Border | `borderDefault`, `borderStrong`, `borderFocus` |
| Brand | `brandPrimary`, `brandPrimaryHover`, `brandPrimaryActive` |
| Status | `statusSuccess`, `statusWarning`, `statusError`, `statusInfo` |

---

## 11. Environment Variables — dart-define

**Never include secrets in the app binary.** Everything in the APK/IPA is reversible.

### Always required

```bash
flutter run \
  --dart-define=API_URL=https://api.example.com \
  --dart-define=APP_ENV=development
```

| Variable | Sensitive | Description |
|---|---|---|
| `API_URL` | No | Backend base URL |
| `APP_ENV` | No | `production` / `staging` / `development` |

### Per-provider — add what your auth provider requires

**Firebase example:**
```bash
--dart-define=FIREBASE_PROJECT_ID=my-project
```

**Auth0 example:**
```bash
--dart-define=AUTH0_DOMAIN=my-tenant.auth0.com \
--dart-define=AUTH0_CLIENT_ID=abc123
```

Only add the variables your chosen auth provider needs. Do not add variables for providers you are not using.

### Access in code

```dart
// core/config/app_config.dart
class AppConfig {
  static const apiUrl = String.fromEnvironment('API_URL');
  static const appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'development');

  // Add provider-specific constants here when needed:
  // static const firebaseProjectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  // static const auth0Domain = String.fromEnvironment('AUTH0_DOMAIN');

  static bool get isProduction => appEnv == 'production';
  static bool get isDevelopment => appEnv == 'development';
}
```

Platform config files (`google-services.json`, `GoogleService-Info.plist`) are treated as platform config, not secrets — use separate files per environment and do not commit production files.

---

## 12. Performance

| Decision | Default |
|----------|---------|
| Network images | `cached_network_image` |
| Dynamic lists | `ListView.builder` or `SliverList` — never `ListView(children: [...])` |
| Skeleton loading | `shimmer` package on initial load — never blank screen + spinner |
| `const` constructors | Used wherever possible |
| Selective rebuilds | `Consumer` or `select` on providers to subscribe only to relevant state fields |

---

## 13. Project Initialization Checklist

### Structure
- [ ] Folder structure from `ARCHITECTURE_MOBILE.md` section 4 created exactly
- [ ] `analysis_options.yaml` with strict lints (`prefer_const_constructors`, `avoid_print`, etc.)
- [ ] `.gitignore` includes: build/, .dart_tool/, google-services.json (prod), GoogleService-Info.plist (prod)

### Dependencies (pubspec.yaml)
- [ ] `flutter_riverpod` + `riverpod_annotation` (state management)
- [ ] `dio` (HTTP client)
- [ ] `go_router` (navigation)
- [ ] `freezed` + `freezed_annotation` + `json_serializable` + `build_runner` (codegen)
- [ ] `connectivity_plus` (offline detection)
- [ ] `permission_handler` (permissions)
- [ ] `cached_network_image` (network images)
- [ ] `shimmer` (skeleton screens)
- [ ] Auth provider SDK: add packages required by the chosen provider (e.g., `firebase_core` + `firebase_auth`, or `auth0_flutter`, or custom JWT package)
- [ ] Push notifications: `firebase_messaging` if using FCM, or equivalent for your provider
- [ ] Dev/test: `flutter_test`, `mocktail`, `integration_test`, `patrol`

### Auth + Splash
- [ ] `AppAuthState` enum with three values (`initializing`, `authenticated`, `unauthenticated`) in `core/auth/auth_state.dart`
- [ ] `AuthService` abstract class in `core/auth/auth_service.dart` with `getToken()`, `refreshToken()`, `logout()`, `stateChanges`
- [ ] Concrete `AuthServiceImpl` in `core/auth/` implementing `AuthService` using the project's chosen auth provider
- [ ] `SplashScreen` in `features/splash/` — logo only, no business logic, no HTTP
- [ ] GoRouter guard redirects to `/splash` when `initializing`, never to `/auth/login` during init
- [ ] No flash of login screen when user is already authenticated

### ApiClient
- [ ] Dio instance in `core/network/api_client.dart`
- [ ] `AuthInterceptor` adds `Authorization: Bearer` via `AuthService.getToken()` — no direct import of auth SDK
- [ ] `TraceInterceptor` adds `X-Trace-ID: <uuid>` per request
- [ ] 401 retry: `AuthService.refreshToken()` → retry once → on second 401: `AuthService.logout()`
- [ ] `DioException` caught in repositories, converted to `AppError`, never propagated raw

### Errors
- [ ] `sealed class AppError` in `core/errors/app_error.dart` with `DomainError`, `NetworkError`, `UnknownError`
- [ ] `ConnectivityService` in `core/network/` detects offline state
- [ ] Offline banner component in `ui/components/`

### Theme
- [ ] Core tokens defined for the project
- [ ] Semantic tokens for light and dark mode
- [ ] `AppColorsExtension` registered in `ThemeData`
- [ ] No widget uses `Colors.X` or literal color values

### Testing
- [ ] At least one use case test using `FakeRepository` (not mocktail)
- [ ] At least one controller test using `mocktail` for use cases
- [ ] At least one widget test for the login screen
- [ ] `integration_test` configured

### Validation
- [ ] `flutter build ios` passes with no errors
- [ ] `flutter build appbundle` passes with no errors
- [ ] `flutter analyze` passes with no warnings
- [ ] `flutter test` passes
- [ ] Auth flow works end-to-end
- [ ] Dark mode renders correctly
