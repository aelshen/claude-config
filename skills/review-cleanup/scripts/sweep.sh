#!/bin/bash
# Deterministic sweep before an LLM review (review-cleanup skill, stage 1).
#   sweep.sh <repo-or-path> <out-dir>
# Finds TypeScript/JavaScript packages (package.json) and Python projects (pyproject.toml,
# requirements.txt, setup.py) up to 3 levels down, and runs whichever tools are already installed.
# Never installs anything: missing tools are listed with the command to add them. With
# SWEEP_ALLOW_NPX=1, npx may download knip and jscpd for this run.
# Each tool's output goes to <out-dir>/<root>.<tool>.txt; <out-dir>/summary.txt has one line per run.
set -uo pipefail
shopt -s nullglob
root=$(cd "${1:?usage: sweep.sh <repo-or-path> <out-dir>}" && pwd)
out=$(mkdir -p "${2:?usage: sweep.sh <repo-or-path> <out-dir>}" && cd "$2" && pwd)
summary="$out/summary.txt"; : > "$summary"
missing=()

note() { echo "$1" | tee -a "$summary"; }
# run <label> <file> <cmd...>: runs in the current directory, keeps all output, records exit code and size
run() {
  local label=$1 file=$2; shift 2
  "$@" > "$file" 2>&1; local rc=$?
  note "$(printf '%-34s exit %-3s %6s lines  %s' "$label" "$rc" "$(wc -l < "$file" | tr -d ' ')" "${file#$out/}")"
}
has() { command -v "$1" >/dev/null 2>&1; }
skip_dirs='-path */node_modules -prune -o -path */.venv -prune -o -path */venv -prune -o -path */.git -prune -o -path */dist -prune -o -path */build -prune -o'

# --- TypeScript / JavaScript --------------------------------------------------------------------
# shellcheck disable=SC2086
for pkg in $(find "$root" -maxdepth 3 $skip_dirs -name package.json -print | sort); do
  dir=$(dirname "$pkg"); name=$(basename "$dir"); [ "$dir" = "$root" ] && name=root
  [ -d "$dir/node_modules" ] || { note "$name: no node_modules, skipped (run the package manager's install first)"; continue; }
  cd "$dir" || continue
  bin="$dir/node_modules/.bin"
  [ -f tsconfig.json ] && [ -x "$bin/tsc" ] && run "$name tsc" "$out/$name.tsc.txt" "$bin/tsc" --noEmit
  if grep -q '"expo"' package.json && [ -x "$bin/expo" ]; then
    run "$name expo lint" "$out/$name.eslint.txt" "$bin/expo" lint
  elif [ -x "$bin/eslint" ]; then
    run "$name eslint" "$out/$name.eslint.txt" "$bin/eslint" . --max-warnings 0
  fi
  npx_flag=--no-install; [ "${SWEEP_ALLOW_NPX:-}" = 1 ] && npx_flag=--yes
  if [ -x "$bin/knip" ] || [ "$npx_flag" = --yes ]; then
    run "$name knip (unused files/exports/deps)" "$out/$name.knip.txt" npx $npx_flag knip --no-progress
  else missing+=("knip ($name): npm i -D knip, or SWEEP_ALLOW_NPX=1"); fi
  src=src; [ -d src ] || src=.
  if [ -x "$bin/jscpd" ] || [ "$npx_flag" = --yes ]; then
    run "$name jscpd (duplication)" "$out/$name.jscpd.txt" npx $npx_flag jscpd --min-lines 8 --min-tokens 70 \
      --ignore '**/node_modules/**,**/*.test.*,**/dist/**' --reporters console "$src"
  else missing+=("jscpd ($name): npm i -D jscpd, or SWEEP_ALLOW_NPX=1"); fi
done

# --- Python ---------------------------------------------------------------------------------------
# shellcheck disable=SC2086
pyroots=$(find "$root" -maxdepth 3 $skip_dirs \( -name pyproject.toml -o -name requirements.txt -o -name setup.py \) -print \
  | xargs -n1 dirname 2>/dev/null | sort -u)
# A project inside another (server/tests with its own requirements.txt) is part of the outer one.
outer=(); for d in $pyroots; do
  inside=; for o in ${outer[@]+"${outer[@]}"}; do case "$d/" in "$o"/*) inside=1;; esac; done
  [ -z "$inside" ] && outer+=("$d")
done
for dir in ${outer[@]+"${outer[@]}"}; do
  name=$(basename "$dir"); [ "$dir" = "$root" ] && name=root
  cd "$dir" || continue
  # Prefer a venv in the project or a parent folder (up to the sweep root), then PATH.
  tool() {
    local d=$dir
    while :; do
      for c in "$d/.venv/bin/$1" "$d/venv/bin/$1"; do [ -x "$c" ] && { echo "$c"; return; }; done
      [ "$d" = "$root" ] || [ "$d" = / ] && break; d=$(dirname "$d")
    done
    has "$1" && command -v "$1"
  }
  if t=$(tool ruff); then
    run "$name ruff (slop rules)" "$out/$name.ruff.txt" "$t" check --no-cache --output-format concise \
      --select E9,F,B,BLE,S110,TRY,ARG,SIM,C90,PLR0912,PLR0915,RET,PERF --exclude .venv,venv .
  else missing+=("ruff ($name): pip install ruff  (or: uvx ruff check ...)"); fi
  if t=$(tool vulture); then
    run "$name vulture (dead code)" "$out/$name.vulture.txt" "$t" . --min-confidence 80 --exclude .venv,venv
  else missing+=("vulture ($name): pip install vulture"); fi
  if t=$(tool radon); then
    run "$name radon (complexity C+)" "$out/$name.radon.txt" "$t" cc -s -n C -e '.venv/*,venv/*' .
  else missing+=("radon ($name): pip install radon"); fi
  for c in mypy pyright; do
    if t=$(tool $c); then run "$name $c" "$out/$name.$c.txt" "$t" .; break; fi
  done
  if t=$(tool bandit); then
    run "$name bandit (security)" "$out/$name.bandit.txt" "$t" -r . -ll -q -x ./.venv,./venv,./tests
  fi
done

# --- Security across languages --------------------------------------------------------------------
if has semgrep; then
  cd "$root" && run "semgrep (p/default)" "$out/semgrep.txt" semgrep scan --config p/default --quiet --error \
    --exclude node_modules --exclude .venv
else missing+=("semgrep: brew install semgrep  (optional; security patterns)"); fi

if [ ${#missing[@]} -gt 0 ]; then
  note ""; note "Not installed (the review still runs; these would find more for free):"
  for m in "${missing[@]}"; do note "  - $m"; done
fi
echo; echo "Outputs in $out"
