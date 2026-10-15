#!/usr/bin/env bash
# Board helper: runs the shared copy from the project-tracking skill (claude-config),
# so a fix there reaches every repo. Config is .github/board.env. Usage: scripts/board.sh help
board="${PROJECT_TRACKING_BOARD:-$HOME/.claude/skills/project-tracking/scripts/board.sh}"
[ -x "$board" ] || { echo "Install claude-config (its install.sh links the project-tracking skill), or set PROJECT_TRACKING_BOARD." >&2; exit 1; }
exec "$board" "$@"
