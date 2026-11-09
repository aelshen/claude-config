---
name: sqn-1
description: "The shared VPS sqn-1 (Hetzner, Arm) that hosts arabayya, checkpoint and playpatch: how to reach it, the per-app layout, and the steps and traps for moving an app onto it (Docker Compose, keys from Infisical, Cloudflare tunnel). Use when deploying or moving a service to the server, SSHing to it, or debugging something running there. Triggers on: sqn-1, VPS, Hetzner, deploy to the server, move off the Mac, docker compose on the server, cloudflared on the server, 46.225.189.46."
---

# sqn-1, the shared server

One small server for every project, set up 2026-10-21. arabayya moved first (arabayya #438); its
`server/DEPLOY-VPS.md`, `server/compose.yaml` and `scripts/vps-deploy.sh` / `scripts/vps-remote.sh` are the reference
implementation. Keys follow the `secrets` skill ("On the VPS").

## The server

| Thing | Value |
|---|---|
| Machine | Hetzner Cloud CAX21: 4 Arm (Ampere) vCPU, 8 GB, 80 GB disk, Nuremberg. About $15 a month with backups |
| Address | 46.225.189.46 (IPv6 too). Hetzner project `sidequest` |
| OS | Ubuntu 26.04 LTS, aarch64, UTC, 4 GB swap (swappiness 10), unattended security updates |
| Users | `ahmad` (the owner, 1Password SSH key) and `claude` (agents, `~/.ssh/sqn_claude` on the owner's Mac). Both have passwordless sudo and are in `docker`. Root login and passwords are off; `AllowUsers ahmad claude` |
| SSH from the Mac | `ssh sqn-1` (the `claude` user, in `~/.ssh/config`) |
| Firewall | Hetzner firewall `sqn-ssh-only`, plus ufw: SSH in, nothing else. Web traffic comes in through Cloudflare tunnels, which connect outward |
| Installed | Docker CE + compose plugin (json logs capped at 10 MB × 5 per container), Infisical CLI |
| Keys | Machine identity `sqn-1` (org-level, Universal Auth, **Viewer on arabayya, checkpoint and playpatch**). Its client id and secret are in `/etc/infisical/vps.env` (root, 600). Nothing to create for a new app among those three |
| Backups | Hetzner's daily server backups (7 kept) |

Memory budget: 8 GB in total. arabayya's API uses about 2.3 GB (`mem_limit: 4g`). Give every service a `mem_limit`,
and resize the server (CAX31, 16 GB) before the total of the limits passes ~7 GB.

## Per-app layout (copy it)

| What | Where |
|---|---|
| Code | `/srv/<app>/repo.git` (bare; pushed from the Mac) and its checkout `/srv/<app>/repo` |
| Data | `/srv/<app>/data`, mounted into the container |
| Keys | `/etc/<app>/secrets.env` (root, 600), rewritten from Infisical `prod` by every deploy |
| Tunnel | `/etc/<app>/tunnel/config.yml` and `credentials.json` |
| Compose project | `name: <app>` in the repo's compose file, so containers and networks don't collide |

## Moving an app here

1. **Image on Arm.** Build it on the Mac first: `docker build --platform linux/arm64 ...`, and run it. The Mac is an
   M4, so dev and prod are both arm64 and what works locally works there. Check every image you pull has an arm64
   build (Postgres, Redis, MinIO, Meilisearch and cloudflared all do).
2. **Code.** The GitHub org has **deploy keys disabled**, so the server can't pull. Push from the Mac instead:
   `ssh sqn-1 'sudo install -d -o claude -g claude /srv/<app> && git init -q --bare /srv/<app>/repo.git && git -C /srv/<app>/repo.git symbolic-ref HEAD refs/heads/main'`,
   then `git remote add sqn-1 sqn-1:/srv/<app>/repo.git && git push sqn-1 main`, then clone it on the server.
   Setting the bare repo's HEAD to `main` matters: without it the clone has nothing to check out.
3. **Keys.** In the deploy script, run as root: source `/etc/infisical/vps.env`, run `infisical login --method=universal-auth ... --plain`,
   then `infisical export --env=prod --projectId=<id> --token=... --format=dotenv` to a temp file, check it has a
   key you expect, `chmod 600`, and `mv` it to `/etc/<app>/secrets.env`. Compose reads it with `env_file:`. The export
   single-quotes each value, and Compose takes single-quoted values literally (no `$` expansion; a one-line `.p8` with
   `\n` survives). Check inside the running container:
   `docker exec <c> printenv NAME | tr -d '\n' | sha256sum`, against the same hash on the Mac.
4. **Ports.** Publish only to loopback (`"127.0.0.1:<port>:<port>"`): **Docker-published ports bypass ufw**. Check
   from outside with `nc -z 46.225.189.46 <port>`.
5. **Data.** Copy SQLite with `sqlite3 x.db ".backup /tmp/x.db"` (safe while the app runs) and an integrity check.
   Copy folders with `COPYFILE_DISABLE=1 tar`: macOS tar otherwise adds `._*` files (and prints many "Ignoring
   unknown extended header keyword" warnings on Linux). `chown` the data to the uid the container runs as.
6. **Check it before the switch** over SSH: `ssh -f -N -L 8701:127.0.0.1:<port> sqn-1`, then compare responses with
   the Mac's.
7. **Tunnel.** Reuse the app's existing named tunnel: copy its credentials JSON from `~/.cloudflared/` to
   `/etc/<app>/tunnel/credentials.json`, owned by **65532** (the cloudflared image's user) with mode 400, and point the
   ingress at the Compose service name (`http://api:8000`), not localhost. `cloudflared tunnel ingress validate`
   works offline. Put the tunnel in a Compose `profiles: [tunnel]` so it starts only at the switch. Two connectors on
   one tunnel share traffic, so the switch is: stop the Mac's connector, then start the server's. Going back is the
   same in reverse, with no DNS change either way.
8. **Scheduled jobs.** launchd jobs on the Mac become in-process schedulers or cron on the server. While both run,
   jobs that write to shared services (Supabase, storage, push notifications) run twice. Check before starting the
   server copy.

9. **The switch** (arabayya's took about 2 minutes of downtime): `launchctl bootout` the Mac's app and tunnel jobs,
   stop the server's app, copy the data again (now final), start the app and `--profile tunnel` on the server, and
   check `cloudflared tunnel info <name>`: the only connector should be `linux_arm64` from 46.225.189.46. Then
   **move the Mac's old plists out of `~/Library/LaunchAgents`** (arabayya uses `~/Library/LaunchAgents-disabled/`),
   or they start again at the next login and split production traffic.
10. **Keep the Mac as dev.** Give it its own tunnel and hostname (`<app>-dev.sidequest.nexus`):
    `cloudflared tunnel --origincert ~/.cloudflared/cert-personal.pem create <app>-dev`, then `route dns`, a config
    file, and a launchd job. Point local dev (Expo's `app/.env`) at it, and keep builds on production. Turn off the
    dev copy's scheduled jobs that cost money or write to shared services.

## Images: built by GitHub Actions, pulled by the server (checkpoint #496, the standard)

The server never builds. Checkpoint is the reference (`.github/workflows/image.yml`, `scripts/vps-deploy.sh`,
`scripts/vps-remote.sh`); arabayya still builds on the server and should move to this.

- **Build:** on merge to main, a workflow runs the tests (the CI workflow made reusable with `workflow_call`), then
  `docker/build-push-action` builds for `linux/arm64` on **`runs-on: ubuntu-24.04-arm`** (native Arm; works on the
  org's free plan for private repos, about 3.5 min cold) and pushes `ghcr.io/side-quest-nexus/<app>:<commit>` and
  `:main` with `GITHUB_TOKEN` (`permissions: packages: write`) and `cache-from/to: type=gha`.
- **Pick:** the Mac's deploy script takes the newest run of that workflow on main (`gh run list --workflow image.yml
  --branch main --limit 1`), waits for it if running, stops if it failed. A docs-only commit has no run, and the newest
  image is still main's.
- **Pull:** in the root deploy script, log in with a classic token from Infisical (`GHCR_PULL_TOKEN`, only
  `read:packages`) into a throwaway `DOCKER_CONFIG` inside the deploy's temp dir, `docker pull`, `docker logout`, so no
  registry login stays on disk. Keep the token out of the container's env file.
- **Run:** tag the running image `<app>-api:previous`, tag the pulled one `<app>-api:latest` (the name compose and the
  jobs use), `up -d --no-build`, health check, roll back to `:previous` on failure, then `docker rmi` the pulled ghcr
  tags (the layers stay under the local tags) and `docker image prune -f`.
- The code checkout is still pushed from the Mac, for the compose file, job scripts and systemd units only.
- **Pin dependencies** (a lock file the Mac, CI and the Dockerfile all install from). Unpinned, CI, the server and the
  Mac ran three different FastAPI versions (checkpoint #494).

## Traps met so far

- **Hetzner, Oct 2026:** prices rose sharply. The US locations and cost-optimized x86 were sold out or about 2×.
  The Arm CAX line in the EU was the value pick (CAX21 $12.49).
- Hetzner puts the console's SSH keys in root's `authorized_keys` **without comments**. Match them by key body when
  splitting them between users.
- 1Password SSH keys in a vault other than Personal/Private aren't offered until
  `~/.config/1Password/ssh/agent.toml` lists that vault. That file replaces the default, so list Personal and
  Private too. The owner's key is in the vault "Side Quest".
- Infisical's dashboard only makes **project-scoped** identities from a project's Access Control page. The org-level
  `sqn-1` identity was made through the API with the owner's CLI login (`infisical user get token`): `POST
  /v1/identities` (role `no-access`), `POST /v1/auth/universal-auth/identities/<id>`,
  `POST /v2/workspace/<project>/identity-memberships/<id>` `{"role":"viewer"}`,
  `POST /v1/auth/universal-auth/identities/<id>/client-secrets`. The secret was piped straight into the root-only
  file, never printed. A new project gets the identity the same way (the membership call only).
- **GHCR needs a classic token to pull.** Fine-grained tokens can't read container packages. Make one with only
  `read:packages` (Settings → Developer settings → Tokens (classic)), store it in the app's Infisical prod. Check its
  scopes without printing it: the `x-oauth-scopes` response header of any `api.github.com` call.
- **GitHub Actions stops silently when the org's budget is hit:** jobs fail with 0 steps and the annotation "recent
  account payments have failed or your spending limit needs to be increased". The fix is the org's Billing and
  licensing → Budgets and alerts (the Actions budget defaults to $0 on the free plan). Seen 2026-10.
- In zsh, `for n in $N` doesn't split a string variable; use `${=N}` (or bash).
- `~/.cloudflared/` had a `cert.pem` for the old kuudoh Cloudflare account, so `tunnel list` showed none of the real
  tunnels and `tunnel login` refused to overwrite it. Now there are two logins, `cert-personal.pem` (sidequest.nexus,
  every tunnel) and `cert-kuudoh.pem`, and no `cert.pem`: pass `--origincert` to each command.
- A merged cost log: arabayya's `usage.jsonl` on the server had a few lines from testing before the switch, so the
  final copy put the Mac's log first and appended those, rather than overwriting.
- **Checkpoint cutover (2026-10-23):** copy SQLite data through the app's own backup and restore (`checkpoint backup --local`,
  then `restore --to` in the image as uid 1000) rather than file copies: it is consistent and integrity-checked. Copy
  caches that hold paid model output separately (backups skip them).
- Don't `chown` an rsync **target** to the container uid between runs: the next `rsync` as `claude` fails with
  `mkstemp ... Permission denied`. Make it world-readable (`chmod -R a+rX`) instead, and chown only the data dir.
- After moving a tunnel's connector, the **first** public request can hang ~1 minute while Cloudflare drops the old
  connector. Re-time before suspecting the server.
- **Long silent jobs over ssh hang locally (2026-10-28):** a `ssh sqn-1 '... docker compose run ...'` that prints
  nothing for many minutes (checkpoint's `scripts/sqn.sh junk`) finished on the server, but the Mac's ssh stayed
  connected to a dead session and never returned. Run long jobs detached on the server
  (`nohup bash -c "..." > /tmp/<job>.log 2>&1 < /dev/null &`, then poll the log) or pass `-o ServerAliveInterval=30`.
  `/srv/<app>/data` isn't writable by the login user; put ad-hoc logs in `/tmp`.
- Memory: with arabayya, checkpoint and playpatch the `mem_limit`s total ~6.7 GB (2026-10-23). The next service needs the resize.
- **Sites that treat the server differently from the Mac (2026-10-24):** sqn-1 is a Hetzner (datacenter, Germany) address.
  - `*.paradoxwikis.com` (Fastly) refuses it outright: HTTP 427, error 54113, on v4 and v6, for any user agent.
  - YouTube shows the EU cookie-consent page (answered by the `SOCS=CAI` cookie). After a burst of requests it gives
    `playabilityStatus` `LOGIN_REQUIRED` ("Sign in to confirm you're not a bot").
  - Fandom, wiki.gg, Steam and Reddit work.
  - Never work around a deliberate block: ask the site to allow the address, or use an official API (the YouTube Data
    API for video metadata). Code must treat a block as "unknown", never as "gone" or "empty".
- **Deploy right after a merge:** the newest image run can still be the previous commit's, because GitHub hasn't queued
  main's yet. Checkpoint's `vps-deploy.sh` now waits for main's own run when the image's inputs changed (#521); copy
  that wait into any app with the same deploy.
