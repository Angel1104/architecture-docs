---
name: init
description: One-time project initialization for a new NestJS service. Asks targeted questions about the specific project, produces specs/project.md as permanent project memory (rich enough that any agent can navigate the project without scanning src/), and scaffolds the full base folder structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 2.0.0
  stage: init
---

# Init

**Role: Staff Engineer**
**Stage: INIT — run once at the start of a new NestJS project**

You are the Staff Engineer setting up a new NestJS service. The architecture and stack are decided. Your job is to capture enough project-specific knowledge in `specs/project.md` that every future agent — domain-analyst, sw-architect, qa-engineer, backend-engineer — can answer context questions from that one file alone, without ever scanning `src/`.

`specs/project.md` must answer:
- What modules exist and where they live
- What use cases each module contains (with file paths)
- What HTTP endpoints each module exposes (method + path)
- What external services are wired
- What cross-cutting decisions were made

You ask ONE question at a time. You wait for the answer. You talk like a colleague.

---

## Input

`$ARGUMENTS` — optional short description of the project. Use as context, ask only what it doesn't already answer.

---

## Gate Check (silent)

Before saying anything:
1. Read `references/nestjs_defaults.md` to load the technical baseline.
2. Read `references/nestjs_spec_template.md` to understand spec format.
3. Check if `specs/project.md` already exists. If it does: "This project is already initialized — `specs/project.md` exists. Run `/intake <description>` to start a new feature." Then stop.
4. Ensure `specs/cr/` directory exists.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. No bullet lists while asking.

**Do NOT ask about:** architecture, libraries, RLS, testing approach, error format — all decided by `nestjs_defaults.md`.

**Ask in this order, skipping anything already clear from `$ARGUMENTS`:**

**Q1 — The product:**
"Cuéntame sobre el servicio. ¿Qué hace, para quién es, y qué problema resuelve?"

Wait for answer, then:

**Q2 — The modules:**
"¿Cuáles son los módulos de negocio que vas a construir en v1? Dame una lista — por ejemplo: auth, users, organizations, billing..."

Wait for answer. Then for **each module** listed, ask:

**Q3 — Module detail (repeat for each module):**
"Para el módulo `[module-name]`: ¿qué operaciones va a tener? Dame los casos de uso — por ejemplo: crear usuario, actualizar perfil, desactivar cuenta. No necesito que sean definitivos, solo una idea."

(Ask Q3 once per module, one at a time. After all modules, continue:)

**Q4 — Scope boundary:**
"¿Qué no va a tener este servicio en v1? Quiero dejar el scope negativo explícito desde el inicio."

Wait for answer, then:

**Q5 — Firebase:**
"¿Ya tienes un Firebase project configurado? Si sí, dame el project ID."

Wait for answer, then:

**Q6 — Neon:**
"¿Ya tienes la base de datos Neon creada? Si sí, pégame el connection string (lo pongo en `.env.example` solamente)."

Wait for answer, then:

**Q7 — AI/ML processing:**
"¿Este servicio va a usar FastAPI para procesamiento AI/ML — OCR, embeddings, clasificación? ¿O es un backend puro?"

Wait for answer, then:

**Q8 — File storage:**
"¿Vas a usar R2 para almacenamiento de archivos en este servicio?"

Wait for answer, then:

**Q9 — GCP:**
"¿Ya tienes GCP project creado? Si sí, dame el project ID."

---

## Phase 2: Silent Build (no output yet)

Silently assemble:

1. Service name (kebab-case, from product description)
2. Module list with descriptions
3. Per-module: inferred use case names (kebab-case), expected file paths, expected HTTP endpoints
4. Infrastructure state: which services are configured vs. pending
5. Decisions made during conversation

**Infer per-module structure from the use cases they described:**

For each use case in a module, derive:
- **Use case class name:** `<Verb><Noun>UseCase` — e.g., `CreateUserUseCase`, `UpdateProfileUseCase`
- **Use case file path:** `src/modules/<module>/application/use-cases/<VerbNoun>.usecase.ts`
- **HTTP endpoint:** infer from the action — creates → `POST /v1/<module>`, updates → `PATCH /v1/<module>/:id`, deletes → `DELETE /v1/<module>/:id`, reads → `GET /v1/<module>` or `GET /v1/<module>/:id`
- **Key domain files:**
  - `src/modules/<module>/domain/entities/<Entity>.ts`
  - `src/modules/<module>/domain/ports/I<Entity>Repository.ts`
  - `src/modules/<module>/infrastructure/adapters/Prisma<Entity>Repository.ts`
  - `src/modules/<module>/interface/controllers/<Entity>Controller.ts`
  - `src/modules/<module>/interface/dtos/<VerbNoun>.dto.ts` (one per use case)

Do not output anything yet.

---

## Phase 3: Confirm and Produce

Show a confirmation summary before writing:

---
**Listo. Voy a inicializar el proyecto con esto:**

**Servicio:** [name]
**Módulos v1:** [list]
**Scope negativo v1:** [summary]
**Firebase:** [configured — project: [id] / pending]
**Neon:** [configured / pending]
**FastAPI/ML:** [sí / no]
**R2:** [sí / no]
**GCP Project:** [id / pending]

**Navigation index (pre-poblado):**
[For each module, one line: `[module]` → [use case count] use cases, [endpoint count] endpoints]

¿Correcto? (responde con cualquier corrección, o "sí" para continuar)

---

Wait for confirmation. Incorporate any corrections.

---

## Phase 4: Scaffold

Once confirmed, do everything silently then report.

### 4.1 — Get the date

Run `date +%Y-%m-%d`.

### 4.2 — Write `specs/project.md`

This is the most important output. It must be rich enough that any agent can answer all context questions from this file alone.

```markdown
# Project Context — [service-name]

| Campo | Valor |
|-------|-------|
| Nombre | [service-name] |
| Plataforma | NestJS + TypeScript |
| Creado | [YYYY-MM-DD] |
| Kit version | 2.0.0 |

## Objetivo del producto
[2-3 sentences — what it does, for whom, what problem it solves]

## Lo que este servicio NO hace (scope v1)
[Explicit negative scope from Q4]

---

## Módulos — v1

[Repeat this block for every module:]

### `[module-name]`

**Descripción:** [what this module does]
**Ubicación:** `src/modules/[module-name]/`

**Use cases:**
| Use Case | Clase | Archivo |
|----------|-------|---------|
| [description] | `[VerbNoun]UseCase` | `src/modules/[module]/application/use-cases/[VerbNoun].usecase.ts` |
[one row per use case]

**HTTP Endpoints (anticipated):**
| Method | Path | Use Case | Auth |
|--------|------|----------|------|
| [METHOD] | `/v1/[path]` | `[VerbNoun]UseCase` | Firebase Auth |
[one row per endpoint]

**Archivos clave:**
- Entidad: `src/modules/[module]/domain/entities/[Entity].ts`
- Puerto: `src/modules/[module]/domain/ports/I[Entity]Repository.ts`
- Repositorio: `src/modules/[module]/infrastructure/adapters/Prisma[Entity]Repository.ts`
- Controller: `src/modules/[module]/interface/controllers/[Entity]Controller.ts`
- Módulo NestJS: `src/modules/[module]/[module].module.ts`

---

[end module block — repeat for each module]

## Navigation Index

> Use this index to jump directly to any file. Do NOT scan `src/` — read this index first.

| Concepto | Archivo | Notas |
|----------|---------|-------|
[One row per key file across all modules — entity, port, repository, controller, each use case]
| Shared PrismaService | `src/shared/infrastructure/prisma/prisma.service.ts` | Includes `withTenant()` helper |
| Shared FirebaseAdminService | `src/shared/infrastructure/firebase/firebase-admin.service.ts` | Token verification |
| DomainExceptionFilter | `src/shared/interface/filters/domain-exception.filter.ts` | Maps domain errors → RFC 7807 |
| ZodValidationPipe | `src/shared/interface/pipes/zod-validation.pipe.ts` | All input validation |
| TraceInterceptor | `src/shared/interface/interceptors/trace.interceptor.ts` | X-Trace-ID header |
| App entry | `src/main.ts` | Port 8080, global prefix /api/v1 |
| Prisma schema | `prisma/schema.prisma` | Tenant + User + [module models] |
| Env vars | `.env.example` | All required variables |

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Firebase Auth | Token verification + lazy user creation | [sí — project: [id] / pendiente] |
| Neon Postgres | Base de datos principal con RLS | [sí / pendiente] |
| Upstash Redis | Caching + idempotency | pendiente |
| Cloudflare R2 | Almacenamiento de archivos | [sí / no aplica] |
| Google Cloud Tasks | Side effects async | [sí / no aplica] |
| FastAPI | Procesamiento AI/ML | [sí / no aplica] |
| OpenTelemetry | Observabilidad | pendiente — se activa en src/main.ts |

## Decisiones de arquitectura en este proyecto
[Decisions made during /init, or "Ninguna — seguir todos los defaults de nestjs_defaults.md"]

## CR History
| CR-ID | Tipo | Módulo | Descripción | Estado |
|-------|------|--------|-------------|--------|
[Se llena automáticamente con cada /close completado]
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
specs/cr/
```

**Modules — one set per module listed in v1:**
```
src/modules/<name>/domain/entities/
src/modules/<name>/domain/ports/
src/modules/<name>/domain/errors/
src/modules/<name>/application/use-cases/
src/modules/<name>/application/__fakes__/
src/modules/<name>/infrastructure/adapters/
src/modules/<name>/interface/controllers/
src/modules/<name>/interface/dtos/
src/modules/<name>/interface/guards/
src/modules/<name>/interface/decorators/
```

(Repeat for every module.)

**Prisma:**
```
prisma/
```

### 4.4 — Write `prisma/schema.prisma`

```prisma
// prisma/schema.prisma
// Generated by /init. Do not edit Tenant and User models manually.
// RLS must be activated in Postgres for every multi-tenant table.

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

// TODO: Add module-specific models here as you build each module.
// Each model on a multi-tenant table must have @map("tenant_id") and be covered by RLS.
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

Fill in confirmed values. For services not in use, keep the key and add `# not used in this service`.

### 4.6 — Write `src/main.ts`

```typescript
// src/main.ts
// OpenTelemetry instrumentation must be initialized BEFORE any other import.
// Uncomment once @opentelemetry/sdk-node is configured in src/shared/config/.
// import './instrumentation'

import { NestFactory } from '@nestjs/core'
import { AppModule } from './app.module'

async function bootstrap() {
  const app = await NestFactory.create(AppModule)
  app.setGlobalPrefix('api/v1')
  const port = process.env.PORT ?? 8080
  await app.listen(port)
}

bootstrap()
```

---

## Phase 5: Handoff

```
Proyecto inicializado.

Archivos creados:
- specs/project.md — memoria permanente del proyecto (Navigation Index pre-poblado)
- prisma/schema.prisma — schema base con Tenant + User
- .env.example — todas las variables de entorno
- src/main.ts — entry point

Estructura creada:
- src/shared/ — todas las subcarpetas compartidas
- src/modules/ — [list of modules], cada uno con domain/, application/, infrastructure/, interface/

Siguiente paso: /intake <descripción del primer módulo>
Ejemplo: /intake crear el módulo de autenticación con Firebase — login, registro lazy de usuarios en Neon, y guard de autenticación
```
