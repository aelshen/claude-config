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
# a `cd <dir> &&` in front of the merge decides the local repo
if [[ "$cmd" =~ ^[[:space:]]*cd[[:space:]]+([^;&|[:space:]]+) ]]; then
  d="${BASH_REMATCH[1]}"; d="${d/#\~/$HOME}"; cd "$d" 2>/dev/null || true
fi
# The target: the first argument after `merge` that is not a flag (number, URL or branch), and -R/--repo.
read -r -a words <<<"${cmd#*pr merge}"
target="" repo=""
for ((k = 0; k < ${#words[@]}; k++)); do
  w="${words[k]}"
  case "$w" in
    \&\&|\;|\|\||\|) break ;;
    -R|--repo) repo="${words[k + 1]:-}"; k=$((k + 1)) ;;
    --repo=*) repo="${w#--repo=}" ;;
    -b|--body|-F|--body-file|-t|--subject|-A|--author-email|--match-head-commit) k=$((k + 1)) ;;
    -*) ;;
    *) [ -z "$target" ] && target="$w" ;;
  esac
done
if [[ "$target" =~ ^https://github\.com/([^/]+/[^/]+)/pull/[0-9]+ ]]; then repo="${BASH_REMATCH[1]}"; fi
here=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)
top=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [ -n "$repo" ] && [ "$repo" != "$here" ]; then  # another repo: read its config from GitHub
  conf=$(gh api "repos/$repo/contents/.github/codex-review.env" -H "Accept: application/vnd.github.raw" 2>/dev/null) || exit 0
else
  [ -n "$top" ] && [ -f "$top/.github/codex-review.env" ] || exit 0
  conf=$(cat "$top/.github/codex-review.env"); repo="$here"
fi
grep -qE '^CODEX_SCOPE="?off' <<<"$conf" && exit 0
pr="${target:-this branch}"
view=(gh pr view ${target:+"$target"} ${repo:+-R "$repo"})
body=$("${view[@]}" --json body -q .body 2>/dev/null) || {
  echo "Blocked: could not read PR $pr${repo:+ in $repo} to check its Codex review and CI." >&2; exit 2; }
if ! grep -qi 'codex review' <<<"$body"; then
  echo "Blocked: PR $pr has no \"Codex review\" section. Run scripts/codex-review.sh, verify the findings, add the section (or \"Codex review: skipped (...)\"), then merge." >&2
  exit 2
fi
checks=$(gh pr checks ${target:+"$target"} ${repo:+-R "$repo"} 2>&1); code=$?
if [ $code -eq 8 ]; then
  echo "Blocked: CI checks on PR $pr are still running. Wait for them (gh pr checks --watch), then merge." >&2
  exit 2
fi
if grep -q "no checks reported" <<<"$checks"; then
  grep -qE '^CODEX_REQUIRE_CI="?0' <<<"$conf" && exit 0  # a repo with no CI says so in its config
  echo "Blocked: no CI checks are registered on PR $pr yet (right after a push they take a moment). Wait and re-check; a repo with no CI sets CODEX_REQUIRE_CI=0 in .github/codex-review.env." >&2
  exit 2
fi
if [ $code -ne 0 ]; then
  echo "Blocked: CI checks on PR $pr failed:" >&2; grep -vE '\bpass\b|skipping' <<<"$checks" | head -5 >&2
  exit 2
fi
exit 0
