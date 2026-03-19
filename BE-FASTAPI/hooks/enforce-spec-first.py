#!/usr/bin/env python3
"""
FastAPI spec-first enforcement hook.

Runs on PreToolUse for Write and Edit tools.
Blocks writes to src/ implementation code if no corresponding reviewed spec
exists in specs/cr/.

Hook protocol:
  - Reads JSON from stdin: {"tool_name": "...", "tool_input": {"file_path": "...", ...}}
  - Exit 0 silently to allow
  - Print JSON with permissionDecision: "deny" to block

Enforcement logic:
  - No specs/cr/ dir           → DENY
  - No spec files at all       → DENY
  - Matching spec + APPROVED   → ALLOW
  - Matching spec + not approved → WARN (allow, but flag)
  - No matching spec found     → DENY (module has no spec — must create one)
"""
import json
import sys
import os
import re


def normalize_path(path):
    """Normalize path to always use forward slashes for consistent matching."""
    return path.replace("\\", "/")


def infer_module_names(file_path):
    """Heuristic: extract possible module names from a src/ file path.

    FastAPI project structure: src/domain/, src/application/, src/adapters/
    We extract the feature concept from the filename (snake_case → kebab-case).

    Examples:
      src/domain/models/user_registration.py → {"user-registration", "user"}
      src/adapters/inbound/registration_router.py → {"registration-router", "registration"}
      src/application/commands/create_order.py → {"create-order", "create"}
    """
    normalized = normalize_path(file_path)
    names = set()

    # Try to find a meaningful segment from known src subdirectories
    for segment_pattern in [
        r'src/domain/(?:models|ports)/([^/]+)\.py$',
        r'src/application/(?:commands|queries)/([^/]+)\.py$',
        r'src/adapters/(?:inbound|outbound)/([^/]+)\.py$',
    ]:
        m = re.search(segment_pattern, normalized)
        if m:
            basename = m.group(1)
            kebab = basename.replace("_", "-")
            names.add(kebab)
            parts = kebab.split("-")
            if len(parts) > 1:
                names.add(parts[0])
                names.add("-".join(parts[:2]))
            return names

    # Fallback: use the file basename
    basename = os.path.splitext(os.path.basename(file_path))[0]
    kebab = basename.replace("_", "-")
    names.add(kebab)
    parts = kebab.split("-")
    if len(parts) > 1:
        names.add(parts[0])
        names.add("-".join(parts[:2]))
    return names


def find_matching_spec(specs_dir, module_names):
    """Check if any spec file matches the inferred module names.
    Returns (matching_spec_file | None, all_spec_files).
    """
    try:
        spec_files = [f for f in os.listdir(specs_dir) if f.endswith(".spec.md")]
    except OSError:
        return None, []

    for spec_file in spec_files:
        spec_name = spec_file.replace(".spec.md", "")
        for module_name in module_names:
            if module_name in spec_name or spec_name in module_name:
                return spec_file, spec_files
    return None, spec_files


def is_spec_reviewed(spec_path):
    """Check if a spec file has REVIEWED or APPROVED status."""
    try:
        with open(spec_path, "r") as f:
            content = f.read(2000)
        return bool(re.search(r"Status\s*\|\s*(REVIEWED|APPROVED)", content, re.IGNORECASE))
    except (IOError, OSError):
        return False


def deny(reason):
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def warn(reason):
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name not in ("Write", "Edit"):
        sys.exit(0)

    file_path = (tool_input.get("file_path", "") or tool_input.get("path", "")).strip()
    if not file_path:
        sys.exit(0)

    file_path_normalized = normalize_path(file_path)

    # Only enforce for src/ implementation paths
    src_pattern = re.compile(r"(^|/)src/(domain|application|adapters)/")
    if not src_pattern.search(file_path_normalized):
        sys.exit(0)

    # Skip generated and config files
    basename = os.path.basename(file_path)
    if basename in ("__init__.py", "conftest.py") or basename.startswith("."):
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    specs_dir = os.path.join(project_dir, "specs", "cr")

    # No specs/cr/ directory at all
    if not os.path.isdir(specs_dir):
        deny(
            "SPEC-FIRST VIOLATION: No specs/cr/ directory found.\n\n"
            "The FastAPI SDM kit requires a specification before implementation.\n"
            "Run `/intake <description>` to create a CR item, then `/spec <cr-id>`.\n\n"
            f"Blocked write to: {file_path}"
        )

    # Infer module names and look for a matching spec
    module_names = infer_module_names(file_path)
    matching_spec, all_specs = find_matching_spec(specs_dir, module_names)

    if not all_specs:
        deny(
            "SPEC-FIRST VIOLATION: No spec files found in specs/cr/.\n\n"
            "The FastAPI SDM kit requires a reviewed specification before writing implementation code.\n"
            "Run `/intake <description>` then `/spec <cr-id>` to create and review a spec.\n\n"
            f"Blocked write to: {file_path}"
        )

    if matching_spec:
        spec_path = os.path.join(specs_dir, matching_spec)
        if is_spec_reviewed(spec_path):
            sys.exit(0)  # All good — reviewed spec exists
        else:
            warn(
                f"SPEC-FIRST WARNING: Found spec '{matching_spec}' but it is not yet APPROVED.\n"
                f"Run '/spec <cr-id>' and complete the review before implementing.\n"
                f"Proceeding with write to: {file_path}"
            )
    else:
        # P0 FIX: No matching spec for this specific module → DENY always.
        # A reviewed spec for a different module does not cover this one.
        deny(
            "SPEC-FIRST VIOLATION: No spec found for this module.\n\n"
            f"Inferred module names: {', '.join(sorted(module_names))}\n"
            f"Existing specs: {', '.join(sorted(all_specs)) or '(none)'}\n\n"
            "Every module requires its own reviewed spec before implementation.\n"
            "Run `/intake <description>` to create a CR item, then `/spec <cr-id>`.\n\n"
            f"Blocked write to: {file_path}"
        )


if __name__ == "__main__":
    main()
