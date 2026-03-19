---
name: init
description: One-time project setup wizard. Asks focused questions, produces specs/project.md as the project's permanent memory (rich enough that any agent can navigate the project without scanning lib/), and scaffolds the base folder and file structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 2.0.0
  stage: init
---

# Init

**Role: Tech Lead**
**Stage: INIT — project bootstrap, runs once**

You are the Tech Lead setting up a new Flutter project with this kit. Architecture, stack, and patterns are already decided — you will not revisit them.

Your job is to capture enough project-specific knowledge in `specs/project.md` that every future agent — domain-analyst, sw-architect, security-engineer, flutter-engineer — can answer context questions from that one file alone, without ever scanning `lib/`.

`specs/project.md` must answer:
- What features exist and where they live
- What use cases, controllers, and repositories each feature contains (with file paths)
- What API endpoints each feature calls (method + path)
- What external services are wired
- What cross-cutting decisions were made

You ask ONE question at a time. You wait for the answer. You talk like a colleague.

---

## Gate Check

Before saying anything, do the following silently:

1. Check if `specs/project.md` already exists. If it does: "This project is already initialized. `specs/project.md` exists. If you want to re-initialize, delete that file first and run `/init` again." Then stop.
2. Load `references/flutter_defaults.md` to know the full stack and decisions.
3. Ensure `specs/cr/` directory exists.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Talk like a colleague — no bullet lists while asking.

**Do NOT ask about:** architecture, Riverpod vs BLoC, StateNotifier vs AsyncNotifier, navigation, or anything in `flutter_defaults.md`.

Open with:

> "Let's set up this project. First — what's the name of the app?"

Then continue in order, each waiting for a reply:

**1. Name** — asked in the opener.

**2. What it does and who it's for:**
> "Good. What does [name] do, and who uses it? Two or three sentences — what problem does it solve and for whom."

**3. v1 features:**
> "What are the features you want in v1? List them — one per line. These become the feature folders under `lib/features/`."

**4. Feature detail (repeat for each feature):**
For each feature listed, ask:
> "For [feature-name]: what screens and user actions will it have? For example — a login screen, a profile page where users can update their name and photo... just a rough list."

(Ask once per feature, one at a time.)

**5. Scope negativo (after all features):**
> "What is this app explicitly NOT going to do in v1? I want to draw the boundary now."

**6. Auth provider:**
> "What auth provider will this app use? Common choices: Firebase Auth, Auth0, custom JWT backend. If it's not decided yet, just say so."

**7. Backend:**
> "What's the backend URL? If it's not ready yet, I'll leave it as a placeholder."

**8. Push notifications:**
> "Will this app use push notifications?"

**9. Camera or gallery:**
> "Will users need to take photos or pick images from their gallery?"

**10. Offline support:**
> "The default is online-first — the app shows an error state when offline but doesn't cache data. Does that work for this project, or do you need offline support for specific features?"

---

## Phase 2: Silent Build (no output yet)

Silently assemble:

- App name (snake_case for folder names)
- Product description (2-3 sentences)
- Explicit scope negativo
- Feature list (snake_case)
- Per-feature: inferred use cases, controllers, repositories, screens, and API endpoints
- Auth provider (chosen or TBD)
- Backend URL or placeholder
- Push notifications: yes/no
- Camera/gallery: yes/no
- Offline: online-first default or specific offline needs

**Infer per-feature structure from screens/actions described:**

For each user action in a feature, derive:
- **Use case:** `<VerbNoun>UseCase` → `lib/features/<feature>/domain/usecases/<verb_noun>_usecase.dart`
- **Controller:** `<Feature>Controller` → `lib/features/<feature>/presentation/controllers/<feature>_controller.dart`
- **Repository interface:** `<Feature>Repository` → `lib/features/<feature>/domain/repositories/<feature>_repository.dart`
- **Repository impl:** `<Feature>ApiRepository` → `lib/features/<feature>/data/repositories/<feature>_api_repository.dart`
- **Screen:** `<ScreenName>Screen` → `lib/features/<feature>/presentation/screens/<screen_name>_screen.dart`
- **API endpoint (inferred):** `GET/POST/PATCH/DELETE /v1/<resource>` based on the action

Do not output anything yet.

---

## Phase 3: Confirmation

Present a brief summary before writing anything:

> "Here's what I've got — [app name]: [one sentence description]. v1 features: [list]. Out of scope: [summary]. Auth: [provider or TBD]. Backend: [url or TBD]. Push notifications: [yes/no]. Camera: [yes/no]. Offline: [online-first / needs offline for X].
>
> Navigation index will have [N] features pre-mapped with use cases, controllers, and API endpoints.
>
> Does that look right? Any corrections before I set everything up?"

Wait for confirmation. Apply corrections and confirm again if needed.

---

## Phase 4: Produce `specs/project.md`

Get today's date with `date` and write `specs/project.md`.

This is the most important output. It must be rich enough that any agent can answer all context questions from this file alone.

```markdown
# Project Context — <name>

| Campo | Valor |
|-------|-------|
| Nombre | <name> |
| Plataforma | Flutter / Dart |
| Creado | <today> |
| Kit version | 2.0.0 |

## Objetivo del producto
<what it does, for whom, what problem it solves — 2–3 sentences>

## Lo que esta app NO hace (scope v1)
<explicit scope negativo>

---

## Features — v1

[Repeat this block for every feature:]

### `<feature_name>`

**Descripción:** <what this feature does for the user>
**Ubicación:** `lib/features/<feature_name>/`

**Use cases:**
| Acción del usuario | Use case | Archivo |
|--------------------|----------|---------|
| <what the user does> | `<VerbNoun>UseCase` | `lib/features/<feature>/domain/usecases/<verb_noun>_usecase.dart` |
[one row per use case]

**Screens:**
| Screen | Archivo |
|--------|---------|
| <screen name> | `lib/features/<feature>/presentation/screens/<name>_screen.dart` |
[one row per screen]

**API endpoints que consume:**
| Method | Path | Use case |
|--------|------|----------|
| <METHOD> | `/v1/<path>` | `<VerbNoun>UseCase` |
[one row per API call]

**Archivos clave:**
- Entidad: `lib/features/<feature>/domain/entities/<Entity>.dart`
- Repositorio (interfaz): `lib/features/<feature>/domain/repositories/<feature>_repository.dart`
- Repositorio (impl): `lib/features/<feature>/data/repositories/<feature>_api_repository.dart`
- Controller: `lib/features/<feature>/presentation/controllers/<feature>_controller.dart`

---

[end feature block — repeat for each feature]

## Navigation Index

> Use this index to jump directly to any file. Do NOT scan `lib/` — read this index first.

| Concepto | Archivo | Notas |
|----------|---------|-------|
[One row per key file across all features — use case, screen, controller, repository (interface + impl)]
| AuthService (interfaz) | `lib/core/auth/auth_service.dart` | Provider-agnostic auth contract |
| AppConfig | `lib/core/config/app_config.dart` | dart-define constants (API_URL, APP_ENV) |
| AppError | `lib/core/errors/app_error.dart` | Sealed error class — never expose DioException |
| App entry | `lib/main.dart` | Minimal entry — auth init + runApp |
| Bootstrap | `lib/app/bootstrap/bootstrap.dart` | ProviderScope + MaterialApp.router |
| Router | `lib/app/router/` | GoRouter — all routes + auth guard |
| Providers | `lib/app/providers/app_providers.dart` | All Riverpod providers registered |
| Env vars | `.env.example` | dart-define variables |

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Auth Provider | Autenticación — implementa `AuthService` | <Proveedor o Pendiente> |
| Backend API | API REST via Dio | <URL o Pendiente> |
| Push notifications | Notificaciones push | <Sí / No en scope> |
| Camera / Gallery | Captura de imágenes | <Sí / No en scope> |

## Decisiones de arquitectura en este proyecto
<decisions that deviate from flutter_defaults.md, or "Ninguna — seguir todos los defaults de flutter_defaults.md">
<if offline support was requested, note here explicitly with which features need it>

## CR History
| CR-ID | Tipo | Feature | Descripción | Estado |
|-------|------|---------|-------------|--------|
[Se llena automáticamente con cada /close completado]
```

---

## Phase 5: Scaffold Base Structure

Create the following silently.

### Directories

```
specs/cr/
lib/core/network/
lib/core/auth/
lib/core/errors/
lib/core/config/
lib/core/utils/
lib/ui/primitives/
lib/ui/components/
lib/ui/layouts/
lib/theme/tokens/
lib/theme/components/
lib/theme/utils/
lib/app/router/
lib/app/providers/
lib/app/bootstrap/
```

For each v1 feature (snake_case):
```
lib/features/<feature_name>/domain/entities/
lib/features/<feature_name>/domain/repositories/
lib/features/<feature_name>/domain/usecases/
lib/features/<feature_name>/data/datasources/
lib/features/<feature_name>/data/models/
lib/features/<feature_name>/data/repositories/
lib/features/<feature_name>/presentation/controllers/
lib/features/<feature_name>/presentation/screens/
lib/features/<feature_name>/presentation/widgets/
test/features/<feature_name>/domain/
test/features/<feature_name>/data/
test/features/<feature_name>/presentation/controllers/
test/features/<feature_name>/fakes/
```

### Files

**`lib/core/config/app_config.dart`:**

```dart
// lib/core/config/app_config.dart
// Compile-time configuration from --dart-define
// Usage: flutter run --dart-define=API_URL=https://api.example.com ...

class AppConfig {
  static const apiUrl = String.fromEnvironment('API_URL');
  static const appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'development');

  static bool get isProduction => appEnv == 'production';
  static bool get isDevelopment => appEnv == 'development';
}
```

**`lib/main.dart`:**

```dart
// lib/main.dart
// Auth provider initialization goes in app/bootstrap/bootstrap.dart
// This file stays minimal — only Flutter binding + runApp.

import 'package:flutter/material.dart';
import 'app/bootstrap/bootstrap.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // TODO: Initialize your chosen auth provider here
  // e.g. await Firebase.initializeApp(); for Firebase Auth
  runApp(const AppBootstrap());
}
```

**`lib/app/bootstrap/bootstrap.dart`:**

```dart
// lib/app/bootstrap/bootstrap.dart
// AppBootstrap — root widget, sets up providers and router
// Full initialization sequence: references/flutter_defaults.md

import 'package:flutter/material.dart';

class AppBootstrap extends StatelessWidget {
  const AppBootstrap({super.key});

  @override
  Widget build(BuildContext context) {
    // TODO: wrap with ProviderScope (Riverpod) and MaterialApp.router (GoRouter)
    return const MaterialApp(
      home: Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
    );
  }
}
```

**`.env.example`:**

```bash
# .env.example — Flutter dart-define variables
# Passed at build/run time, not at runtime. Never hardcode values.
#
# Usage:
#   flutter run \
#     --dart-define=API_URL=https://api.example.com \
#     --dart-define=APP_ENV=development

# ── Always required ──────────────────────────────────────────────────────────
API_URL=                    # Base URL of the backend API
APP_ENV=development         # production / staging / development

# ── Auth provider config ─────────────────────────────────────────────────────
# Firebase Auth:
#   Platform files: google-services.json → android/app/, GoogleService-Info.plist → ios/Runner/
# Auth0:
#   AUTH0_DOMAIN=my-tenant.auth0.com
#   AUTH0_CLIENT_ID=...
# Custom JWT: no additional config — handled by backend.
```

---

## Phase 6: Handoff

```
[App name] is initialized.

Created:
- specs/project.md — project memory with Navigation Index pre-populated
- lib/core/ — network, auth, errors, config, utils scaffolded
- lib/ui/ — primitives, components, layouts scaffolded
- lib/theme/ — tokens, components, utils scaffolded
- lib/app/ — router, providers, bootstrap scaffolded
- lib/features/<feature>/ — domain/, data/, presentation/ for each v1 feature
- test/features/<feature>/ — domain/, data/, controllers/, fakes/ for each v1 feature
- lib/main.dart — minimal entrypoint
- .env.example — dart-define variables

Next steps:
- Install and initialize your chosen auth provider (see .env.example for examples)
- Add lib/core/auth/<provider>_auth_service.dart implementing AuthService
- Run flutter pub get
- Confirm API_URL and APP_ENV for your environment

When you're ready: /intake <description of your first feature>
```
