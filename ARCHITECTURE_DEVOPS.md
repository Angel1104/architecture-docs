# ARCHITECTURE — DevOps, Entornos y Despliegue

> **Documento para agentes de IA y desarrolladores.**
> Lee `ARCHITECTURE.md` primero para entender el sistema completo. Este documento cubre la estrategia de entornos, dominios, DNS, CI/CD con GitHub Actions, permisos de infraestructura y seguridad de red.
> Todas las decisiones están tomadas. No improvises configuraciones de infraestructura ni CI/CD.

---

## ÍNDICE

1. [Estrategia de entornos](#1-estrategia-de-entornos)
2. [Dominios y DNS](#2-dominios-y-dns)
3. [Cloudflare — DNS, WAF y seguridad](#3-cloudflare--dns-waf-y-seguridad)
4. [Vercel — despliegue web](#4-vercel--despliegue-web)
5. [Google Cloud Run — despliegue backend](#5-google-cloud-run--despliegue-backend)
6. [Permisos e IAM](#6-permisos-e-iam)
7. [CI/CD con GitHub Actions](#7-cicd-con-github-actions)
8. [Rollback](#8-rollback)
9. [CI/CD Mobile — Android e iOS](#9-cicd-mobile--android-e-ios)
10. [Checklist de infraestructura nueva](#10-checklist-de-infraestructura-nueva)

---

## 1. Estrategia de entornos

### Configuración estándar: 3 entornos

| Entorno | Rama Git | Deploy | Propósito |
|---|---|---|---|
| `dev` | cualquier rama feature | Local / manual | Desarrollo local, datos falsos, servicios emulados |
| `staging` | `main` | Automático en push | QA, integración, pruebas con servicios reales |
| `prod` | tag `v*` (ej: `v1.0.0`) | Manual con aprobación | Producción real |

### Configuración mínima: 2 entornos

Cuando el proyecto es nuevo o el equipo es pequeño, se puede operar con solo 2 entornos:

| Entorno | Rama Git | Deploy | Propósito |
|---|---|---|---|
| `dev` | cualquier rama feature | Local / manual | Desarrollo local |
| `prod` | `main` | Automático en push a `main` | Producción |

**Cuándo escalar a 3 entornos:** cuando el equipo supera 2 personas, cuando hay clientes en producción, o cuando se necesita QA antes de producción. No antes.

### Aislamiento por entorno

Cada entorno tiene recursos **completamente separados**. No se comparten bases de datos, colas, ni buckets entre entornos.

| Recurso | dev | staging | prod |
|---|---|---|---|
| Neon Postgres | branch `dev` o local | proyecto `staging` | proyecto `prod` |
| Upstash Redis | instancia `dev` | instancia `staging` | instancia `prod` |
| Cloudflare R2 | bucket `[app]-dev` | bucket `[app]-staging` | bucket `[app]-prod` |
| Firebase project | proyecto `[app]-dev` | proyecto `[app]-staging` | proyecto `[app]-prod` |
| GCP project | proyecto `[app]-dev` | proyecto `[app]-staging` | proyecto `[app]-prod` |
| Cloud Run (backend) | local Docker / no aplica | service `backend-staging` | service `backend-prod` |
| Vercel | preview deployments | dominio `staging.[app].com` | dominio `[app].com` |

### Variables de entorno por entorno

Las variables se almacenan en:
- **dev**: `.env.local` (nunca commiteado)
- **staging**: GitHub Actions Secrets (environment `staging`) + Google Secret Manager proyecto staging
- **prod**: GitHub Actions Secrets (environment `prod`) + Google Secret Manager proyecto prod

---

## 2. Dominios y DNS

### Flujo de vida de un dominio

```
Compra en Squarespace → Delegación DNS a Cloudflare → Uso en Vercel / Cloud Run
```

### Paso 1 — Comprar el dominio en Squarespace

Squarespace es solo el registrar (la entidad que registra el dominio). Se compra ahí, pero los DNS **no se gestionan en Squarespace**.

### Paso 2 — Delegar los nameservers a Cloudflare

Inmediatamente después de comprar el dominio:

1. Crear el dominio en Cloudflare (plan Free es suficiente para la mayoría de proyectos).
2. Cloudflare provee 2 nameservers propios (ej: `aria.ns.cloudflare.com`, `bob.ns.cloudflare.com`).
3. En Squarespace → Domains → DNS Settings → Custom Nameservers → pegar los de Cloudflare.
4. La propagación toma entre 1-24 horas.

**A partir de este punto, todos los registros DNS se gestionan en Cloudflare, no en Squarespace.**

### Paso 3 — Configurar registros DNS en Cloudflare

Una vez que Cloudflare controla el dominio, se crean los registros necesarios:

| Tipo | Nombre | Valor | Proxy | Propósito |
|---|---|---|---|---|
| `CNAME` | `@` o `www` | `cname.vercel-dns.com` | ✅ Proxied | Web (Next.js en Vercel) |
| `CNAME` | `api` | `[region]-docker.pkg.dev` o URL de Cloud Run | ✅ Proxied | Backend NestJS |
| `CNAME` | `staging` | `cname.vercel-dns.com` | ✅ Proxied | Web staging |
| `CNAME` | `api-staging` | URL de Cloud Run staging | ✅ Proxied | Backend staging |
| `TXT` | `@` | Verificación de dominio (Vercel, Firebase, etc.) | ❌ DNS only | Verificaciones |

**Regla:** todos los registros de servicio van con proxy de Cloudflare activado (nube naranja). Solo los registros TXT de verificación van sin proxy.

### Estructura de subdominios

| Subdominio | Apunta a | Entorno |
|---|---|---|
| `[app].com` | Vercel | prod (web) |
| `www.[app].com` | Vercel (redirect a raíz) | prod (web) |
| `api.[app].com` | Cloud Run | prod (backend) |
| `staging.[app].com` | Vercel | staging (web) |
| `api-staging.[app].com` | Cloud Run | staging (backend) |

`dev` no tiene subdominio público. Corre en `localhost`.

---

## 3. Cloudflare — DNS, WAF y seguridad

### Por qué Cloudflare (más allá de R2)

Cloudflare actúa como proxy delante de Vercel y Cloud Run. Esto añade:
- **DDoS protection** automático sin configuración adicional.
- **WAF** (Web Application Firewall) con reglas gestionadas.
- **Caché de edge** para assets estáticos.
- **SSL/TLS** automático end-to-end.
- **Turnstile** para captcha sin fricciones.

### SSL/TLS

Configurar en Cloudflare → SSL/TLS:
- Modo: **Full (strict)** — nunca `Flexible`. El tráfico entre Cloudflare y el origen (Vercel/Cloud Run) también va cifrado.
- Always Use HTTPS: **activado**.
- Minimum TLS Version: **TLS 1.2**.
- Automatic HTTPS Rewrites: **activado**.

### WAF — Reglas mínimas a activar

En Cloudflare → Security → WAF:

| Regla | Acción | Motivo |
|---|---|---|
| OWASP Core Ruleset | Block | Protección contra SQLi, XSS, etc. |
| Cloudflare Managed Rules | Block | Exploits conocidos actualizados por Cloudflare |
| Rate limiting: API endpoints | Block tras 100 req/min por IP | Fuerza bruta y scraping |
| Rate limiting: Auth endpoints (`/v1/auth/*`) | Block tras 10 req/min por IP | Brute force de login |
| Bot Fight Mode | On | Bloquea bots maliciosos automáticamente |

### Turnstile — Captcha sin fricciones

Cloudflare Turnstile reemplaza reCAPTCHA. Es invisible para el usuario en la mayoría de casos y no tiene los problemas de privacidad de Google.

**Cuándo usarlo:**
- Formulario de login (si hay intentos de fuerza bruta en prod).
- Formulario de registro público.
- Formulario de contacto o cualquier endpoint público sin auth.

**Cuándo NO usarlo:**
- Endpoints autenticados (ya tienen Firebase Auth como barrera).
- Flujos internos (dashboard, operaciones de usuario logueado).

**Integración:**

```
1. Cloudflare Dashboard → Turnstile → Add Site → obtener site key + secret key
2. Site key: va en el frontend (NEXT_PUBLIC_TURNSTILE_SITE_KEY)
3. Secret key: va en el backend como secreto en Secret Manager
4. El frontend envía el token de Turnstile en el body del request
5. El backend verifica el token llamando a la API de Cloudflare antes de procesar
```

```typescript
// En el NestJS use case o guard que protege el endpoint público:
const verified = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
  method: 'POST',
  body: JSON.stringify({
    secret: process.env.TURNSTILE_SECRET_KEY,
    response: turnstileToken, // viene del cliente en el body
  }),
});
const { success } = await verified.json();
if (!success) throw new DomainError('captcha/invalid', 'Verificación fallida', 400);
```

### Reglas de Cloudflare

- Nunca desactivar el proxy (nube naranja) en registros de servicio — esto expone la IP de origen.
- El modo SSL debe ser siempre **Full (strict)**. `Flexible` crea una falsa sensación de seguridad.
- Turnstile solo en endpoints públicos que reciben tráfico no autenticado.
- Las reglas de WAF se configuran por dominio, no globalmente — staging puede tener reglas menos estrictas que prod.

---

## 4. Vercel — despliegue web

### Estructura de proyectos en Vercel

Se crea **un solo proyecto de Vercel** por aplicación web. Los entornos se manejan dentro del mismo proyecto con ramas y variables de entorno separadas.

```
Vercel Project: [app-name]
├── Production    → rama: main (o tag v*)   → [app].com
├── Preview       → rama: main (staging)    → staging.[app].com
└── Development   → ramas feature           → [hash].vercel.app
```

### Configuración de dominios en Vercel

1. Vercel → Project → Settings → Domains.
2. Agregar `[app].com` y `www.[app].com` para producción.
3. Agregar `staging.[app].com` como alias de la rama `main` (o la rama de staging).
4. Vercel provee los valores CNAME que se configuran en Cloudflare (ver sección 2).

### Variables de entorno en Vercel

En Vercel → Project → Settings → Environment Variables:

| Variable | Production | Preview | Development |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://api.[app].com` | `https://api-staging.[app].com` | `http://localhost:3001` |
| `NEXT_PUBLIC_APP_ENV` | `production` | `staging` | `development` |
| `NEXT_PUBLIC_FIREBASE_*` | proyecto firebase prod | proyecto firebase staging | proyecto firebase dev |
| `NEXT_PUBLIC_TURNSTILE_SITE_KEY` | site key prod | site key staging | site key test (bypass) |

**Turnstile en desarrollo:** Cloudflare provee site keys especiales para testing que siempre pasan la verificación. Usar esas en `dev` y `staging` para no bloquear el desarrollo.

### Deploy en Vercel

| Trigger | Entorno | Dominio |
|---|---|---|
| Push a rama feature | Preview (development) | `[hash]-[app].vercel.app` |
| Push a `main` | Preview (staging) | `staging.[app].com` |
| Tag `v*` o promoción manual | Production | `[app].com` |

---

## 5. Google Cloud Run — despliegue backend

### Estructura de servicios en GCP

Un proyecto GCP por entorno. Nunca compartir proyectos entre entornos.

```
GCP Project: [app]-staging
├── Cloud Run: backend-staging        → api-staging.[app].com
├── Cloud Run: ai-services-staging
├── Cloud Tasks: queues-staging
├── Secret Manager: secretos staging
└── Cloud Logging / Trace / Monitoring

GCP Project: [app]-prod
├── Cloud Run: backend-prod           → api.[app].com
├── Cloud Run: ai-services-prod
├── Cloud Tasks: queues-prod
├── Secret Manager: secretos prod
└── Cloud Logging / Trace / Monitoring
```

### Dominio custom en Cloud Run

Cloud Run no sirve directamente en el dominio custom. El tráfico llega vía Cloudflare:

```
Cliente → Cloudflare (api.[app].com) → Cloud Run URL interna
```

Para esto, en Cloud Run → Domain Mappings se mapea el subdominio al servicio, o se usa Cloudflare como proxy reverso apuntando a la URL pública de Cloud Run.

### Configuración mínima de Cloud Run

```yaml
# Por servicio, por entorno
service: backend-[entorno]
region: us-central1
min-instances: 0        # escala a cero en staging
min-instances: 1        # al menos 1 en prod (evita cold start en el primer request)
max-instances: 10       # staging
max-instances: 100      # prod (ajustar según carga)
memory: 512Mi           # staging
memory: 1Gi             # prod
cpu: 1
timeout: 60s
concurrency: 80
```

### Variables de entorno en Cloud Run

Las variables no sensibles se configuran directamente. Las sensibles se montan desde Secret Manager:

```bash
gcloud run deploy backend-prod \
  --set-env-vars NODE_ENV=production,PORT=8080,... \
  --set-secrets DATABASE_URL=database-url:latest,\
                FIREBASE_PRIVATE_KEY=firebase-private-key:latest,...
```

---

## 6. Permisos e IAM

### Principio: mínimo privilegio

Cada servicio tiene un Service Account dedicado con **solo los permisos que necesita**. Nunca usar la cuenta de Compute Engine por defecto ni dar `roles/editor` o `roles/owner` a servicios.

### Service Accounts por servicio

| Service Account | Permisos GCP | Propósito |
|---|---|---|
| `backend-sa@[app]-[env].iam.gserviceaccount.com` | Secret Manager Accessor, Cloud Tasks Enqueuer, Logging Writer, Trace Agent | NestJS backend |
| `ai-services-sa@[app]-[env].iam.gserviceaccount.com` | Secret Manager Accessor, Logging Writer, Trace Agent | FastAPI services |
| `github-deploy-sa@[app]-[env].iam.gserviceaccount.com` | Cloud Run Developer, Artifact Registry Writer, Secret Manager Accessor (solo lectura) | GitHub Actions deploy |

### Roles mínimos por servicio

**Backend NestJS:**
```
roles/secretmanager.secretAccessor    → leer secretos
roles/cloudtasks.enqueuer             → encolar tasks
roles/logging.logWriter               → escribir logs
roles/cloudtrace.agent                → enviar trazas
roles/storage.objectCreator           → (si sube a GCS, no R2)
```

**GitHub Actions (deploy):**
```
roles/run.developer                   → deployar en Cloud Run
roles/artifactregistry.writer         → subir imágenes Docker
roles/iam.serviceAccountUser          → impersonar el SA del servicio
```

### Autenticación de GitHub Actions con GCP

Usar **Workload Identity Federation** en lugar de claves JSON de service account. Es más seguro y las claves no se almacenan en GitHub Secrets.

```yaml
# En el workflow de GitHub Actions:
- uses: google-github-actions/auth@v2
  with:
    workload_identity_provider: 'projects/[PROJECT_NUMBER]/locations/global/workloadIdentityPools/github/providers/github'
    service_account: 'github-deploy-sa@[app]-prod.iam.gserviceaccount.com'
```

### GitHub Environments y Secrets

Crear dos environments en GitHub → Repository → Settings → Environments:

**Environment: `staging`**
- No requiere aprobación manual
- Secrets: variables de staging (URLs, project IDs, etc.)

**Environment: `prod`**
- Requiere aprobación de al menos 1 reviewer antes de ejecutar el deploy
- Secrets: variables de producción
- Solo puede ser triggered desde rama `main` o tags `v*`

---

## 7. CI/CD con GitHub Actions

### Estructura de workflows

```
.github/
└── workflows/
    ├── ci.yml              ← Tests y build en cada PR
    ├── deploy-staging.yml  ← Deploy a staging en push a main
    └── deploy-prod.yml     ← Deploy a prod en tag v*
```

---

### `ci.yml` — Validación en cada PR

Se ejecuta en cada pull request. No despliega nada.

```yaml
name: CI

on:
  pull_request:
    branches: [main]

jobs:
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: testdb
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci
        working-directory: ./backend

      - name: Run migrations on test DB
        run: npx prisma migrate deploy
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb

      - name: Run tests
        run: npm run test:ci
        working-directory: ./backend
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/testdb
          NODE_ENV: test

  test-web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
        working-directory: ./web
      - run: npm run type-check
        working-directory: ./web
      - run: npm run test:ci
        working-directory: ./web

  build-check:
    runs-on: ubuntu-latest
    needs: [test-backend, test-web]
    steps:
      - uses: actions/checkout@v4
      - name: Build backend Docker image (smoke test)
        run: docker build -t backend-test ./backend
```

---

### `deploy-staging.yml` — Deploy a staging en push a `main`

```yaml
name: Deploy Staging

on:
  push:
    branches: [main]

jobs:
  deploy-backend-staging:
    runs-on: ubuntu-latest
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER_STAGING }}
          service_account: ${{ secrets.DEPLOY_SA_STAGING }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker us-central1-docker.pkg.dev

      - name: Build and push backend image
        run: |
          docker build -t us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_STAGING }}/backend/nestjs:${{ github.sha }} ./backend
          docker push us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_STAGING }}/backend/nestjs:${{ github.sha }}

      - name: Run DB migrations
        run: |
          # Ejecutar migraciones usando Cloud Run Jobs o desde el contenedor
          gcloud run jobs execute migrate-staging \
            --region us-central1 \
            --wait

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy backend-staging \
            --image us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_STAGING }}/backend/nestjs:${{ github.sha }} \
            --region us-central1 \
            --platform managed \
            --service-account ${{ secrets.BACKEND_SA_STAGING }} \
            --set-env-vars NODE_ENV=staging,PORT=8080,GOOGLE_CLOUD_PROJECT=${{ secrets.GCP_PROJECT_STAGING }} \
            --set-secrets DATABASE_URL=database-url:latest,FIREBASE_PRIVATE_KEY=firebase-private-key:latest,REDIS_URL=redis-url:latest,R2_ACCESS_KEY_ID=r2-access-key:latest,R2_SECRET_ACCESS_KEY=r2-secret-key:latest \
            --min-instances 0 \
            --max-instances 10

  deploy-web-staging:
    runs-on: ubuntu-latest
    # Vercel despliega automáticamente en push a main via integración Git.
    # Este job solo verifica que el deploy de Vercel fue exitoso.
    steps:
      - name: Wait for Vercel staging deploy
        run: echo "Vercel deploys automatically via Git integration"
```

---

### `deploy-prod.yml` — Deploy a producción en tag `v*`

```yaml
name: Deploy Production

on:
  push:
    tags:
      - 'v*'   # v1.0.0, v1.2.3, etc.

jobs:
  deploy-backend-prod:
    runs-on: ubuntu-latest
    environment: prod   # ← requiere aprobación manual en GitHub

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER_PROD }}
          service_account: ${{ secrets.DEPLOY_SA_PROD }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker us-central1-docker.pkg.dev

      - name: Build and push backend image
        run: |
          docker build -t us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_PROD }}/backend/nestjs:${{ github.ref_name }} ./backend
          docker push us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_PROD }}/backend/nestjs:${{ github.ref_name }}

      - name: Run DB migrations
        run: |
          gcloud run jobs execute migrate-prod \
            --region us-central1 \
            --wait

      - name: Deploy to Cloud Run (with traffic split for safety)
        run: |
          # Deploy la nueva versión sin enviarle tráfico aún
          gcloud run deploy backend-prod \
            --image us-central1-docker.pkg.dev/${{ secrets.GCP_PROJECT_PROD }}/backend/nestjs:${{ github.ref_name }} \
            --region us-central1 \
            --platform managed \
            --service-account ${{ secrets.BACKEND_SA_PROD }} \
            --set-env-vars NODE_ENV=production,PORT=8080,GOOGLE_CLOUD_PROJECT=${{ secrets.GCP_PROJECT_PROD }} \
            --set-secrets DATABASE_URL=database-url:latest,FIREBASE_PRIVATE_KEY=firebase-private-key:latest,REDIS_URL=redis-url:latest,R2_ACCESS_KEY_ID=r2-access-key:latest,R2_SECRET_ACCESS_KEY=r2-secret-key:latest \
            --min-instances 1 \
            --max-instances 100 \
            --no-traffic   # ← no recibe tráfico todavía

      - name: Smoke test new revision
        run: |
          NEW_URL=$(gcloud run revisions describe $(gcloud run revisions list --service=backend-prod --region=us-central1 --format='value(name)' --limit=1) --region=us-central1 --format='value(status.url)')
          curl -f "$NEW_URL/health" || exit 1

      - name: Migrate traffic to new revision
        run: |
          gcloud run services update-traffic backend-prod \
            --to-latest \
            --region us-central1
```

---

### Secrets de GitHub Actions por environment

**Environment `staging`:**

| Secret | Descripción |
|---|---|
| `WIF_PROVIDER_STAGING` | Workload Identity Federation provider path |
| `DEPLOY_SA_STAGING` | Service account de deploy para staging |
| `GCP_PROJECT_STAGING` | ID del proyecto GCP de staging |
| `BACKEND_SA_STAGING` | Service account del backend en staging |

**Environment `prod`:**

| Secret | Descripción |
|---|---|
| `WIF_PROVIDER_PROD` | Workload Identity Federation provider path |
| `DEPLOY_SA_PROD` | Service account de deploy para prod |
| `GCP_PROJECT_PROD` | ID del proyecto GCP de prod |
| `BACKEND_SA_PROD` | Service account del backend en prod |

**Los secretos de las aplicaciones** (DATABASE_URL, FIREBASE_PRIVATE_KEY, etc.) viven en Google Secret Manager, no en GitHub. GitHub Actions solo tiene acceso a los secrets de infraestructura necesarios para hacer el deploy.

---

## 8. Rollback

### Backend (Cloud Run)

Cloud Run mantiene todas las revisiones desplegadas. El rollback es instantáneo:

```bash
# Ver revisiones disponibles
gcloud run revisions list --service=backend-prod --region=us-central1

# Enviar todo el tráfico a una revisión anterior
gcloud run services update-traffic backend-prod \
  --to-revisions=backend-prod-00042-xyz=100 \
  --region=us-central1
```

**En GitHub Actions (rollback manual):**
```yaml
# .github/workflows/rollback-prod.yml
name: Rollback Production

on:
  workflow_dispatch:
    inputs:
      revision:
        description: 'Cloud Run revision name to rollback to'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: prod
    steps:
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER_PROD }}
          service_account: ${{ secrets.DEPLOY_SA_PROD }}
      - uses: google-github-actions/setup-gcloud@v2
      - name: Rollback traffic
        run: |
          gcloud run services update-traffic backend-prod \
            --to-revisions=${{ inputs.revision }}=100 \
            --region=us-central1
```

### Web (Vercel)

Vercel mantiene historial de deployments. El rollback se hace desde el dashboard de Vercel → Deployments → seleccionar deployment anterior → Promote to Production. No requiere re-deploy.

### Base de datos

**No hay rollback automático de migraciones.** Las migraciones siguen el patrón expand/contract (ver `ARCHITECTURE_BACKEND.md` sección 10). Si una migración tiene un problema:

1. El código anterior sigue funcionando porque expand/contract garantiza compatibilidad hacia atrás.
2. Se hace rollback del código (Cloud Run o Vercel) a la revisión anterior.
3. La migración de contracción (eliminar columnas/tablas antiguas) se pospone hasta que el código nuevo sea estable.

**Regla:** nunca hacer una migración que rompa la versión anterior del código. Si es inevitable, el deploy del código y la migración deben ocurrir en la misma ventana de mantenimiento con monitoreo activo.

---

## 9. CI/CD Mobile — Android e iOS

### Herramientas

| Herramienta | Propósito | Costo |
|---|---|---|
| **Fastlane** | Build, signing, y distribución automática | Gratis, open source |
| **fastlane match** | Gestión de certificados y provisioning profiles iOS en un repositorio privado | Gratis |
| **GitHub Actions** | Runner del pipeline | Gratis para repos privados (límite de minutos mensuales) |
| **GitHub Actions macOS runner** | Requerido para builds de iOS | Consume minutos más rápido (10x vs Linux) |

> **Runners macOS:** GitHub incluye minutos gratuitos mensuales. iOS consume más minutos por ser macOS. En proyectos activos con muchos pushes, monitorear el consumo.

### Estructura de workflows

```
.github/
└── workflows/
    ├── ci-mobile.yml          ← Tests y análisis Flutter en cada PR
    ├── deploy-android.yml     ← Build AAB + Play Store internal track
    └── deploy-ios.yml         ← Build IPA + TestFlight
```

### Estructura de Fastlane en el repositorio

```
mobile/
└── fastlane/
    ├── Appfile              ← app_identifier, apple_id, package_name
    ├── Fastfile             ← lanes definidas (android, ios)
    ├── Matchfile            ← configuración de match para iOS
    └── Pluginfile           ← plugins si se necesitan
```

---

### `ci-mobile.yml` — Tests en cada PR

```yaml
name: CI Mobile

on:
  pull_request:
    branches: [main]
    paths:
      - 'mobile/**'

jobs:
  test-flutter:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.x'
          channel: 'stable'
          cache: true

      - name: Install dependencies
        run: flutter pub get
        working-directory: ./mobile

      - name: Analyze
        run: flutter analyze
        working-directory: ./mobile

      - name: Run tests
        run: flutter test --coverage
        working-directory: ./mobile
```

---

### `deploy-android.yml` — Build AAB + Play Store internal track

**Prerrequisitos:**
- App creada en Google Play Console con al menos un build manual subido previamente.
- Service account de Google Play con permiso "Release manager" en la app.
- Keystore de firma generado y almacenado en GitHub Secrets.

```yaml
name: Deploy Android

on:
  push:
    tags:
      - 'v*'   # mismo tag que dispara el deploy de backend/web
  workflow_dispatch:   # permite trigger manual

jobs:
  deploy-android:
    runs-on: ubuntu-latest
    environment: prod

    steps:
      - uses: actions/checkout@v4

      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.x'
          channel: 'stable'
          cache: true

      - name: Install dependencies
        run: flutter pub get
        working-directory: ./mobile

      - name: Setup Ruby for Fastlane
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.2'
          bundler-cache: true
          working-directory: ./mobile

      - name: Decode keystore
        run: |
          echo "${{ secrets.ANDROID_KEYSTORE_BASE64 }}" | base64 --decode > mobile/android/app/keystore.jks

      - name: Build AAB
        run: |
          flutter build appbundle --release \
            --dart-define=APP_ENV=production \
            --dart-define=API_URL=${{ secrets.PROD_API_URL }} \
            --dart-define=FIREBASE_PROJECT_ID=${{ secrets.FIREBASE_PROJECT_ID_PROD }}
        working-directory: ./mobile
        env:
          KEYSTORE_PATH: android/app/keystore.jks
          KEYSTORE_PASSWORD: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
          KEY_ALIAS: ${{ secrets.ANDROID_KEY_ALIAS }}
          KEY_PASSWORD: ${{ secrets.ANDROID_KEY_PASSWORD }}

      - name: Upload to Play Store (internal track)
        uses: r0adkll/upload-google-play@v1
        with:
          serviceAccountJsonPlainText: ${{ secrets.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON }}
          packageName: ${{ secrets.ANDROID_PACKAGE_NAME }}
          releaseFiles: mobile/build/app/outputs/bundle/release/app-release.aab
          track: internal
          status: completed
          changesNotSentForReview: false
```

**Secrets requeridos (environment `prod`):**

| Secret | Descripción |
|---|---|
| `ANDROID_KEYSTORE_BASE64` | Keystore `.jks` codificado en base64 (`base64 -i keystore.jks`) |
| `ANDROID_KEYSTORE_PASSWORD` | Password del keystore |
| `ANDROID_KEY_ALIAS` | Alias de la key dentro del keystore |
| `ANDROID_KEY_PASSWORD` | Password de la key |
| `ANDROID_PACKAGE_NAME` | Package name de la app (ej: `com.company.app`) |
| `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON` | JSON del service account de Google Play Console |

**Flujo después del workflow:**
```
GitHub Actions → Play Store internal track → Tú promueves a alpha/beta/prod desde Play Console
```

---

### `deploy-ios.yml` — Build IPA + TestFlight

**Prerrequisitos:**
- App creada en App Store Connect.
- Apple Developer account activa ($99/año — costo inevitable, no es de herramientas).
- Repositorio privado para `fastlane match` (puede ser otro repo GitHub privado).

```yaml
name: Deploy iOS

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  deploy-ios:
    runs-on: macos-latest   # ← iOS requiere macOS obligatoriamente
    environment: prod

    steps:
      - uses: actions/checkout@v4

      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.x'
          channel: 'stable'
          cache: true

      - name: Install dependencies
        run: flutter pub get
        working-directory: ./mobile

      - name: Setup Ruby for Fastlane
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.2'
          bundler-cache: true
          working-directory: ./mobile

      - name: Install Fastlane
        run: bundle install
        working-directory: ./mobile

      - name: Run Fastlane deploy iOS
        run: bundle exec fastlane ios deploy
        working-directory: ./mobile
        env:
          MATCH_PASSWORD: ${{ secrets.MATCH_PASSWORD }}
          MATCH_GIT_BASIC_AUTHORIZATION: ${{ secrets.MATCH_GIT_BASIC_AUTHORIZATION }}
          APP_STORE_CONNECT_API_KEY_ID: ${{ secrets.APP_STORE_CONNECT_API_KEY_ID }}
          APP_STORE_CONNECT_API_ISSUER_ID: ${{ secrets.APP_STORE_CONNECT_API_ISSUER_ID }}
          APP_STORE_CONNECT_API_KEY_CONTENT: ${{ secrets.APP_STORE_CONNECT_API_KEY_CONTENT }}
          FLUTTER_DART_DEFINES: "APP_ENV=production,API_URL=${{ secrets.PROD_API_URL }},FIREBASE_PROJECT_ID=${{ secrets.FIREBASE_PROJECT_ID_PROD }}"
```

**`mobile/fastlane/Fastfile` — lane de iOS:**

```ruby
default_platform(:ios)

platform :ios do
  desc "Build y subir a TestFlight"
  lane :deploy do
    # Sincronizar certificados y provisioning profiles desde el repo de match
    match(
      type: "appstore",
      readonly: true,
      app_identifier: ENV["IOS_BUNDLE_ID"]
    )

    # Incrementar build number automáticamente
    increment_build_number(
      build_number: ENV["GITHUB_RUN_NUMBER"],
      xcodeproj: "Runner.xcodeproj"
    )

    # Build Flutter (genera el .xcarchive)
    sh("flutter build ipa --release " \
       "--dart-define=APP_ENV=production " \
       "--dart-define=API_URL=#{ENV['PROD_API_URL']} " \
       "--dart-define=FIREBASE_PROJECT_ID=#{ENV['FIREBASE_PROJECT_ID_PROD']}")

    # Subir a TestFlight
    upload_to_testflight(
      api_key_path: nil,
      api_key: {
        key_id: ENV["APP_STORE_CONNECT_API_KEY_ID"],
        issuer_id: ENV["APP_STORE_CONNECT_API_ISSUER_ID"],
        key_content: ENV["APP_STORE_CONNECT_API_KEY_CONTENT"],
        is_key_content_base64: true
      },
      ipa: "../build/ios/ipa/*.ipa",
      skip_waiting_for_build_processing: true   # no espera — el agente no se bloquea
    )
  end
end
```

**`mobile/fastlane/Matchfile` — configuración de certificados:**

```ruby
git_url("https://github.com/[org]/[app]-certificates")   # repo privado solo para certs
storage_mode("git")
type("appstore")
app_identifier(["com.company.app"])
username("")   # vacío — se usa App Store Connect API key
```

**Secrets requeridos (environment `prod`):**

| Secret | Descripción |
|---|---|
| `MATCH_PASSWORD` | Password para encriptar/desencriptar certs en el repo de match |
| `MATCH_GIT_BASIC_AUTHORIZATION` | Token base64 para acceder al repo privado de certs (`echo -n "user:token" \| base64`) |
| `APP_STORE_CONNECT_API_KEY_ID` | Key ID de la API key de App Store Connect |
| `APP_STORE_CONNECT_API_ISSUER_ID` | Issuer ID de App Store Connect |
| `APP_STORE_CONNECT_API_KEY_CONTENT` | Contenido del archivo `.p8` codificado en base64 |
| `IOS_BUNDLE_ID` | Bundle identifier de la app (ej: `com.company.app`) |

**Flujo después del workflow:**
```
GitHub Actions → TestFlight (build disponible) → Tú invitas testers o promueves a App Store desde App Store Connect
```

---

### Repositorio privado para `fastlane match`

`fastlane match` almacena los certificados de iOS y provisioning profiles **encriptados** en un repositorio Git privado. Esto evita que cada desarrollador tenga que gestionar certificados manualmente.

```
[app]-certificates (repo privado)
├── certs/
│   └── distribution/     ← certificados .cer y .p12 (encriptados)
└── profiles/
    └── appstore/          ← provisioning profiles .mobileprovision (encriptados)
```

**Crear el repo de match:**
```bash
cd mobile
bundle exec fastlane match init
# → ingresa la URL del repo privado de certificados
# → ingresa el MATCH_PASSWORD (guárdalo en Secret Manager y en GitHub Secrets)

bundle exec fastlane match appstore
# → genera certificados y profiles, los sube encriptados al repo
```

**Regla:** el repo de certificados nunca es el mismo repo que el código. Es un repo separado, privado, con acceso restringido.

---

### Versionado de la app mobile

El build number se incrementa automáticamente usando `GITHUB_RUN_NUMBER` (número incremental de GitHub Actions). El version name (`1.0.0`) se controla en:
- Android: `mobile/pubspec.yaml` → campo `version: 1.0.0+1` (la parte antes de `+` es el version name)
- iOS: usa el mismo `pubspec.yaml` vía Flutter

**Para hacer un release:**
1. Actualizar `version` en `pubspec.yaml` (ej: `1.1.0+1`).
2. Crear tag `v1.1.0` en Git.
3. Los workflows de Android e iOS se disparan automáticamente.

---

## 10. Checklist de infraestructura nueva

### Dominio y DNS
- [ ] Dominio comprado en Squarespace
- [ ] Nameservers de Squarespace apuntando a Cloudflare
- [ ] Dominio activo en Cloudflare (estado: Active)
- [ ] Registros CNAME creados para web (Vercel) y API (Cloud Run)
- [ ] SSL/TLS en modo Full (strict)
- [ ] Always Use HTTPS activado
- [ ] HTTPS Rewrites automáticos activados

### Cloudflare seguridad
- [ ] OWASP Core Ruleset activado en WAF
- [ ] Cloudflare Managed Rules activado
- [ ] Rate limiting configurado para `/v1/auth/*` (10 req/min por IP)
- [ ] Rate limiting configurado para API general (100 req/min por IP)
- [ ] Bot Fight Mode activado
- [ ] Turnstile site creado (site key + secret key obtenidos)

### GCP
- [ ] Proyecto GCP staging creado (`[app]-staging`)
- [ ] Proyecto GCP prod creado (`[app]-prod`)
- [ ] Artifact Registry habilitado en ambos proyectos
- [ ] Service Accounts creados con roles mínimos (sección 6)
- [ ] Workload Identity Federation configurado para GitHub Actions
- [ ] Secret Manager habilitado, secretos creados en ambos proyectos
- [ ] Cloud Tasks queues creados en ambos proyectos
- [ ] Cloud Run servicios configurados con los SA correctos

### Vercel
- [ ] Proyecto Vercel creado y conectado al repositorio GitHub
- [ ] Dominio custom agregado (prod y staging)
- [ ] Variables de entorno configuradas por environment (Production / Preview)
- [ ] Vercel despliega correctamente en push a `main`

### GitHub Actions
- [ ] Environment `staging` creado sin aprobación requerida
- [ ] Environment `prod` creado con aprobación requerida (1+ reviewer)
- [ ] Secrets de staging configurados en environment `staging`
- [ ] Secrets de prod configurados en environment `prod`
- [ ] Workflow `ci.yml` pasa en un PR de prueba
- [ ] Workflow `deploy-staging.yml` despliega correctamente en push a `main`
- [ ] Workflow `deploy-prod.yml` requiere aprobación y despliega en tag `v*`
- [ ] Workflow `rollback-prod.yml` funciona con `workflow_dispatch`

### Mobile — Android
- [ ] App creada en Google Play Console con primer build manual subido
- [ ] Keystore de firma generado y guardado de forma segura (no en el repo)
- [ ] Keystore codificado en base64 y almacenado en GitHub Secret `ANDROID_KEYSTORE_BASE64`
- [ ] Service account de Google Play Console creado con permiso "Release manager"
- [ ] JSON del service account almacenado en GitHub Secret `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
- [ ] Secrets de Android configurados en environment `prod` de GitHub
- [ ] Workflow `deploy-android.yml` construye AAB correctamente
- [ ] Build sube al internal track de Play Store sin errores

### Mobile — iOS
- [ ] App creada en App Store Connect
- [ ] Apple Developer account activa ($99/año)
- [ ] Repositorio privado de certificados creado (`[app]-certificates`)
- [ ] `fastlane match init` ejecutado y repo configurado en `Matchfile`
- [ ] `fastlane match appstore` ejecutado — certificados y profiles generados y subidos al repo
- [ ] `MATCH_PASSWORD` guardado en Secret Manager y en GitHub Secret
- [ ] App Store Connect API key creada (tipo "App Manager")
- [ ] Secrets de iOS configurados en environment `prod` de GitHub
- [ ] Workflow `deploy-ios.yml` construye IPA correctamente
- [ ] Build aparece en TestFlight sin errores

### Validación end-to-end
- [ ] `https://[app].com` carga correctamente con HTTPS
- [ ] `https://api.[app].com/health` responde 200
- [ ] `https://staging.[app].com` carga correctamente
- [ ] `https://api-staging.[app].com/health` responde 200
- [ ] Turnstile funciona en formulario de login en producción
- [ ] Deploy de staging se activa automáticamente en push a `main`
- [ ] Deploy de prod requiere aprobación manual antes de ejecutarse
- [ ] Rollback de prod funciona correctamente
- [ ] Tag `v*` dispara deploy de Android e iOS simultáneamente
- [ ] AAB aparece en Play Store internal track
- [ ] IPA aparece en TestFlight

---

*Versión: 1.1 — Marzo 2026*
*Complementa `ARCHITECTURE.md`. Lee ese documento primero para el contexto del sistema completo.*
