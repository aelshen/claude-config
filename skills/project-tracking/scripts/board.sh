#!/usr/bin/env bash
# board.sh — keep a repo's GitHub Project board in step with its issues.
# Part of the project-tracking skill; one copy serves every repo.
#
#   board.sh add  <issue#> [Column] [P0-P3]  add (idempotent) and set Status / Priority
#   board.sh move <issue#> <Column>          Backlog | Ready | "In progress" | "In review" | Done
#   board.sh prio <issue#> <P0-P3>           set Priority
#   board.sh list [Column]                   this repo's items, optionally one column
#   board.sh sync [--apply]                  find drift (closed-not-Done, open-not-on-board,
#                                            PR-open-not-In-review, unlinked merged PRs);
#                                            dry run unless --apply
#   board.sh refresh                         re-read field/option ids (after editing the board)
#
# Config: .github/board.env at the repo root, e.g.
#   BOARD_OWNER=Kuudoh        # org or user that owns the Project
#   BOARD_PROJECT=1           # project number
#   BOARD_REPO=Kuudoh/kuudoh  # optional; defaults to the current repo
#   BOARD_SINCE=2026-10-07    # optional, inclusive; set it to the day AFTER adoption
#                             # (compared in UTC: evening merges west of UTC are already tomorrow)
#   BOARD_PR_CHECK=off        # optional: repo has no PR check on purpose (e.g. a planning repo)
# Issue# -> item ids are cached per owner+project (git common dir, so worktrees share it;
# ~/.cache/project-tracking outside git), so move/prio skip item-add after the first touch.
# Needs gh (with the `project` scope: gh auth refresh -s project) and jq.
# Bash 3.2 compatible (macOS /bin/bash).
set -euo pipefail

die() { echo "board.sh: $*" >&2; exit 1; }

gh() { # pass-through; explain the error gh prints for a rate-limited `gh project` call
  local err rc=0
  err="$(mktemp)"
  command gh "$@" 2> "$err" || rc=$?
  if [ "$rc" -ne 0 ]; then
    cat "$err" >&2
    if grep -qiE 'unknown owner type|rate limit' "$err"; then
      echo "board.sh: GitHub's GraphQL limit (account-wide; 'gh api rate_limit' can still show quota). Wait a few minutes and retry once; don't loop." >&2
    fi
  fi
  rm -f "$err"
  return "$rc"
}

root="$(git rev-parse --show-toplevel 2>/dev/null)" || { [ -n "${BOARD_ENV:-}" ] || die "not inside a git repo"; root=; }  # BOARD_ENV: run outside a repo (a server image)
env_file="${BOARD_ENV:-$root/.github/board.env}"  # BOARD_ENV: audit a repo without writing into it
[ -f "$env_file" ] || die "no $env_file (see the project-tracking skill)"
# shellcheck disable=SC1091
. "$env_file"
: "${BOARD_OWNER:?BOARD_OWNER missing in .github/board.env}"
: "${BOARD_PROJECT:?BOARD_PROJECT missing in .github/board.env}"
BOARD_REPO="${BOARD_REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"

cache="${XDG_CACHE_HOME:-$HOME/.cache}/project-tracking/${BOARD_OWNER}-${BOARD_PROJECT}.tsv"

refresh() { # project id + every single-select field's options, one TSV line each
  mkdir -p "$(dirname "$cache")"
  {
    printf '__project\t%s\t\t\n' "$(gh project view "$BOARD_PROJECT" --owner "$BOARD_OWNER" --format json --jq .id)"
    gh project field-list "$BOARD_PROJECT" --owner "$BOARD_OWNER" --format json \
      --jq '.fields[] | select(.options) | .name as $f | .id as $fid | .options[] | [$f, $fid, .name, .id] | @tsv'
  } > "$cache.tmp" && mv "$cache.tmp" "$cache"
}

lookup() { # field name, option name -> "fieldId<TAB>optionId" (empty if unknown)
  [ -s "$cache" ] || refresh
  awk -F'\t' -v f="$1" -v o="$2" '$1 == f && $3 == o { print $2 "\t" $4; exit }' "$cache"
}

project_id() { [ -s "$cache" ] || refresh; awk -F'\t' '$1 == "__project" { print $2; exit }' "$cache"; }

# Issue# -> item id cache, one file per owner+project like $cache. It sits in the git common dir
# (shared by every worktree), or next to $cache outside git. Lines: "<repo>\t<issue#>\t<item id>".
common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || common=""
if [ -n "$common" ]; then items_cache="$common/project-tracking/${BOARD_OWNER}-${BOARD_PROJECT}.items.tsv"
else items_cache="${cache%.tsv}.items.tsv"; fi

cached_item() { [ -s "$items_cache" ] && awk -F'\t' -v r="$BOARD_REPO" -v n="$1" '$1 == r && $2 == n { print $3; exit }' "$items_cache" || true; }

forget_item() {
  [ -s "$items_cache" ] || return 0
  awk -F'\t' -v r="$BOARD_REPO" -v n="$1" '!($1 == r && $2 == n)' "$items_cache" > "$items_cache.tmp" || true
  mv "$items_cache.tmp" "$items_cache"
}

item_for() { # issue number -> project item id. Cached; on a miss item-add (idempotent) returns
  # the id directly, so this never waits on item-list (which lags minutes behind adds).
  local id
  case "$1" in ''|*[!0-9]*) die "not an issue number: '$1'" ;; esac
  id="$(cached_item "$1")"
  if [ -z "$id" ]; then
    id="$(gh project item-add "$BOARD_PROJECT" --owner "$BOARD_OWNER" \
      --url "https://github.com/$BOARD_REPO/issues/$1" --format json --jq .id)"
    [ -n "$id" ] || die "no project item for #$1 (not an issue number, or gh returned nothing)"
    mkdir -p "$(dirname "$items_cache")"
    printf '%s\t%s\t%s\n' "$BOARD_REPO" "$1" "$id" >> "$items_cache"
  fi
  printf '%s\n' "$id"
}

set_option() { # item id, field name, option name
  local ids
  ids="$(lookup "$2" "$3")"
  if [ -z "$ids" ]; then refresh; ids="$(lookup "$2" "$3")"; fi
  if [ -z "$ids" ]; then
    die "no option '$3' in field '$2'. Options: $(awk -F'\t' -v f="$2" '$1 == f { printf "%s; ", $3 }' "$cache")"
  fi
  gh project item-edit --id "$1" --project-id "$(project_id)" \
    --field-id "${ids%%$'\t'*}" --single-select-option-id "${ids#*$'\t'}" > /dev/null
}

set_for() { # issue number, field name, option name. A cached id can be stale (card deleted):
  # if the edit fails on one, drop it and retry once through item-add.
  local id cached
  cached="$(cached_item "$1")"; id="$(item_for "$1")"
  if [ -n "$cached" ] && ! set_option "$id" "$2" "$3"; then
    forget_item "$1"; set_option "$(item_for "$1")" "$2" "$3"
  else
    [ -n "$cached" ] || set_option "$id" "$2" "$3"
  fi
}

items_json() { # this repo's board items as [{n, status, priority, id}]
  gh project item-list "$BOARD_PROJECT" --owner "$BOARD_OWNER" --limit 2000 --format json |
    jq --arg r "$BOARD_REPO" '[.items[] | select(.content.repository == $r and .content.type == "Issue")
      | {n: .content.number, status: (.status // null), priority: (.priority // null), id, title: .content.title}]'
}

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in
  add)
    [ $# -ge 1 ] || die "usage: board.sh add <issue#> [Column] [P0-P3]"
    set_for "$1" Status "${2:-Backlog}"
    if [ -n "${3:-}" ]; then set_for "$1" Priority "$3"; fi
    echo "#$1 → ${2:-Backlog}${3:+ ($3)}" ;;
  move)
    [ $# -eq 2 ] || die "usage: board.sh move <issue#> <Column>"
    set_for "$1" Status "$2"
    echo "#$1 → $2" ;;
  prio)
    [ $# -eq 2 ] || die "usage: board.sh prio <issue#> <P0-P3>"
    set_for "$1" Priority "$2"
    echo "#$1 priority $2" ;;
  list)
    items_json | jq -r --arg c "${1:-}" '.[] | select($c == "" or .status == $c)
      | "#\(.n)\t\(.status // "-")\t\(.priority // "-")\t\(.title)"' ;;
  refresh)
    refresh; echo "cached $(wc -l < "$cache" | tr -d ' ') ids in $cache" ;;
  sync)
    apply=false; [ "${1:-}" = "--apply" ] && apply=true
    board="$(items_json)"
    issues="$(gh issue list -R "$BOARD_REPO" -s all -L 2000 --json number,state,title)"
    prs="$(gh pr list -R "$BOARD_REPO" -s open -L 200 --json number,closingIssuesReferences)"
    merged="$(gh pr list -R "$BOARD_REPO" -s merged -L 30 ${BOARD_SINCE:+--search "merged:>=$BOARD_SINCE"} \
      --json number,title,labels,closingIssuesReferences,body)"
    # One action per line: "<issue#>\t<Column>\t<reason>"
    actions="$(jq -rn --argjson b "$board" --argjson i "$issues" --argjson p "$prs" '
      ($b | map({key: (.n | tostring), value: .}) | from_entries) as $on
      | ([$p[].closingIssuesReferences[].number] | unique) as $inreview
      | $i[] | . as $x | ($on[$x.number | tostring]) as $card
      | if $x.state == "CLOSED" then
          (if $card and $card.status != "Done" then "\($x.number)\tDone\tclosed, card in \($card.status // "no column")" else empty end)
        elif ($card | not) then "\($x.number)\t\(if ([$x.number] | inside($inreview)) then "In review" else "Backlog" end)\topen, not on the board"
        elif ([$x.number] | inside($inreview)) and ($card.status != "In review") then "\($x.number)\tIn review\tPR open, card in \($card.status // "no column")"
        elif $card.status == "Done" then "\($x.number)\tBacklog\treopened, card in Done"
        else empty end')"
    unlinked="$(jq -r '.[] | select((.closingIssuesReferences | length) == 0
      and ([.labels[].name] | index("no-issue") | not)
      and ((.body // "") | gsub("(?s)```.*?```"; "") | gsub("`[^`]*`"; "") | test("(?i)\\b(close[sd]?|fix(e[sd])?|resolve[sd]?|refs?|part of)\\s+([\\w.-]+/[\\w.-]+)?#[0-9]+") | not))
      | "PR #\(.number) \(.title)"' <<< "$merged")"
    if [ -z "$actions" ]; then echo "Board in step with issues."; else
      echo "Drift ($( [ "$apply" = true ] && echo fixing || echo "dry run; --apply to fix")):"
      while IFS=$'\t' read -r n col why; do
        echo "  #$n → $col   ($why)"
        if [ "$apply" = true ]; then set_for "$n" Status "$col"; fi
      done <<< "$actions"
    fi
    if [ -n "$unlinked" ]; then
      echo "Merged PRs (last 30${BOARD_SINCE:+, since $BOARD_SINCE}) with no issue link and no no-issue label:"
      echo "$unlinked" | sed 's/^/  /'
    fi ;;
  *) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; [ -z "$cmd" ] || exit 2 ;;
esac
