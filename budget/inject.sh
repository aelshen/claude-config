#!/bin/bash
# UserPromptSubmit: one line of budget facts every turn; a directive only
# when a threshold is crossed. Numbers come from the status line's cache.
CTX_WARN=${CLAUDE_BUDGET_CTX_WARN:-80}; CTX_ACT=${CLAUDE_BUDGET_CTX_ACT:-85}
LIM_WARN=${CLAUDE_BUDGET_LIM_WARN:-80}; LIM_ACT=${CLAUDE_BUDGET_LIM_ACT:-92}
sid=$(jq -r '.session_id // empty')
f="$HOME/.claude/state/budget/$sid.json"
[ -n "$sid" ] && [ -f "$f" ] || exit 0
jq -c --argjson cw "$CTX_WARN" --argjson ca "$CTX_ACT" --argjson lw "$LIM_WARN" --argjson la "$LIM_ACT" '
  def t: localtime | strftime("%a %H:%M");
  def left($s): ($s - now) as $d | if $d <= 0 then "now" else "in \($d/3600|floor)h\(($d%3600)/60|floor|tostring|if length<2 then "0"+. else . end)m" end;
  def win($n; $w): if $w == null then empty else "\($n) \($w.used_percentage|floor)% used (resets \($w.resets_at|t), \(left($w.resets_at)))" end;
  (.ctx_pct // 0) as $ctx
  | ([.five_hour.used_percentage, .seven_day.used_percentage] | map(. // 0) | max) as $lim
  | (now - .updated_at | floor) as $age
  | ([ (if .ctx_pct == null then "context n/a (no API response yet)" else "context \($ctx|floor)% of \((.ctx_size // 0)/1000|floor)k" end), win("5h"; .five_hour), win("7d"; .seven_day) ] | join(" · ")) as $facts
  | [ "[budget] \($facts) · as of \($age)s ago" ]
    + (if $ctx >= $ca then ["[budget ACTION] Context is at \($ctx|floor)%. Start the handoff now, even mid-task: run the session-handoff skill, then tell the user to /compact (same task) or /clear (different task). Finish the current step only after the notes are written."]
       elif $ctx >= $cw then ["[budget] Context past \($cw)%: at the next natural break, write state with the session-handoff skill before starting any large new step."] else [] end)
    + (if $lim >= $la then ["[budget ACTION] Plan limit at \($lim|floor)%. Do not start new work or subagents. Write resume notes now (session-handoff skill), then tell the user what is left and when the limit resets."]
       elif $lim >= $lw then ["[budget] Plan limit past \($lw)%: size the remaining work to fit, prefer doing it inline over spawning subagents or workflows."] else [] end)
  | {hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: join("\n")}}' "$f"
