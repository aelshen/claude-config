#!/bin/bash
# PreToolUse on Agent/Workflow: ask once near the 5h/7d limit, refuse at the edge.
ASK=${CLAUDE_BUDGET_BRAKE_ASK:-90}; DENY=${CLAUDE_BUDGET_BRAKE_DENY:-97}
sid=$(jq -r '.session_id // empty')
f="$HOME/.claude/state/budget/$sid.json"
[ -n "$sid" ] && [ -f "$f" ] || exit 0
jq -c --argjson a "$ASK" --argjson d "$DENY" '
  ([.five_hour.used_percentage, .seven_day.used_percentage] | map(. // 0) | max) as $lim
  | if $lim >= $d then {hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
        permissionDecisionReason: "Plan limit at \($lim|floor)%: no new subagents. Finish inline or write resume notes."}}
    elif $lim >= $a then {hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "ask",
        permissionDecisionReason: "Plan limit at \($lim|floor)%. Spawn a subagent anyway?"}}
    else empty end' "$f"
