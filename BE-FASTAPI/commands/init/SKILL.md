---
name: init
description: One-time project initialization for a new FastAPI AI/ML service. Asks targeted questions about the specific service, produces specs/project.md as permanent project memory, and scaffolds the full base folder structure including app/, workers/, models/, .env.example, requirements.txt, and app/main.py.
allowed-tools: Read, Write, Bash(date:*), Bash(mkdir:*), Glob
metadata:
  version: 1.0.0
  stage: init
---

# Init

**Role: Staff Engineer**
**Stage: INIT — run once at the start of a new FastAPI service**

You are the Staff Engineer setting up a new FastAPI AI/ML service. You know the full stack and architecture — you don't need to ask about it. FastAPI services in this stack have a single job: receive tasks from Cloud Tasks (OIDC-authenticated), process them with AI/ML logic, and return results. You need to understand what this specific service processes and what infrastructure it needs.

You ask ONE question at a time. You wait for the answer. You build each question on what was said before. You talk like a colleague, not like a configuration form.

---

## Input

`$ARGUMENTS` — optional short description of the service. If provided, use it as context and ask only what it doesn't already answer. If empty, start the conversation from scratch.

---

## Gate Check (silent)

Before saying anything:
1. Read `CLAUDE.md` to load the technical baseline and hexagonal architecture rules.
2. Check if `specs/project.md` already exists. If it does, tell the developer: "Este servicio ya está inicializado — `specs/project.md` existe. Corre `/intake <descripción>` para empezar un nuevo feature." Then stop.
3. Check if `specs/` directory exists. If not, create it.

---

## Phase 1: Discovery Conversation

Ask ONE question at a time. Wait for the reply. Reference the developer's actual words in follow-up questions. No bullet lists while asking — talk like a colleague.

**Do NOT ask about:**
- Architecture (hexagonal, domain/application/adapters — already decided)
- Auth mechanism (OIDC from Cloud Tasks — always, never Firebase)
- Which framework (FastAPI + Python 3.13 — always)
- Validation approach (Pydantic — always)
- Anything covered in CLAUDE.md

**Ask in this order, skipping anything already clear from `$ARGUMENTS`:**

**Q1 — The service:**
"¿Qué tipo de procesamiento AI/ML hace este servicio? ¿OCR, embeddings, clasificación, extracción de datos — o algo distinto?"

Wait for answer, then:

**Q2 — The endpoints:**
"¿Cuáles son las operaciones que va a exponer? Dame una lista de los endpoints — por ejemplo: process-document, generate-embedding, classify-intent..."

Wait for answer, then:

**Q3 — Request pattern:**
"¿Este servicio solo recibe requests de Cloud Tasks de forma async, o también va a recibir llamadas síncronas directas de NestJS para respuestas inmediatas? ¿O ambos?"

Wait for answer, then:

**Q4 — Database:**
"¿Va a necesitar Neon Postgres? Algunos servicios FastAPI solo leen y escriben en R2, sin base de datos relacional."

Wait for answer, then:

**Q5 — File storage:**
"¿Va a leer o escribir archivos en R2? ¿Para qué — resultados de procesamiento, documentos de entrada, modelos?"

Wait for answer, then:

**Q6 — GCP:**
"¿Ya tienes el GCP project creado? Si sí, dame el project ID."

---

## Phase 2: Silent Build (no output yet)

Once you have all answers, silently assemble:

1. The service name (derive from the processing type if not stated — kebab-case)
2. The endpoint list (normalized to kebab-case)
3. Which infrastructure services are active
4. Whether it's async-only (Cloud Tasks) or also sync (direct HTTP from NestJS)
5. Any explicit decisions made during the conversation

Do not output anything yet.

---

## Phase 3: Confirm and Produce

Show a brief summary confirmation before writing anything:

---
**Listo. Voy a inicializar el servicio con esto:**

**Servicio:** [name]
**Tipo de procesamiento:** [description]
**Endpoints v1:** [list]
**Patrón de requests:** [async Cloud Tasks / sync NestJS / ambos]
**Neon Postgres:** [sí / no]
**R2:** [sí — para: [uso] / no]
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
| Plataforma | FastAPI + Python 3.13 |
| Creado | [YYYY-MM-DD] |

## Objetivo del producto
[2-3 sentences from what the developer said — what it processes, for whom (NestJS), what AI/ML operations it runs]

## Lo que este servicio NO hace
- No valida tokens Firebase (solo OIDC de GCP Cloud Tasks)
- No acepta requests directos de clientes (solo de NestJS o Cloud Tasks)
- No contiene lógica de negocio principal — orquesta NestJS, procesa FastAPI
[Any other explicit negative scope stated by the developer]

## Módulos — v1
| Módulo | Descripción | Ubicación | Estado |
|--------|-------------|-----------|--------|
[one row per endpoint/service — description inferred from context, location is app/services/<name>.py or app/api/v1/endpoints/<name>.py, status is "pending"]

## Servicios externos configurados
| Servicio | Uso | Configurado |
|----------|-----|-------------|
| Cloud Tasks OIDC | Recibe requests async de NestJS | pendiente — ALLOWED_SERVICE_ACCOUNT |
| Neon Postgres | [uso / no aplica] | [sí / pendiente / no aplica] |
| Cloudflare R2 | [uso / no aplica] | [sí / pendiente / no aplica] |
| Google Cloud Project | Proyecto GCP | [sí — project: [id] / pendiente] |

## Patrón de requests
[async Cloud Tasks únicamente / también HTTP sync directo de NestJS / ambos]

## Decisiones tomadas en este proyecto
[Any decisions made during the conversation, or "ninguna — seguir defaults de CLAUDE.md"]

## Module Map (se actualiza con cada /build completado)
| Módulo | Archivos clave | Handlers | Endpoints expuestos |
|--------|---------------|----------|---------------------|
[one empty row per endpoint/service]
```

### 4.3 — Create folder structure

Create these directories (use `mkdir -p`):

```
app/api/v1/endpoints/
app/core/
app/services/
app/models/
app/workers/
specs/
```

**Endpoint files — one per endpoint listed in v1:**

For each endpoint named `<endpoint-name>` in the list, create `app/api/v1/endpoints/<endpoint_name>.py`:
```python
# app/api/v1/endpoints/<endpoint_name>.py
# Endpoint: POST /internal/tasks/<endpoint-name>
# Handler for [description from conversation]
# TODO: implement after running /intake <endpoint-name>
```

(Use underscores for Python file names, e.g. `process_document.py` for endpoint `process-document`.)

**Core files:**

`app/core/config.py`:
```python
# app/core/config.py
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

`app/core/security.py`:
```python
# app/core/security.py
# OIDC token validation for Cloud Tasks requests.
# Validates that the request comes from the authorized GCP service account.
# See ARCHITECTURE_BACKEND.md § 5 for the full auth flow.
# TODO: implement OIDC validation using google-auth
from fastapi import HTTPException, Request


async def verify_oidc_token(request: Request) -> str:
    """Verify GCP OIDC token from Cloud Tasks. Returns the service account email."""
    # TODO: implement
    raise NotImplementedError
```

`app/core/logging.py`:
```python
# app/core/logging.py
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

**Router file:**

`app/api/v1/router.py`:
```python
# app/api/v1/router.py
from fastapi import APIRouter

# TODO: import and include one router per endpoint
# from app.api.v1.endpoints import <endpoint_name>

router = APIRouter()

# router.include_router(<endpoint_name>.router, prefix="/<endpoint-name>", tags=["<endpoint-name>"])
```

**Main file:**

`app/main.py`:
```python
# app/main.py
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.v1.router import router
from app.core.config import settings
from app.core.logging import configure_logging


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
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=False)
```

(Replace `[service-name]` with the actual service name.)

### 4.4 — Write `.env.example`

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
# This service validates every incoming request against this value.
ALLOWED_SERVICE_ACCOUNT=
```

If the developer confirmed GCP project ID, fill `GOOGLE_CLOUD_PROJECT=<id>`.
If the developer said no Neon, add a comment `# not used in this service` to the DATABASE_URL line.
If the developer said no R2, add a comment `# not used in this service` to the R2 block.

### 4.5 — Write `requirements.txt`

```
fastapi
uvicorn[standard]
pydantic
pydantic-settings
google-auth
google-cloud-tasks
```

If the developer confirmed Neon/Postgres, add:
```
sqlalchemy
asyncpg
```

If the developer confirmed R2, add:
```
boto3
```

---

## Phase 5: Handoff

After all files and folders are created, report:

---
**Servicio inicializado.**

**Archivos creados:**
- `specs/project.md` — memoria permanente del servicio
- `app/main.py` — entry point con lifespan y router
- `app/api/v1/router.py` — router principal
- `app/api/v1/endpoints/` — [list of endpoint files]
- `app/core/config.py`, `app/core/security.py`, `app/core/logging.py`
- `.env.example` — variables de entorno
- `requirements.txt` — dependencias base

**Estructura creada:**
- `app/services/` — servicios de dominio (vacía — se puebla con /build)
- `app/models/` — modelos Pydantic (vacía — se puebla con /build)
- `app/workers/` — workers async (vacía — se puebla si aplica)

**Siguiente paso:** corre `/intake <descripción del primer endpoint>` para empezar.

Por ejemplo: `/intake implementar el endpoint process-document — recibe un document_url desde Cloud Tasks, hace OCR con [librería], y escribe el resultado en R2`

---
