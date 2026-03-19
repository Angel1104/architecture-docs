# FE-WEB Kit Changelog

## v2.0.0 — 2026-03-18

### Changed
- `/init` now generates a rich `specs/project.md` with Navigation Index pre-populated from day one — agents no longer scan `src/` for context
- `/init` asks about screens and user actions per feature during setup, deriving anticipated use cases, hooks, screens, and API endpoints
- `/init` creates `specs/cr/` directory at init time
- `/close` now updates `specs/project.md` after every CR (not just features) — updates use case tables, screen tables, endpoint tables, Navigation Index, and CR History
- `specs/project.md` template adds `kit_version`, `## Navigation Index`, and `## CR History` sections
- Feature scaffold now includes `domain/use-cases/` directory from the start

### Fixed
- Hook bypass: no matching spec for specific feature now always denies (was allowing if any other reviewed spec existed)
- `settings.json` hook path was already correct (`.claude/hooks/enforce-spec-first.js`) — no change needed
- All `grep` commands in sw-architect agent replaced with `rg` (ripgrep) — BSD grep incompatibility on macOS

## v1.0.0 — initial release
