# Flutter Technical Defaults — comocom

This document codifies every Flutter-specific technical decision that applies to all comocom mobile features. The `flutter-engineer` and `sw-architect` agents read this file before writing or reviewing any Flutter spec or code. Defaults here are settled decisions — not open questions.

---

## 1. Architecture

| Decision | Default |
|----------|---------|
| Pattern | Clean Architecture: domain → application → infrastructure → presentation |
| State management | BLoC (`flutter_bloc`) — Cubit for simple state, full BLoC for event-driven flows |
| DI | `get_it` service locator, registered in `core/di/injection.dart` |
| Immutable data | All entities, models, and BLoC states use `freezed` |
| Error handling | `dartz` `Either<Failure, T>` across domain and application layers |
| Navigation | `go_router` with auth redirect guard and named routes |

---

## 2. Auth & Token Handling

| Decision | Default |
|----------|---------|
| Token storage | `flutter_secure_storage` only — never SharedPreferences, never in-memory across sessions |
| Token injection | Dio auth interceptor adds `Authorization: Bearer <token>` to every request |
| Tenant context | `tenant_uid` and `tenant_role` are JWT claims — never passed as manual parameters or stored separately |
| Token refresh | Silent refresh on 401. On refresh failure: clear all tokens, navigate to login root |
| Logout | Clear all `FlutterSecureStorage` keys + all Hive boxes + navigate to login |
| Role enforcement | GoRouter redirect guard reads `tenant_role` from decoded JWT. BLoC receives role from auth state. |
| JWT decoding | Decode locally for claims only — never trust locally decoded claims for security decisions; always let the backend enforce |

---

## 3. API Client (Dio)

| Decision | Default |
|----------|---------|
| HTTP client | Dio with typed interceptors |
| Auth interceptor | Added globally in `core/network/api_client.dart` |
| Timeout | Connect: 10s, Receive: 30s |
| Retry | 3 retries with exponential backoff for network errors only. Never retry 4xx. |
| Base URL | From environment config (`flutter_dotenv` or compile-time constants) |
| Error mapping | `DioException` → typed `Failure` in repository `catch` block. Never let `DioException` cross the infrastructure boundary. |
| JSON serialization | `freezed` + `json_serializable`. No manual `fromJson` implementations. |

---

## 4. Local Storage

| Decision | Default |
|----------|---------|
| Sensitive data | `flutter_secure_storage` — tokens, user credentials |
| Structured cache | `hive` — feature-level data caches, keyed by `userId` prefix |
| Simple preferences | `shared_preferences` — non-sensitive UI prefs (theme, onboarding seen flag). Never store tokens here. |
| User-scoped keys | All Hive box names and SharedPreferences keys that store user data must include `_${userId}` suffix |
| Cache invalidation | On logout: `Hive.deleteFromDisk()` for user-data boxes; `FlutterSecureStorage.deleteAll()` |
| Offline fallback | Features that display lists should cache last successful response in Hive for offline display |

---

## 5. State Management (BLoC)

| Decision | Default |
|----------|---------|
| State shape | Sealed class with `freezed`: `initial`, `loading`, `loaded(data)`, `error(message)` |
| Event shape | Abstract class with concrete subclasses, one per user action or lifecycle event |
| BLoC scope | One BLoC per feature screen / flow. Do not share BLoCs across unrelated features. |
| BLoC registration | Registered in `get_it`. Provided to widget tree via `BlocProvider`. |
| Loading indicator | Every BLoC has a `loading` state. UI always shows a skeleton or progress indicator during loading. |
| Error display | `error(message)` state maps to a user-visible error banner or dialog. Never silently swallow errors. |
| Empty state | `loaded(data)` with empty collection maps to an explicit empty state widget. Never show a blank screen. |

---

## 6. Navigation

| Decision | Default |
|----------|---------|
| Router | `go_router` |
| Auth guard | `GoRouter.redirect` checks token validity before allowing navigation to authenticated routes |
| Role guard | Routes requiring admin role check `tenant_role` claim; redirect to "Access Denied" screen if insufficient |
| Deep links | Defined in `AndroidManifest.xml` and `Info.plist`. Route handler in `go_router` |
| Back stack | Never pop to a screen that requires fresh data without triggering a reload event |
| Push notification taps | FCM notification tap opens specific route with payload data; handled in `FirebaseMessaging.onMessageOpenedApp` |

---

## 7. Error Handling

| Decision | Default |
|----------|---------|
| No connectivity | `ConnectivityBloc` monitors network state. Show persistent banner when offline. |
| 401 response | Auth interceptor handles silently (refresh attempt). If refresh fails, navigate to login. |
| 403 response | BLoC emits `error("You don't have permission")`. Show in-screen error, not a dialog. |
| 404 response | BLoC emits `error("Not found")`. Show empty state widget. |
| 5xx response | BLoC emits `error("Something went wrong")`. Show retry button. Log to Crashlytics. |
| Exception logging | All unexpected exceptions caught at BLoC boundary, logged to Firebase Crashlytics with non-PII context |
| User-facing messages | Predefined message strings from a constants file. Never expose raw API error messages. |

---

## 8. Testing

| Decision | Default |
|----------|---------|
| Unit tests | Use case and repository tests with `mockito` mocks |
| BLoC tests | `bloc_test` package — verify event → state transitions |
| Widget tests | `flutter_test` — verify screen renders correct state, buttons trigger correct events |
| Integration tests | `integration_test` package for critical user flows |
| Tenant isolation | Every repository test verifies that calling with a different `userId` returns no results |
| Test naming | `test_<action>_<condition>_<expectedResult>` |

---

## 9. Permissions

| Decision | Default |
|----------|---------|
| Request timing | Always request at point-of-need — never on app launch |
| Package | `permission_handler` |
| Denied handling | Show rationale dialog first. On permanent denial, show settings redirect. |
| Camera / Storage | Only request when user initiates an action that requires it |

---

## 10. Performance

| Decision | Default |
|----------|---------|
| Images | `cached_network_image` for all network images |
| Lists | `ListView.builder` / `SliverList` — never `ListView(children: [...])` for dynamic data |
| Skeleton screens | Show skeleton (`shimmer`) on initial load. Never blank screen + spinner. |
| `const` constructors | Used wherever possible on stateless widgets |
| Avoid rebuild triggers | `BlocSelector` to subscribe only to relevant state fields |

---

## 11. Firebase

| Decision | Default |
|----------|---------|
| Auth | Firebase Authentication — JWT issued by Firebase, custom claims set server-side |
| Push notifications | Firebase Cloud Messaging (FCM) — initialized in `main.dart` |
| Crashlytics | All unexpected errors reported automatically |
| Analytics | Firebase Analytics for screen views — use `FirebaseAnalyticsObserver` with GoRouter |
