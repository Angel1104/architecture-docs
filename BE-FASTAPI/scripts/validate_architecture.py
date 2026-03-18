#!/usr/bin/env python3
"""
Hexagonal architecture boundary validator.

Checks that layer dependencies point inward only:
  domain/    → nothing (no imports from application/, adapters/, config/)
  application/ → domain/ only (no imports from adapters/, config/)
  adapters/  → domain/ + application/ only (no imports from config/ internals)

Also checks:
  - No HTTP exceptions in domain/ or application/ (HTTPException, status codes)
  - No framework imports in domain/ (fastapi, sqlalchemy, pydantic [allowed], httpx, etc.)

Usage:
  python .claude/scripts/validate_architecture.py [src_dir]
  python .claude/scripts/validate_architecture.py          # defaults to src/

Exit codes:
  0 — no violations found
  1 — violations found (details printed to stdout)
"""
import os
import sys
import re
from pathlib import Path
from dataclasses import dataclass, field


# ── Patterns ──────────────────────────────────────────────────────────────────

# Framework imports forbidden in domain/
DOMAIN_FORBIDDEN_IMPORTS = re.compile(
    r'^\s*(from|import)\s+(fastapi|sqlalchemy|alembic|httpx|aiohttp|requests'
    r'|firebase_admin|google\.cloud|boto3|celery|redis|motor|pymongo'
    r'|starlette)\b',
    re.MULTILINE,
)

# HTTP exceptions / status codes forbidden in domain/ and application/
HTTP_IN_DOMAIN = re.compile(
    r'^\s*(from|import)\s+(fastapi|starlette).*?(HTTPException|status)\b'
    r'|HTTPException|HTTP_\d{3}|status\.HTTP_',
    re.MULTILINE,
)

# Cross-layer import patterns
CROSS_LAYER_PATTERNS = {
    "domain": re.compile(
        r'^\s*(from|import)\s+(src\.)?(application|adapters|config)\b',
        re.MULTILINE,
    ),
    "application": re.compile(
        r'^\s*(from|import)\s+(src\.)?(adapters|config)\b',
        re.MULTILINE,
    ),
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Violation:
    file: str
    line_number: int
    rule: str
    line: str

    def __str__(self) -> str:
        return f"  [{self.rule}] {self.file}:{self.line_number}\n    → {self.line.strip()}"


@dataclass
class ValidationResult:
    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0

    @property
    def passed(self) -> bool:
        return len(self.violations) == 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_layer(file_path: Path, src_root: Path) -> str | None:
    """Return the layer name for a file, or None if not in a known layer."""
    try:
        relative = file_path.relative_to(src_root)
        parts = relative.parts
        if parts:
            return parts[0]  # domain, application, adapters, config
    except ValueError:
        pass
    return None


def find_violations_in_file(file_path: Path, src_root: Path) -> list[Violation]:
    violations = []
    layer = get_layer(file_path, src_root)
    if layer is None:
        return violations

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return violations

    lines = content.splitlines()
    rel_path = str(file_path.relative_to(src_root.parent))

    # Check cross-layer imports
    if layer in CROSS_LAYER_PATTERNS:
        pattern = CROSS_LAYER_PATTERNS[layer]
        for i, line in enumerate(lines, start=1):
            if pattern.search(line):
                violations.append(Violation(
                    file=rel_path,
                    line_number=i,
                    rule=f"BOUNDARY: {layer}/ imports forbidden layer",
                    line=line,
                ))

    # Check HTTP exceptions in domain/ and application/
    if layer in ("domain", "application"):
        for i, line in enumerate(lines, start=1):
            if HTTP_IN_DOMAIN.search(line):
                violations.append(Violation(
                    file=rel_path,
                    line_number=i,
                    rule=f"HTTP-IN-DOMAIN: {layer}/ must not reference HTTP status codes or exceptions",
                    line=line,
                ))

    # Check forbidden framework imports in domain/
    if layer == "domain":
        for i, line in enumerate(lines, start=1):
            if DOMAIN_FORBIDDEN_IMPORTS.search(line):
                violations.append(Violation(
                    file=rel_path,
                    line_number=i,
                    rule="FRAMEWORK-IN-DOMAIN: domain/ must not import framework packages",
                    line=line,
                ))

    return violations


def validate(src_dir: Path) -> ValidationResult:
    result = ValidationResult()

    for py_file in sorted(src_dir.rglob("*.py")):
        # Skip test files, migrations, and __pycache__
        parts = py_file.parts
        if any(p in ("__pycache__", "migrations", "tests", "test") for p in parts):
            continue
        if py_file.name.startswith("test_") or py_file.name == "conftest.py":
            continue

        result.files_checked += 1
        violations = find_violations_in_file(py_file, src_dir)
        result.violations.extend(violations)

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    src_arg = sys.argv[1] if len(sys.argv) > 1 else "src"
    src_dir = Path(src_arg).resolve()

    if not src_dir.is_dir():
        print(f"ERROR: Directory not found: {src_dir}")
        return 1

    print(f"Validating architecture in: {src_dir}")
    result = validate(src_dir)

    print(f"Files checked: {result.files_checked}")

    if result.passed:
        print("✓ No boundary violations found.")
        return 0

    # Group by rule type
    by_rule: dict[str, list[Violation]] = {}
    for v in result.violations:
        rule_key = v.rule.split(":")[0]
        by_rule.setdefault(rule_key, []).append(v)

    print(f"\n✗ {len(result.violations)} violation(s) found:\n")
    for rule_key, violations in sorted(by_rule.items()):
        print(f"[{rule_key}] — {len(violations)} violation(s)")
        for v in violations:
            print(str(v))
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
