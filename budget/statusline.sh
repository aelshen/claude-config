#!/bin/bash
# Status line: renders context + plan limits for you, and caches the same
# numbers per session so the UserPromptSubmit hook can show them to Claude.
input=$(cat)
dir="$HOME/.claude/state/budget"
sid=$(jq -r '.session_id // empty' <<<"$input")
if [ -n "$sid" ]; then
  jq -c '{updated_at: now, model: .model.display_name,
          ctx_pct: .context_window.used_percentage, ctx_size: .context_window.context_window_size,
          five_hour: .rate_limits.five_hour, seven_day: .rate_limits.seven_day}' <<<"$input" \
    > "$dir/$sid.tmp" && mv "$dir/$sid.tmp" "$dir/$sid.json"
  find "$dir" -name '*.json' -mtime +7 -delete 2>/dev/null
fi
jq -r '
  def c($p): if $p == null then "" elif $p >= 85 then "\u001b[31m" elif $p >= 60 then "\u001b[33m" else "\u001b[32m" end;
  def pct($p): if $p == null then "–" else "\($p | floor)%" end;
  def win($name; $w): if $w == null then empty
    else "\(c($w.used_percentage))\($name) \(pct($w.used_percentage))\u001b[0m ↻\($w.resets_at | localtime | strftime("%a %H:%M"))" end;
  .context_window.used_percentage as $cp
  | [ "\(.model.display_name)",
      "\(c($cp))ctx \(pct($cp))\u001b[0m of \((.context_window.context_window_size // 0) / 1000 | floor)k",
      win("5h"; .rate_limits.five_hour),
      win("7d"; .rate_limits.seven_day),
      ((.workspace.current_dir // "") | split("/") | last) ] | map(select(. != null and . != ""))
  | join("  ·  ")' <<<"$input"
