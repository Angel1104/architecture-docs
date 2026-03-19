# BE-FASTAPI Kit Changelog

## v2.0.0 — 2026-03-18

### Changed
- `/init` now generates a rich `specs/project.md` with Navigation Index pre-populated from day one — agents no longer scan `src/` for context
- `/init` asks about each endpoint's input/output during setup, deriving anticipated command/query class names and file paths
- `/init` creates `specs/cr/` directory at init time
- `/close` now updates `specs/project.md` after every CR (not just features) — updates endpoint sections, Navigation Index, and CR History
- `specs/project.md` template adds `kit_version`, `## Navigation Index`, and `## CR History` sections
- Scaffold now creates `src/domain/exceptions.py` with base domain error classes

### Fixed
- `enforce-spec-first.py` hook: no matching spec for specific module now always denies (was allowing if any other reviewed spec existed)
- `enforce-spec-first.py`: now correctly searches `specs/cr/` (was searching `specs/`)
- `enforce-spec-first.py`: path pattern now matches FastAPI's `src/domain/`, `src/application/`, `src/adapters/` structure
- `settings.json`: hook path corrected to `.claude/hooks/enforce-spec-first.py`, using `python3`
- All `grep` commands in sw-architect agent replaced with `rg` (ripgrep) — BSD grep incompatibility on macOS
- `/close`: test command changed to `pytest --tb=short -q` (full suite, not just CR-specific tests)

## v1.0.0 — initial release
