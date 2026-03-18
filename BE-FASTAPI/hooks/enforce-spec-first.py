#!/usr/bin/env python
"""
comocom spec-first enforcement hook.

Runs on PreToolUse for Write and Edit tools.
Blocks writes to src/ implementation code if no corresponding reviewed spec exists.

Hook protocol:
  - Reads JSON from stdin: {"tool_name": "...", "tool_input": {"file_path": "...", ...}}
  - Exit 0 silently to allow
  - Print JSON with permissionDecision: "deny" to block
"""
import json
import sys
import os
import re


def normalize_path(path):
    """Normalize path to always use forward slashes for consistent matching."""
    return os.path.normpath(path).replace("\\", "/")


def infer_feature_names(file_path):
    """Heuristic: extract possible feature names from a file path.

    Examples:
      src/domain/models/user_registration.py → {"user-registration"}
      src/adapters/inbound/registration_router.py → {"registration-router", "registration"}
      src/application/commands/create_order.py → {"create-order"}
    """
    basename = os.path.splitext(os.path.basename(file_path))[0]
    # Convert snake_case to kebab-case
    kebab = basename.replace("_", "-")
    names = {kebab}
    # Also try partial matches (first word, first two words)
    parts = kebab.split("-")
    if len(parts) > 1:
        names.add(parts[0])
        names.add("-".join(parts[:2]))
    return names


def find_matching_spec(specs_dir, feature_names):
    """Check if any spec file matches the inferred feature names."""
    try:
        spec_files = [f for f in os.listdir(specs_dir) if f.endswith(".spec.md")]
    except OSError:
        return None, []

    for spec_file in spec_files:
        spec_name = spec_file.replace(".spec.md", "")
        for feature_name in feature_names:
            if feature_name in spec_name or spec_name in feature_name:
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

    file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
    if not file_path:
        sys.exit(0)

    # Normalize to forward slashes for cross-platform regex matching
    file_path_normalized = normalize_path(file_path)

    # Detect project type from directory structure
    # Backend: enforces src/domain|application|adapters
    # Flutter: enforces lib/features (but only if lib/ exists and src/ does not)
    # If neither matches, allow
    has_src = os.path.isdir(os.path.join(project_dir, "src"))
    has_lib = os.path.isdir(os.path.join(project_dir, "lib"))

    backend_pattern = re.compile(r"(^|/)src/(domain|application|adapters)/")
    flutter_pattern = re.compile(r"(^|/)lib/features/")

    is_backend_file = backend_pattern.search(file_path_normalized)
    is_flutter_file = flutter_pattern.search(file_path_normalized)

    if not is_backend_file and not is_flutter_file:
        sys.exit(0)

    # For Flutter files, only enforce if this is clearly a Flutter project
    if is_flutter_file and not has_lib:
        sys.exit(0)

    # For backend files, only enforce if this is clearly a backend project
    if is_backend_file and not has_src:
        sys.exit(0)

    # Skip generated, config, and init files
    basename = os.path.basename(file_path)
    if basename in ("__init__.py", "conftest.py") or basename.startswith("."):
        sys.exit(0)
    # Skip Dart generated files
    if basename.endswith(".g.dart") or basename.endswith(".freezed.dart"):
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    specs_dir = os.path.join(project_dir, "specs")

    # No specs/ directory at all
    if not os.path.isdir(specs_dir):
        deny(
            "SPEC-FIRST VIOLATION: No specs/ directory found.\n\n"
            "The comocom methodology requires a specification before implementation.\n"
            "Run `/spec-init <feature-name>` to create a spec first.\n\n"
            f"Blocked write to: {file_path}"
        )

    # Try to match this file to a specific spec
    feature_names = infer_feature_names(file_path)
    matching_spec, all_specs = find_matching_spec(specs_dir, feature_names)

    if not all_specs:
        deny(
            "SPEC-FIRST VIOLATION: No spec files found in specs/.\n\n"
            "The comocom methodology requires a reviewed specification before "
            "writing implementation code.\n"
            "Run `/spec-init <feature-name>` to create a spec, then "
            "`/spec-review <feature-name>` to review it.\n\n"
            f"Blocked write to: {file_path}"
        )

    if matching_spec:
        # Found a matching spec — check if it's reviewed
        spec_path = os.path.join(specs_dir, matching_spec)
        if is_spec_reviewed(spec_path):
            sys.exit(0)  # All good
        else:
            warn(
                f"SPEC-FIRST WARNING: Found spec '{matching_spec}' but it is not yet REVIEWED.\n"
                f"Run `/spec-review {matching_spec.replace('.spec.md', '')}` before implementing.\n"
                f"Proceeding with write to: {file_path}"
            )
    else:
        # No matching spec — check if ANY reviewed spec exists (soft enforcement)
        has_any_reviewed = any(
            is_spec_reviewed(os.path.join(specs_dir, sf)) for sf in all_specs
        )
        if has_any_reviewed:
            warn(
                f"SPEC-FIRST WARNING: No spec matches this file.\n"
                f"Inferred feature names: {', '.join(sorted(feature_names))}\n"
                f"Existing specs: {', '.join(sorted(all_specs))}\n"
                f"Consider creating a spec for this feature with `/spec-init <feature-name>`.\n"
                f"Proceeding with write to: {file_path}"
            )
        else:
            deny(
                "SPEC-FIRST VIOLATION: No reviewed specs found.\n\n"
                "Specs exist but none have REVIEWED/APPROVED status.\n"
                "Run `/spec-review <feature-name>` to review a spec before implementing.\n\n"
                f"Blocked write to: {file_path}"
            )


if __name__ == "__main__":
    main()
