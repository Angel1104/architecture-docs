---
name: init
description: One-time project initialization for a new FastAPI AI/ML service. Asks targeted questions, produces specs/project.md as permanent project memory (rich enough that any agent can navigate the project without scanning src/), and scaffolds the full base folder structure.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 2.0.0
  stage: init
---

# Init

**Role: Staff Engineer**
**Stage: INIT — run once at the start of a new FastAPI service**

You are the Staff Engineer setting up a new FastAPI AI/ML service. The architecture and stack are decided. FastAPI services in this stack have a single job: receive tasks from Cloud Tasks (OIDC-authenticated), process them with AI/ML logic, and return results.

Your job is to capture enough project-specific knowledge in `specs/project.md` that every future agent — domain-analyst, sw-architect, security-engineer, backend-engineer — can answer context questions from that one file alone, without ever scanning `src/`.

`specs/project.md` must answer:
- What endpoints exist and what each one processes
- What use case (command/query) each endpoint triggers (with file path)
- What domain models are involved
- What external services are wired
- What cross-cutting decisions were made

You ask ONE question at a time. You wait for the answer. You talk like a colleague.

---

## Input

`$ARGUMENTS` — optional short description of the service. Use as context, ask only what it doesn't already answer.

---

## Gate Check (silent)

Before saying anything:
1. Read `CLAUDE.md` to load the technical baseline and hexagonal architecture rules.
2. Check if `specs/project.md` already exists. If it does: "Este servicio ya está inicializado — `specs/project.md` existe. Corre `/intake <descripción>` para empezar un nuevo feature." Then stop.
3. Ensure `specs/cr/` directory exists.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. No bullet lists while asking.

**Do NOT ask about:** architecture, OIDC auth (always required), Pydantic (always), or anything in CLAUDE.md.

**Q1 — The service:**
"¿Qué tipo de procesamiento AI/ML hace este servicio? ¿OCR, embeddings, clasificación, extracción de datos — o algo distinto?"

Wait for answer, then:

**Q2 — The endpoints:**
"¿Cuáles son las operaciones que va a exponer? Dame una lista de los endpoints — por ejemplo: process-document, generate-embedding, classify-intent..."

Wait for answer. Then for **each endpoint** listed, ask:

**Q3 — Endpoint detail (repeat for each endpoint):**
"Para el endpoint `[endpoint-name]`: ¿qué recibe, qué procesa, y qué devuelve o persiste? Dame una descripción breve."

(Ask Q3 once per endpoint, one at a time. After all endpoints, continue:)

**Q4 — Request pattern:**
"¿Este servicio solo recibe requests de Cloud Tasks de forma async, o también va a recibir llamadas síncronas directas de NestJS para respuestas inmediatas? ¿O ambos?"

Wait for answer, then:

**Q5 — Database:**
"¿Va a necesitar Neon Postgres? Algunos servicios FastAPI solo leen y escriben en R2, sin base de datos relacional."

Wait for answer, then:

**Q6 — File storage:**
"¿Va a leer o escribir archivos en R2? ¿Para qué — resultados de procesamiento, documentos de entrada, modelos?"

Wait for answer, then:

**Q7 — GCP:**
"¿Ya tienes el GCP project creado? Si sí, dame el project ID."

---

## Phase 2: Silent Build (no output yet)

Silently assemble:

1. Service name (kebab-case)
2. Endpoint list with descriptions
3. Per-endpoint: inferred command/query names, domain models, expected file paths
4. Infrastructure: which services are active
5. Request pattern: async-only or also sync
6. Decisions made during conversation

**Infer per-endpoint structure from the description:**

For each endpoint, derive:
- **HTTP path:** `POST /internal/tasks/<endpoint-name>` (async) or `POST /internal/sync/<endpoint-name>` (sync)
- **Command/Query class:** `<ProcessNoun>Command` or `<GetNoun>Query`
- **Command/Query file:** `src/application/commands/<process_noun>_command.py` or `src/application/queries/<get_noun>_query.py`
- **Domain model:** `src/domain/models/<noun>.py`
- **Port interface:** `src/domain/ports/<noun>_repository.py` (if persisting)
- **Adapter (outbound):** `src/adapters/outbound/<noun>_repository.py`
- **Router file:** `src/adapters/inbound/<endpoint_name>.py`

Do not output anything yet.

---

## Phase 3: Confirm and Produce

Show a confirmation summary before writing:

---
**Listo. Voy a inicializar el servicio con esto:**

**Servicio:** [name]
**Tipo de procesamiento:** [description]
**Endpoints v1:** [list]
**Patrón de requests:** [async Cloud Tasks / sync NestJS / ambos]
**Neon Postgres:** [sí / no]
**R2:** [sí — para: [uso] / no]
**GCP Project:** [id / pending]

**Navigation index (pre-poblado):**
[For each endpoint, one line: `POST /internal/tasks/[name]` → [Command/Query class] → [domain models involved]]

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
| Plataforma | FastAPI + Python 3.13 |
| Creado | [YYYY-MM-DD] |
| Kit version | 2.0.0 |

## Objetivo del producto
[2-3 sentences — what it processes, for whom (NestJS/Cloud Tasks), what AI/ML operations it runs]

## Lo que este servicio NO hace
- No valida tokens Firebase (solo OIDC de GCP Cloud Tasks)
- No acepta requests directos de clientes (solo de NestJS vía Cloud Tasks)
- No contiene lógica de negocio principal — orquesta NestJS, procesa FastAPI
[Any other explicit negative scope stated by the developer]

---

## Endpoints — v1

[Repeat this block for every endpoint:]

### `POST /internal/tasks/[endpoint-name]` [or /internal/sync/ for sync]

**Descripción:** [what it receives, what it processes, what it returns/persists]
**Patrón:** [async Cloud Tasks / sync directo de NestJS]
**Auth:** GCP OIDC (Cloud Tasks service account)

**Use case:**
| Clase | Archivo |
|-------|---------|
| `[ProcessNoun]Command` | `src/application/commands/[process_noun]_command.py` |

**Domain models:**
| Modelo | Archivo |
|--------|---------|
| `[Noun]` | `src/domain/models/[noun].py` |
[one row per domain model involved]

**Archivos clave:**
- Router (inbound): `src/adapters/inbound/[endpoint_name].py`
- Port (outbound): `src/domain/ports/[noun]_repository.py` (if persisting)
- Adapter (outbound): `src/adapters/outbound/[noun]_repository.py` (if persisting)

---

[end endpoint block — repeat for each endpoint]

## Navigation Index

> Use this index to jump directly to any file. Do NOT scan `src/` — read this index first.

| Concepto | Archivo | Notas |
|----------|---------|-------|
[One row per key file across all endpoints]
| OIDC validation | `src/config/security.py` | Validates GCP service account token |
| Settings | `src/config/settings.py` | Pydantic BaseSettings — all env vars |
| Logging | `src/config/logging.py` | Structured JSON for Cloud Logging |
| Main router | `src/adapters/inbound/router.py` | Includes all endpoint routers |
| App entry | `src/main.py` | FastAPI app + lifespan |
| Env vars | `.env.example` | All required variables |

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Cloud Tasks OIDC | Recibe requests async de NestJS | pendiente — ALLOWED_SERVICE_ACCOUNT |
| Neon Postgres | [uso / no aplica] | [sí / pendiente / no aplica] |
| Cloudflare R2 | [uso / no aplica] | [sí / pendiente / no aplica] |
| Google Cloud Project | Proyecto GCP | [sí — project: [id] / pendiente] |

## Patrón de requests
[async Cloud Tasks únicamente / también HTTP sync directo de NestJS / ambos]

## Decisiones de arquitectura en este proyecto
[Decisions made during /init, or "Ninguna — seguir defaults de CLAUDE.md"]

## CR History
| CR-ID | Tipo | Endpoint | Descripción | Estado |
|-------|------|----------|-------------|--------|
[Se llena automáticamente con cada /close completado]
```

### 4.3 — Create folder structure

```
src/domain/models/
src/domain/ports/
src/domain/exceptions.py
src/application/commands/
src/application/queries/
src/adapters/inbound/
src/adapters/outbound/
src/config/
specs/cr/
```

**Endpoint router files — one per endpoint in v1:**

For each endpoint `<endpoint-name>`, create `src/adapters/inbound/<endpoint_name>.py`:
```python
# src/adapters/inbound/<endpoint_name>.py
# POST /internal/tasks/<endpoint-name>
# Handler for [description from conversation]
# TODO: implement after running /intake <endpoint-name>
from fastapi import APIRouter, Depends
from src.config.security import verify_oidc_token

router = APIRouter()

@router.post("/<endpoint-name>")
async def handle(
    # TODO: add Pydantic request body
    _: str = Depends(verify_oidc_token),
):
    raise NotImplementedError
```

(Use underscores for Python file names: `process_document.py` for `process-document`.)

### 4.4 — Core config files

**`src/config/settings.py`:**
```python
# src/config/settings.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    environment: str = "development"
    port: int = 8080

    # Database
    database_url: str = ""

    # Cloudflare R2
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""

    # GCP
    google_cloud_project: str = ""
    allowed_service_account: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
```

**`src/config/security.py`:**
```python
# src/config/security.py
# OIDC token validation for Cloud Tasks requests.
# Validates that the request comes from the authorized GCP service account.
from fastapi import HTTPException, Request


async def verify_oidc_token(request: Request) -> str:
    """Verify GCP OIDC token from Cloud Tasks. Returns the service account email."""
    # TODO: implement using google-auth
    raise NotImplementedError
```

**`src/config/logging.py`:**
```python
# src/config/logging.py
# Structured JSON logging for Cloud Logging.
import logging
import sys


def configure_logging() -> None:
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

**`src/domain/exceptions.py`:**
```python
# src/domain/exceptions.py
# Domain exceptions — never reference HTTP status codes here.

class DomainError(Exception):
    """Base class for all domain errors."""

class NotFoundError(DomainError):
    pass

class ValidationError(DomainError):
    pass
```

**`src/adapters/inbound/router.py`:**
```python
# src/adapters/inbound/router.py
from fastapi import APIRouter

# TODO: import and include one router per endpoint
# from src.adapters.inbound import <endpoint_name>

router = APIRouter()

# router.include_router(<endpoint_name>.router, prefix="/<endpoint-name>", tags=["<endpoint-name>"])
```

**`src/main.py`:**
```python
# src/main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.adapters.inbound.router import router
from src.config.settings import settings
from src.config.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


app = FastAPI(
    title="[service-name]",
    lifespan=lifespan,
)

app.include_router(router, prefix="/internal/tasks")


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=settings.port, reload=False)
```

### 4.5 — Write `.env.example`

```bash
# .env.example
# All secrets are mounted from Secret Manager in Cloud Run.
# Never commit .env — only this file.

# Runtime
ENVIRONMENT=
PORT=8080

# Database — Neon Postgres
# Secret Manager: DATABASE_URL
# (remove if this service does not use Postgres)
DATABASE_URL=

# Cloudflare R2
# Secret Manager: R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY
# (remove if this service does not use R2)
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Google Cloud Platform
GOOGLE_CLOUD_PROJECT=

# Cloud Tasks OIDC auth
# The service account email that Cloud Tasks uses to call this service.
ALLOWED_SERVICE_ACCOUNT=
```

Fill in confirmed values. For services not in use, keep the key and add `# not used in this service`.

### 4.6 — Write `requirements.txt`

```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
google-auth
google-cloud-tasks
```

If Neon/Postgres confirmed, add:
```
sqlalchemy
asyncpg
```

If R2 confirmed, add:
```
boto3
```

---

## Phase 5: Handoff

```
Servicio inicializado.

Archivos creados:
- specs/project.md — memoria permanente del servicio (Navigation Index pre-poblado)
- src/main.py — entry point con lifespan y router
- src/adapters/inbound/router.py — router principal
- src/adapters/inbound/[endpoints] — un archivo por endpoint
- src/config/settings.py, security.py, logging.py
- src/domain/exceptions.py
- .env.example — variables de entorno
- requirements.txt — dependencias base

Estructura creada:
- src/domain/models/ — modelos de dominio
- src/domain/ports/ — interfaces de repositorio
- src/application/commands/ — comandos (writes)
- src/application/queries/ — queries (reads)
- src/adapters/outbound/ — repositorios concretos

Siguiente paso: /intake <descripción del primer endpoint>
Ejemplo: /intake implementar process-document — recibe document_url desde Cloud Tasks, hace OCR, escribe resultado en R2
```
