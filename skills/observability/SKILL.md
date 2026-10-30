---
name: observability
description: "One logging, tracing and error-reporting standard for every service, built on OpenTelemetry, so picking or changing a vendor (Logfire, Grafana Cloud, Axiom, a local collector) is a configuration change and never a code change. Use when adding logging, request tracing, LLM/agent call tracing or Sentry to a service, when reviewing how a service logs, when moving services onto a shared host, or when choosing where telemetry goes. Triggers on: logging, logs, structured logs, tracing, traces, OpenTelemetry, OTel, OTLP, Logfire, Grafana, Axiom, Datadog, Sentry, request id, trace id, agent traces, LLM traces, observability, monitoring, debugging production."
---

# Observability

Every service logs, traces and reports errors the same way, so one tool can show all of
them and a request can be followed from the proxy through the app into each model call.
**OpenTelemetry (OTel) is the interface.** Code talks only to the OTel API and the standard
library's logger; where the data goes is set by environment variables.

Why (October 2026 survey of arabayya, checkpoint and playpatch, ahead of a shared host):

- Three shapes of log: arabayya `print()`s plain text, checkpoint has loggers in 26 files
  but never configures them (so info lines are dropped), playpatch writes pino JSON.
  Nothing could be searched across services. → **One JSON line format.**
- No request ids anywhere, so a crash report couldn't be tied to the log lines or model
  calls that led to it. → **Trace context on every line, propagated in and out.**
- Two home-made spend ledgers in different formats. → **Model calls are spans with the
  standard GenAI attributes; the ledgers keep their job (spend caps) in one field set.**
- The vendor wasn't chosen yet. → **Vendor-neutral by construction.**

## No shared library

Don't build a cross-repo logging package. The services are in two languages and deploy
separately; a shared package would need publishing and version pinning in every repo,
while the per-service code is about 100 lines. OTel already is the shared interface. Each
service has **one telemetry module** (the only file that imports OTel SDK or exporter
packages) that follows this standard, and the reference files give the code to copy:

- Python (FastAPI): `references/python.md`. Reference implementation, verified against a
  collector: arabayya `server/telemetry.py` (Side-Quest-Nexus/arabayya#396).
- Node (Next.js, workers): `references/node.md`
- Collector config (local check and the shared host): `references/collector.md`
- Adoption briefs for existing services: `references/briefs/`

## The switch

| State | Set | What happens |
|---|---|---|
| **Off** (default, dev, tests) | nothing | JSON log lines on stdout with trace ids; spans are created but not exported. No network calls. |
| **Local collector** | `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` | Everything goes to a collector (see below), which decides the destination. |
| **Vendor direct** | `OTEL_EXPORTER_OTLP_ENDPOINT=<vendor OTLP URL>`, `OTEL_EXPORTER_OTLP_HEADERS=<auth>` | Traces and logs go to the vendor. |

Always set `OTEL_SERVICE_NAME` and `OTEL_RESOURCE_ATTRIBUTES=deployment.environment.name=production`
(or `development`). Use `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`: several vendors accept
only HTTP, and Python already defaults to it, Node doesn't.

Vendor examples (check the vendor's docs when wiring one; keys go in `.env` or a secret
store, never in the repo):

- Logfire: endpoint `https://logfire-us.pydantic.dev` (or `logfire-eu`), header
  `Authorization=<write token>`.
- Grafana Cloud: the stack's OTLP gateway URL, header `Authorization=Basic <base64 id:token>`.
- Any other OTLP vendor: its endpoint and header. Nothing else changes.

**On a shared host, run one OpenTelemetry Collector** (`otel/opentelemetry-collector-contrib`
container) and point every service at it. The collector holds the vendor endpoint and key,
drops or scrubs what must not leave the box (see Privacy), and can send to two places
while you compare vendors. Changing vendor is then one edit to the collector config.

## Service names

`<app>-<role>`: `arabayya-api`, `checkpoint-api`, `playpatch-web`, `playpatch-workers`,
`delphi-<role>`. `service.version` is the app version or git short sha.

## Logs

One JSON object per line on stdout. Services don't write their own log files; the process
manager (launchd, Docker) captures stdout and rotates it.

Required fields:

| Field | Value |
|---|---|
| `ts` | ISO 8601 UTC with milliseconds: `2026-10-18T21:04:05.123Z` |
| `level` | `debug`, `info`, `warn`, `error` |
| `service` | the service name |
| `env` | `production` or `development` |
| `msg` | a short fixed sentence; put variable data in fields, not in the message |
| `trace_id`, `span_id` | from the current span (32 and 16 hex chars), omitted outside a span |

Anything else is a flat field with a lowercase dotted or snake_case name (`route`,
`status`, `duration_ms`, `job`, `error.type`, `detail`). When export is on, the same records
also go out as OTel log records, so the vendor links each line to its trace.

Take the trace ids when the line is logged, not when a handler formats it (a log-record
factory in Python, a pino `mixin` in Node). Route the web server's own loggers (uvicorn,
Next) through the same formatter, and raise HTTP client libraries to `warn`: their info
lines carry full URLs, which can hold keys or topic names.

Levels: `error` = someone or something failed and nobody will retry; `warn` = degraded but
handled (a fallback, a retry, a limit hit); `info` = one line per request, job run or
state change; `debug` = off in production.

Command-line tools a person runs by hand may keep printing plain text for that person.
The rule is for code that runs inside the service or its scheduled jobs.

## Traces

- **One server span per HTTP request**, from the framework's OTel instrumentation. It
  honours an incoming W3C `traceparent` header (from the proxy or a calling service) and
  starts a new trace otherwise.
- **Every response carries `X-Trace-Id: <trace_id>`.** Clients show or report it (a
  feedback form, a support email), and it's the search key in every tool.
- **One per-request log line** at `info` when the request ends: `msg="request"`, `method`,
  `route` (the route template, never the raw path with ids in it), `status`, `duration_ms`.
  Turn off the server's own access log (uvicorn `--no-access-log`) so there is one line.
- **Background jobs** (schedulers, queues, cron) start a root span per run, named after the
  job, so a job's model calls group under it.
- **Thread pools and queues keep the trace.** Python's `ThreadPoolExecutor` doesn't pass
  context on: wrap the function (`carry(fn)` in the reference) or the model calls it makes
  become separate root traces. A queue job (BullMQ) carries the `traceparent` in its payload
  and the worker continues it.
- **Outgoing HTTP client spans are optional.** Model calls already have their own span;
  add httpx/fetch instrumentation only if calls to other services need debugging.
- Sample everything while volume is small. Later: `OTEL_TRACES_SAMPLER=parentbased_traceidratio`
  with `OTEL_TRACES_SAMPLER_ARG=0.1`.

## Model and agent calls

Wrap every model call at the one place the service calls a provider (its LLM client
module) in a span following the OTel GenAI conventions. The conventions are still marked
Development, so keep the attribute names in that one module.

- Span name `chat <model>`, kind CLIENT.
- `gen_ai.operation.name` = `chat`; `gen_ai.provider.name` = `anthropic` or `openai`;
  `gen_ai.request.model`, `gen_ai.response.model`; `gen_ai.usage.input_tokens`,
  `gen_ai.usage.output_tokens`; on failure `error.type` and span status ERROR.
- Service attributes: `app.llm.purpose` (the task, e.g. `lexicon`, `research`),
  `app.llm.cost_usd`, `app.llm.batch` (true for batch API results).
- Agent loops: a parent span `invoke_agent <name>` around the loop, and one
  `execute_tool <tool>` span per tool call (`gen_ai.tool.name`), so the vendor shows the
  loop as a tree.
- **Prompt and output text are not recorded by default.** Opt in per service with
  `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`, only where the text holds no
  personal data (see Privacy). Then record them as span events `gen_ai.input.messages`,
  `gen_ai.output.messages`, truncated to 8 KB each.

**Spend ledgers stay** (caps and daily summaries read them). Every line carries `service`
and `trace_id`, so a cost leads to its trace. A new ledger uses `ts` (ISO 8601 UTC),
`service`, `purpose`, `model`, `input_tokens`, `output_tokens`, `usd`, `batch`, `trace_id`.
An existing ledger keeps its field names until a cross-service spend report needs them;
renaming is a migration (read both shapes until the old lines age out).

## Errors

Sentry stays for crash reports and alerts (and for the phone apps, which OTel doesn't
cover here). Every Sentry event carries `trace_id` as a tag, plus `environment` and
`release`, so a crash leads to its trace. Sentry's own tracing stays off: no transactions
go to Sentry; traces go through OTel. Where Sentry owns the tracer provider (its Node SDK v8+,
the PlayPatch setup in `references/node.md`), its sampler also decides which spans OTel
records, and `tracesSampleRate: 0` records none (checked with @sentry/nextjs 10.73). There,
"off" means `tracesSampleRate: 1` plus `beforeSendTransaction: () => null`. Where you own the
provider (arabayya's Python setup), keep `traces_sample_rate=0`. Use a Sentry SDK's "existing
OpenTelemetry setup" mode when it has one, so there is one tracer provider, not two.

## Privacy

Telemetry is a third-party disclosure once it is exported. List the vendor in the privacy
policy before turning export on in production.

- Never put in logs or attributes: emails, names, IPs, raw user or device ids, auth
  headers, tokens, request bodies, cookies. If you need to group by user, use a salted hash.
- Arbitrary user-written text (feedback, chat input) is not logged and not captured as
  message content.
- **Children's services (playpatch):** nothing from kid surfaces leaves the host. The
  service drops kid-route spans and logs before export, and the collector filters them again.
  Kid surfaces are the same route list the service's Sentry filter uses.

## Checks

A service meets the standard when:

1. With no OTEL variables set, a request prints one JSON `request` line with `trace_id`,
   and the response has `X-Trace-Id` with the same id.
2. With `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318` and a debug collector running
   (`docker run --rm -p 4318:4318 otel/opentelemetry-collector-contrib` with the debug
   exporter, config in `references/collector.md`), one request shows a server span, any
   model-call spans as its children, and the log records with the same trace id.
3. A test asserts the JSON line fields and that no email, device id or auth header appears
   in a log line for a request that carries them.
4. Sentry events (a dev-only test route) carry the `trace_id` tag.
5. Tests and local runs make no network calls when no OTEL variables are set.
