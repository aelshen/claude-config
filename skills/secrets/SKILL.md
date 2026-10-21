---
name: secrets
description: "One way to store, load, add and rotate API keys and other secrets in every repo: Infisical (cloud, org Side Quest Nexus) holds them, apps read plain environment variables, and agents move values without ever seeing them. Use when adding or rotating a key, moving a repo off .env secrets, wiring secrets into a scheduled job, Docker or the VPS, or when a job fails to get its keys. Triggers on: API key, secret, credentials, .env, rotate key, new key, Infisical, infisical run, machine identity, Keychain, env_file, secret store, 1Password."
---

# Secrets

Every repo keeps its secrets in **Infisical** and reads them as ordinary environment variables. `.env` files keep
non-secret settings only. 1Password is the owner's personal backup and holds the Infisical admin login; apps never
talk to it.

Why (October 2026): the owner had keys in many plain `.env` files, was creating new keys for every project, and is
moving the services onto one Docker VPS (probably Hetzner). A secret store had to work for local dev, for scheduled
jobs on the Mac, and on that server, for free.

Reference implementation: delphi (Side-Quest-Nexus/delphi-trx #29, PR #30): `scripts/daily.sh`, `.infisical.json`,
and the "Secrets" section of its `HANDOFF.md`.

## Layout

| Thing | Value |
|---|---|
| Instance | Infisical Cloud US, `https://app.infisical.com` (the CLI's default) |
| Org | Side Quest Nexus |
| Projects | one per repo: `arabayya`, `checkpoint`, `delphi`, `playpatch` (already created) |
| Environments | `dev` (local work) and `prod` (scheduled jobs, the VPS). `staging` exists by default and stays unused. |
| Secret names | exactly the variable name the app reads (`ANTHROPIC_API_KEY`), never prefixed with the project |
| Repo link | `.infisical.json` at the repo root (or the app's folder), committed. It holds only the project id. |

Project ids: `infisical sm projects list`. Environments: `infisical sm projects get --projectId=<id>`.

### Identities (free tier: 5 in total, people and machines together)

| Identity | Kind | Access | Used by |
|---|---|---|---|
| the owner | user | admin | `infisical run` in dev, adding and rotating keys |
| `delphi-mac` | machine (Universal Auth) | Viewer on `delphi` | launchd jobs on the owner's Mac |
| one VPS identity (to create) | machine (Universal Auth) | Viewer on every project | deploys on the VPS |

**One machine identity per machine, never one per app.** Four app identities plus the owner would use all 5 seats.
A second project that needs unattended jobs on the Mac gets `delphi-mac` added to it as Viewer (rename it to
`mac-jobs` in the dashboard when that happens). A new identity must be added **inside each project** (Project →
Access Control → Machine Identities) with role **Viewer**; the org-level role stays "No access". An identity that is
not in the project, or is there as "No access", gets `403 ... not allowed to describeSecret`.

Free tier also lacks version history, audit logs and automatic rotation: an overwritten value is gone, which is
why 1Password stays the backup.

## What goes in, what doesn't

- **In:** anything that grants access or costs money: model API keys, broker keys, database URLs with passwords,
  service-role keys, signing keys, webhook and tunnel tokens, `NEXTAUTH_SECRET`, encryption keys, Sentry DSNs (low
  risk, but keep them together).
- **Out (stays in `.env` or config):** ports, modes, feature flags, model names, URLs without credentials.
- **Public client values** (`EXPO_PUBLIC_*`, `NEXT_PUBLIC_*`, Supabase anon/publishable keys) ship inside the app
  build and are not secret. They may live in Infisical for convenience, but the build must have them at build time
  (Next inlines `NEXT_PUBLIC_*` at `next build`; Expo builds read them from EAS environment variables).
- **Multi-line values and files** (Apple `.p8` keys, Google service-account JSON) are stored as one secret and
  set from a file with `NAME=@path`.

## Rules for agents

These keep key values out of transcripts, which are stored.

1. **Never print a value.** No `cat .env`, no `--plain` or `--show-values` to the screen, no `echo $KEY`, no
   `env`/`printenv` dumps. Print names, counts and lengths only (`${#v} chars`).
2. **Never ask the owner to paste a key into the chat.** They put it in a file (or the clipboard) and tell you the
   name; you move it with the CLI.
3. **Verify by fingerprint, not by eye:**
   `[ "$(grep '^K=' .env | cut -d= -f2- | tr -d '"' | shasum)" = "$(infisical secrets get K --env=prod --plain --silent | shasum)" ]`
4. **Interactive commands are the owner's**, run in their own Terminal: `infisical login` (region menu; pass
   `--domain https://app.infisical.com/api` to skip it) and `infisical init` (project menu). A `!` command in the
   session can't answer arrow-key menus and dies with `^D`. Instead of `init`, write `.infisical.json` yourself
   from the project id.
5. Temporary files holding values go in the session scratchpad with `umask 077`, and are deleted in the same
   command that uses them.
6. Use `--silent --telemetry=false` in scripts and scheduled jobs.

## Adopting it in a repo

1. **Survey (names only):** which `.env` files exist, which names are secrets, how the app loads them (pydantic
   `BaseSettings`, `load_dotenv`, `process.env`, compose `env_file`/`--env-file`), and every way it starts (dev
   server, scripts, launchd/cron, Docker, CI). Precedence matters: pydantic-settings and dotenv do not override a
   variable already in the environment, so `infisical run` wins over a stale `.env` line.
2. **Import:** copy only the secret lines into a scratch file and push them to both environments:
   ```bash
   umask 077; grep -E '^(NAME1|NAME2)=' .env > "$T"
   for e in prod dev; do infisical secrets set --file "$T" --env=$e --projectId=<id> --silent --telemetry=false; done
   rm -f "$T"
   ```
   Then check every name with the fingerprint in rule 3. Skip names whose value is blank.
3. **Test with an empty environment** so nothing leaks in from your shell or `.env`:
   `env -i HOME=$HOME PATH=$PATH infisical run --env=prod -- <a command that calls each provider>`.
4. **Wire each way the app starts:**
   - Local dev: `infisical run -- <cmd>` (uses `dev` via `.infisical.json`). Put it in the `package.json`
     script or `Makefile` target so nobody has to remember it.
   - Scheduled jobs on the Mac (launchd): the block below.
   - Docker on the VPS: see "On the VPS".
5. **Remove the secret lines from `.env`**, keep `.env.example` with the names and blank values, and confirm
   `.env` is gitignored.
6. **Run the real thing once** (for launchd: `launchctl kickstart gui/$(id -u)/<label>` and read its log).
7. **Document it** in the repo's `HANDOFF.md`/README: project, environments, identity, how to run by hand.

### Scheduled jobs on the Mac

Machine identity credentials live in the login Keychain (service `<identity>`; accounts `client-id` and
`client-secret`). The owner stores them in their own Terminal, typing the value at the prompt:

```bash
security add-generic-password -U -s delphi-infisical -a client-id -w
security add-generic-password -U -s delphi-infisical -a client-secret -w
```

The job script logs in and re-runs itself under `infisical run` (from delphi's `scripts/daily.sh`):

```bash
if [ -f .infisical.json ] && [ -z "${DELPHI_SECRETS_LOADED:-}" ]; then
  fail() { echo "== $(date -u +%FT%TZ) $1 ERROR secrets: $2"; exit 1; }
  id=$(security find-generic-password -s delphi-infisical -a client-id -w 2>/dev/null) || fail "$1" "Keychain item delphi-infisical/client-id missing"
  secret=$(security find-generic-password -s delphi-infisical -a client-secret -w 2>/dev/null) || fail "$1" "Keychain item delphi-infisical/client-secret missing"
  token=$(infisical login --method=universal-auth --client-id="$id" --client-secret="$secret" --plain --silent --telemetry=false 2>/dev/null) \
    || fail "$1" "infisical machine-identity login failed (network, or a revoked client secret)"
  project=$(python -c 'import json; print(json.load(open(".infisical.json"))["workspaceId"])')
  export DELPHI_SECRETS_LOADED=1
  exec infisical run --token="$token" --projectId="$project" --env=prod --silent --telemetry=false -- "$0" "$@"
fi
```

A job that can't get its keys must stop before doing anything with side effects, with one `ERROR secrets:` line.
The plist's `PATH` must include `/opt/homebrew/bin` (where `infisical` lives). Items created by `security` are
readable by `security` from a LaunchAgent without a prompt.

When testing the way launchd runs it, quote the whole command: `bash -lc "./scripts/job.sh arg"`.
`bash -lc ./scripts/job.sh arg` passes `arg` as `$0` of the shell, not to the script.

### On the VPS (Docker Compose)

Containers never talk to Infisical and images don't contain its CLI. The deploy script, as root, writes one
env file per app and Compose reads it:

```bash
infisical export --env=prod --projectId=<id> --token="$TOKEN" --silent --telemetry=false > /etc/<app>/.env
chmod 600 /etc/<app>/.env
docker compose --env-file /etc/<app>/.env up -d     # or env_file: [/etc/<app>/.env] per service
```

The VPS identity's client id and secret live in a root-only file on the host (e.g. `/etc/infisical/vps.env`, mode
600). A rotated key takes effect on the next deploy or `export` plus `docker compose up -d`.

## Maintenance

| Task | Steps |
|---|---|
| **Add or rotate a key** | The owner puts the value in a file (e.g. `~/Work/new_llm_keys.txt`) and names it. Run `infisical secrets set NAME=@/path --env=prod` and the same for `dev` (for a line in a `.env`-style file, extract it to a scratch file first). Fingerprint-check, then restart what uses it (scheduled jobs pick it up on their next run). Revoke the old key at the provider only after the new one is confirmed working. Remind the owner to update 1Password and delete the source file. |
| **Rotate a machine identity's secret** | Dashboard: identity → Universal Auth → create a new client secret. Owner updates the Keychain item (`security add-generic-password -U ...`) or the VPS file. Run one job. Then delete the old client secret. |
| **New project** | Create it in the dashboard, then follow "Adopting it in a repo". |
| **New machine** | One new machine identity for that machine, Viewer on the projects it runs. Check the seat count first (5 on free). |
| **Lost or leaked key** | Revoke at the provider first, then set the new value as above. Infisical keeps no history, so nothing else to clean there; check `git log -p` and transcripts for the old value if it was ever in a file. |

## Troubleshooting

| Symptom | Cause |
|---|---|
| `403 ... not allowed to describeSecret on secrets` | Identity not added to the project, or its project role is "No access". Set Viewer. |
| `Could not fetch secrets` with a machine token | Same as above, or the token expired (log in again each run; don't cache tokens). |
| `infisical login` dies with `error: ^D` / `Unable to parse domain url` | Run interactively in a real Terminal, not through `!`. |
| `ERROR secrets: Keychain item ... missing` in a job log | The Keychain items were never created, or were created under a different service name. |
| App still uses an old key | A stale value in the process environment, or the job wasn't restarted. Infisical values only reach a process when it starts. |

## Per-project notes

`references/projects.md`: what each repo has today (names only) and what adopting it involves.
