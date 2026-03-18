# ARCHITECTURE — Backend (NestJS + FastAPI)

> **Documento para agentes de IA.**
> Lee `ARCHITECTURE.md` primero para entender el sistema completo. Este documento cubre exclusivamente la capa backend: NestJS y FastAPI.
> Todas las decisiones están tomadas. Sigue este documento como fuente de verdad al scaffoldear o extender el backend. No improvises estructura ni cambies naming sin justificación.

---

## Stack de esta capa

| Componente | Tecnología |
|---|---|
| API principal | NestJS + TypeScript |
| AI/ML services | FastAPI + Python |
| Infraestructura | Google Cloud Run |
| Base de datos | Neon Postgres + Prisma |
| Caché | Upstash Redis |
| Storage | Cloudflare R2 |
| Event bus | Google Cloud Tasks |
| Auth identidad | Firebase Admin SDK |
| Secretos | Google Secret Manager |
| Observabilidad | OpenTelemetry → Cloud Trace + Logging + Monitoring |

---

## 1. Responsabilidad y scope

**NestJS** es la API principal del sistema. Cubre:
- Reglas de negocio y autorización
- Orquestación de workflows
- Integración con Neon, Firebase Auth, R2, Redis y Cloud Tasks
- Exposición de API REST `/v1/` para web y mobile

**FastAPI** procesa tareas especializadas de AI/ML. Cubre:
- OCR, embeddings, clasificación, procesamiento de documentos
- Tareas batch y pipelines AI
- Agentes y workflows de procesamiento

**Regla fundamental:** NestJS orquesta. FastAPI procesa. La lógica de negocio principal no vive en FastAPI.

**Lo que el backend NO hace:**
- Servir assets estáticos o el frontend web (eso es Vercel)
- Validar tokens Firebase en FastAPI (solo NestJS lo hace)
- Recibir requests directamente de clientes en FastAPI (solo vía Cloud Tasks)

---

## 2. Arquitectura Hexagonal — NestJS

### Diagrama de capas

```mermaid
graph TD
    subgraph Interface["Interface — Borde externo"]
        HTTP["HTTP Request"]
        Controller["Controller"]
        DTO["DTO + Validación"]
        Guard["Auth Guard"]
    end

    subgraph Application["Application — Orquestación"]
        UseCase["Use Case"]
        Port["Puerto (interface)"]
    end

    subgraph Domain["Domain — Núcleo del negocio"]
        Entity["Entidad"]
        VO["Value Object"]
        Rule["Regla de negocio"]
        DomainEvent["Evento de dominio"]
        DomainError["Error de dominio"]
    end

    subgraph Infrastructure["Infrastructure — Adaptadores"]
        Repo["Repositorio Prisma"]
        FirebaseAdapter["Firebase Adapter"]
        R2Adapter["R2 Adapter"]
        TasksAdapter["Cloud Tasks Adapter"]
        RedisAdapter["Redis Adapter"]
    end

    HTTP --> Guard --> Controller --> DTO
    DTO --> UseCase
    UseCase --> Entity
    UseCase --> Port
    Port -.->|"implementa"| Repo
    Port -.->|"implementa"| FirebaseAdapter
    Port -.->|"implementa"| R2Adapter
    Port -.->|"implementa"| TasksAdapter
    Port -.->|"implementa"| RedisAdapter

    Domain -.->|"nunca importa"| Infrastructure
    Domain -.->|"nunca importa"| Interface
```

### Reglas de dependencia — estrictas

```mermaid
graph LR
    Interface --> Application
    Application --> Domain
    Infrastructure --> Domain
    Infrastructure --> Application

    Interface -. "❌ nunca" .-> Infrastructure
    Domain -. "❌ nunca" .-> Infrastructure
    Domain -. "❌ nunca" .-> Application
```

---

## 3. Estructura de carpetas — NestJS

```
src/
├── modules/
│   ├── auth/
│   │   ├── domain/
│   │   │   ├── entities/       ← Entidades puras
│   │   │   ├── ports/          ← Interfaces (contratos hacia infraestructura)
│   │   │   └── errors/         ← Errores tipados del dominio
│   │   ├── application/
│   │   │   └── use-cases/      ← Un archivo por caso de uso
│   │   ├── infrastructure/
│   │   │   └── adapters/       ← Implementaciones de los puertos
│   │   ├── interface/
│   │   │   ├── guards/         ← Firebase Auth guard
│   │   │   └── decorators/     ← CurrentUser, Roles
│   │   └── auth.module.ts
│   │
│   ├── users/                  ← Misma estructura de 4 capas
│   ├── organizations/          ← Misma estructura de 4 capas
│   ├── files/                  ← Misma estructura de 4 capas
│   └── billing/                ← Misma estructura de 4 capas
│
├── shared/
│   ├── domain/                 ← BaseEntity, BaseValueObject, DomainEvent
│   ├── application/            ← UseCase interface
│   ├── infrastructure/
│   │   ├── prisma/             ← PrismaService
│   │   ├── redis/              ← RedisService
│   │   ├── cloud-tasks/        ← CloudTasksService
│   │   ├── r2/                 ← R2Service
│   │   └── firebase/           ← FirebaseAdminService
│   ├── interface/
│   │   ├── interceptors/       ← TraceInterceptor, LoggingInterceptor
│   │   ├── filters/            ← DomainExceptionFilter
│   │   └── pipes/              ← ZodValidationPipe
│   └── config/                 ← Composition root, configuración global
│
└── main.ts
```

---

## 4. Reglas operativas del backend

- Los controllers ejecutan use cases y transforman DTOs. No contienen lógica de negocio.
- Los side effects (emails, notificaciones, webhooks) se despachan como Cloud Tasks desde el use case, no directamente.
- Todo endpoint de escritura tiene el Firebase Auth guard aplicado.
- Todo input externo se valida con Zod antes de llegar al controller.
- Cada request recibe un `traceId` en el interceptor de entrada que viaja en logs y en headers de respuesta.
- Ningún controller ni use case importa directamente desde `infrastructure/`. Solo desde `domain/ports/`.

---

## 5. Servicio FastAPI

### Responsabilidad y restricciones

- Solo recibe requests de Cloud Tasks (con OIDC token de GCP). **No acepta requests directos de clientes.**
- No usa Firebase Auth. Solo valida OIDC tokens de GCP.
- No contiene lógica de negocio. Solo procesamiento especializado.
- Puede leer y escribir en Neon y R2 directamente.

### Flujo de comunicación

```mermaid
sequenceDiagram
    participant UC as NestJS Use Case
    participant CT as Cloud Tasks
    participant FA as FastAPI
    participant DB as Neon / R2

    UC->>CT: Encola task (payload tipado)
    CT->>FA: POST /internal/tasks/:nombre (OIDC token)
    FA->>FA: Procesa (OCR, embedding, etc.)
    FA->>DB: Guarda resultado
    FA-->>CT: 200 OK
    Note over CT: Task completado
```

### Estructura de carpetas — FastAPI

```
app/
├── api/
│   └── v1/
│       ├── router.py           ← Registro de todos los endpoints
│       └── endpoints/          ← Un archivo por tipo de servicio (ocr, embeddings, etc.)
│
├── core/
│   ├── config.py               ← Variables de entorno
│   ├── security.py             ← Validación de OIDC token GCP
│   └── logging.py              ← Logging estructurado JSON
│
├── services/                   ← Lógica de procesamiento por dominio
├── models/                     ← Pydantic: requests y responses
├── workers/                    ← Procesamiento batch
└── main.py
```

---

## 6. Formato de error — RFC 7807

Todos los errores del sistema devuelven este formato. Sin excepciones.

| Campo | Tipo | Descripción |
|---|---|---|
| `type` | string | Código de tipo de error |
| `title` | string | Mensaje legible para humanos |
| `status` | number | HTTP status code |
| `detail` | string | Detalle específico del error |
| `traceId` | string | Correlation ID del request |
| `timestamp` | string | ISO 8601 |
| `fieldErrors` | array | Solo en errores de validación: campo + mensaje |

### Flujo de error

```mermaid
flowchart LR
    Error["Error ocurre"] --> Type{¿Tipo?}
    Type -->|"Error de dominio"| Domain["DomainError\n4xx con código estable"]
    Type -->|"Error de infraestructura"| Infra["Se loggea internamente\nNunca se expone al cliente"]
    Type -->|"Error de validación"| Validation["422 con fieldErrors\npor campo"]
    Type -->|"Error no esperado"| Unknown["500 genérico\ntraceId para debugging"]

    Domain --> Response["ErrorResponse RFC 7807\ntype + title + status + detail + traceId"]
    Infra --> Response
    Validation --> Response
    Unknown --> Response
```

---

## 7. Auth — implementación completa

### División de responsabilidades

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

**Regla:** Firebase autentica. El backend autoriza. La base de datos decide el negocio.

### Flujo de sincronización (Firebase → Neon)

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

### Esquema mínimo de usuarios en Neon

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | UUID | Identificador interno |
| `firebase_uid` | VARCHAR(128) UNIQUE | UID de Firebase |
| `email` | VARCHAR(255) UNIQUE | Email verificado |
| `name` | VARCHAR(255) | Nombre del usuario |
| `tenant_id` | UUID FK | Tenant al que pertenece |
| `role` | VARCHAR(50) | Rol: `owner`, `admin`, `member` |
| `plan` | VARCHAR(50) | Plan: `free`, `pro`, `enterprise` |
| `status` | VARCHAR(50) | Estado: `active`, `suspended`, `deleted` |
| `last_seen_at` | TIMESTAMPTZ | Último acceso |
| `created_at` | TIMESTAMPTZ | Fecha de creación |
| `updated_at` | TIMESTAMPTZ | Última modificación |

---

## 8. Multi-tenancy — Row Level Security

### Estrategia fijada: RLS en Postgres

```mermaid
graph TD
    Request["Request autenticado"] --> Guard["Auth Guard\nObtiene tenant_id del usuario"]
    Guard --> TX["Inicia transacción Postgres\nSET LOCAL app.tenant_id = :tenantId"]
    TX --> Query["Query a cualquier tabla con RLS"]
    Query --> RLS["Postgres RLS Policy\nUSING tenant_id = current_setting(app.tenant_id)"]
    RLS --> Result["Solo filas del tenant correcto"]
```

### Reglas de multi-tenancy

- Cada tabla multi-tenant tiene columna `tenant_id UUID NOT NULL` con índice.
- RLS se activa en Postgres para cada tabla multi-tenant.
- El `tenant_id` proviene del usuario autenticado en Neon — **nunca del request body ni de query params**.
- Nunca hacer queries a tablas con RLS sin haber seteado `app.tenant_id` en la transacción.
- Ningún endpoint acepta `tenant_id` como input del cliente para operaciones sobre sus propios datos.
- Tablas globales (catálogos, configuración del sistema) no usan RLS.

---

## 9. Flujos de datos async

### Side effect con Cloud Tasks

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

### Subida de archivo (presigned URL)

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

## 10. Base de datos — Prisma

### Reglas de migración

- Usar siempre `prisma migrate dev` en desarrollo y `prisma migrate deploy` en CI/CD.
- Toda migración debe seguir el patrón **expand/contract**: nunca eliminar una columna o tabla en el mismo deploy que la reemplaza. Primero añadir la nueva estructura (expand), luego migrar datos, luego eliminar la antigua (contract) en un deploy posterior.
- RLS se activa desde el primer schema. No es algo que se agrega después.

### Schema mínimo de arranque

```prisma
model Tenant {
  id         String   @id @default(uuid())
  name       String
  slug       String   @unique
  plan       String   @default("free")
  status     String   @default("active")
  createdAt  DateTime @default(now())
  updatedAt  DateTime @updatedAt
  users      User[]
}

model User {
  id          String   @id @default(uuid())
  firebaseUid String   @unique @map("firebase_uid")
  email       String   @unique
  name        String
  tenantId    String   @map("tenant_id")
  role        String   @default("member")
  plan        String   @default("free")
  status      String   @default("active")
  lastSeenAt  DateTime? @map("last_seen_at")
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt
  tenant      Tenant   @relation(fields: [tenantId], references: [id])

  @@index([tenantId])
  @@map("users")
}
```

### Setup de RLS en Postgres

```sql
-- Activar RLS en tabla multi-tenant
ALTER TABLE [tabla] ENABLE ROW LEVEL SECURITY;

-- Policy para lectura y escritura del tenant correcto
CREATE POLICY tenant_isolation ON [tabla]
  USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- El PrismaService debe setear el contexto en cada transacción
-- SET LOCAL app.tenant_id = '[tenantId]';
```

---

## 11. Observabilidad — implementación backend

### Stack

```mermaid
graph LR
    Services["NestJS\nFastAPI"] -->|"OpenTelemetry SDK"| OTel["OpenTelemetry\nColector"]
    OTel --> Trace["Cloud Trace\nTrazas distribuidas"]
    OTel --> Logging["Cloud Logging\nLogs estructurados JSON"]
    OTel --> Metrics["Cloud Monitoring\nMétricas y alertas"]
    Metrics --> Alerts["Alertas\nEmail / PagerDuty"]
```

### Implementación en NestJS

- Inicializar OpenTelemetry **antes de cualquier otro import** en `main.ts`.
- El `TraceInterceptor` en `shared/interface/interceptors/` genera un UUID como `traceId` para cada request y lo adjunta al header `X-Trace-ID` de la respuesta.
- Todos los logs incluyen `traceId`. Ver formato de log en `ARCHITECTURE.md` sección 12.

### Alertas mínimas a configurar

| Alerta | Umbral | Acción |
|---|---|---|
| Error rate alto | > 1% en 5 minutos | Notificación inmediata |
| Latencia p99 alta | > 2 segundos | Notificación |
| Instancias Cloud Run altas | > umbral por servicio | Revisión de costo |
| Errores 5xx en aumento | Tendencia creciente | Revisión urgente |

---

## 12. Variables de entorno

### Backend NestJS

| Variable | Secret | Descripción |
|---|---|---|
| `NODE_ENV` | No | `production` / `staging` / `development` |
| `PORT` | No | `8080` en Cloud Run |
| `DATABASE_URL` | Sí | Connection string de Neon Postgres |
| `FIREBASE_PROJECT_ID` | No | ID del proyecto Firebase |
| `FIREBASE_CLIENT_EMAIL` | Sí | Service account de Firebase Admin |
| `FIREBASE_PRIVATE_KEY` | Sí | Clave privada de Firebase Admin |
| `REDIS_URL` | Sí | URL de Upstash Redis |
| `R2_ACCOUNT_ID` | No | ID de cuenta Cloudflare |
| `R2_ACCESS_KEY_ID` | Sí | Key de acceso R2 |
| `R2_SECRET_ACCESS_KEY` | Sí | Secret de acceso R2 |
| `R2_BUCKET_NAME` | No | Nombre del bucket |
| `GOOGLE_CLOUD_PROJECT` | No | ID del proyecto GCP |
| `CLOUD_TASKS_QUEUE_LOCATION` | No | `us-central1` |
| `FASTAPI_INTERNAL_URL` | No | URL interna de FastAPI en Cloud Run |

### FastAPI

| Variable | Secret | Descripción |
|---|---|---|
| `ENVIRONMENT` | No | `production` / `staging` / `development` |
| `PORT` | No | `8080` en Cloud Run |
| `DATABASE_URL` | Sí | Connection string de Neon Postgres |
| `R2_ACCOUNT_ID` | No | ID de cuenta Cloudflare |
| `R2_ACCESS_KEY_ID` | Sí | Key de acceso R2 |
| `R2_SECRET_ACCESS_KEY` | Sí | Secret de acceso R2 |
| `R2_BUCKET_NAME` | No | Nombre del bucket |
| `GOOGLE_CLOUD_PROJECT` | No | ID del proyecto GCP |
| `ALLOWED_SERVICE_ACCOUNT` | No | Service account de Cloud Tasks autorizado |

### Reglas de secretos

- En Cloud Run: los secretos se montan como variables de entorno referenciando Secret Manager con `--set-secrets`.
- Cada servicio tiene su propio Service Account con acceso solo a los secretos que necesita (principio de mínimo privilegio).
- Los secretos en producción se rotan cada 90 días.
- Variables no sensibles pueden ir como variables de entorno directas en Cloud Run.
- Nunca commitear `.env` ni `.env.local`. Solo `.env.example` con valores vacíos.

---

## 13. Versionado de API

### Estrategia fijada: versionado por URL

Todos los endpoints públicos van bajo `/v1/`. El prefijo vive en el controller NestJS como `@Controller('v1/[módulo]')`.

### Cuándo crear `/v2/`

**No se crea `/v2/` por preferencia de diseño ni por refactorings internos.** Solo se crea cuando hay un breaking change real que afecta a clientes en producción y no se puede evitar.

Un breaking change es:
- Eliminar un campo de la respuesta que los clientes usan.
- Cambiar el tipo de un campo existente.
- Cambiar la semántica de un parámetro (mismo nombre, diferente comportamiento).
- Cambiar la estructura del body de un request requerido.

**No es un breaking change:**
- Añadir campos nuevos opcionales a la respuesta.
- Añadir parámetros opcionales a un endpoint.
- Añadir endpoints nuevos.
- Cambios internos de implementación (base de datos, servicios).

### Proceso para introducir `/v2/`

1. Crea el nuevo endpoint bajo `/v2/` en el mismo módulo.
2. Mantén `/v1/` funcionando durante el período de migración. No lo elimines en el mismo deploy.
3. Comunica el deprecation a los clientes con el header `Deprecation: true` y `Sunset: [fecha]`.
4. Elimina `/v1/` solo cuando todos los clientes hayan migrado.

### Regla para agentes

Si estás scaffoldeando un módulo nuevo, siempre usa `/v1/`. Nunca crees un módulo directamente en `/v2/` a menos que el documento de spec lo indique explícitamente.

---

## 14. Paginación

### Estrategia fijada: cursor-based

**No se usa offset/page number.** La paginación por cursor es consistente con inserciones concurrentes y no tiene el problema de "registro saltado" del offset.

### Contrato de respuesta paginada

```typescript
// shared/interface/pagination.types.ts
export type PaginatedResponse<T> = {
  data: T[];
  nextCursor: string | null;  // null = no hay más páginas
  hasMore: boolean;
};

export type PaginationParams = {
  cursor?: string;  // ausente = primera página
  limit?: number;   // default: 20, max: 100
};
```

### Implementación en el repositorio

```typescript
// En el repositorio Prisma, la query siempre incluye:
const items = await prisma.item.findMany({
  where: { tenantId, ...(cursor ? { id: { gt: cursor } } : {}) },
  orderBy: { createdAt: 'asc' },  // orden estable requerido para cursor
  take: limit + 1,  // toma uno extra para saber si hay más
});

const hasMore = items.length > limit;
const data = hasMore ? items.slice(0, -1) : items;
const nextCursor = hasMore ? data[data.length - 1].id : null;
```

### Reglas de paginación

- Todos los endpoints de listado devuelven `PaginatedResponse<T>`. Nunca arrays planos sin paginación.
- El `limit` máximo es 100. Si el cliente pide más, se responde con 400.
- El orden del cursor debe ser estable: siempre ordena por un campo único + `createdAt`. Nunca por campos que pueden cambiar.
- El cursor es opaco para el cliente: es un ID o un string encodeado. Nunca un número de página.

---

## 15. Side effects síncronos

### Cuándo NO usar Cloud Tasks

Cloud Tasks es para side effects que pueden procesarse en background y donde el cliente no necesita el resultado para continuar (procesamiento de documentos, emails, notificaciones, webhooks).

**Hay casos válidos donde el side effect debe ser síncrono** dentro del request:

| Caso | Estrategia |
|---|---|
| Verificar existencia en servicio externo antes de continuar (ej: validar IBAN en banco) | Llamada directa desde el use case via puerto de infraestructura |
| Enviar email de verificación y necesitar confirmar que se envió | Llamada directa, el use case espera el resultado |
| Generar un thumbnail/preview pequeño que el cliente necesita en la respuesta | Llamada directa a FastAPI vía HTTP interno (no Cloud Tasks) |
| Registrar un evento de auditoría que debe ser parte de la transacción | Escritura en DB dentro de la misma transacción Prisma |

### Llamada síncrona a FastAPI

Cuando NestJS necesita resultado síncrono de FastAPI, la llamada va directamente vía HTTP interno (no Cloud Tasks). FastAPI tiene endpoints `/internal/sync/[operacion]` para estos casos además de los endpoints de tasks async.

```mermaid
sequenceDiagram
    participant UC as NestJS Use Case
    participant FA as FastAPI
    participant DB as Neon

    UC->>FA: POST /internal/sync/generate-thumbnail (OIDC)
    FA->>FA: Genera thumbnail
    FA-->>UC: { thumbnailUrl }
    UC->>DB: Guarda resultado con thumbnail
    UC-->>Client: Respuesta con thumbnail incluido
```

### Reglas para side effects síncronos

- Si la operación síncrona falla y la operación principal no puede continuar sin ella: lanza un `DomainError` con 422 o 424 según aplique.
- Si la operación síncrona falla pero la operación principal sí puede continuar: loggea el error como `warn`, continúa, y encola un retry vía Cloud Tasks.
- Nunca bloquear el request más de 10 segundos en una llamada síncrona a servicio externo. Si el servicio externo es lento, rediseñar como async.
- Los endpoints `/internal/sync/` de FastAPI también se protegen con OIDC token de GCP.

---

## 16. Testing strategy — backend

### Postura

**No se mockea la base de datos en tests de repositorios.** Los tests de repositorios usan una base de datos real (Neon en staging, o Postgres local via Docker en desarrollo). Esto previene que divergencias entre el mock y Prisma oculten bugs.

### Capas y herramientas

| Qué testear | Herramienta | Tipo |
|---|---|---|
| Use cases (lógica de dominio) | Jest + repositorios fake (implement los puertos) | Unitario |
| Controllers (HTTP layer) | Jest + Supertest + NestJS testing module | Integración |
| Repositorios Prisma | Jest + base de datos real (Docker Compose) | Integración |
| Flujos E2E críticos | Jest + Supertest contra servicio levantado | E2E |

### Reglas de testing

- Los tests de use cases usan implementaciones `Fake` de los puertos del repositorio. No usan `jest.mock()` de Prisma.
- Los tests de controllers usan el módulo de testing de NestJS con providers reales o fakes controlados. Se testea el contrato HTTP: status codes, estructura de respuesta, headers.
- Los tests de repositorios requieren una base de datos real. En CI, el workflow levanta un contenedor Postgres con Docker. Cada test suite limpia sus datos al inicio con `prisma.$transaction` + `deleteMany`.
- Nunca usar `jest.mock()` sobre servicios de infraestructura (Firebase, R2, Redis) en tests de use cases. Esos tienen sus propios ports/fakes.
- Los tests viven junto al código que testean: `modules/auth/application/use-cases/__tests__/login.usecase.spec.ts`.

### Tests de FastAPI

| Qué testear | Herramienta | Tipo |
|---|---|---|
| Servicios de procesamiento | pytest | Unitario |
| Endpoints (validación OIDC, contrato de respuesta) | pytest + httpx | Integración |

- Los tests de FastAPI mockean el OIDC token en tests de integración usando un token de test firmado con la clave del service account de test.

---

## 17. Instrucciones para agentes — crear nuevo módulo backend

1. Crea la carpeta bajo `src/modules/[nombre]/` con las cuatro subcarpetas: `domain/`, `application/`, `infrastructure/`, `interface/`.
2. Define la entidad en `domain/entities/`. Extiende `BaseEntity`.
3. Define los errores en `domain/errors/`. Extiende `DomainError`.
4. Define el puerto del repositorio en `domain/ports/` como interface TypeScript pura.
5. Crea los use cases en `application/use-cases/`. Uno por acción de negocio.
6. Implementa el repositorio en `infrastructure/repositories/` con Prisma. Implementa el puerto.
7. Crea el controller en `interface/controllers/`. Solo llama use cases.
8. Define los DTOs en `interface/dtos/` con Zod para validación.
9. Registra el módulo en NestJS y agrégalo a `app.module.ts`.

---

## 18. Instrucciones para agentes — agregar side effect async

1. Define el tipo del task en `shared/infrastructure/cloud-tasks/`.
2. Crea el handler en el módulo correspondiente como endpoint `POST /internal/tasks/[task-name]`.
3. Protege el endpoint con OIDC token de GCP, **no con Firebase Auth**.
4. Despacha el task desde el use case usando `CloudTasksService`. Nunca desde el controller.
5. Define retry policy y deadline en la configuración del task.

---

## 19. Instrucciones para agentes — proyecto nuevo (backend)

1. Crea la estructura de carpetas exacta definida en la sección 3.
2. Configura las dependencias base de NestJS y FastAPI.
3. Instala dependencias de testing: Jest, Supertest, `@nestjs/testing`.
4. Configura Prisma con el schema mínimo: tablas `users` y `tenants` con RLS desde el inicio.
5. Activa RLS en todas las tablas multi-tenant desde el primer schema.
6. Configura `firebase-admin` en el shared module del backend.
7. Implementa el Auth Guard con lazy creation de usuario en Neon (flujo de la sección 7).
8. Configura OpenTelemetry en el backend **antes de cualquier otra lógica**.
9. Crea los tipos `PaginatedResponse<T>` y `PaginationParams` en `shared/interface/pagination.types.ts`.
10. Crea el `.env.example` con todas las variables de la sección 12 con valores vacíos.
11. Crea el `Dockerfile` para Cloud Run en backend y FastAPI.
12. Configura `docker-compose.yml` con Postgres para tests de integración locales.

---

## 20. Checklist de proyecto nuevo — backend

### Estructura
- [ ] Estructura exacta de carpetas de NestJS creada
- [ ] Estructura de FastAPI creada
- [ ] Dependencias base instaladas (NestJS, Prisma, firebase-admin, OpenTelemetry)
- [ ] `.env.example` completo con todas las variables requeridas
- [ ] `Dockerfile` para NestJS y FastAPI

### Base de datos
- [ ] Schema Prisma con tablas base: `users`, `tenants`
- [ ] RLS activado en tablas multi-tenant
- [ ] Índices en `tenant_id` en todas las tablas con RLS
- [ ] Primera migración generada con `prisma migrate dev`

### Auth
- [ ] Firebase project configurado
- [ ] `firebase-admin` inicializado en el shared module
- [ ] Auth Guard implementado con lazy creation de usuario en Neon
- [ ] Flujo completo de sync (firebase_uid → Neon) probado

### Infraestructura
- [ ] Upstash Redis conectado y disponible como servicio
- [ ] Cloud Tasks configurado y disponible como servicio
- [ ] R2 conectado con generación de URLs firmadas funcionando
- [ ] Secret Manager configurado con todos los secretos del proyecto

### Observabilidad
- [ ] OpenTelemetry inicializado en el backend
- [ ] Trace interceptor implementado (genera traceId por request)
- [ ] Logging estructurado JSON configurado
- [ ] Alertas mínimas configuradas en Cloud Monitoring

### API y paginación
- [ ] Todos los controllers usan prefijo `/v1/`
- [ ] `PaginatedResponse<T>` y `PaginationParams` definidos en shared
- [ ] Al menos el endpoint de listado principal usa paginación cursor-based

### Testing
- [ ] Jest configurado con cobertura
- [ ] `docker-compose.yml` con Postgres para tests locales
- [ ] Al menos un test unitario de use case con repositorio fake
- [ ] Al menos un test de integración de controller con Supertest

### Validación final
- [ ] Build de NestJS pasa sin errores
- [ ] Build de FastAPI pasa sin errores
- [ ] Tests pasan (`jest --runInBand`)
- [ ] `GET /health` responde 200 correctamente
- [ ] Flujo completo de auth funciona end-to-end: login → token → request autenticado
- [ ] Multi-tenancy verificado: datos de un tenant no son visibles desde otro
- [ ] Paginación verificada: cursor devuelve página siguiente correcta

---

*Versión: 1.1 — Marzo 2026*
*Derivado de ARCHITECTURE.md v3.0. Lee ese documento primero para el contexto del sistema completo.*
