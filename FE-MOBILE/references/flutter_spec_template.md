# Flutter Feature Specification Template

This document defines the canonical format for **Flutter mobile feature** specifications. Use this template when the primary deliverable is a Flutter screen, flow, or mobile capability.

For backend API features, use `spec_template.md` instead.
For full-stack features (new backend API + Flutter UI), use both templates and link them.

---

## Spec Lifecycle

```
DRAFT → REVIEWED → APPROVED → IMPLEMENTING → DONE
```

## Required Sections

Every Flutter spec MUST contain all 10 sections. A spec missing any section cannot be REVIEWED.

---

### 1. Problem Statement
- What specific user problem does this solve?
- Who experiences this problem? (user persona, role: admin / member)
- What is the impact of NOT solving it?
- **Out of Scope**: what this feature does NOT cover (navigation to unrelated screens, backend logic already specced separately, etc.)

### 2. Bounded Context
- Which feature domain does this belong to? (e.g., Agent Management, Billing, Onboarding)
- What screens / UI state does this feature OWN?
- What does it DEPEND ON from the backend? (which API spec)
- What does it DEPEND ON from other Flutter features? (shared providers, shared widgets, navigation state)
- What state does it PUBLISH for other features to react to? (e.g., via a shared provider or callback)

### 3. Screens & Entry Points
Every UI surface this feature introduces or modifies. For each:
- Screen name (as it would appear in GoRouter route name)
- How it is reached (bottom nav tab, push from list, deep link, push notification tap, modal)
- Auth required? Role restrictions?
- What data must be loaded before the screen can render? (async pre-fetch vs. skeleton-first)

| Screen Name | Route Path | Entry Trigger | Auth Required | Role | Pre-fetch Data |
|-------------|------------|---------------|---------------|------|----------------|

> Rule: Every screen that displays user-specific data must verify the user is authenticated before rendering. Use the auth guard in GoRouter. The guard must respect the `initializing` state.

### 4. Backend API Dependencies
Every backend endpoint this feature calls, plus local device dependencies. For each API call:
- HTTP method + path
- Purpose
- Auth: Bearer JWT required?
- Which controller/use case owns this call?

| Endpoint | Method | Purpose | Auth | Owned By |
|----------|--------|---------|------|----------|

**Device Service Dependencies**

| Service | Purpose | Permission Required | When Requested |
|---------|---------|---------------------|----------------|

### 5. Controller & State Contracts
For each Riverpod controller introduced by this feature:

**[ControllerName] (StateNotifier\<[Feature]State\>)**
```dart
// State (freezed sealed class)
@freezed
class [Feature]State with _$[Feature]State {
  const factory [Feature]State.initial() = _Initial;
  const factory [Feature]State.loading() = _Loading;
  const factory [Feature]State.loaded([Feature]Data data) = _Loaded;
  const factory [Feature]State.error(AppError error) = _Error;
}
```

**Controller methods** (one per user action):
```dart
class [Feature]Controller extends StateNotifier<[Feature]State> {
  Future<void> load(String userId);
  Future<void> submit([Feature]Params params);
}
```

**API Models** (Dio request/response — separate from domain entities)
```dart
@freezed
class [Feature]Response with _$[Feature]Response {
  factory [Feature]Response.fromJson(Map<String, dynamic> json) = _[Feature]Response;
  // fields matching the backend response schema
}
```

**Domain Entity** (immutable, pure Dart — what the controller exposes to the UI)
```dart
@freezed
class [Feature]Data with _$[Feature]Data {
  // fields the UI needs — may differ from API response
}
```

### 6. Auth & User Context
- **Token injection**: Auth interceptor in Dio adds `Authorization: Bearer <token>` via `AuthService.getToken()`. Never pass tokens manually from feature code.
- **Token refresh**: On 401 response, auth interceptor calls `AuthService.refreshToken()` and retries once. On second 401, calls `AuthService.logout()`.
- **Auth state**: GoRouter guard reads `AppAuthState` from `authServiceProvider`. Redirects to `/splash` during `initializing`, to `/auth/login` when `unauthenticated`.
- **User data scoping**: All API calls are scoped to the authenticated user via the Bearer token. The backend enforces RLS.
- **No local token storage**: `AuthService` implementation manages tokens internally. Feature code never stores, reads, or decodes tokens.

### 7. Acceptance Criteria
GIVEN/WHEN/THEN format. Each criterion must be:
- **Specific**: no vague terms
- **Measurable**: has a pass/fail condition
- **Testable**: can be verified with a use case test, controller test, widget test, or integration test
- **Independent**: does not depend on other criteria's order

- [ ] **AC-1**: GIVEN ... WHEN ... THEN ...

### 8. Error Scenarios

#### 8.1 Network & Auth Errors (mandatory — applies to all authenticated Flutter features)

| Error | Trigger | User-Visible Behavior | Retryable? |
|-------|---------|----------------------|------------|
| No network connectivity | `connectivity_plus` detects offline | Show "No internet connection" banner; disable action buttons | Yes — retry when connection restored |
| Request timeout | Dio receive timeout | Controller emits `NetworkError` state | Yes — retry button |
| 401 — token expired | Interceptor refresh fails | Silent refresh attempted; if fails → AuthService emits logout → GoRouter redirects to login | No — requires re-auth |
| 403 — insufficient permission | Backend returns 403 | Controller emits `DomainError(status: 403)`, screen shows "You don't have access" | No |
| 422 — validation error | Backend returns 422 with fieldErrors | Map `DomainError.fieldErrors` to form fields via controller state | No — fix input |
| 500 — server error | API returns 5xx | Controller emits `NetworkError`, screen shows generic message with `traceId` | Yes — retry button |

#### 8.2 Feature-Specific Errors

| Error Condition | User-Visible Behavior | Controller State |
|-----------------|----------------------|-----------------|
| (from feature rules/limits) | | |

### 9. Navigation & Side Effects

**Navigation Flow**
```
[EntryPoint] → [Screen A] → [Screen B (success)]
                           → [Screen C (error/empty)]
[Back stack]: [describe expected back behavior]
[Deep link]: [URL pattern if applicable]
[Push notification tap]: [which screen it opens, with which data]
```

**State Invalidation**
| Action | Provider Invalidated | Reason |
|--------|---------------------|--------|
| (e.g., item created successfully) | (list provider) | stale data |

**Side Effects**
| Action | Side Effect | Async? |
|--------|------------|--------|
| (e.g., file upload) | (backend processes via Cloud Tasks) | Yes |

### 10. Non-Functional Requirements

- **Offline behavior**: `[describe what works offline / what requires connectivity — default is online-first, no local persistence in v1]`
- **Optimistic updates**: `[yes/no — if yes, describe the revert path]`
- **Frame rate**: No jank during scroll or transition. Target 60fps / 120fps on capable devices.
- **Initial load**: First meaningful render within 300ms of navigation. Use skeleton screens, not blank/spinner.
- **Permissions**: `[list device permissions required and when the app requests them — always just-in-time, never on app launch]`
- **Accessibility**: All interactive elements have semantic labels. Supports system font size scaling.
- **App size impact**: No large asset bundles added without review. Images use `cached_network_image`.

---

## Quality Checklist

A Flutter spec is ready for review when:

- [ ] No "TBD", "TODO", "BUSINESS DECISION REQUIRED" remains
- [ ] All screens listed with route paths and entry triggers
- [ ] Controller states defined (sealed classes with `AppError`)
- [ ] Every API endpoint the feature calls is listed in §4
- [ ] No local storage dependencies (online-first v1) — or explicitly specified with justification
- [ ] Navigation flow described (§9)
- [ ] Offline behavior explicitly defined (not "TBD")
- [ ] Device permissions listed with when-requested timing
- [ ] Auth error scenarios covered (§8.1)
- [ ] Every acceptance criterion follows GIVEN/WHEN/THEN
- [ ] No business logic described in presentation layer terms
- [ ] Technical defaults applied (see `flutter_defaults.md`)

---

## Annotation Conventions

- `(default)` — Flutter technical default from `flutter_defaults.md`
- `(inferred — verify)` — derived from context; needs author confirmation
- `BUSINESS DECISION REQUIRED` — only the product owner can fill this in
