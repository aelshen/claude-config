# Codex: shared guidance (linked to ~/.codex/AGENTS.md by claude-config's install.sh)

The repo's own AGENTS.md and the review rules it points at (REVIEW.md, CLAUDE.md doctrine) come first.

## When reviewing a change (`codex review`)
- Report defects a reviewer must act on: wrong behaviour, data loss, privacy or security leaks, a second code path or
  cache the change forgot, broken deploy or rollback. Cite file:line and the concrete input that breaks.
- Not findings: style, naming, comments, "consider adding a test" without a failing case, and anything the repo's
  review rules call deliberate.
- Your sandbox cannot open network sockets: a test that starts a server or calls the network failing there is not a
  finding. Say once that you could not run it.
- Only the committed diff is under review; untracked local files are not part of the change.
