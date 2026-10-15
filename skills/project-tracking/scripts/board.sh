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
#   BOARD_SINCE=2026-10-06    # optional; PRs merged before this (pre-adoption) aren't flagged
# Needs gh (with the `project` scope: gh auth refresh -s project) and jq.
# Bash 3.2 compatible (macOS /bin/bash).
set -euo pipefail

die() { echo "board.sh: $*" >&2; exit 1; }

root="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not inside a git repo"
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

item_for() { # issue number -> project item id. item-add is idempotent and returns the id
  # directly, so this never waits on item-list (which lags minutes behind adds).
  gh project item-add "$BOARD_PROJECT" --owner "$BOARD_OWNER" \
    --url "https://github.com/$BOARD_REPO/issues/$1" --format json --jq .id
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

items_json() { # this repo's board items as [{n, status, priority, id}]
  gh project item-list "$BOARD_PROJECT" --owner "$BOARD_OWNER" --limit 2000 --format json |
    jq --arg r "$BOARD_REPO" '[.items[] | select(.content.repository == $r and .content.type == "Issue")
      | {n: .content.number, status: (.status // null), priority: (.priority // null), id, title: .content.title}]'
}

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in
  add)
    [ $# -ge 1 ] || die "usage: board.sh add <issue#> [Column] [P0-P3]"
    item="$(item_for "$1")"
    set_option "$item" Status "${2:-Backlog}"
    [ -n "${3:-}" ] && set_option "$item" Priority "$3"
    echo "#$1 → ${2:-Backlog}${3:+ ($3)}" ;;
  move)
    [ $# -eq 2 ] || die "usage: board.sh move <issue#> <Column>"
    set_option "$(item_for "$1")" Status "$2"
    echo "#$1 → $2" ;;
  prio)
    [ $# -eq 2 ] || die "usage: board.sh prio <issue#> <P0-P3>"
    set_option "$(item_for "$1")" Priority "$2"
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
      and ((.body // "") | test("(?i)\\b(close[sd]?|fix(e[sd])?|resolve[sd]?|refs?|part of)\\s+([\\w.-]+/[\\w.-]+)?#[0-9]+") | not))
      | "PR #\(.number) \(.title)"' <<< "$merged")"
    if [ -z "$actions" ]; then echo "Board in step with issues."; else
      echo "Drift ($( [ "$apply" = true ] && echo fixing || echo "dry run; --apply to fix")):"
      while IFS=$'\t' read -r n col why; do
        echo "  #$n → $col   ($why)"
        if [ "$apply" = true ]; then set_option "$(item_for "$n")" Status "$col"; fi
      done <<< "$actions"
    fi
    if [ -n "$unlinked" ]; then
      echo "Merged PRs (last 30${BOARD_SINCE:+, since $BOARD_SINCE}) with no issue link and no no-issue label:"
      echo "$unlinked" | sed 's/^/  /'
    fi ;;
  *) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; [ -z "$cmd" ] || exit 2 ;;
esac
