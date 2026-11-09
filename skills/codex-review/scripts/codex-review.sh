#!/usr/bin/env bash
# Codex peer review before a PR merges: one shared copy for every repo (repos keep a stub in scripts/codex-review.sh).
# Reviews the branch's COMMITTED changes against a base with `codex review`; Codex reads the repo's AGENTS.md (point it
# at the house review rules). Findings are leads: verify each, fix it or say in the PR why not.
#
#   codex-review.sh [base]                    review this branch (base: origin/main); logs the run
#   codex-review.sh mark [-R owner/repo] <pr> <real> <noise> [note]   record what the findings turned out to be
#   codex-review.sh report [days]             per repo: PRs, rounds, findings, real, noise, time
#
# Per-repo config, .github/codex-review.env (no file = review everything):
#   CODEX_SCOPE=all|risky|off     risky: review only when a changed file matches CODEX_PATHS
#   CODEX_PATHS="supabase/* server/identity.py"   bash patterns; * also matches /
#   CODEX_EXCLUDE="tests/golden/* app/src/i18n/*"  changes only here are never reviewed
# Log: ${CODEX_REVIEW_STATE:-~/.claude/state/codex-review}/{runs,marks}.tsv
set -euo pipefail
state="${CODEX_REVIEW_STATE:-$HOME/.claude/state/codex-review}"
mkdir -p "$state"
runs="$state/runs.tsv" marks="$state/marks.tsv"
[ -f "$runs" ] || printf 'date\trepo\tbranch\tpr\tround\tsecs\tfindings\tp1\toutput\n' >"$runs"
[ -f "$marks" ] || printf 'date\trepo\tpr\treal\tnoise\tnote\n' >"$marks"

# the origin's repo name, not the checkout's folder (a worktree is named after its branch)
repo_name() { local u; u=$(git remote get-url origin 2>/dev/null) || u=$(git rev-parse --show-toplevel); u="${u%.git}"; echo "${u##*[/:]}"; }

report() {
  local days="${1:-3650}" since
  since=$(date -v-"${days}"d '+%Y-%m-%d' 2>/dev/null || date -d "-$days days" '+%Y-%m-%d')
  awk -F'\t' -v since="$since" '
    FNR == 1 { next }
    FILENAME ~ /runs/ && $1 >= since { r[$2]++; s[$2] += $6; f[$2] += $7; p1[$2] += $8; if ($4 != "") prs[$2 SUBSEP $4] = 1; repos[$2] = 1 }
    FILENAME ~ /marks/ && $1 >= since { real[$2] += $4; noise[$2] += $5; m[$2]++; repos[$2] = 1 }
    END {
      printf "%-14s %5s %6s %8s %4s %5s %6s %8s\n", "repo", "PRs", "rounds", "findings", "P1", "real", "noise", "avg secs"
      for (k in prs) { split(k, a, SUBSEP); n[a[1]]++ }
      for (x in repos) printf "%-14s %5d %6d %8d %4d %5d %6d %8d\n", x, n[x], r[x], f[x], p1[x], real[x], noise[x], r[x] ? s[x] / r[x] : 0
      print "(findings and P1 are counted from the runs; real and noise from `mark`, once per PR)"
    }' "$runs" "$marks"
}

case "${1:-}" in
  report) shift; report "$@"; exit ;;
  mark)  # mark [-R owner/repo] <pr> <real> <noise> [note]: -R when the PR is in another repo than this checkout
    shift; name=""
    if [ "${1:-}" = -R ]; then name="${2##*/}"; shift 2; fi
    [ $# -ge 3 ] || { echo "usage: $0 mark [-R owner/repo] <pr> <real> <noise> [note]" >&2; exit 2; }
    name="${name:-$(repo_name)}"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d')" "$name" "$1" "$2" "$3" "${4:-}" >>"$marks"
    echo "marked $name #$1: $2 real, $3 noise"; exit ;;
  -h|--help|help) sed -n '2,16p' "$0"; exit ;;
esac

cd "$(git rev-parse --show-toplevel)"
base="${1:-origin/main}"
command -v codex >/dev/null || { echo "codex CLI not found (npm i -g @openai/codex, then codex login)" >&2; exit 1; }
# Only committed work leaves this machine: refuse a dirty tree (untracked files never go).
[ -z "$(git status --porcelain --untracked-files=no)" ] || { echo "commit or stash your changes first: only the committed diff is reviewed" >&2; exit 1; }
git fetch -q origin
changed=$(git diff --name-only "$base"...HEAD)
[ -n "$changed" ] || { echo "no changes against $base" >&2; exit 1; }

CODEX_SCOPE=all CODEX_PATHS="" CODEX_EXCLUDE=""
[ -f .github/codex-review.env ] && . .github/codex-review.env
matches() {  # matches <file> <patterns...>
  local f="$1" p; shift
  for p in "$@"; do [[ "$f" == $p ]] && return 0; done
  return 1
}
kept=() risky=0
while IFS= read -r f; do
  # shellcheck disable=SC2086
  matches "$f" $CODEX_EXCLUDE && continue
  kept+=("$f")
  # shellcheck disable=SC2086
  matches "$f" $CODEX_PATHS && risky=1
done <<<"$changed"
skip=""
[ "$CODEX_SCOPE" = off ] && skip="off for this repo"
[ -z "$skip" ] && [ ${#kept[@]} -eq 0 ] && skip="only excluded paths changed"
[ -z "$skip" ] && [ "$CODEX_SCOPE" = risky ] && [ $risky -eq 0 ] && skip="no risky paths changed"
if [ -n "$skip" ]; then
  echo "Codex review: skipped ($skip). Put that line in the PR's \"Codex review\" section."
  exit 0
fi

branch=$(git branch --show-current)
pr=$(gh pr view --json number -q .number 2>/dev/null || true)
round=$(( $(awk -F'\t' -v r="$(repo_name)" -v b="$branch" '$2 == r && $3 == b' "$runs" | wc -l) + 1 ))
[ "$round" -le 2 ] || echo "round $round: past two rounds, review again only to check a P1 fix" >&2

out="$(mktemp "${TMPDIR:-/tmp}/codex-review.XXXXXX")"
start=$(date +%s)
# Codex writes its transcript to stderr and the verdict to stdout.
codex review --base "$base" >"$out.verdict" 2>"$out" || { echo "codex review failed; output: $out" >&2; tail -20 "$out" >&2; exit 1; }
secs=$(( $(date +%s) - start ))
if [ -s "$out.verdict" ]; then
  verdict=$(cat "$out.verdict")
else  # fallback: everything after the transcript's last line that is just "codex"
  verdict=$(awk '/^codex$/ { buf = ""; found = 1; next } found { buf = buf $0 "\n" } END { printf "%s", buf }' "$out")
fi
printf '%s\n' "$verdict"
findings=$(grep -cE '^\s*- \[P[0-9]\]' <<<"$verdict" || true)
p1=$(grep -cE '^\s*- \[P[01]\]' <<<"$verdict" || true)
printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$(date '+%Y-%m-%d %H:%M')" "$(repo_name)" "$branch" "$pr" "$round" "$secs" "$findings" "$p1" "$out" >>"$runs"
echo
echo "(round $round, $secs s, $findings finding(s); full output: $out)"
echo "When the PR is settled: $0 mark ${pr:-<pr>} <real> <noise> \"note\""
