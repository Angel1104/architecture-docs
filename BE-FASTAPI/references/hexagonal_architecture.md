# Hexagonal Architecture — comocom Patterns

## Core Principle

The domain is the center. It knows nothing about HTTP, databases, queues, or any framework. All external interaction flows through ports (interfaces) and adapters (implementations).

## Layer Map

```
┌─────────────────────────────────────────────────────────┐
│                     INBOUND ADAPTERS                     │
│   FastAPI routers · Event consumers · CLI · Schedulers   │
├─────────────────────────────────────────────────────────┤
│                   APPLICATION LAYER                      │
│          Commands (writes) · Queries (reads)             │
├─────────────────────────────────────────────────────────┤
│                     DOMAIN LAYER                         │
│     Models · Ports · Services · Events · Exceptions      │
├─────────────────────────────────────────────────────────┤
│                    OUTBOUND ADAPTERS                     │
│   Repositories · API clients · Gateways · Publishers     │
└─────────────────────────────────────────────────────────┘
```

## Dependency Direction (STRICT)

```
domain/      → NOTHING
application/ → domain/ ONLY
adapters/    → domain/ + application/ + external libraries
config/      → everything (composition root)
```

If any file in `domain/` imports from `adapters/` or `application/`, the architecture is broken.

## Directory Structure

```
src/
├── domain/
│   ├── models/          # Entities, Value Objects, Aggregates
│   │   ├── __init__.py
│   │   └── <entity>.py  # Contains class + factory methods + validation
│   ├── ports/           # Abstract interfaces
│   │   ├── __init__.py
│   │   ├── inbound/     # Operations the outside world calls on us
│   │   │   └── <use_case>_port.py
│   │   └── outbound/    # Operations we need from the outside world
│   │       ├── <entity>_repository.py
│   │       └── <service>_client.py
│   ├── services/        # Domain logic orchestrating entities + ports
│   │   └── <service>.py
│   ├── events/          # Domain event definitions
│   │   └── <context>_events.py
│   └── exceptions.py    # Domain-specific exceptions (not HTTP)
│
├── application/
│   ├── commands/        # Write operations (CQRS)
│   │   └── <action>_command.py  # Command DTO + Handler
│   └── queries/         # Read operations (CQRS)
│       └── <query>.py   # Query DTO + Handler
│
├── adapters/
│   ├── inbound/         # Drives the application
│   │   ├── api/         # FastAPI routers
│   │   │   ├── <resource>_router.py
│   │   │   ├── schemas/  # Pydantic request/response models
│   │   │   └── middleware/  # Auth, tenant resolution, error handling
│   │   └── event_handlers/  # Async event consumers
│   │       └── <event>_handler.py
│   └── outbound/        # Driven by the application
│       ├── persistence/  # Database repositories
│       │   └── <entity>_repository_impl.py
│       ├── clients/      # External API adapters
│       │   └── <service>_adapter.py
│       └── gateways/     # Gateway wrappers (Bridge pattern)
│           └── <service>_gateway.py
│
└── config/
    ├── container.py     # Dependency injection wiring
    ├── settings.py      # Environment config (Pydantic BaseSettings)
    └── events.py        # Event bus wiring
```

## Pattern: Bridge (Port → Adapter → Gateway)

Use the Bridge pattern for all external API integrations. The Gateway adds cross-cutting concerns without polluting the adapter logic.

```python
# domain/ports/outbound/payment_client.py
from abc import ABC, abstractmethod

class PaymentClient(ABC):
    @abstractmethod
    async def charge(self, tenant_uid: str, amount: Decimal, currency: str) -> PaymentResult:
        ...

# adapters/outbound/clients/stripe_adapter.py
import stripe

class StripeAdapter(PaymentClient):
    """Pure API translation — no retry/rate-limit logic here."""
    async def charge(self, tenant_uid: str, amount: Decimal, currency: str) -> PaymentResult:
        result = await stripe.PaymentIntent.create(amount=int(amount * 100), currency=currency)
        return PaymentResult(id=result.id, status=result.status)

# adapters/outbound/gateways/payment_gateway.py
class PaymentGateway(PaymentClient):
    """Wraps the adapter with cross-cutting concerns."""
    def __init__(self, adapter: StripeAdapter, rate_limiter: RateLimiter, circuit_breaker: CircuitBreaker):
        self._adapter = adapter
        self._rate_limiter = rate_limiter
        self._circuit_breaker = circuit_breaker

    async def charge(self, tenant_uid: str, amount: Decimal, currency: str) -> PaymentResult:
        await self._rate_limiter.acquire(tenant_uid)
        async with self._circuit_breaker:
            return await self._adapter.charge(tenant_uid, amount, currency)
```

In DI wiring, bind `PaymentClient` → `PaymentGateway(StripeAdapter(...))`.

## Pattern: NEL (Event-Driven Side Effects)

Side effects MUST be decoupled via domain events. Never call notification/email/webhook services directly from domain or application layers.

```python
# domain/events/user_events.py
@dataclass(frozen=True)
class UserRegistered:
    tenant_uid: str
    user_id: str
    email: str
    registered_at: datetime

# application/commands/register_user.py
class RegisterUserHandler:
    def __init__(self, repo: UserRepository, event_bus: EventBus):
        self._repo = repo
        self._event_bus = event_bus

    async def execute(self, command: RegisterUser) -> User:
        user = User.create(tenant_uid=command.tenant_uid, email=command.email, ...)
        await self._repo.save(command.tenant_uid, user)
        await self._event_bus.publish(UserRegistered(
            tenant_uid=command.tenant_uid,
            user_id=user.id,
            email=user.email,
            registered_at=user.created_at,
        ))
        return user

# adapters/inbound/event_handlers/welcome_email_handler.py
class WelcomeEmailHandler:
    """Consumes UserRegistered events — lives in adapters, NOT in domain."""
    def __init__(self, email_client: EmailClient):
        self._email_client = email_client

    async def handle(self, event: UserRegistered):
        await self._email_client.send_welcome(event.email, event.user_id)
```

## Pattern: DAL (Data Access Layer)

Repositories implement outbound ports. They translate between domain models and database rows.

```python
# adapters/outbound/persistence/user_repository_impl.py
class PostgresUserRepository(UserRepository):
    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_by_id(self, tenant_uid: str, user_id: str) -> Optional[User]:
        row = await self._db.execute(
            select(UserRow)
            .where(UserRow.tenant_uid == tenant_uid)  # ALWAYS scope by tenant
            .where(UserRow.id == user_id)
        )
        result = row.scalar_one_or_none()
        return self._to_domain(result) if result else None

    async def save(self, tenant_uid: str, user: User) -> User:
        row = self._to_row(user, tenant_uid)
        self._db.add(row)
        await self._db.flush()
        return user
```

## Anti-Patterns (REJECT these in code review)

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| `from adapters.outbound import ...` in domain/ | Breaks dependency direction | Define a port interface in domain/ports/ |
| `send_email(user.email)` in a command handler | Couples side effects | Publish a domain event, handle in adapter |
| `db.query(User).all()` without tenant filter | Cross-tenant data leakage | Always `.where(tenant_uid == ctx.tenant_uid)` |
| `requests.get(url)` in domain service | Domain depends on HTTP library | Define outbound port, implement in adapter |
| `raise HTTPException(404)` in domain | Domain knows about HTTP | Raise `EntityNotFound`, map to 404 in adapter |
| Singleton/global tenant state | Thread-safety issues, test pollution | Pass TenantContext through ports explicitly |
