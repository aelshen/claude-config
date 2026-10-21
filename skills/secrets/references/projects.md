# Per-project notes (survey 2026-10-21, names only; re-check before acting)

Infisical projects exist for all four. Delete the default "Example Project" when convenient.

## delphi (done)

- Project `delphi` (`a183639e-53e7-48ed-99c1-0a20ec0eac7c`), `prod` and `dev`: ANTHROPIC_API_KEY, OPENAI_API_KEY,
  ALPACA_PAPER_API_KEY, ALPACA_PAPER_SECRET_KEY.
- launchd jobs via `scripts/daily.sh` and identity `delphi-mac`. Hand runs: `infisical run -- delphi <cmd>`.
- `.env` still has blank FINNHUB_API_KEY and FRED_API_KEY; set them in Infisical if they are ever used.

## arabayya

- `server/.env` (FastAPI, `server/Dockerfile`; scripts load it with `library_store.load_env(args.env_file)`):
  OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_SECRET_KEY, SUPABASE_URL, STORYWEAVER_PASSWORD, SENTRY_DSN,
  APPLE_KEY_ID, APPLE_PRIVATE_KEY (multi-line `.p8`: set with `@file`).
- `app/.env` (Expo): EXPO_PUBLIC_* only (Supabase anon key and URL, API URL, Sentry DSN, PostHog key). Public build
  config, read by EAS at build time; not part of this migration.
- Check every `load_env(args.env_file)` caller: those scripts read a file explicitly, so under `infisical run` they
  must not fail when the file lacks the keys (or should prefer the environment).
- This repo is planning the VPS: the "On the VPS" section of SKILL.md is the secrets part of that plan.

## playpatch (children's service)

- Repo checkout is `~/Work/playpatch/playpatch` (nested). Compose files in `infrastructure/compose/`, run with
  `--env-file ../../.env`.
- `.env`: DB_PASSWORD, DATABASE_URL, REDIS_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MEILISEARCH_URL,
  MEILISEARCH_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, NEXTAUTH_SECRET, NEXTAUTH_URL, REALDEBRID_API_KEY,
  SENTRY_DSN, NEXT_PUBLIC_SENTRY_DSN, NEXT_PUBLIC_APP_URL, YOUTUBE_API_KEY, CLOUDFLARE_TUNNEL_TOKEN,
  R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, RESEND_API_KEY, GEMINI_VERTEX_KEY_DIR, GEMINI_VERTEX_CREDENTIALS,
  DATA_ENCRYPTION_KEY (`.env.example` also lists REDIS_PASSWORD, CRON_SECRET, OLLAMA_URL).
- Compose already takes one env file, so the VPS pattern fits directly: `infisical export` to the file passed to
  `--env-file`. Locally: `infisical run -- docker compose ...` or export to the same path.
- DATA_ENCRYPTION_KEY encrypts stored data: **back it up in 1Password before moving it**. Losing it loses the data,
  and Infisical's free tier keeps no history.
- GEMINI_VERTEX_CREDENTIALS / _KEY_DIR point at a service-account file: store the JSON as one secret (`@file`) and
  have the deploy write it to the path the app expects.
- `NEXT_PUBLIC_*` values must be present at `next build`.

## checkpoint

- Root `.env` (gitignored): OPENAI_API_KEY, ANTHROPIC_API_KEY, SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY,
  SUPABASE_ACCESS_TOKEN (listed twice; keep one), CLOUDFLARE_API_TOKEN, RESEND_API_KEY, SENTRY_DSN,
  CHECKPOINT_GEMINI_API_KEY.
- Python (`pyproject.toml`) with `spend.jsonl`; check how it loads `.env` and how it is started before wiring
  `infisical run`.
