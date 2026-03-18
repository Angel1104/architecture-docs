# ARCHITECTURE MASTER DOCUMENT
## Stack: Next.js + Flutter + NestJS + FastAPI

> **Documento para agentes de IA.**
> Todas las decisiones están tomadas. No hay opciones a elegir. Sigue este documento como fuente de verdad al scaffoldear un proyecto nuevo. No improvises estructura, no cambies naming sin justificación, no omitas capas.

---

## Dónde ir

Lee este documento completo primero. Luego navega al documento de tu plataforma:

| Estoy construyendo... | Lee este documento |
|---|---|
| La aplicación web (Next.js) | [ARCHITECTURE_WEB.md](ARCHITECTURE_WEB.md) |
| La aplicación mobile (Flutter) | [ARCHITECTURE_MOBILE.md](ARCHITECTURE_MOBILE.md) |
| El backend (NestJS + FastAPI) | [ARCHITECTURE_BACKEND.md](ARCHITECTURE_BACKEND.md) |
| Un concern transversal | Este documento (continúa leyendo) |

---

## ÍNDICE

1. [Stack completo y justificaciones](#1-stack-completo-y-justificaciones)
2. [Vista general del sistema](#2-vista-general-del-sistema)
3. [Contrato de auth](#3-contrato-de-auth)
4. [Multi-tenancy](#4-multi-tenancy)
5. [Flujos de datos del sistema](#5-flujos-de-datos-del-sistema)
6. [Infraestructura y despliegue](#6-infraestructura-y-despliegue)
7. [Observabilidad](#7-observabilidad)
8. [Contrato de API](#8-contrato-de-api)
8. [Gestión de secretos](#8-gestión-de-secretos)
9. [Reglas no negociables](#9-reglas-no-negociables)

---

## 1. Stack completo y justificaciones

| Capa | Tecnología | Justificación |
|---|---|---|
| **Web** | Next.js 14+ (App Router) + TypeScript + Tailwind CSS | Framework React con SSR, SSG y App Router nativos. Mejor opción para landing + dashboard en un solo proyecto. |
| **Mobile** | Flutter (Dart) — cross-platform compilado a nativo | Compila a ARM nativo. Un solo codebase para iOS y Android con rendimiento real, no WebView. |
| **Backend core** | NestJS + TypeScript en **Google Cloud Run** | Escala a cero en tráfico bajo, se expande en picos. Arquitectura hexagonal en TypeScript con tipado compartible con el frontend. |
| **Servicios AI** | FastAPI + Python en **Google Cloud Run** | Python es el ecosistema natural para AI/ML. Aislado del backend core para escalar y actualizar independientemente. |
| **Base de datos** | Neon Postgres | Postgres serverless con elasticidad de costo real. Se pausa cuando no hay tráfico. |
| **Auth** | Firebase Authentication | Resuelve identidad, login, providers OAuth y sesiones. El backend maneja la autorización de negocio por separado. |
| **Storage** | Cloudflare R2 | Sin egress fees. Archivos e imágenes con URLs firmadas. Postgres solo guarda metadata. |
| **Caché** | Upstash Redis | Redis serverless sin servidores que mantener. Compatible con el modelo de Cloud Run. |
| **Event bus** | Google Cloud Tasks | Simple, integrado con Cloud Run, suficiente para side effects async. Pub/Sub solo si se necesitan múltiples suscriptores. |
| **Secretos** | Google Secret Manager | Secretos montados en Cloud Run como variables de entorno desde Secret Manager. Nunca en código ni repositorio. |
| **Migraciones DB** | Prisma Migrate | Migraciones versionadas, reproducibles y parte del pipeline CI/CD. |
| **Observabilidad** | OpenTelemetry + GCP (Trace + Logging + Monitoring) | Estándar vendor-neutral instrumentado una vez, exportado a GCP. |

### ¿Por qué Vercel para web?

Next.js es construido por Vercel. El despliegue en Vercel ofrece optimizaciones que Cloud Run no da sin trabajo extra: edge caching automático, ISR (Incremental Static Regeneration), preview deployments por rama, y CDN global sin configuración.

**Decisión fijada: Vercel para web.**

---

## 2. Vista general del sistema

```mermaid
graph TD
    Users([Usuarios])

    subgraph Clients["Clientes"]
        Web["Web\nNext.js — Vercel"]
        Mobile["Mobile\nFlutter — iOS/Android"]
    end

    subgraph GCP["Google Cloud Platform"]
        Backend["Backend Core\nNestJS — Cloud Run"]
        FastAPI["Servicios AI\nFastAPI — Cloud Run"]
        Tasks["Cloud Tasks\nEvent Bus async"]
        SecretMgr["Secret Manager\nSecretos"]
    end

    subgraph Data["Datos y Storage"]
        Neon[("Neon Postgres\nBase relacional")]
        Redis[("Upstash Redis\nCaché")]
        R2["Cloudflare R2\nArchivos e imágenes"]
    end

    subgraph Auth["Identidad"]
        Firebase["Firebase Auth\nLogin y tokens"]
    end

    Users --> Web
    Users --> Mobile

    Web -->|HTTPS REST /v1/| Backend
    Mobile -->|HTTPS REST /v1/| Backend

    Web -->|Token Firebase| Firebase
    Mobile -->|Token Firebase| Firebase
    Firebase -->|Token validado| Backend

    Backend --> Neon
    Backend --> Redis
    Backend --> R2
    Backend --> Tasks
    Backend --> SecretMgr

    Tasks -->|OIDC protegido| FastAPI
    FastAPI --> Neon
    FastAPI --> R2
```

---

## 3. Contrato de auth

**Regla fundamental:** Firebase autentica. El backend autoriza. La base de datos decide el negocio.

```mermaid
graph LR
    subgraph Firebase["Firebase Auth"]
        Login["Login / Registro"]
        Providers["OAuth Providers"]
        Token["Emisión de JWT"]
    end

    subgraph Backend["NestJS Backend"]
        Validate["Validación del token"]
        Authorize["Autorización de negocio"]
        TenantCheck["Verificación de tenant"]
        PermCheck["Verificación de permisos"]
    end

    subgraph Neon["Neon Postgres"]
        UserData["Datos del usuario"]
        Roles["Roles y plan"]
        Permissions["Permisos por recurso"]
    end

    Firebase -->|JWT| Backend
    Backend -->|Consulta| Neon
```

### Flujo de sincronización (primera vez)

```mermaid
sequenceDiagram
    participant Client as Cliente (Web/Mobile)
    participant Firebase as Firebase Auth
    participant Guard as NestJS Auth Guard
    participant Neon as Neon Postgres

    Client->>Firebase: Login (email, Google, etc.)
    Firebase-->>Client: JWT token

    Client->>Guard: Request con Bearer token
    Guard->>Firebase: verifyIdToken(token)
    Firebase-->>Guard: UID + email verificados

    Guard->>Neon: Buscar usuario por firebase_uid

    alt Usuario no existe (primera vez)
        Guard->>Neon: Crear usuario en Neon
        Neon-->>Guard: Usuario creado
    else Usuario existe
        Guard->>Neon: Actualizar last_seen_at
        Neon-->>Guard: Usuario actualizado
    end

    Guard-->>Client: Request autorizado con contexto de usuario Neon
```

### Responsabilidad por capa

| Capa | Responsabilidad de auth |
|---|---|
| Web | Inicializar Firebase client SDK, adjuntar token en requests, manejar logout en 401. Ver `ARCHITECTURE_WEB.md`. |
| Mobile | Inicializar Firebase client SDK, interceptor Dio con token, retry en 401. Ver `ARCHITECTURE_MOBILE.md`. |
| Backend | `verifyIdToken`, lazy creation de usuario en Neon, autorización de negocio. Ver `ARCHITECTURE_BACKEND.md`. |

---

## 4. Multi-tenancy

**Estrategia fijada: Row Level Security (RLS) en Postgres.**

El `tenant_id` proviene del usuario autenticado en Neon — **nunca del request body ni de query params**.

```mermaid
graph TD
    Request["Request autenticado"] --> Guard["Auth Guard\nObtiene tenant_id del usuario"]
    Guard --> TX["Inicia transacción Postgres\nSET LOCAL app.tenant_id = :tenantId"]
    TX --> Query["Query a cualquier tabla con RLS"]
    Query --> RLS["Postgres RLS Policy\nUSING tenant_id = current_setting(app.tenant_id)"]
    RLS --> Result["Solo filas del tenant correcto"]
```

**Reglas:**
- Cada tabla multi-tenant tiene columna `tenant_id UUID NOT NULL` con índice.
- RLS se activa en Postgres para cada tabla multi-tenant.
- Nunca hacer queries a tablas con RLS sin haber seteado `app.tenant_id` en la transacción.
- Ningún endpoint acepta `tenant_id` como input del cliente.
- Tablas globales (catálogos, configuración del sistema) no usan RLS.

La implementación completa vive en `ARCHITECTURE_BACKEND.md` sección 8.

---

## 5. Flujos de datos del sistema

### Side effect async (Cloud Tasks)

```mermaid
sequenceDiagram
    participant Client as Cliente
    participant NestJS as NestJS Use Case
    participant CT as Cloud Tasks
    participant FastAPI as FastAPI / Handler

    Client->>NestJS: POST /v1/documents/process
    NestJS->>NestJS: Ejecuta lógica de dominio
    NestJS->>CT: Encola task (payload tipado, retry policy)
    NestJS-->>Client: 202 Accepted (procesamiento async)

    CT->>FastAPI: POST /internal/tasks/process-document (OIDC)
    FastAPI->>FastAPI: OCR / Embedding / Clasificación
    FastAPI-->>CT: 200 OK
```

### Subida de archivo

```mermaid
sequenceDiagram
    participant Client as Cliente (Web/Mobile)
    participant NestJS as NestJS
    participant R2 as Cloudflare R2
    participant Neon as Neon Postgres

    Client->>NestJS: POST /v1/files/upload-url
    NestJS->>R2: Genera URL firmada (presigned URL)
    R2-->>NestJS: URL firmada con expiración
    NestJS-->>Client: { uploadUrl, fileId }

    Client->>R2: PUT directo con el archivo (sin pasar por NestJS)
    R2-->>Client: 200 OK

    Client->>NestJS: POST /v1/files/confirm { fileId }
    NestJS->>Neon: Guarda metadata del archivo
    NestJS-->>Client: File confirmado
```

---

## 6. Infraestructura y despliegue

```mermaid
graph TD
    subgraph Users["Usuarios"]
        Browser["Browser"]
        AppMobile["App Mobile"]
    end

    subgraph Vercel["Vercel"]
        NextJS["Next.js\nSSR + CDN global"]
    end

    subgraph GCP["Google Cloud Platform"]
        CloudRun1["Cloud Run\nNestJS Backend"]
        CloudRun2["Cloud Run\nFastAPI Services"]
        CloudTasks["Cloud Tasks\nQueues"]
        SecretMgr["Secret Manager"]
        Trace["Cloud Trace + Logging"]
    end

    subgraph External["Servicios externos"]
        Firebase["Firebase Auth"]
        Neon["Neon Postgres\nServerless"]
        Upstash["Upstash Redis\nServerless"]
        R2["Cloudflare R2\nStorage"]
    end

    Browser --> NextJS
    AppMobile --> CloudRun1
    NextJS --> CloudRun1
    CloudRun1 --> CloudRun2
    CloudRun1 --> CloudTasks
    CloudTasks --> CloudRun2
    CloudRun1 --> Firebase
    CloudRun1 --> Neon
    CloudRun1 --> Upstash
    CloudRun1 --> R2
    CloudRun2 --> Neon
    CloudRun2 --> R2
    CloudRun1 --> SecretMgr
    CloudRun2 --> SecretMgr
    CloudRun1 --> Trace
    CloudRun2 --> Trace
```

### Entornos

| Entorno | Propósito | Características |
|---|---|---|
| `dev` | Desarrollo local | Datos falsos, secretos locales en `.env.local`, servicios locales o emulados |
| `staging` | QA e integración | Datos anonimizados, servicios reales pero instancias separadas, deploy automático en merge a `main` |
| `prod` | Producción | Credenciales propias, Secret Manager, alertas activas, deploy manual o con aprobación |

---

## 7. Observabilidad

### Formato de log obligatorio

Todos los logs del sistema son JSON estructurado con estos campos mínimos. El `traceId` viaja en el header `X-Trace-ID` entre todos los servicios — web, mobile y backend deben adjuntarlo en cada request.

| Campo | Requerido | Descripción |
|---|---|---|
| `timestamp` | Sí | ISO 8601 |
| `level` | Sí | `debug`, `info`, `warn`, `error` |
| `service` | Sí | Nombre del servicio (`backend-core`, `ai-services`) |
| `traceId` | Sí | UUID del request (viaja en `X-Trace-ID`) |
| `message` | Sí | Descripción del evento |
| `context` | No | Objeto con datos relevantes (userId, tenantId, etc.) |

### Convención del traceId

- Cada request genera un UUID v4 como `traceId`.
- El cliente lo envía en el header `X-Trace-ID` (o lo genera si no tiene uno).
- El backend lo lee, lo propaga a todos sus logs y lo devuelve en el header `X-Trace-ID` de la respuesta.
- FastAPI recibe el `traceId` via Cloud Tasks y lo propaga en sus logs.

### Reglas de logging

- Nunca loggear datos sensibles: tokens, passwords, números de tarjeta, PII sin enmascarar.
- Siempre incluir `traceId` en cada log statement.
- Los errores de dominio se loggean como `warn`. Los errores de infraestructura como `error`.

La implementación completa de OpenTelemetry y alertas vive en `ARCHITECTURE_BACKEND.md` sección 11.

---

## 8. Contrato de API

### Versionado

Todos los endpoints públicos viven bajo `/v1/`. El versionado es por URL.

**Breaking change** (requiere `/v2/`): eliminar o renombrar campos de respuesta, cambiar tipo de campo, cambiar semántica de parámetro existente.

**No es breaking change** (no requiere `/v2/`): añadir campos opcionales a la respuesta, añadir parámetros opcionales, añadir endpoints nuevos.

La implementación y el proceso completo de versionado viven en `ARCHITECTURE_BACKEND.md` sección 13.

### Paginación

Todos los endpoints de listado usan **paginación cursor-based**. No se usa offset/page number.

```
GET /v1/[recurso]?cursor=[id]&limit=20
→ { data: [...], nextCursor: "abc123" | null, hasMore: true | false }
```

La implementación completa del contrato y los tipos viven en `ARCHITECTURE_BACKEND.md` sección 14.

---

## 9. Gestión de secretos

**Reglas universales — aplican a todas las capas:**

- Nunca commitear `.env` ni `.env.local`. Solo `.env.example` con valores vacíos y comentarios explicativos.
- Nunca poner secretos en código ni en repositorio.
- Los secretos en producción se rotan cada 90 días.

**Por capa:**

| Capa | Mecanismo |
|---|---|
| Backend (Cloud Run) | Google Secret Manager. Montados como env vars con `--set-secrets`. Cada servicio tiene su propio Service Account con mínimo privilegio. |
| Web (Vercel) | Variables `NEXT_PUBLIC_` para config pública (no secretos reales). Variables privadas para llamadas server-side. Ver `ARCHITECTURE_WEB.md`. |
| Mobile (Flutter) | `--dart-define` en tiempo de compilación. Nunca secretos en el binario. Ver `ARCHITECTURE_MOBILE.md`. |

---

## 10. Reglas no negociables

Estas reglas no tienen excepciones por deadline, por "es solo temporal" ni por preferencia personal.

| # | Regla |
|---|---|
| 1 | Ninguna feature importante empieza sin spec revisada. |
| 2 | No hay lógica de negocio en controllers, screens ni widgets. |
| 3 | No hay colores, spacing ni medidas hardcodeadas en features. |
| 4 | Ninguna feature accede a HTTP directamente. Solo a través del ApiClient. |
| 5 | Todo input externo se valida en el borde del sistema antes de entrar al dominio. |
| 6 | Todo endpoint de escritura requiere autenticación. |
| 7 | El dominio no importa infraestructura. Nunca. |
| 8 | Los errores de infraestructura nunca se exponen directamente a la UI. |
| 9 | Los side effects importantes salen por Cloud Tasks, no directo desde el use case. |
| 10 | No hay secretos en código ni en repositorio. |
| 11 | No hay acceso cross-tenant. El tenant_id viene del usuario autenticado. |
| 12 | Toda operación sensible es auditable. |
| 13 | Ninguna migración de DB rompe la versión anterior del código (expand/contract). |
| 14 | Ningún log contiene datos sensibles sin enmascarar. |
| 15 | Ningún servicio expone endpoints sin validación de identidad. |

---

*Versión: 3.0 — Marzo 2026*
*Este documento es el contrato del sistema. Para implementación, lee el documento de tu plataforma: `ARCHITECTURE_WEB.md`, `ARCHITECTURE_MOBILE.md`, o `ARCHITECTURE_BACKEND.md`.*
