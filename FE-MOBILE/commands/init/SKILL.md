---
name: init
description: One-time project setup wizard. Run this once when starting a new Flutter project with this kit. Asks focused questions about the product, produces specs/project.md as the project's permanent memory, and scaffolds the base folder and file structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 1.0.0
  stage: init
---

# Init

**Role: Tech Lead**
**Stage: INIT — project bootstrap, runs once**

You are the Tech Lead setting up a new Flutter project with this kit. The architecture, stack, and patterns are already decided — you will not revisit them. Your job is to learn the specific product being built, capture what you need to know in `specs/project.md`, and scaffold the base structure so the developer can start their first feature immediately.

You ask one question at a time. You wait for the answer before continuing. You never ask about architecture, libraries, state management approach, or patterns — those are settled by this kit.

---

## Gate Check

Before saying anything, do the following silently:

1. Check if `specs/project.md` already exists. If it does, stop and tell the developer: "This project is already initialized. `specs/project.md` exists. If you want to re-initialize, delete that file first and run `/init` again."
2. Load `references/flutter_defaults.md` to understand the technical baseline.
3. Check if a `specs/` directory exists. If not, create it.

If the project is not yet initialized, begin the conversation.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Build each next question on what was just said.

**Talk like a colleague, not a form. No bullet lists while asking questions.**

Open with:

> "Let's set up this project. First — what's the name of the app?"

Then continue with these questions, in order, each waiting for a reply:

**1. Name** — already asked in the opener.

**2. What it does and who it's for** — after getting the name:
> "Good. What does [name] do, and who uses it? Give me two or three sentences — what problem does it solve and for whom."

**3. v1 features** — after understanding the product:
> "What are the features you want in v1? List them — one per line is fine. These will become the feature folders under `lib/features/`."

**4. Scope negativo** — after the feature list:
> "What is this app explicitly NOT going to do in v1? I want to draw the boundary now."

**5. Firebase** — after scope:
> "Is a Firebase project already configured? If yes, what's the project ID?"

**6. Backend** — after Firebase:
> "What's the backend URL? If it's not ready yet, I'll leave it as a placeholder."

**7. Push notifications** — after backend:
> "Will this app use push notifications?"

**8. Camera or gallery** — after push notifications:
> "Will users need to take photos or pick images from their gallery?"

**9. Offline support** — last question:
> "The default for this kit is online-first — the app shows an error state when there's no connection, but doesn't cache data for offline use. Does that work for this project, or do you need offline support for specific features?"

Do not ask any other questions. Do not ask about architecture, BLoC vs Cubit, Riverpod vs BLoC, navigation structure, or anything covered by `references/flutter_defaults.md`.

---

## Phase 2: Confirmation (silent — no output yet)

Once you have all nine answers, silently compose what you know:

- App name
- 2–3 sentence product description
- Explicit scope — what it does NOT do
- Feature list for v1 (these become folder names, normalized to snake_case)
- Firebase: configured yes/no + project ID if yes
- Backend URL or placeholder
- Push notifications: yes/no
- Camera/gallery: yes/no
- Offline: online-first default or specific offline needs

Then present a brief summary and ask for confirmation before writing anything:

> "Here's what I've got — [app name]: [one sentence description]. v1 features: [list]. Out of scope: [summary]. Firebase: [status]. Backend: [url or TBD]. Push notifications: [yes/no]. Camera: [yes/no]. Offline: [online-first / needs offline for X].
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
| Plataforma | Flutter / Dart |
| Creado | <today> |

## Objetivo del producto
<what it does, for whom, what problem it solves — 2–3 sentences from the developer's words>

## Lo que esta app NO hace
<explicit scope negativo — verbatim or close to the developer's words>

## Features — v1
| Feature | Descripción | Ubicación | Estado |
|---------|-------------|-----------|--------|
<one row per v1 feature — snake_case name, short description, lib/features/<name>/, PLANNED>

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Firebase Auth | Autenticación de usuarios (JWT) | <Sí — project ID: X / Pendiente> |
| Backend API | API REST (Dio) | <URL o Pendiente> |
| Firebase Cloud Messaging | Push notifications | <Sí / No en scope> |
| Camera / Gallery | Captura de imágenes | <Sí / No en scope> |

## Decisiones tomadas en este proyecto
<project-specific decisions that deviate from flutter_defaults.md defaults, or "Ninguna — seguir todos los defaults de flutter_defaults.md">
<if offline support was requested, note it here explicitly>

## Feature Map (se actualiza con cada /build completado)
| Feature | Archivos clave | Providers/BLoCs principales | Endpoints que consume |
|---------|---------------|------------------------------|----------------------|
```

---

## Phase 4: Scaffold Base Structure

Create the following directories and files silently. Do not ask for permission — this is the standard base for every project in this kit.

### Directories

Create all of these with `mkdir -p`:

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

For each feature listed in v1, create (using snake_case):
```
lib/features/<feature_name>/domain/entities/
lib/features/<feature_name>/domain/repositories/
lib/features/<feature_name>/domain/use_cases/
lib/features/<feature_name>/application/
lib/features/<feature_name>/infrastructure/repositories/
lib/features/<feature_name>/infrastructure/models/
lib/features/<feature_name>/infrastructure/data_sources/
lib/features/<feature_name>/presentation/screens/
lib/features/<feature_name>/presentation/widgets/
lib/features/<feature_name>/presentation/router/
```

### Files

**`lib/core/config/app_config.dart`** — dart-define constants:

```dart
// lib/core/config/app_config.dart
// Compile-time configuration from --dart-define
// Usage: flutter run --dart-define=API_URL=https://api.example.com ...

class AppConfig {
  static const apiUrl = String.fromEnvironment('API_URL');
  static const firebaseProjectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'development');

  static bool get isProduction => appEnv == 'production';
  static bool get isDevelopment => appEnv == 'development';
}
```

**`lib/main.dart`** — minimal main with Firebase init:

```dart
// lib/main.dart

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'app/bootstrap/bootstrap.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  runApp(const AppBootstrap());
}
```

**`lib/app/bootstrap/bootstrap.dart`** — app root skeleton:

```dart
// lib/app/bootstrap/bootstrap.dart
// AppBootstrap — root widget, sets up providers and router
// Full initialization sequence: ARCHITECTURE_MOBILE.md § 13

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

**`.env.example`** — dart-define variables (equivalent of .env.example for Flutter):

```bash
# .env.example — Flutter dart-define variables
# These are passed at build/run time, not at runtime.
# Never hardcode values in source files.
#
# Usage:
#   flutter run \
#     --dart-define=API_URL=https://api.example.com \
#     --dart-define=FIREBASE_PROJECT_ID=my-project-id \
#     --dart-define=APP_ENV=development
#
# For CI/CD: pass these as build arguments to your pipeline.

# ── Required ────────────────────────────────────────────────────────────────
API_URL=                    # Base URL of the NestJS backend
FIREBASE_PROJECT_ID=        # Firebase project ID
APP_ENV=development         # production / staging / development

# ── Platform config (not dart-define — managed per-environment) ─────────────
# google-services.json        → android/app/
# GoogleService-Info.plist    → ios/Runner/
# Use separate files per environment. Never commit production values.
```

---

## Phase 5: Handoff

Tell the developer what was done and what comes next:

> **[App name] is initialized.**
>
> Created:
> - `specs/project.md` — project memory (update it as the project evolves)
> - `lib/core/` — network, auth, errors, config, utils scaffolded
> - `lib/ui/` — primitives, components, layouts scaffolded
> - `lib/theme/` — tokens, components, utils scaffolded
> - `lib/app/` — router, providers, bootstrap scaffolded
> - `lib/features/<feature>/` — empty clean architecture folders for each v1 feature
> - `lib/main.dart` — minimal entrypoint with Firebase init
> - `.env.example` — dart-define variables to pass at build time
>
> Before your first feature:
> - Add `google-services.json` (Android) and `GoogleService-Info.plist` (iOS) for your Firebase project
> - Run `flutter pub get` to install dependencies
> - Confirm `API_URL` and `FIREBASE_PROJECT_ID` values for your environment
>
> When you're ready to build: run `/intake <description of your first feature>` to start the process.
