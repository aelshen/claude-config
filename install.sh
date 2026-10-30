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
# Codex's global guidance (codex-review skill), unless you keep your own file there.
codex_md="$HOME/.codex/AGENTS.md" codex_src="$repo/skills/codex-review/assets/codex-AGENTS.md"
if [ "$(readlink "$codex_md" 2>/dev/null)" = "$codex_src" ]; then :
elif [ ! -e "$codex_md" ] && [ ! -L "$codex_md" ]; then
  mkdir -p "$HOME/.codex"; ln -s "$codex_src" "$codex_md"; echo "linked $codex_md"
else
  echo "kept your $codex_md (not a link); merge skills/codex-review/assets/codex-AGENTS.md into it by hand"
fi

# Settings are merged, not linked: your machine-specific keys stay put.
# Hook arrays are combined: your own hooks (e.g. a local Bash guard) stay, this repo's are added once.
settings="$dest/settings.json"
[ -f "$settings" ] || echo '{}' > "$settings"
mkdir -p "$backup"; cp "$settings" "$backup/settings.json"
jq -s '.[0] as $l | .[1] as $r | ($l * $r)
  | .hooks = (reduce ((($l.hooks // {}) | keys) + (($r.hooks // {}) | keys) | unique)[] as $e ({};
      .[$e] = ((($l.hooks[$e] // []) + ($r.hooks[$e] // [])) | reduce .[] as $x ([]; if index([$x]) then . else . + [$x] end))))' \
  "$settings" "$repo/settings.json" > "$settings.new" && mv "$settings.new" "$settings"
echo "merged settings.json (backup in $backup)"
