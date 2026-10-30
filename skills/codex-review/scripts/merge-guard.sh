#!/usr/bin/env bash
# PreToolUse hook (Bash): before `gh pr merge` in a repo that has .github/codex-review.env, refuse when the PR body has
# no "Codex review" section (a "skipped (...)" line counts), or when its CI checks are still running or not yet
# registered (right after a push `gh pr checks --watch` returns at once, so a merge can beat CI). Anything else passes.
# Override for one command: start it with CODEX_GUARD=off.
input=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$input")
[[ "$cmd" =~ (^|[;&|[:space:]])gh[[:space:]]+pr[[:space:]]+merge([[:space:]]|$) ]] || exit 0
[[ "$cmd" == *CODEX_GUARD=off* ]] && exit 0
cwd=$(jq -r '.cwd // ""' <<<"$input")
cd "${cwd:-.}" 2>/dev/null || exit 0
# a `cd <dir> &&` in front of the merge decides the repo
if [[ "$cmd" =~ ^[[:space:]]*cd[[:space:]]+([^;&|[:space:]]+) ]]; then
  d="${BASH_REMATCH[1]}"; d="${d/#\~/$HOME}"; cd "$d" 2>/dev/null || true
fi
top=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -f "$top/.github/codex-review.env" ] || exit 0
CODEX_SCOPE=all; . "$top/.github/codex-review.env"
[ "$CODEX_SCOPE" = off ] && exit 0
rest="${cmd#*pr merge}"
pr=$(grep -oE '(^|[[:space:]])[0-9]+([[:space:]]|$)' <<<"$rest" | head -1 | tr -d '[:space:]')
body=$(cd "$top" && gh pr view ${pr:+"$pr"} --json body -q .body 2>/dev/null) || exit 0
if ! grep -qi 'codex review' <<<"$body"; then
  echo "Blocked: PR ${pr:-for this branch} has no \"Codex review\" section. Run scripts/codex-review.sh, verify the findings, add the section (or \"Codex review: skipped (...)\"), then merge." >&2
  exit 2
fi
checks=$(cd "$top" && gh pr checks ${pr:+"$pr"} 2>&1); code=$?
if [ $code -eq 8 ]; then
  echo "Blocked: CI checks on PR ${pr:-for this branch} are still running. Wait for them (gh pr checks --watch), then merge." >&2
  exit 2
fi
if grep -q "no checks reported" <<<"$checks"; then
  echo "Blocked: no CI checks are registered on PR ${pr:-for this branch} yet (right after a push they take a moment). Wait and re-check; for a repo with no CI, prefix the merge with CODEX_GUARD=off." >&2
  exit 2
fi
if [ $code -ne 0 ]; then
  echo "Blocked: CI checks on PR ${pr:-for this branch} failed:" >&2; grep -vE '\bpass\b|skipping' <<<"$checks" | head -5 >&2
  exit 2
fi
exit 0
