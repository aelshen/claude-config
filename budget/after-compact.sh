#!/bin/bash
# SessionStart(compact|clear): point Claude back at any notes it wrote.
src=$(jq -r '.source // empty')
jq -nc --arg s "$src" '{hookSpecificOutput: {hookEventName: "SessionStart",
  additionalContext: "[budget] Session restarted via \($s). Before continuing, read the latest handoff notes (HANDOFF.md or the repo working-notes dir) and resume from their Next section."}}'
