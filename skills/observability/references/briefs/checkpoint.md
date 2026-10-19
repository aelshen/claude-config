# Brief: Checkpoint adopts the observability standard

**For:** the Checkpoint session (repo `~/Work/checkpoint`). **From:** the owner's arabayya
session, 2026-10-18. Open a Checkpoint issue for this first (project-tracking rule).

## Goal

Checkpoint logs, traces and reports errors the way `skills/observability/SKILL.md` describes,
so that on the shared Hetzner host one tool shows Checkpoint, Arabayya and PlayPatch, and the
owner can pick a vendor (Logfire is the current front-runner) by setting two environment
variables. **Read SKILL.md and `references/python.md` first.** Arabayya already did this
(Side-Quest-Nexus/arabayya#396). Its `server/telemetry.py` and `server/tests/test_telemetry.py`
are the code to copy, verified against a collector.

## What's there now (survey, 2026-10-18; re-check before acting)

- FastAPI app `checkpoint/web/app.py`, run by `checkpoint serve` → `uvicorn.run(...)`
  (`checkpoint/cli.py:735`); middleware `CORSMiddleware` and `limits.Guard`.
- `logging.getLogger(__name__)` in 26 modules and 59 `log.*` calls, but **no `basicConfig` or
  handler anywhere**, so INFO lines are dropped and WARNING+ go to Python's bare last-resort
  handler. 108 `print()`s, 48 of them in `cli.py`.
- All model calls go through `llm._client()`, which records spend to `spend.jsonl` and the
  active per-answer trace (`checkpoint/trace.py`, JSON files under `games/<slug>/traces/`).
- JSONL ledgers per game: `asks.jsonl`, `runs.jsonl`, `onboarding.jsonl`, `feedback.jsonl`,
  `semantic/changes.jsonl`, `_optouts.jsonl`.
- No Sentry or any other error reporting. No request ids. Streaming answers in `web/stream.py`.

## Do

1. **`checkpoint/telemetry.py`** from arabayya's, with `SERVICE = "checkpoint-api"` and ENV
   from `OTEL_RESOURCE_ATTRIBUTES` or Checkpoint's dev flag. Add the three pinned packages to
   `pyproject.toml`.
2. **Call `telemetry.setup()` in `checkpoint serve`** before the app is imported, and
   `telemetry.instrument(app)` in `web/app.py`. Its 26 existing loggers then just work. Check
   the existing `log.*` calls for `extra=` keys that collide with LogRecord attributes, and
   for f-string messages that should become a fixed message plus fields (do the noisy ones;
   don't rewrite all 59 for style).
3. **Runtime `print()`s → logger**, in modules that run inside the server or the launchd
   jobs (`patches`, `corrections`). `cli.py` output for a person at the terminal stays `print`.
4. **Model calls:** wrap `llm._client()`'s call path in `model_call(...)` / `record_usage(...)`
   (`chat <model>`, provider, model, `app.llm.purpose` = the existing `caller`, tokens,
   `app.llm.cost_usd`). Add `service` and `trace_id` to each `spend.jsonl` line, keeping the
   existing fields; `limits.py:78` reads it for the daily cap. Note that `web_search` "searches"
   cost money too, so put the count on the span (`app.llm.searches`).
5. **Agent loop** (`agent.py`): an `invoke_agent <name>` span around the loop and an
   `execute_tool <tool>` span per tool call (`gen_ai.tool.name`), so a slow or wrong answer
   shows as a tree. Thread pools carry context (`telemetry.carry`).
6. **Per-answer traces (`trace.py`):** keep them; they're the product's own record. Put the
   OTel `trace_id` in each trace file and use the same id in the `spend.jsonl` `trace` field
   if that's simple, so one id finds the file, the log lines and the spans. Don't delete the
   30-day retention.
7. **Streaming:** for SSE responses the `request` line's `duration_ms` measures time to the
   first byte, not the end of the stream. Either log a second `stream done` line with the total
   duration, or say so in the README.
8. **Sentry (errors only)**, like arabayya `server/error_reports.py`: `sentry-sdk[fastapi]`,
   off unless `SENTRY_DSN` is set, `send_default_pii=False`, `traces_sample_rate=0`, no local
   variables or request bodies, `before_send` drops IP, user and all headers, and tags `trace_id`,
   `environment` and `release`. The owner creates the Sentry project and puts the DSN in `.env`;
   don't block on it.
9. **Docs:** a "Logs and traces" README section like arabayya's `server/README.md`, and the
   launchd plist templates' logs become JSON lines.

## Done when

The five checks in SKILL.md pass. Most important: with a local collector, one answer request
shows the server span → `invoke_agent` → `execute_tool` and `chat` spans as one tree, the log
records share its trace id, and the response's `X-Trace-Id` matches. All tests pass, and the
tests make no network calls with no `OTEL_*` set.

## Don't

- Don't pick or wire a vendor. Export stays off; the owner will choose.
- Don't record prompt or answer text by default. If game content is public, the opt-in
  (`OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`) can be turned on later; user
  questions are user-written text, so leave it off unless the owner decides otherwise.
- Don't change the JSONL ledgers' existing field names.
