# Tenant Isolation — comocom Rules

## Principle

Every data path in the system MUST be scoped to a tenant. There is no acceptable cross-tenant data leakage. A query that returns another tenant's data is a P0 security incident.

## Tenant Context Flow

```
Request → Middleware (extract tenant_uid) → Router → Use Case → Port → Adapter (scope query)
```

Tenant context flows EXPLICITLY through function parameters. Never use global state, thread-locals, or context variables.

## Implementation Rules

### Rule 1: Middleware Extracts, Adapter Validates

```python
# adapters/inbound/api/middleware/tenant_middleware.py
from fastapi import Request, HTTPException

async def resolve_tenant(request: Request) -> str:
    """Extract tenant_uid from JWT claims. Runs as a FastAPI Depends()."""
    token_payload = request.state.auth_payload  # Set by auth middleware
    tenant_uid = token_payload.get("tenant_uid")
    if not tenant_uid:
        raise HTTPException(status_code=403, detail="Tenant context required")
    return tenant_uid
```

### Rule 2: Every Port Method Includes tenant_uid

```python
# domain/ports/outbound/document_repository.py
class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_uid: str, doc_id: str) -> Optional[Document]:
        ...

    @abstractmethod
    async def list_all(self, tenant_uid: str, page: int, size: int) -> list[Document]:
        ...

    @abstractmethod
    async def save(self, tenant_uid: str, document: Document) -> Document:
        ...

    @abstractmethod
    async def delete(self, tenant_uid: str, doc_id: str) -> None:
        ...
```

Every method takes `tenant_uid` as its first parameter (after self). No exceptions.

### Rule 3: Every Query Filters by tenant_uid

```python
# adapters/outbound/persistence/document_repository_impl.py
class PostgresDocumentRepository(DocumentRepository):
    async def get_by_id(self, tenant_uid: str, doc_id: str) -> Optional[Document]:
        stmt = (
            select(DocumentRow)
            .where(DocumentRow.tenant_uid == tenant_uid)  # MANDATORY
            .where(DocumentRow.id == doc_id)
        )
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def list_all(self, tenant_uid: str, page: int, size: int) -> list[Document]:
        stmt = (
            select(DocumentRow)
            .where(DocumentRow.tenant_uid == tenant_uid)  # MANDATORY
            .order_by(DocumentRow.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self._db.execute(stmt)
        return [self._to_domain(row) for row in result.scalars()]
```

### Rule 4: Domain Events Include tenant_uid

```python
@dataclass(frozen=True)
class DocumentCreated:
    tenant_uid: str  # ALWAYS included
    document_id: str
    created_by: str
    created_at: datetime
```

Event handlers MUST validate they are processing events for the correct tenant context.

### Rule 5: No Cross-Tenant Joins

Database queries MUST NOT join across tenants. If you need data from multiple tenants (e.g., admin dashboard), that is a separate bounded context with explicit authorization.

```sql
-- WRONG: No tenant filter
SELECT * FROM documents WHERE id = :doc_id;

-- CORRECT: Always scoped
SELECT * FROM documents WHERE tenant_uid = :tenant_uid AND id = :doc_id;

-- WRONG: Cross-tenant join
SELECT d.*, u.name FROM documents d JOIN users u ON d.user_id = u.id;

-- CORRECT: Scoped join
SELECT d.*, u.name
FROM documents d
JOIN users u ON d.user_id = u.id AND u.tenant_uid = d.tenant_uid
WHERE d.tenant_uid = :tenant_uid;
```

### Rule 6: Row-Level Security as Defense-in-Depth

In addition to application-level filtering, configure PostgreSQL RLS:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON documents
    USING (tenant_uid = current_setting('app.current_tenant_uid'));
```

Set the session variable in the adapter before executing queries:

```python
async def _set_tenant_context(self, tenant_uid: str):
    # IMPORTANT: Use parameterized query to prevent SQL injection via tenant_uid
    await self._db.execute(text("SET LOCAL app.current_tenant_uid = :tid"), {"tid": tenant_uid})
```

This is defense-in-depth — application code still filters by tenant_uid, and RLS catches any bugs.

## Testing Tenant Isolation

Every feature MUST include cross-tenant isolation tests:

```python
class TestTenantIsolation:
    async def test_tenant_a_cannot_see_tenant_b_data(self):
        # Create document for tenant A
        doc = await repo.save("tenant-a", Document(...))

        # Query as tenant B — must return None
        result = await repo.get_by_id("tenant-b", doc.id)
        assert result is None

    async def test_list_only_returns_own_tenant(self):
        await repo.save("tenant-a", Document(title="A's doc"))
        await repo.save("tenant-b", Document(title="B's doc"))

        results = await repo.list_all("tenant-a", page=1, size=100)
        assert all(d.tenant_uid == "tenant-a" for d in results)
        assert len(results) == 1

    async def test_tenant_uid_required(self):
        with pytest.raises((ValueError, TypeError)):
            await repo.save(None, Document(...))
```

## Anti-Patterns

| Anti-Pattern | Risk | Fix |
|---|---|---|
| Global `current_tenant` variable | Thread-safety, test pollution | Pass tenant_uid through ports |
| Middleware sets `g.tenant` or `request.state.tenant` and adapters read it | Hidden coupling, hard to test | Explicit parameter passing |
| `WHERE id = :id` without tenant filter | Cross-tenant data access | Always include `AND tenant_uid = :tenant_uid` |
| Admin endpoints without tenant scope | Privilege escalation | Separate bounded context with explicit authorization |
| Batch jobs without tenant iteration | Processing wrong tenant's data | Iterate per-tenant with explicit context |
