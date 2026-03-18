#!/usr/bin/env python3
"""
Conventional Commits enforcement hook.

Runs on PreToolUse for Bash tool. Validates that git commit messages
follow the Conventional Commits specification.

Hook protocol:
  - Reads JSON from stdin: {"tool_name": "...", "tool_input": {"command": "..."}}
  - Exit 0 silently to allow
  - Print JSON with permissionDecision: "deny" to block

Conventional Commits format:
  <type>(<scope>): <description>

Types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert
"""
import json
import sys
import re


CONVENTIONAL_PATTERN = re.compile(
    r'^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(\(.+\))?!?:\s.+'
)


def extract_commit_message(command: str) -> str | None:
    """Extract commit message from a git commit command string."""
    # Match: git commit -m "msg" or git commit -m 'msg'
    # Also handles: git commit --message="msg" and multi-flag variants
    patterns = [
        r'git\s+commit\b.*?\s-m\s+"([^"]+)"',
        r"git\s+commit\b.*?\s-m\s+'([^']+)'",
        r'git\s+commit\b.*?\s--message="([^"]+)"',
        r"git\s+commit\b.*?\s--message='([^']+)'",
        r'git\s+commit\b.*?\s-m\s+([^\s\'"]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, command, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def deny(reason: str) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))
    sys.exit(0)


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if tool_name != "Bash":
        sys.exit(0)

    command = tool_input.get("command", "")

    # Only inspect git commit commands
    if "git" not in command or "commit" not in command:
        sys.exit(0)

    # Skip --amend without a new message (reusing previous message is fine)
    if "--amend" in command and "-m" not in command and "--message" not in command:
        sys.exit(0)

    commit_msg = extract_commit_message(command)

    # If we can't parse the message, allow through (e.g. heredoc commits)
    if commit_msg is None:
        sys.exit(0)

    # Skip merge commits and fixup commits
    if commit_msg.startswith("Merge ") or commit_msg.startswith("fixup! "):
        sys.exit(0)

    if not CONVENTIONAL_PATTERN.match(commit_msg):
        deny(
            "CONVENTIONAL COMMITS VIOLATION\n\n"
            f'Message: "{commit_msg}"\n\n'
            "Expected format: <type>(<scope>): <description>\n\n"
            "Valid types: feat, fix, docs, style, refactor, perf, test, chore, ci, build, revert\n\n"
            "Examples:\n"
            "  feat(auth): add JWT refresh token rotation\n"
            "  fix(tenant): prevent cross-tenant query leak\n"
            "  docs: update spec template with port signatures\n"
            "  test(user): add cross-tenant isolation test\n"
            "  chore: bump FastAPI to 0.115"
        )


if __name__ == "__main__":
    main()
