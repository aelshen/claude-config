#!/usr/bin/env bash
# Codex peer review: runs the shared copy from the codex-review skill (claude-config), so a fix there reaches every
# repo. Config is .github/codex-review.env. Usage: scripts/codex-review.sh [base] | mark <pr> <real> <noise> | report
review="${CODEX_REVIEW_SCRIPT:-$HOME/.claude/skills/codex-review/scripts/codex-review.sh}"
[ -x "$review" ] || { echo "Install claude-config (its install.sh links the codex-review skill), or set CODEX_REVIEW_SCRIPT." >&2; exit 1; }
exec "$review" "$@"
