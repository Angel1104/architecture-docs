#!/usr/bin/env bash
# =============================================================================
# setup-kit.sh — Install an SDM kit into a target project
#
# Usage:
#   ./setup-kit.sh <kit> <target-project-path>
#
# Kits:
#   nestjs    → BE-NESTJS kit (NestJS + TypeScript backend)
#   fastapi   → BE-FASTAPI kit (FastAPI + Python backend)
#   web       → FE-WEB kit (Next.js frontend)
#   mobile    → FE-MOBILE kit (Flutter mobile)
#
# Examples:
#   ./setup-kit.sh nestjs ~/Projects/my-api
#   ./setup-kit.sh mobile ~/Projects/my-app
#   ./setup-kit.sh web    ~/Projects/my-web
#
# What it does:
#   1. Copies agents/, commands/, hooks/, references/ into <target>/.claude/
#   2. Copies settings.json into <target>/.claude/settings.json
#   3. Copies CLAUDE.md into <target>/CLAUDE.md
#   4. Makes hook scripts executable
#   5. Validates the install is complete
# =============================================================================

set -euo pipefail

# ── Resolve script directory (works even when called from another dir) ────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[info]${NC}  $*"; }
success() { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Usage ─────────────────────────────────────────────────────────────────────
usage() {
  echo ""
  echo -e "${BOLD}Usage:${NC} $0 <kit> <target-project-path>"
  echo ""
  echo -e "${BOLD}Kits:${NC}"
  echo "  nestjs   — NestJS + TypeScript backend"
  echo "  fastapi  — FastAPI + Python backend"
  echo "  web      — Next.js frontend"
  echo "  mobile   — Flutter mobile"
  echo ""
  echo -e "${BOLD}Examples:${NC}"
  echo "  $0 nestjs ~/Projects/my-api"
  echo "  $0 mobile ~/Projects/my-app"
  echo ""
  exit 1
}

# ── Argument validation ───────────────────────────────────────────────────────
[[ $# -lt 2 ]] && usage

KIT_NAME="$1"
TARGET="$2"

# Map kit name → source directory
case "$KIT_NAME" in
  nestjs)  KIT_DIR="$SCRIPT_DIR/BE-NESTJS" ;;
  fastapi) KIT_DIR="$SCRIPT_DIR/BE-FASTAPI" ;;
  web)     KIT_DIR="$SCRIPT_DIR/FE-WEB" ;;
  mobile)  KIT_DIR="$SCRIPT_DIR/FE-MOBILE" ;;
  *)       die "Unknown kit '$KIT_NAME'. Valid kits: nestjs, fastapi, web, mobile" ;;
esac

# Validate kit source exists
[[ -d "$KIT_DIR" ]] || die "Kit directory not found: $KIT_DIR"

# Validate or create target directory
if [[ ! -d "$TARGET" ]]; then
  warn "Target directory does not exist: $TARGET"
  read -r -p "Create it? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || die "Aborted."
  mkdir -p "$TARGET"
  success "Created $TARGET"
fi

TARGET="$(cd "$TARGET" && pwd)"  # Resolve to absolute path
CLAUDE_DIR="$TARGET/.claude"

echo ""
echo -e "${BOLD}Installing $KIT_NAME SDM kit into:${NC}"
echo "  $TARGET"
echo ""

# ── Safety: warn if .claude/ already exists ───────────────────────────────────
if [[ -d "$CLAUDE_DIR" ]]; then
  warn ".claude/ already exists in the target project."
  warn "Existing files will be overwritten."
  read -r -p "Continue? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || die "Aborted. No changes made."
fi

# ── Install ───────────────────────────────────────────────────────────────────

# 1. Create .claude/ structure
mkdir -p "$CLAUDE_DIR"

# 2. Copy agents/
if [[ -d "$KIT_DIR/agents" ]]; then
  rm -rf "$CLAUDE_DIR/agents"
  cp -r "$KIT_DIR/agents" "$CLAUDE_DIR/agents"
  success "Copied agents/ ($(ls "$CLAUDE_DIR/agents" | wc -l | tr -d ' ') agents)"
else
  warn "No agents/ directory in kit — skipping"
fi

# 3. Copy commands/
if [[ -d "$KIT_DIR/commands" ]]; then
  rm -rf "$CLAUDE_DIR/commands"
  cp -r "$KIT_DIR/commands" "$CLAUDE_DIR/commands"
  success "Copied commands/ ($(ls "$CLAUDE_DIR/commands" | wc -l | tr -d ' ') commands)"
else
  warn "No commands/ directory in kit — skipping"
fi

# 4. Copy hooks/
if [[ -d "$KIT_DIR/hooks" ]]; then
  rm -rf "$CLAUDE_DIR/hooks"
  cp -r "$KIT_DIR/hooks" "$CLAUDE_DIR/hooks"
  # Make hooks executable
  find "$CLAUDE_DIR/hooks" -type f \( -name "*.js" -o -name "*.py" -o -name "*.sh" \) -exec chmod +x {} \;
  success "Copied hooks/ and made them executable"
else
  warn "No hooks/ directory in kit — skipping"
fi

# 5. Copy references/
if [[ -d "$KIT_DIR/references" ]]; then
  rm -rf "$CLAUDE_DIR/references"
  cp -r "$KIT_DIR/references" "$CLAUDE_DIR/references"
  success "Copied references/ ($(ls "$CLAUDE_DIR/references" | wc -l | tr -d ' ') files)"
else
  warn "No references/ directory in kit — skipping"
fi

# 6. Copy settings.json
if [[ -f "$KIT_DIR/settings.json" ]]; then
  cp "$KIT_DIR/settings.json" "$CLAUDE_DIR/settings.json"
  success "Copied settings.json"
else
  warn "No settings.json in kit — skipping"
fi

# 7. Copy CLAUDE.md (with confirmation if it already exists)
if [[ -f "$TARGET/CLAUDE.md" ]]; then
  warn "CLAUDE.md already exists at target root."
  read -r -p "Overwrite? [y/N] " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    cp "$KIT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
    success "Overwrote CLAUDE.md"
  else
    info "Skipped CLAUDE.md — keeping existing file"
  fi
else
  cp "$KIT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
  success "Copied CLAUDE.md"
fi

# ── Validation ────────────────────────────────────────────────────────────────
echo ""
info "Validating install..."

ERRORS=0

check() {
  local path="$1"
  local label="$2"
  if [[ -e "$path" ]]; then
    success "$label"
  else
    error "MISSING: $label ($path)"
    ERRORS=$((ERRORS + 1))
  fi
}

check "$TARGET/CLAUDE.md"                    "CLAUDE.md"
check "$CLAUDE_DIR/settings.json"            ".claude/settings.json"
check "$CLAUDE_DIR/agents"                   ".claude/agents/"
check "$CLAUDE_DIR/commands"                 ".claude/commands/"
check "$CLAUDE_DIR/hooks"                    ".claude/hooks/"
check "$CLAUDE_DIR/references"               ".claude/references/"

# Check at least one hook is executable
HOOK_COUNT=$(find "$CLAUDE_DIR/hooks" -type f \( -name "*.js" -o -name "*.py" \) 2>/dev/null | wc -l | tr -d ' ')
if [[ "$HOOK_COUNT" -gt 0 ]]; then
  success "Hook scripts present ($HOOK_COUNT)"
else
  warn "No hook scripts found in .claude/hooks/"
fi

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
if [[ $ERRORS -gt 0 ]]; then
  die "$ERRORS validation error(s) found. Install incomplete."
else
  echo -e "${BOLD}${GREEN}✓ $KIT_NAME kit installed successfully.${NC}"
  echo ""
  echo -e "${BOLD}Next steps:${NC}"
  echo "  1. Open the project in Claude Code:"
  echo "     cd $TARGET && claude"
  echo ""
  echo "  2. Run /init to set up project context:"
  echo "     /init"
  echo ""
  echo "  3. Start your first CR:"
  echo "     /intake <describe what you want to build>"
  echo ""
fi
