---
name: remote-sessions
description: "How the owner runs Claude Code sessions on the Mac mini so they can be reached from the iPhone: one tmux session per project (ccs), opened from Warp tabs on the Mac and from Termius over Tailscale on the phone (cc), plus `preview` links for local dev servers and files. Use when starting a long-running session, moving an existing session into tmux, opening something on the owner's phone, or debugging the phone connection. Triggers on: tmux, ccs, cc, Termius, mosh, phone, remote session, from my phone, preview link, open this on my phone, Warp tabs, launch configuration, hub."
---

# Remote sessions: the Mac from the phone

Set up 2026-10-28. Claude sessions run inside tmux on the Mac mini, one tmux session per project.
On the Mac each one is a Warp tab; on the phone, Termius attaches to the same sessions. Nothing
goes through a third party: the phone reaches the Mac over Tailscale only.

## The commands (in `bin/`, linked into `~/.local/bin`)

| Command | What it does |
|---|---|
| `ccs <name> <dir> [claude args]` | Open, or reattach to, the tmux session `<name>` running Claude in `<dir>`. Starts Claude with `--dangerously-skip-permissions` (the owner's default; `CCS_PROMPTS=1 ccs …` for a session with prompts). With `-c` it continues the last conversation in `<dir>`, or starts fresh if there is none |
| `ccs <name> <dir> --resume <id>` | Continue one specific conversation (use this when several sessions share a folder: `-c` picks the newest, which may be another session's) |
| `cc` | From the phone: attach and show the session picker |
| `preview <port>` | Mirror `localhost:<port>` to `http://<mac>:<port>/` for the tailnet, and print the link |
| `preview <file or dir>` | Share that folder on `http://<mac>:8099/<folder>/` and print the file's link (mockups, PDFs, screenshots) |
| `preview list` / `preview off` | What is shared / stop sharing everything |

When you start a dev server or produce a mockup the owner should look at, run `preview` and give them
the link: they may be reading on the phone. Only tailnet devices can open it.

## Keys in the picker and inside sessions

Switch: tap or arrows, then Enter. Kill: `x`, then `y` (stops that Claude; `ccs … -c` brings the
conversation back). Close the picker: `q`. Inside a session: `Ctrl-b s` opens the picker, `Ctrl-b d`
disconnects without stopping anything. Closing a Warp tab only disconnects; the session keeps running.
To end one: `/exit` in Claude, then `exit`.

## The pieces

| Piece | Where |
|---|---|
| Mac on Tailscale | `ahmads-mac-mini`, 100.81.140.122 (owner's tailnet `aelshen@github`) |
| SSH | Remote Login on. `/etc/ssh/sshd_config.d/100-phone-access.conf`: keys only, `AllowUsers ahmadelshenawy`, no root |
| Phone | Termius (free tier; Blink was $20/yr). Key "aelshen-mac" (Termius SSH ID). Mosh on |
| Phone key | `~/.ssh/authorized_keys`: `command="~/.local/bin/cc-login",restrict,pty` (terminal only, no forwarding) |
| `cc-login` | Plain login → `cc`. A command the app sends runs as sent, except `mosh-server new` gets `-- cc` appended so mosh opens the picker too |
| tmux config | `tmux.conf` here, linked to `~/.tmux.conf`: mouse on, status bar off, Warp tab title = session name |
| Warp tabs | Launch configuration `~/.warp/launch_configurations/claude-sessions.yaml` (copy in `warp-claude-sessions.yaml`): work, checkpoint, arabayya, delphi, playpatch, each `ccs <name> <dir> -c` |
| PATH for remote logins | `~/.zshenv` adds `/opt/homebrew/bin` (tmux, mosh-server) and `~/.local/bin` |

Access: the tailnet policy gives owner/admin full access; invited members (Harriet) only reach the
NAS's Photos ports, so they cannot reach the Mac.

## Moving a session into tmux

`/exit` it in Warp, then in the same tab `ccs <name> <dir> -c` (or `--resume <id>` if other sessions
share the folder). The conversation comes back; instruction files are re-read on resume.

## What carries over

- **Messaging between sessions** (ListAgents / SendMessage) works the same inside tmux.
- **Login** is one file, `~/.claude/.credentials.json` (mode 600), shared by every session.
- **Claude Code updates:** new sessions get the new version; running ones keep theirs until reopened.
- **Settings, CLAUDE.md, skills, memory:** shared files; new sessions always see the latest.

## Traps met so far

- **A tmux server started from the phone can't read the Mac's Keychain** (remote logins have no GUI
  security session), so Claude inside it asks to log in. `/login` then saves to
  `~/.claude/.credentials.json`, which every session uses from then on. Prefer starting the tmux server
  from Warp.
- **Termius ends every command it sends with a newline.** `cc-login` strips trailing whitespace before
  appending `-- cc`; without that, the append ran as a second, failing command and Termius gave up.
- **mosh opens a plain shell** unless given a command, so a forced `command=` alone doesn't put mosh
  logins into the picker.
- **Termius runs probe commands on each login** (`echo $SHELL`, `uname`, `cat ~/.bash_history`). They
  go through `cc-login` unchanged. Turn off its history features if that matters.
- **`sudo sshd -t` fails with "no hostkeys available"** until Remote Login has been turned on once
  (macOS creates the host keys then).
- **Claude Code isn't on PATH for non-interactive SSH** unless `~/.zshenv` sets it; `ccs` calls
  `~/.local/bin/claude` directly.
- **`preview <port>` shows a dead link for `expo start --localhost`**: Expo listens on IPv6 `[::1]` only, while
  `preview` proxies to `127.0.0.1`. Check with `lsof -nP -iTCP:<port> -sTCP:LISTEN`; if it says `[::1]`, run
  `tailscale serve --bg --http=<port> "http://[::1]:<port>"` instead. The tailnet link stays the same.
- **Scrolling on the phone:** Claude Code's fullscreen mode (alternate screen + mouse capture) keeps scrolling
  to itself, and Termius swipes don't drive it well. `ccs` starts sessions with
  `CLAUDE_CODE_DISABLE_ALTERNATE_SCREEN=1` (classic renderer), so output lands in tmux history and a swipe or
  the wheel scrolls it. Sessions started before this change keep fullscreen until reopened with `ccs`.
- **Option-Delete (delete word) doesn't work in tmux by default:** Warp sends it as a plain Delete
  unless the app switches on Warp's extended keyboard mode, which Claude does outside tmux but can't through
  tmux. Fix in Warp: Settings → Features → Keys → "Left Option key is Meta" (right Option still types
  special characters). tmux extended-keys did not help. Ctrl-W always works.
