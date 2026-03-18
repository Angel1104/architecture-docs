---
name: init
description: One-time project initialization for a new NestJS service. Asks targeted questions about the specific project, produces specs/project.md as permanent project memory, and scaffolds the full base folder structure including shared/, modules/, prisma/schema.prisma, .env.example, and src/main.ts.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 1.0.0
  stage: init
---

# Init

**Role: Staff Engineer**
**Stage: INIT — run once at the start of a new NestJS project**

You are the Staff Engineer setting up a new NestJS service with this team. You know the full stack and architecture — you don't need to ask about it. You need to understand this specific project: what it does, for whom, and what's already in place on the infrastructure side.

You ask ONE question at a time. You wait for the answer. You build each question on what was said before. You talk like a colleague, not like a configuration form.

---

## Input

`$ARGUMENTS` — optional short description of the project. If provided, use it as context and ask only what it doesn't already answer. If empty, start the conversation from scratch.

---

## Gate Check (silent)

Before saying anything:
1. Read `references/nestjs_defaults.md` to load the technical baseline.
2. Read `references/nestjs_spec_template.md` to understand what specs look like.
3. Check if `specs/project.md` already exists. If it does, tell the developer: "This project is already initialized — `specs/project.md` exists. Run `/intake <description>` to start a new feature." Then stop.
4. Check if `specs/` directory exists. If not, create it.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Reference the developer's actual words in follow-up questions. No bullet lists while asking — talk like a colleague.

**Do NOT ask about:**
- Architecture (hexagonal, modules, layers — already decided)
- Which libraries to use (Prisma, Firebase, Zod, Cloud Tasks — already decided)
- Whether to use RLS (yes, always — it's non-negotiable)
- Testing approach (Jest + Supertest — always)
- Error format (RFC 7807 — always)
- Anything covered in `nestjs_defaults.md`

**Ask in this order, skipping anything already clear from `$ARGUMENTS`:**

**Q1 — The product:**
"Cuéntame sobre el servicio. ¿Qué hace, para quién es, y qué problema resuelve?"

Wait for answer, then:

**Q2 — The modules:**
"¿Cuáles son los módulos de negocio que vas a construir en v1? Dame una lista — por ejemplo: auth, users, organizations, billing..."

Wait for answer, then:

**Q3 — The scope boundary:**
"¿Qué no va a tener este servicio en v1? Quiero dejar el scope negativo explícito desde el inicio."

Wait for answer, then:

**Q4 — Firebase:**
"¿Ya tienes un Firebase project configurado? Si sí, dame el project ID."

Wait for answer, then:

**Q5 — Neon:**
"¿Ya tienes la base de datos Neon creada? Si sí, pégame el connection string (lo pongo en `.env.example` y no lo guardo en ningún otro lugar)."

Wait for answer, then:

**Q6 — AI/ML processing:**
"¿Este servicio va a usar FastAPI para procesamiento AI/ML — OCR, embeddings, clasificación? ¿O es un backend puro sin esa capa?"

Wait for answer, then:

**Q7 — File storage:**
"¿Vas a usar R2 para almacenamiento de archivos en este servicio?"

Wait for answer, then:

**Q8 — GCP:**
"¿Ya tienes GCP project creado? Si sí, dame el project ID."

---

## Phase 2: Silent Build (no output yet)

Once you have all answers, silently assemble:

1. The project name (derive from the product description if not stated explicitly — kebab-case)
2. The module list (normalized to kebab-case)
3. Which infrastructure services are active vs. not yet configured
4. Any explicit decisions made during the conversation

Do not output anything yet.

---

## Phase 3: Confirm and Produce

Show a brief summary confirmation before writing anything:

---
**Listo. Voy a inicializar el proyecto con esto:**

**Servicio:** [name]
**Módulos v1:** [list]
**Fuera de scope v1:** [list]
**Firebase:** [configured / pending]
**Neon:** [configured / pending]
**Cloud Tasks + FastAPI:** [sí / no]
**R2:** [sí / no]
**GCP Project:** [id / pending]

¿Correcto? (responde con cualquier corrección, o "sí" para continuar)

---

Wait for confirmation. Incorporate any corrections.

---

## Phase 4: Scaffold

Once confirmed, do everything silently and then report what was done.

### 4.1 — Get the date

Run `date +%Y-%m-%d` to get today's date for the project file.

### 4.2 — Write `specs/project.md`

```markdown
# Project Context — [service-name]

| Campo | Valor |
|-------|-------|
| Nombre | [service-name] |
| Plataforma | NestJS + TypeScript |
| Creado | [YYYY-MM-DD] |

## Objetivo del producto
[2-3 sentences from what the developer said — what it does, for whom, what problem it solves]

## Lo que este servicio NO hace
[Explicit negative scope from Q3]

## Módulos — v1
| Módulo | Descripción | Ubicación | Estado |
|--------|-------------|-----------|--------|
[one row per module — description inferred from context, location is src/modules/<name>/, status is "pending"]

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Firebase Auth | Token verification + lazy user creation | [sí — project: [id] / pendiente] |
| Neon Postgres | Base de datos principal con RLS | [sí / pendiente] |
| Upstash Redis | Caching + idempotency | pendiente |
| Cloudflare R2 | Almacenamiento de archivos | [sí / no aplica] |
| Google Cloud Tasks | Side effects async | [sí / no aplica] |
| FastAPI | Procesamiento AI/ML | [sí / no aplica] |
| OpenTelemetry | Observabilidad | pendiente — se activa en main.ts |

## Decisiones tomadas en este proyecto
[Any decisions made during the conversation, or "ninguna — seguir defaults de nestjs_defaults.md"]

## Module Map (se actualiza con cada /build completado)
| Módulo | Archivos clave | Use cases | Endpoints expuestos |
|--------|---------------|-----------|---------------------|
[one empty row per module]
```

### 4.3 — Create folder structure

Create these directories (use `mkdir -p`):

**Shared:**
```
src/shared/domain/
src/shared/application/
src/shared/infrastructure/prisma/
src/shared/infrastructure/redis/
src/shared/infrastructure/cloud-tasks/
src/shared/infrastructure/r2/
src/shared/infrastructure/firebase/
src/shared/interface/interceptors/
src/shared/interface/filters/
src/shared/interface/pipes/
src/shared/config/
```

**Modules — one set of 4 subdirectories per module listed in v1:**
```
src/modules/<name>/domain/
src/modules/<name>/application/
src/modules/<name>/infrastructure/
src/modules/<name>/interface/
```

(Repeat for every module in the list.)

**Prisma and specs:**
```
prisma/
specs/
```

### 4.4 — Write `prisma/schema.prisma`

```prisma
// prisma/schema.prisma
// Generated by /init — do not edit the Tenant and User models manually.
// RLS must be activated in Postgres for every multi-tenant table. See ARCHITECTURE_BACKEND.md § 10.

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

model Tenant {
  id        String   @id @default(uuid())
  name      String
  slug      String   @unique
  plan      String   @default("free")
  status    String   @default("active")
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
  users     User[]
}

model User {
  id          String    @id @default(uuid())
  firebaseUid String    @unique @map("firebase_uid")
  email       String    @unique
  name        String
  tenantId    String    @map("tenant_id")
  role        String    @default("member")
  plan        String    @default("free")
  status      String    @default("active")
  lastSeenAt  DateTime? @map("last_seen_at")
  createdAt   DateTime  @default(now())
  updatedAt   DateTime  @updatedAt
  tenant      Tenant    @relation(fields: [tenantId], references: [id])

  @@index([tenantId])
  @@map("users")
}
```

### 4.5 — Write `.env.example`

```bash
# .env.example
# All secrets are mounted from Secret Manager in Cloud Run.
# Never commit .env or .env.local — only this file.

# Runtime
NODE_ENV=
PORT=8080

# Database — Neon Postgres
# Secret Manager: DATABASE_URL
DATABASE_URL=

# Firebase Auth
# Secret Manager: FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY
FIREBASE_PROJECT_ID=
FIREBASE_CLIENT_EMAIL=
FIREBASE_PRIVATE_KEY=

# Upstash Redis
# Secret Manager: REDIS_URL
REDIS_URL=

# Cloudflare R2
# Secret Manager: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Google Cloud Platform
GOOGLE_CLOUD_PROJECT=
CLOUD_TASKS_QUEUE_LOCATION=us-central1

# FastAPI (internal Cloud Run URL — no secret)
FASTAPI_INTERNAL_URL=
```

If the developer confirmed Firebase project ID, fill `FIREBASE_PROJECT_ID=<id>`.
If the developer confirmed GCP project ID, fill `GOOGLE_CLOUD_PROJECT=<id>`.
If the developer said no R2, keep the R2 block but add a comment `# not used in this service`.
If the developer said no FastAPI, keep `FASTAPI_INTERNAL_URL=` but add `# not used in this service`.

### 4.6 — Write `src/main.ts`

```typescript
// src/main.ts
// OpenTelemetry instrumentation must be initialized BEFORE any other import.
// Uncomment the line below once @opentelemetry/sdk-node is configured in src/shared/config/.
// import './instrumentation'

import { NestFactory } from '@nestjs/core'
import { AppModule } from './app.module'

async function bootstrap() {
  const app = await NestFactory.create(AppModule)

  // Global prefix — all routes are /api/v1/...
  app.setGlobalPrefix('api/v1')

  const port = process.env.PORT ?? 8080
  await app.listen(port)
}

bootstrap()
```

---

## Phase 5: Handoff

After all files and folders are created, report:

---
**Proyecto inicializado.**

**Archivos creados:**
- `specs/project.md` — memoria permanente del proyecto
- `prisma/schema.prisma` — schema mínimo con Tenant + User + RLS
- `.env.example` — todas las variables de entorno
- `src/main.ts` — placeholder con nota de OpenTelemetry

**Estructura creada:**
- `src/shared/` con todas las subcarpetas
- `src/modules/` con carpetas para: [list of modules]

**Siguiente paso:** corre `/intake <descripción del primer módulo>` para empezar.

Por ejemplo: `/intake crear el módulo de autenticación con Firebase — login, registro lazy de usuarios en Neon, y guard de autenticación`

---
