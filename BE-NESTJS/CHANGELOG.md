# BE-NESTJS Kit Changelog

## v2.0.0 — 2026-03-18

### Changed
- `/init` now generates a rich `specs/project.md` with Navigation Index pre-populated from day one — agents no longer scan `src/` for context
- `/init` asks about use cases per module during setup, deriving anticipated file paths, endpoints, and class names
- `/init` creates `specs/cr/` directory at init time
- `/close` now updates `specs/project.md` after every CR (not just features) — updates use case tables, endpoints, Navigation Index, and CR History
- `specs/project.md` template adds `kit_version`, `## Navigation Index`, and `## CR History` sections
- `src/modules/` scaffold now includes `domain/ports/`, `domain/errors/`, `application/__fakes__/`, `interface/guards/`, `interface/decorators/` from the start

### Fixed
- Hook bypass: no matching spec for specific module now always denies (was allowing if any other reviewed spec existed)
- `delete` in canonical Prisma repository pattern now requires `tenantId` and wraps in `withTenant()` — prevents cross-tenant deletes
- All `grep` commands in sw-architect agent replaced with `rg` (ripgrep) — BSD grep incompatibility on macOS
- `settings.json` hook path corrected to `.claude/hooks/enforce-spec-first.js`
- FakeRepository in `plan/SKILL.md` canonized to use `Map<string, T>` — consistent with qa-engineer.md
- `qa-engineer.md` now shows correct pattern for testing real `FirebaseAuthGuard` without mock override
- FastAPI sync call timeout rule added to `nestjs_defaults.md` — `{ timeout: 10_000 }` required on all sync calls

## v1.0.0 — initial release
