#!/bin/bash
# Links this repo into ~/.claude and merges settings.json into your settings.
# Existing files are moved to ~/.claude/backups/<timestamp>/ first. Re-runnable.
set -euo pipefail
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
repo=$(cd "$(dirname "$0")" && pwd)
dest="$HOME/.claude"
backup="$dest/backups/$(date +%Y%m%d%H%M%S)"
mkdir -p "$dest/agents" "$dest/skills" "$dest/state/budget"

link() {  # link <repo-relative-path> <dest-path>
  local src="$repo/$1" dst="$2"
  if [ -L "$dst" ] && [ "$(readlink "$dst")" = "$src" ]; then return; fi
  if [ -e "$dst" ] || [ -L "$dst" ]; then
    mkdir -p "$backup/$(dirname "${dst#$dest/}")"; mv "$dst" "$backup/${dst#$dest/}"
  fi
  ln -s "$src" "$dst"; echo "linked $dst"
}

link CLAUDE.md "$dest/CLAUDE.md"
link budget "$dest/budget"
for f in "$repo"/agents/*.md; do link "agents/$(basename "$f")" "$dest/agents/$(basename "$f")"; done
for d in "$repo"/skills/*/; do n=$(basename "$d"); link "skills/$n" "$dest/skills/$n"; done

# Settings are merged, not linked: your machine-specific keys stay put.
# Hook arrays are replaced for the events this repo defines.
settings="$dest/settings.json"
[ -f "$settings" ] || echo '{}' > "$settings"
mkdir -p "$backup"; cp "$settings" "$backup/settings.json"
jq -s '.[0] * .[1]' "$settings" "$repo/settings.json" > "$settings.new" && mv "$settings.new" "$settings"
echo "merged settings.json (backup in $backup)"
