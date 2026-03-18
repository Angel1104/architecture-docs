# ARCHITECTURE — Mobile (Flutter)

> **Documento para agentes de IA.**
> Lee `ARCHITECTURE.md` primero para entender el sistema completo. Este documento cubre exclusivamente la capa mobile: Flutter.
> Todas las decisiones están tomadas. Sigue este documento como fuente de verdad al scaffoldear o extender la aplicación mobile. No improvises estructura ni cambies naming sin justificación.

---

## Stack de esta capa

| Componente | Tecnología |
|---|---|
| Framework | Flutter (Dart) |
| Target | iOS + Android (compilado a ARM nativo) |
| HTTP client | Dio |
| Estado | Riverpod (StateNotifier / AsyncNotifier) |
| Navegación | GoRouter |
| Modelos | freezed + json_serializable |
| Auth cliente | Firebase Authentication (firebase_auth) |
| Push notifications | firebase_messaging |
| Permisos | permission_handler |

---

## 1. Responsabilidad y scope

> Flutter compila a código ARM nativo. Es cross-platform, **no "no nativa"**. Esta distinción es importante al comunicar con clientes y stakeholders.

Flutter cubre: aplicación mobile principal, autenticación mobile, pantallas operativas, consumo del backend compartido, flujos de carga y descarga de archivos.

**Lo que la capa mobile NO hace:**
- Contener lógica de negocio (eso es el backend NestJS).
- Validar tokens Firebase server-side para autorización de negocio (eso es NestJS).
- Comunicarse directamente con Neon, Redis o cualquier base de datos.
- Gestionar archivos directamente (la subida va a R2 vía URLs firmadas que entrega NestJS).

---

## 2. Flujo de datos

```mermaid
flowchart LR
    Screen["Screen\n(presentation/)"] --> Controller["Controller\nStateNotifier"]
    Controller --> UseCase["Use Case\n(domain/)"]
    UseCase --> Repo["Repository\nAbstract"]
    Repo --> DS["Remote DataSource\n(data/)"]
    DS --> Client["ApiClient\nDio"]
    Client -->|"Bearer token\nX-Trace-ID"| Backend["Backend\n/v1/"]
```

---

## 3. Clean architecture — capas

### Regla de dependencia

```
presentation/ → domain/ ← data/
```

- `domain/` no tiene dependencias externas. Solo Dart puro.
- `data/` implementa los contratos de `domain/`.
- `presentation/` consume `domain/` via use cases.

### Responsabilidad de cada capa

| Capa | Vive en | Contiene |
|---|---|---|
| Domain | `features/[nombre]/domain/` | Entidades puras, repositorios abstractos, use cases |
| Data | `features/[nombre]/data/` | Modelos JSON (freezed), datasources remotos, implementaciones de repositorios |
| Presentation | `features/[nombre]/presentation/` | Controllers (StateNotifier), screens, widgets propios de la feature |

---

## 4. Estructura de carpetas

```
lib/
├── core/                   ← Infraestructura base de la app
│   ├── network/            ← ApiClient (Dio), interceptores, endpoints
│   ├── auth/               ← AuthService, almacenamiento de token
│   ├── errors/             ← Tipos de error sellados (sealed class)
│   ├── config/             ← Variables de entorno, constantes
│   └── utils/              ← Extensions, formatters
│
├── ui/                     ← Librería de componentes reutilizables
│   ├── primitives/         ← AppButton, AppInput, AppCard, AppText
│   ├── components/         ← EmptyState, ErrorView, LoadingOverlay, PageHeader
│   └── layouts/            ← ScaffoldWithNav, AuthLayout
│
├── theme/                  ← Motor de tema. Ver sección 9.
│
├── app/                    ← Bootstrap de la aplicación
│   ├── router/             ← GoRouter: rutas y guards de navegación
│   ├── providers/          ← Riverpod ProviderScope, registro de providers
│   └── bootstrap/          ← Inicialización de servicios al arrancar
│
├── features/               ← Una carpeta por dominio del producto
│   ├── auth/
│   │   ├── data/
│   │   │   ├── datasources/    ← Llamadas HTTP concretas
│   │   │   ├── models/         ← Modelos JSON (freezed)
│   │   │   └── repositories/   ← Implementación del repositorio
│   │   ├── domain/
│   │   │   ├── entities/       ← Entidades puras sin dependencias externas
│   │   │   ├── repositories/   ← Contrato abstracto del repositorio
│   │   │   └── usecases/       ← Un caso de uso por acción de negocio
│   │   └── presentation/
│   │       ├── controllers/    ← StateNotifier de Riverpod
│   │       ├── screens/        ← Pantallas completas
│   │       └── widgets/        ← Widgets propios de esta feature
│   ├── home/
│   ├── profile/
│   └── files/
│
└── main.dart
```

---

## 5. Reglas de la capa mobile

- Ninguna screen llama a HTTP directamente. El flujo siempre es: screen → controller → use case → repository → datasource → ApiClient.
- Ningún widget de feature usa colores, spacing o radios con valores literales.
- El tema siempre pasa por `ThemeData`, `ColorScheme` y extensiones propias. Nunca valores directos de color.
- Los controllers son `StateNotifier` de Riverpod. No hay `setState` para estado de negocio.
- Los repositorios son abstracciones (`abstract class`). Las implementaciones viven en `data/repositories/`.
- Cada use case tiene un único método público `execute()`.

---

## 6. ApiClient — contrato (Dio)

`core/network/` contiene el ApiClient basado en Dio. Es el único punto de salida HTTP de toda la aplicación mobile.

**Responsabilidades del ApiClient:**
- Adjuntar el Bearer token de Firebase en el header `Authorization`.
- Generar y adjuntar un UUID como `X-Trace-ID` en cada request.
- Manejar errores HTTP y transformarlos en errores tipados (`sealed class` en `core/errors/`).
- Interceptar 401 para refrescar token y reintentar.

**Estructura de interceptores Dio:**
```dart
// core/network/interceptors/auth_interceptor.dart
// Agrega Authorization: Bearer [token] a cada request

// core/network/interceptors/trace_interceptor.dart
// Agrega X-Trace-ID: [uuid] a cada request
```

**Cómo obtener el token:**
```dart
import 'package:firebase_auth/firebase_auth.dart';

final token = await FirebaseAuth.instance.currentUser?.getIdToken();
```

**Regla de retry en 401:**
1. Interceptar el 401.
2. Llamar `getIdToken(forceRefresh: true)`.
3. Reintentar el request original una vez.
4. Si vuelve a fallar, emitir un evento de logout.

---

## 7. Auth — perspectiva mobile

### Responsabilidad del cliente mobile

La capa mobile solo gestiona la identidad del usuario en el cliente:
- Inicializar el Firebase client SDK.
- Manejar el estado de sesión (login, logout, estado de carga inicial).
- Obtener y refrescar el token para adjuntarlo en cada request.

**La capa mobile NO valida tokens. NO toma decisiones de autorización de negocio.** Eso es responsabilidad del backend NestJS (ver `ARCHITECTURE_BACKEND.md` sección 7).

### Flujo en el cliente mobile

1. Usuario hace login → Firebase emite JWT.
2. El `AuthService` en `core/auth/` observa `FirebaseAuth.instance.authStateChanges()`.
3. El interceptor de Dio llama `getIdToken()` antes de cada request.
4. Si el backend responde 401, el interceptor intenta `getIdToken(forceRefresh: true)` y reintenta. Si vuelve a fallar, emite logout.

### Inicialización Firebase (mobile)

```dart
// app/bootstrap/app_bootstrap.dart
import 'package:firebase_core/firebase_core.dart';

await Firebase.initializeApp(
  options: DefaultFirebaseOptions.currentPlatform,
);
```

---

## 8. Manejo de errores — cliente mobile

### Principio

Los errores del backend llegan en formato RFC 7807 (ver `ARCHITECTURE_BACKEND.md` sección 6). El ApiClient los parsea en una clase sellada `AppError`. Los controllers los propagan al estado. Las screens los muestran.

### Tipo `AppError` (sealed class)

```dart
// core/errors/app_error.dart
sealed class AppError {
  const AppError();
}

// Error de dominio del backend: 4xx con código estable
class DomainError extends AppError {
  final String type;    // código estable: 'user/not-found'
  final String title;   // se muestra al usuario
  final int status;
  final String detail;
  final String traceId;
  final List<FieldError> fieldErrors; // solo en 422
  const DomainError({...});
}

// Error de red o infraestructura: 5xx, timeout, sin conexión
class NetworkError extends AppError {
  final String? traceId; // puede no existir si no hubo respuesta
  final bool isOffline;
  const NetworkError({this.traceId, this.isOffline = false});
}

// Error no esperado: para bugs, no para mostrar al usuario
class UnknownError extends AppError {
  final Object cause;
  const UnknownError(this.cause);
}
```

### Reglas de manejo de errores

- El ApiClient captura todas las `DioException` y las convierte en `AppError`. Las screens nunca ven `DioException` ni `Exception` crudos.
- Los controllers propagan `AppError` en el estado (nunca hacen `catch` silencioso).
- Las screens muestran solo `error.title` o `error.detail` del `DomainError`. Nunca el `type` ni el stack trace.
- Los errores `NetworkError` con `isOffline: true` muestran un banner/snackbar de "Sin conexión". Ver sección 9.
- Los errores 5xx muestran un mensaje genérico con el `traceId` visible para que el usuario pueda reportarlo.
- Los errores de validación (422 con `fieldErrors`) se mapean a los campos del formulario correspondiente.

---

## 9. Offline y conectividad

### Postura: online-first, sin persistencia local por defecto

La app es **online-first**. No hay caché local persistente ni sincronización offline en v1. La postura debe declararse explícitamente para que no se añada sin criterio.

**Lo que SÍ se hace:**
- Detectar estado de red con `connectivity_plus`.
- Mostrar un banner de "Sin conexión" cuando no hay red, antes de intentar llamadas HTTP.
- Deshabilitar acciones que requieren red cuando está offline (botones de guardar, enviar).

**Lo que NO se hace en v1:**
- Persistencia local con Hive, sqflite, Drift, Isar ni ningún otro.
- Cola de operaciones offline para sincronizar cuando vuelva la conexión.
- Caché de datos para lectura offline.

Si un proyecto necesita soporte offline real, debe documentarlo explícitamente en un ADR antes de añadir cualquier dependencia de persistencia local.

### Optimistic updates

**No se usan optimistic updates por defecto.** Son complejos de revertir correctamente y crean inconsistencias si el backend falla.

La excepción permitida es para acciones de UI de baja consecuencia donde el fallo es extremadamente raro (ej: marcar un ítem como favorito). En ese caso:

1. Actualiza el estado local inmediatamente.
2. Llama al backend.
3. Si falla: revierte el estado local y muestra un snackbar de error.
4. El caso de revert debe estar implementado antes de activar el optimistic update.

Si no se implementa el revert, no se hace optimistic update.

---

## 10. Estado — Riverpod

### Patrones establecidos

| Caso de uso | Pattern |
|---|---|
| Estado async (loading/data/error) | `AsyncNotifier` |
| Estado de negocio con acciones | `StateNotifier` |
| Estado derivado (computed) | `Provider` / `FutureProvider` |
| Estado de UI puro (ej: toggle) | `StateProvider` (solo para UI local) |

### Reglas de Riverpod

- Todo estado de negocio vive en Riverpod. No hay `setState` para estado de negocio.
- `setState` solo para estado de UI puramente local y efímero (ej: animaciones, focus).
- Registra todos los providers en `app/providers/app_providers.dart`.
- Los controllers solo consumen use cases del dominio. No llaman datasources directamente.

### Ejemplo de estructura de un provider

```dart
// features/auth/presentation/controllers/auth_controller.dart
class AuthController extends StateNotifier<AuthState> {
  final LoginUseCase _loginUseCase;

  AuthController(this._loginUseCase) : super(const AuthState.initial());

  Future<void> login(String email, String password) async {
    state = const AuthState.loading();
    final result = await _loginUseCase.execute(LoginParams(email, password));
    state = result.fold(
      (error) => AuthState.error(error),
      (user) => AuthState.authenticated(user),
    );
  }
}
```

---

## 11. Navegación — GoRouter

### Estructura

Las rutas viven en `app/router/app_router.dart`. Los guards de autenticación redirigen según el estado de auth.

### Reglas de navegación

- Todas las rutas están definidas en `app_router.dart`. No hay navegación ad-hoc con `Navigator.push` en features.
- El guard de auth observa el stream de `AuthService` para redirigir automáticamente.
- Los deep links se registran en `app_router.dart`.

### Ejemplo de guard de auth

```dart
redirect: (context, state) {
  final isAuthenticated = ref.read(authServiceProvider).isAuthenticated;
  final isGoingToAuth = state.matchedLocation.startsWith('/auth');

  if (!isAuthenticated && !isGoingToAuth) return '/auth/login';
  if (isAuthenticated && isGoingToAuth) return '/home';
  return null;
},
```

---

## 12. Theme architecture — Flutter

### Jerarquía de tokens

Los tokens siguen tres niveles: Core → Semantic → Component (ver diagrama en `ARCHITECTURE.md` sección 7).

Para Flutter, los semantic tokens se implementan como extensiones de `ThemeData`.

### Estructura de carpetas del tema (Flutter)

```
theme/
├── tokens/
│   ├── core.dart             ← Primitivos: paleta completa, escala de spacing, radios, tipografía
│   ├── semantic.light.dart   ← Roles semánticos para modo claro
│   └── semantic.dark.dart    ← Roles semánticos para modo oscuro
│
└── flutter/
    ├── color_scheme.dart   ← ColorScheme generado desde semantic tokens
    ├── text_theme.dart     ← TextTheme generado desde semantic tokens
    ├── extensions.dart     ← AppColorsExtension, AppTextExtension
    └── app_theme.dart      ← ThemeData completo: light + dark
```

### Cómo consumir el tema en un widget

```dart
// ✅ Correcto — usa extensión del tema
final colors = Theme.of(context).extension<AppColors>()!;
Container(color: colors.backgroundPrimary)

// ❌ Incorrecto — valor literal
Container(color: Colors.white)
Container(color: Color(0xFFFFFFFF))
```

### Semantic tokens mínimos requeridos

| Categoría | Tokens mínimos |
|---|---|
| Background | `backgroundPrimary`, `backgroundSecondary`, `backgroundTertiary` |
| Surface | `surfaceDefault`, `surfaceRaised`, `surfaceOverlay` |
| Text | `textPrimary`, `textSecondary`, `textDisabled`, `textInverse` |
| Border | `borderDefault`, `borderStrong`, `borderFocus` |
| Brand | `brandPrimary`, `brandPrimaryHover`, `brandPrimaryActive` |
| Status | `statusSuccess`, `statusWarning`, `statusError`, `statusInfo` |

### Reglas del tema Flutter

- Nunca usar `Colors.blue` ni valores literales de color en features.
- Nunca usar valores numéricos de color directos (`Color(0xFF...)`).
- Siempre usar `Theme.of(context).extension<AppColors>()` para colores.
- Siempre usar `Theme.of(context).textTheme` para tipografía.
- El tema soporta modo claro y oscuro via `ThemeData.light()` y `ThemeData.dark()`.

---

## 13. Splash screen e inicialización

### El problema

Entre que la app arranca y `authStateChanges()` emite el primer valor, hay un gap de ~300-500ms donde el estado de auth es desconocido. Sin manejo explícito, GoRouter redirige al usuario a `/auth/login` aunque ya estuviera autenticado — produciendo un flash visible.

### Solución fijada: estado de inicialización explícito

El `AuthService` expone tres estados distintos, no dos:

```dart
// core/auth/auth_state.dart
enum AppAuthState {
  initializing,   // Firebase aún no ha emitido el primer valor
  authenticated,  // Usuario autenticado
  unauthenticated // Usuario no autenticado (sabemos con certeza)
}
```

El guard de GoRouter solo redirige cuando el estado NO es `initializing`:

```dart
// app/router/app_router.dart
redirect: (context, state) {
  final authState = ref.read(authServiceProvider).state;

  // Mientras inicializa: no redirigir, mostrar splash
  if (authState == AppAuthState.initializing) return '/splash';

  final isAuthenticated = authState == AppAuthState.authenticated;
  final isGoingToAuth = state.matchedLocation.startsWith('/auth');
  final isOnSplash = state.matchedLocation == '/splash';

  if (!isAuthenticated && !isGoingToAuth) return '/auth/login';
  if (isAuthenticated && (isGoingToAuth || isOnSplash)) return '/home';
  return null;
},
```

### Pantalla splash

La pantalla `/splash` muestra el logo y un indicador de carga mínimo. Su único trabajo es existir mientras `authStateChanges()` no ha emitido. En cuanto el estado cambia de `initializing`, GoRouter redirige automáticamente.

```dart
// features/splash/presentation/screens/splash_screen.dart
class SplashScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(child: AppLogo()), // sin lógica, solo visual
    );
  }
}
```

### Secuencia de arranque en bootstrap

```dart
// app/bootstrap/app_bootstrap.dart
Future<void> bootstrap() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 1. Firebase primero — todo lo demás depende de esto
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  // 2. Servicios que no dependen de auth
  await _initServices();

  // 3. Arrancar la app — el AuthService escucha authStateChanges internamente
  runApp(ProviderScope(child: AppWidget()));
}
```

### Reglas de inicialización

- Nunca navegar desde el splash programáticamente. El guard de GoRouter maneja la redirección.
- El estado `initializing` nunca persiste más de 3 segundos. Si Firebase tarda más, asumir error de conectividad y mostrar `NetworkError`.
- La pantalla splash no tiene providers de negocio ni hace llamadas HTTP.

---

## 14. Permisos de plataforma

### Librería fijada: `permission_handler`

Todos los permisos del sistema se gestionan con `permission_handler`. No se usan APIs nativas directamente.

### Permisos comunes y cuándo pedirlos

| Permiso | Cuándo pedirlo |
|---|---|
| Notificaciones push | Al primer login exitoso, explicando el valor antes de pedir |
| Cámara | Justo antes de abrir la cámara, no al arrancar la app |
| Galería (fotos) | Justo antes de abrir el selector de imágenes |
| Almacenamiento (Android <13) | Justo antes de descargar un archivo |

**Regla fundamental:** Nunca pedir permisos al arrancar la app. Se piden en el momento en que el usuario intenta usar la funcionalidad que los requiere (just-in-time).

### Patrón estándar para pedir un permiso

```dart
// core/utils/permission_utils.dart
Future<bool> requestCameraPermission() async {
  final status = await Permission.camera.status;

  if (status.isGranted) return true;

  if (status.isPermanentlyDenied) {
    // El usuario denegó permanentemente — dirigir a Settings
    await openAppSettings();
    return false;
  }

  final result = await Permission.camera.request();
  return result.isGranted;
}
```

### Manejo de permiso denegado permanentemente

Si el usuario denegó un permiso permanentemente, **no mostrar el dialog del sistema** (ya no aparece). En su lugar:

1. Mostrar un bottom sheet explicando por qué se necesita el permiso.
2. Ofrecer un botón "Abrir configuración" que llama `openAppSettings()`.
3. No bloquear el flujo del usuario — el feature simplemente no está disponible.

### Notificaciones push

Las notificaciones push requieren configuración adicional:
- iOS: `firebase_messaging` necesita la entitlement `APS Environment` en el perfil de provisioning.
- Android: el `google-services.json` ya incluye la config necesaria.
- El token FCM se obtiene con `FirebaseMessaging.instance.getToken()` y se envía al backend para guardarlo asociado al usuario.

### Reglas de permisos

- Nunca asumir que un permiso está concedido. Siempre verificar antes de usarlo.
- Los permisos se solicitan desde el use case o el controller, nunca desde un widget directamente.
- Si el permiso es denegado, el controller emite un estado de error tipado que la screen muestra. No hay lógica de permisos en las screens.

---

## 15. Variables de entorno — mobile (dart-define)

### Regla fundamental

**Nunca incluir secretos en la aplicación mobile.** Todo lo que va en el APK/IPA es visible para cualquiera que decomple el binario.

### Cómo pasar configuración al app

Usar `--dart-define` en tiempo de compilación:

```bash
flutter run \
  --dart-define=API_URL=https://api.example.com \
  --dart-define=FIREBASE_PROJECT_ID=my-project
```

### Variables de configuración de la app

| Variable | Tipo | Descripción |
|---|---|---|
| `API_URL` | Público | URL base del backend NestJS |
| `FIREBASE_PROJECT_ID` | Público | ID del proyecto Firebase |
| `APP_ENV` | Público | `production` / `staging` / `development` |

**Regla:** Las credenciales de Firebase (google-services.json / GoogleService-Info.plist) se tratan como configuración de plataforma, no como secretos — pero tampoco se commitean con valores de producción. Usa archivos distintos por entorno.

### Acceso en código

```dart
// core/config/app_config.dart
class AppConfig {
  static const apiUrl = String.fromEnvironment('API_URL');
  static const firebaseProjectId = String.fromEnvironment('FIREBASE_PROJECT_ID');
  static const appEnv = String.fromEnvironment('APP_ENV', defaultValue: 'development');
}
```

---

## 16. Testing strategy — mobile

### Postura

El testing en Flutter sigue tres niveles nativos del framework. No se mockean las implementaciones de repositorios concretos en tests de use cases — se usan implementaciones fake que implementan el mismo contrato abstracto.

### Capas y herramientas

| Qué testear | Herramienta | Tipo |
|---|---|---|
| Use cases y lógica de dominio | `flutter_test` | Unitario |
| Controllers (StateNotifier) con repositorios fake | `flutter_test` + `mocktail` | Unitario |
| Widgets de features y flujos de pantalla | `flutter_test` (widget tests) | Integración |
| Flujos críticos end-to-end | `integration_test` + `patrol` | E2E |

### Reglas de testing

- Los tests de use cases usan implementaciones `Fake` del repositorio abstracto (clase que extiende el abstract), no mocks de Mockito/mocktail. Esto garantiza que la implementación fake implementa el mismo contrato.
- Los tests de controllers usan `mocktail` para los use cases. Son tests unitarios rápidos.
- Los tests de widget prueban el flujo visible: estados de loading, data y error de cada pantalla.
- Los tests E2E con `patrol` cubren solo los flujos críticos: login, el happy path principal, y el flujo de cámara/archivos si aplica.
- Los tests viven junto a su código: `features/auth/domain/usecases/login_usecase_test.dart`.
- Nunca se mockea el `ApiClient` de Dio directamente. Si un test necesita simular HTTP, usa un repositorio fake.

---

## 17. Instrucciones para agentes — crear nueva feature Flutter

1. Crea `lib/features/[nombre]/` con: `data/`, `domain/`, `presentation/`.
2. En `domain/`: crea la entidad, el abstract del repositorio y los use cases.
3. En `data/`: crea el modelo con freezed, el datasource remoto y la implementación del repositorio.
4. En `presentation/`: crea el controller (StateNotifier), las screens y los widgets.
5. Registra los providers en `app/providers/app_providers.dart`.
6. Agrega las rutas en `app/router/app_router.dart`.

---

## 18. Instrucciones para agentes — proyecto nuevo (mobile)

1. Crea la estructura de carpetas exacta definida en la sección 4.
2. Instala dependencias base: flutter, riverpod, dio, go_router, firebase_core, firebase_auth, firebase_messaging, freezed, json_serializable, connectivity_plus, permission_handler.
3. Instala dependencias de testing: flutter_test (incluido), mocktail, integration_test, patrol.
4. Crea el `AppAuthState` enum en `core/auth/auth_state.dart` con los tres estados: `initializing`, `authenticated`, `unauthenticated`.
5. Implementa el `AuthService` en `core/auth/` con `authStateChanges()` y estado `initializing` inicial.
6. Crea la pantalla `SplashScreen` en `features/splash/`.
7. Configura GoRouter con guard que respeta el estado `initializing` (sección 13).
8. Inicializa Firebase en `app/bootstrap/app_bootstrap.dart` con la secuencia correcta.
9. Crea el `ApiClient` base en `core/network/` con los interceptores de auth, trace y parseo de errores a `AppError`.
10. Crea la `sealed class AppError` en `core/errors/app_error.dart`.
11. Configura el `ConnectivityService` en `core/network/` para detectar estado de red.
12. Crea la estructura de tema base en `theme/` con los semantic tokens mínimos de la sección 12.
13. Verifica que ningún componente base tiene colores o valores hardcodeados.

---

## 19. Checklist de proyecto nuevo — mobile

### Estructura
- [ ] Estructura exacta de carpetas creada
- [ ] Dependencias base instaladas (riverpod, dio, go_router, firebase_core, firebase_auth, freezed)
- [ ] `analysis_options.yaml` configurado con lints estrictos
- [ ] `.gitignore` configurado (build, .dart_tool, google-services.json de prod)

### Inicialización y splash
- [ ] `AppAuthState` enum con tres estados (`initializing`, `authenticated`, `unauthenticated`)
- [ ] `SplashScreen` creada en `features/splash/`
- [ ] Guard de GoRouter respeta estado `initializing` (no redirige hasta que Firebase emite)
- [ ] No hay flash de login screen cuando el usuario ya estaba autenticado
- [ ] Bootstrap inicializa Firebase antes de `runApp`

### Auth
- [ ] Firebase project configurado para iOS y Android
- [ ] Firebase inicializado en bootstrap
- [ ] `AuthService` implementado con `authStateChanges()`
- [ ] Interceptor de Dio implementado para adjuntar Bearer token
- [ ] Manejo de 401 (refresh + retry) implementado
- [ ] Guard de auth en GoRouter configurado
- [ ] Flujo completo de login → token → request autenticado probado

### Permisos
- [ ] `permission_handler` instalado
- [ ] `permission_utils.dart` con patrón estándar de request + permanentlyDenied
- [ ] Ningún widget solicita permisos directamente (va por controller)
- [ ] FCM token se obtiene y envía al backend tras login (si el proyecto usa push)

### ApiClient
- [ ] `core/network/` implementado con Dio + interceptores
- [ ] `X-Trace-ID` generado y adjuntado en cada request
- [ ] Errores HTTP transformados a `sealed class` tipados
- [ ] Ninguna feature llama HTTP directamente

### Theme
- [ ] Core tokens definidos para el proyecto
- [ ] Semantic tokens para light y dark definidos
- [ ] `AppColorsExtension` implementado
- [ ] `ThemeData` light y dark configurados en `app_theme.dart`
- [ ] Verificado que ningún widget base usa `Colors.X` o literales

### Manejo de errores
- [ ] `sealed class AppError` creada en `core/errors/`
- [ ] ApiClient parsea DioException a AppError
- [ ] Manejo de 401 (force refresh + retry + logout) implementado
- [ ] Banner de "Sin conexión" implementado con connectivity_plus
- [ ] Errores 5xx muestran mensaje genérico con traceId visible

### Testing
- [ ] mocktail y patrol instalados
- [ ] Al menos un test unitario de use case con repositorio fake
- [ ] Al menos un test de widget del flujo de login
- [ ] integration_test configurado

### Validación final
- [ ] Build iOS pasa sin errores (`flutter build ios`)
- [ ] Build Android pasa sin errores (`flutter build appbundle`)
- [ ] Análisis estático sin errores (`flutter analyze`)
- [ ] Tests pasan (`flutter test`)
- [ ] Flujo de auth funciona end-to-end
- [ ] Modo oscuro funciona correctamente

---

*Versión: 1.2 — Marzo 2026*
*Derivado de ARCHITECTURE.md v3.0. Lee ese documento primero para el contexto del sistema completo.*
