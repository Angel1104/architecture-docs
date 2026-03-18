# Flutter Feature Specification Template

This document defines the canonical format for **Flutter mobile feature** specifications at comocom. Use this template when the primary deliverable is a Flutter screen, flow, or mobile capability.

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
- What does it DEPEND ON from other Flutter features? (shared BLoCs, shared widgets, navigation state)
- What events does it PUBLISH for other features to react to? (e.g., `AgentHiredEvent` → refresh list screen)

### 3. Screens & Entry Points
Every UI surface this feature introduces or modifies. For each:
- Screen name (as it would appear in GoRouter route name)
- How it is reached (bottom nav tab, push from list, deep link, push notification tap, modal)
- Auth required? Role restrictions?
- What data must be loaded before the screen can render? (async pre-fetch vs. skeleton-first)

| Screen Name | Route Path | Entry Trigger | Auth Required | Role | Pre-fetch Data |
|-------------|------------|---------------|---------------|------|----------------|

> Rule: Every screen that displays tenant-specific data must verify the user is authenticated before rendering. Use the auth guard in GoRouter.

### 4. Backend API Dependencies
Every backend endpoint this feature calls, plus local device dependencies. For each API call:
- HTTP method + path
- Purpose
- Auth: Bearer JWT required?
- Which BLoC/use case owns this call?

| Endpoint | Method | Purpose | Auth | Owned By |
|----------|--------|---------|------|----------|

**Local Storage Dependencies**

| Storage Type | Key / Collection | Data Stored | Scoped To User? |
|-------------|-----------------|-------------|-----------------|
| FlutterSecureStorage | (key name) | (what) | Yes — cleared on logout |
| Hive | (box name) | (what) | Yes — keyed by user_id |
| SharedPreferences | (key name) | (what — non-sensitive only) | (yes/no) |

**Device Service Dependencies**

| Service | Purpose | Permission Required | When Requested |
|---------|---------|---------------------|----------------|

### 5. BLoC & State Contracts
For each BLoC introduced by this feature:

**[BLoCName]**
```dart
// Events
abstract class [Feature]Event {}
class Load[Feature] extends [Feature]Event { /* fields */ }
class Submit[Feature] extends [Feature]Event { /* fields */ }

// States (freezed sealed class)
@freezed
class [Feature]State with _$[Feature]State {
  const factory [Feature]State.initial() = _Initial;
  const factory [Feature]State.loading() = _Loading;
  const factory [Feature]State.loaded([Feature]Data data) = _Loaded;
  const factory [Feature]State.error(String message) = _Error;
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

**Domain Entity** (immutable, pure Dart — what the BLoC exposes to the UI)
```dart
@freezed
class [Feature]Data with _$[Feature]Data {
  // fields the UI needs — may differ from API response
}
```

### 6. Auth & Tenant Context
- **Token storage**: Access token and refresh token stored in `FlutterSecureStorage` only (never SharedPreferences)
- **Token injection**: Auth interceptor in Dio adds `Authorization: Bearer <token>` to every request. `tenant_uid` is a JWT claim — never passed manually.
- **Token refresh**: On 401 response, auth interceptor attempts silent refresh. On refresh failure, navigates to login screen and clears all stored tokens.
- **Role enforcement**: `tenant_role` claim from JWT controls which screens are accessible and which UI elements are visible. Role check in GoRouter redirect guard.
- **Local data scoping**: Any locally cached data (Hive, SharedPreferences) must be keyed by `user_id` or cleared completely on logout.
- **Logout**: Clears all tokens from FlutterSecureStorage, clears all Hive boxes, navigates to login root.

### 7. Acceptance Criteria
GIVEN/WHEN/THEN format. Each criterion must be:
- **Specific**: no vague terms
- **Measurable**: has a pass/fail condition
- **Testable**: can be verified with a BLoC test, widget test, or integration test
- **Independent**: does not depend on other criteria's order

- [ ] **AC-1**: GIVEN ... WHEN ... THEN ...

### 8. Error Scenarios

#### 8.1 Network & Auth Errors (mandatory — applies to all authenticated Flutter features)

| Error | Trigger | User-Visible Behavior | Retryable? |
|-------|---------|----------------------|------------|
| No network connectivity | `DioException` — no connection | Show "No internet connection" banner; cache displayed if available | Yes — retry button |
| Request timeout | `DioException` — receive timeout | Show "Request timed out" message | Yes — retry button |
| 401 — expired token | Auth interceptor refresh fails | Silent refresh attempted; if fails → navigate to login | No — requires re-auth |
| 401 — invalid token | Token tampered or from wrong issuer | Navigate to login; clear all tokens | No |
| 403 — insufficient role | Role guard rejection | Show "You don't have access to this" screen | No |
| 500 — server error | API returns 5xx | Show generic "Something went wrong" message; log error | Yes — retry button |

#### 8.2 Feature-Specific Errors

| Error Condition | User-Visible Behavior | Screen / BLoC State |
|-----------------|----------------------|---------------------|
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

**Cache Invalidation**
| Action | Cache Invalidated | Reason |
|--------|------------------|--------|
| (e.g., agent hired successfully) | agent list cache | stale data |

**Cross-feature Events**
| Event Published | Consumed By | Purpose |
|----------------|------------|---------|
| (e.g., AgentStatusChanged) | AgentListBloc | Refresh list without full reload |

### 10. Non-Functional Requirements

- **Offline behavior**: `[describe what works offline / what requires connectivity]`
- **Frame rate**: No jank during scroll or transition. Target 60fps / 120fps on capable devices.
- **Initial load**: First meaningful render within 300ms of navigation. Use skeleton screens, not blank/spinner.
- **Permissions**: `[list device permissions required and when the app requests them — always request at point-of-need, not on app launch]`
- **Accessibility**: All interactive elements have semantic labels. Supports system font size scaling.
- **App size impact**: No large asset bundles added without review. Images use cached_network_image.
- **Error logging**: All unexpected errors reported to Firebase Crashlytics with non-PII context.

---

## Quality Checklist

A Flutter spec is ready for review when:

- [ ] No "TBD", "TODO", "BUSINESS DECISION REQUIRED" remains
- [ ] All screens listed with route paths and entry triggers
- [ ] BLoC events and states defined (sealed classes)
- [ ] Every API endpoint the feature calls is listed in §4
- [ ] Local storage keys listed and scoped-to-user confirmed
- [ ] Navigation flow diagrammed (§9)
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
