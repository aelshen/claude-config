#!/usr/bin/env bash
# audit.sh — score the current repo against the project-tracking standard.
#
#   audit.sh          report only
#   audit.sh --fix    also add what is missing: labels, issue forms, PR template,
#                     the PR-links-issue workflow, docs/WORKFLOW.md, scripts/board.sh.
#                     Never overwrites an existing file or label.
#
# Run from inside the repo. Board checks need .github/board.env (see board.sh).
# Bash 3.2 compatible.
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
assets="$here/../assets"
fix=false; [ "${1:-}" = "--fix" ] && fix=true
root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "not inside a git repo" >&2; exit 2; }
cd "$root"
repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null)" || { echo "gh can't see this repo" >&2; exit 2; }

fails=0; warns=0
pass() { echo "  PASS  $*"; }
warn() { echo "  WARN  $*"; warns=$((warns + 1)); }
fail() { echo "  FAIL  $*"; fails=$((fails + 1)); }

place() { # asset path, repo path: copy if missing (with --fix)
  if [ -e "$2" ]; then pass "$2"; return; fi
  if [ "$fix" = true ]; then mkdir -p "$(dirname "$2")"; cp "$assets/$1" "$2"; echo "  ADDED $2"; else fail "$2 missing"; fi
}

env_file="${BOARD_ENV:-.github/board.env}"
# shellcheck disable=SC1090
[ -f "$env_file" ] && . "$env_file"

echo "Project tracking audit: $repo"

echo "Files"
place WORKFLOW.md docs/WORKFLOW.md
forms=$(grep -l "Acceptance criteria" .github/ISSUE_TEMPLATE/*.yml 2>/dev/null | wc -l | tr -d ' ')
if [ "$forms" -ge 1 ]; then pass "$forms issue form(s) with acceptance criteria"
else place ISSUE_TEMPLATE/task.yml .github/ISSUE_TEMPLATE/task.yml; place ISSUE_TEMPLATE/epic.yml .github/ISSUE_TEMPLATE/epic.yml; fi
grep -lq "How to verify" .github/ISSUE_TEMPLATE/*.yml 2>/dev/null && pass "an issue form has 'How to verify'" || warn "no issue form has a 'How to verify' section"
grep -lq "type:bug" .github/ISSUE_TEMPLATE/*.yml 2>/dev/null && pass "a bug form (type:bug)" || place ISSUE_TEMPLATE/bug.yml .github/ISSUE_TEMPLATE/bug.yml
pr_tpl="$(ls .github/pull_request_template.md .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null | head -1)"
if [ -z "$pr_tpl" ]; then place pull_request_template.md .github/pull_request_template.md
elif grep -Eiq '(closes|fixes|refs) #' "$pr_tpl"; then pass "$pr_tpl asks for an issue link"
else warn "$pr_tpl doesn't ask for 'Closes #N'"; fi
if [ "${BOARD_PR_CHECK:-on}" = off ]; then pass "PR check off by config (BOARD_PR_CHECK=off)"
else place workflows/pr-links-issue.yml .github/workflows/pr-links-issue.yml; fi
if [ -e scripts/board.sh ]; then
  if grep -q "project-tracking" scripts/board.sh; then pass "scripts/board.sh uses the shared helper"
  else warn "scripts/board.sh is a local copy; replace it with the shim (assets/board-shim.sh) so fixes reach every repo"; fi
elif [ "$fix" = true ]; then mkdir -p scripts; cp "$assets/board-shim.sh" scripts/board.sh; chmod +x scripts/board.sh; echo "  ADDED scripts/board.sh"
else fail "scripts/board.sh missing"; fi

echo "Labels"
have="$(gh label list -R "$repo" -L 200 --json name --jq '.[].name')"
grep -v '^#' "$assets/labels.tsv" | while IFS=$'\t' read -r name color desc; do
  [ -n "$name" ] || continue
  if printf '%s\n' "$have" | grep -qx "$name"; then continue; fi
  if [ "$fix" = true ]; then gh label create "$name" -R "$repo" --color "$color" --description "$desc" > /dev/null && echo "  ADDED label $name"
  else echo "  FAIL  label $name missing"; fi
done
missing=$(grep -v '^#' "$assets/labels.tsv" | cut -f1 | while read -r n; do printf '%s\n' "$have" | grep -qx "$n" || echo "$n"; done | wc -l | tr -d ' ')
[ "$fix" = true ] || { [ "$missing" = 0 ] && pass "standard labels present" || fails=$((fails + 1)); }
printf '%s\n' "$have" | grep -q '^area:' && pass "area:* labels defined" || fail "no area:* labels (define this repo's areas)"
printf '%s\n' "$have" | grep -Eqx 'P[0-3]' && warn "P0-P3 labels exist: priority belongs in the board's Priority field (labels can't sort the board)"

echo "Board"
if [ ! -f "$env_file" ]; then fail ".github/board.env missing (BOARD_OWNER, BOARD_PROJECT, BOARD_SINCE)"
else
  fields="$(gh project field-list "$BOARD_PROJECT" --owner "$BOARD_OWNER" --format json 2>/dev/null)"
  if [ -z "$fields" ]; then fail "can't read project $BOARD_OWNER/$BOARD_PROJECT (gh auth refresh -s project?)"
  else
    status="$(jq -r '.fields[] | select(.name == "Status") | [.options[].name] | join("|")' <<< "$fields")"
    [ "$status" = "Backlog|Ready|In progress|In review|Done" ] && pass "Status columns" || fail "Status columns are '$status', want Backlog|Ready|In progress|In review|Done (rename in the board's settings)"
    prio="$(jq -r '.fields[] | select(.name == "Priority") | [.options[].name] | join("|")' <<< "$fields")"
    if [ "$prio" = "P0|P1|P2|P3" ]; then pass "Priority field"
    elif [ "$fix" = true ] && [ -z "$prio" ]; then
      gh project field-create "$BOARD_PROJECT" --owner "$BOARD_OWNER" --name Priority --data-type SINGLE_SELECT \
        --single-select-options "P0,P1,P2,P3" > /dev/null && echo "  ADDED Priority field"
    else fail "Priority field is '${prio:-missing}', want P0|P1|P2|P3"; fi
    # Built-in project workflows (no API to switch them on: Project → ⋯ → Workflows).
    q='query($o:String!,$n:Int!){ %s(login:$o){ projectV2(number:$n){ workflows(first:20){ nodes{ name enabled } } } } }'
    wf="$(gh api graphql -f query="$(printf "$q" organization)" -f o="$BOARD_OWNER" -F n="$BOARD_PROJECT" --jq '.data.organization.projectV2.workflows.nodes' 2>/dev/null ||
          gh api graphql -f query="$(printf "$q" user)" -f o="$BOARD_OWNER" -F n="$BOARD_PROJECT" --jq '.data.user.projectV2.workflows.nodes' 2>/dev/null)"
    for w in "Item closed" "Pull request merged" "Pull request linked to issue" "Auto-add to project"; do
      on="$(jq -r --arg w "$w" '.[] | select(.name == $w) | .enabled' <<< "${wf:-[]}" 2>/dev/null)"
      [ "$on" = true ] && pass "board workflow '$w' on" || fail "board workflow '$w' is off (Project → ⋯ → Workflows)"
    done
  fi
  echo "Practice"
  sync="$("$here/board.sh" sync 2>&1)"
  drift=$(printf '%s\n' "$sync" | grep -c '^  #')
  unlinked=$(printf '%s\n' "$sync" | grep -c '^  PR #')
  [ "$drift" = 0 ] && pass "no board drift" || fail "$drift card(s) out of step (board.sh sync --apply)"
  [ "$unlinked" = 0 ] && pass "recent merged PRs all link an issue" || warn "$unlinked recent merged PR(s) with no issue link (board.sh sync lists them)"
fi

echo
echo "Result: $fails fail, $warns warn"
[ "$fails" = 0 ]
