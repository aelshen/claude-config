# Brief: Delphi adopts the observability standard

**For:** the Delphi session (repo `~/Work/delphi`, `aelshen/delphi-trx`). **From:** the Delphi session, 2026-10-19,
at the owner's request via the arabayya session. **Read SKILL.md and `references/python.md` first.** Copy from
arabayya `server/telemetry.py` (`setup`, `carry`, `model_call`, `record_usage`) and its tests.

## What's there now (survey, 2026-10-19; re-check before acting)

- **Not a web service.** A Typer CLI (`delphi/cli.py`) run by 8 launchd jobs (`scripts/daily.sh <job>`: cycle, monitor,
  open-check, options-check, sync, summary). Each job's stdout and stderr go to `logs/swing-*.log`. Plus a local Streamlit UI
  (`delphi ui`) and long research or backtest runs (`replay-calls`, `swing-replay`). No HTTP server of its own, so no
  request spans and no `X-Trace-Id`. The unit of work is a **job run**.
- Logging: `logging.basicConfig` plain text at `cli.py:35`, about 25 module loggers, and about 100 `rprint`/`print` calls.
  The council's narrative output (the chair's summary, orders, blocks) is what the owner reads in `logs/swing-cycle.log`.
- Model calls all go through `LLMProvider.structured()`:
  - `delphi/llm/anthropic_provider.py`, with batch results via `anthropic_batch.py` on background threads;
  - `delphi/llm/openai_provider.py`.
- The council loop (`council/deliberation.py`) runs propose, critique and decide rounds, with seats in parallel on a
  `ThreadPoolExecutor`. The optional discovery round calls an `enricher` that fetches data, which acts as a tool.
- **Spend ledger:** the SQLite `llm_calls` table in each profile's journal (model, tokens, cache, reasoning). Cost is
  computed by `delphi/pricing.py`, and `focus-report` and `daily-summary` read it.
- No Sentry and no error reporting. There's no user PII, but `.env` holds broker and LLM keys and an EDGAR user agent
  with a contact email, and the Alpaca, httpx and urllib3 loggers can print URLs.

## Do

1. **`delphi/telemetry.py`** from arabayya's: `SERVICE = "delphi-jobs"` for CLI and launchd runs and `delphi-ui` for
   Streamlit; ENV from `OTEL_RESOURCE_ATTRIBUTES`, defaulting to `development`; `service.version` = git short sha. Pin
   the OTel packages in `pyproject.toml`. Export stays off unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
2. **Replace `basicConfig`** with `telemetry.setup()` in the Typer app callback, so every command's JSON lines carry
   `service`, `env`, `trace_id`. Raise `httpx`, `urllib3`, `alpaca`, `yfinance`, `anthropic` and `openai` loggers to
   `warn`.
3. **One root span per job run:** span `job <command>` (for example `job run`, `job monitor`), with attributes `app.profile`
   (`DELPHI_PROFILE`), `app.mode` (paper, live, dryrun, replay) and `app.cycle_id` once the journal has it. Record each
   cycle's `trace_id` in the `cycles` row (new column), so a journal cycle leads to its trace.
4. **Model calls:** wrap `structured()` in both providers in `model_call(...)` / `record_usage(...)`: `chat <model>`,
   `gen_ai.provider.name`, tokens plus cache read and write, `app.llm.cost_usd` from `pricing.call_cost`,
   `app.llm.purpose` = round (`propose`, `critique`, `decide`, `discovery`, `review`, `retro`), and `app.llm.batch`.
   - Batch results arrive on the batcher's thread. Capture the span context when the request is queued and end the
     span when the future resolves, so batched calls still sit under their job.
5. **Council as an agent:**
   - one `invoke_agent council` span per deliberation, with a child span per round;
   - seat calls are the `chat` spans, and the seat thread pool uses `telemetry.carry`;
   - the discovery enricher becomes `execute_tool enrich`;
   - `replay-calls` and `swing-replay` worker pools carry context too.
6. **Spend ledger:** add `service` and `trace_id` columns to `llm_calls` (migration via the existing `ALTER TABLE`
   list in `journal/store.py`). Keep the existing columns.
7. **Runtime output:**
   - Code that runs in launchd jobs logs structured lines (`order submitted`, `risk block`, `exit`, `stop placed`)
     with fields: symbol, proposal id, status, reasons.
   - The chair's long narrative stays readable: keep it in the journal (it already is) and keep `daily-summary` and
     `focus-report` as the human views. Don't dump multi-paragraph text into JSON lines.
   - Hand-run commands (`calls-report`, `focus-report`, `doctor`) keep rich output.
8. **Errors:** no Sentry for now (single-user local tool). An uncaught exception in a job logs one `error` line with
   `error.type` and the trace id, and the job span is marked ERROR. Revisit Sentry only on the shared host.
9. **Docs:** a "Logs and traces" section in the README and HANDOFF, and a note in `scripts/install_launchd.sh` that logs
   are JSON lines (`jq` recipes for the daily review).

## Done when

- With no `OTEL_*` set, `DELPHI_PROFILE=qqq,qqq-swing delphi deliberate --council fake` prints JSON lines with one
  `trace_id`, and makes no network calls to a collector.
- With a local debug collector, one `delphi run` shows `job run` → `invoke_agent council` → rounds → `chat <model>`
  spans (tokens, cost) as one tree. Its log records share the trace id, and the journal cycle row has the same
  `trace_id`.
- A test asserts the JSON fields and that no API key, auth header or the EDGAR contact email appears in a log line.
- All tests pass.

## Don't

- Don't pick or wire a vendor. Don't record prompt or output text: snapshots hold paid news content, and positions are
  private.
- Don't change the journal's existing columns, and don't make the daily review harder to read.
- Don't touch the trading logic, risk limits or prompts.
