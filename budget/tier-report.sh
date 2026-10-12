#!/bin/bash
# Who spent what: tokens and list-price cost per agent type and model, from
# Claude Code transcripts in ~/.claude/projects. Use it to check that the model
# tiering (CLAUDE.md § Model Tiering) is saving anything.
#   tier-report.sh [days]   (default 7)
# Costs are API list prices; on a Pro/Max plan read them as relative weight.
set -euo pipefail
command -v jq >/dev/null || { echo "jq is required" >&2; exit 1; }
days=${1:-7}
root="$HOME/.claude/projects"

{
  # Main sessions: <project>/<session>.jsonl
  find "$root" -mindepth 2 -maxdepth 2 -name '*.jsonl' -mtime "-$days" -print0 |
    xargs -0 -r jq -c 'select(.type=="assistant" and .message.usage) |
      {who: "main", model: .message.model, id: .message.id, u: .message.usage}' 2>/dev/null
  # Subagents: <project>/<session>/subagents/agent-*.jsonl (+ .meta.json with agentType)
  find "$root" -path '*/subagents/agent-*.jsonl' -mtime "-$days" -print0 |
    while IFS= read -r -d '' f; do
      who=$(jq -r '.agentType // "unknown"' "${f%.jsonl}.meta.json" 2>/dev/null || echo unknown)
      jq -c --arg who "$who" 'select(.type=="assistant" and .message.usage) |
        {who: $who, model: .message.model, id: .message.id, u: .message.usage}' "$f" 2>/dev/null
    done
} | jq -rs '
  # $/MTok: [input, output]. Cache: read 0.1x, 5m write 1.25x, 1h write 2x.
  def price(m): if   (m|test("opus"))   then [4, 20]
                elif (m|test("fable|mythos")) then [10, 50]
                elif (m|test("sonnet")) then [2, 10]
                elif (m|test("haiku"))  then [0.10, 0.50]
                else [0, 0] end;
  def cost: price(.model) as [$i, $o]
    | (.u.input_tokens // 0) * $i
    + (.u.cache_read_input_tokens // 0) * $i * 0.1
    + (.u.cache_creation.ephemeral_5m_input_tokens // 0) * $i * 1.25
    + (.u.cache_creation.ephemeral_1h_input_tokens // 0) * $i * 2
    + (.u.output_tokens // 0) * $o
    | . / 1e6;
  map(select(.model and (.model | startswith("<") | not))) | unique_by(.id)
  | group_by([.who, .model])
  | map({who: .[0].who, model: .[0].model, calls: length,
         input: (map((.u.input_tokens // 0) + (.u.cache_read_input_tokens // 0) + (.u.cache_creation_input_tokens // 0)) | add),
         output: (map(.u.output_tokens // 0) | add),
         cost: (map(cost) | add)})
  | sort_by(-.cost) as $rows
  | ($rows | map(.cost) | add // 0) as $total
  | (["AGENT", "MODEL", "CALLS", "IN_TOK", "OUT_TOK", "COST_USD", "SHARE"] | @tsv),
    ($rows[] | [.who, .model, .calls, .input, .output,
                (.cost * 100 | round / 100), "\((.cost / ([$total, 1e-9] | max) * 100) | round)%"] | @tsv),
    (["TOTAL", "", "", "", "", ($total * 100 | round / 100), ""] | @tsv)
' | column -t -s $'\t'
echo "(last $days days; list prices; Haiku priced at its <=100K-prompt rate)"
