# Python (FastAPI) services

The reference implementation is arabayya `server/telemetry.py` (Side-Quest-Nexus/arabayya#396),
verified against a collector: request span → `chat <model>` child spans, job root spans, log
records with matching trace ids. Copy it and change the service name, the env rule and the
model-call wiring. It is about 180 lines; the pieces and the traps are below.

## Packages

```
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-http
opentelemetry-instrumentation-fastapi
```

The exporters are imported only when `OTEL_EXPORTER_OTLP_ENDPOINT` (or
`OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`) is set, so tests and dev runs never open a connection.

## The module

1. **Constants from the environment.** `SERVICE = OTEL_SERVICE_NAME or "<app>-api"`;
   `ENV` from `deployment.environment.name` in `OTEL_RESOURCE_ATTRIBUTES`, else the app's dev
   flag; `VERSION` from `service.version`, else `git rev-parse --short HEAD`, else `unknown`.
2. **`setup()`**, called once at the top of the app module, after `.env` is loaded and before
   other imports log anything:
   - `TracerProvider(resource=Resource.create({...service.name, service.version, deployment.environment.name}))`,
     always (even with no exporter, so trace ids exist), plus `BatchSpanProcessor(OTLPSpanExporter())` when exporting.
   - A log-record factory that stamps `trace_id`/`span_id` from the current span onto each
     record. (Reading the span in the formatter is wrong: a formatter may run later, outside the span.)
   - Root logger at `LOG_LEVEL` (default INFO), one `StreamHandler(sys.stdout)` with the JSON
     formatter; when exporting, also `LoggingHandler(logger_provider=LoggerProvider + BatchLogRecordProcessor(OTLPLogExporter()))`.
     The `_logs` modules are still underscore-named in 1.45; they work, and they're imported in this one place only.
   - uvicorn: clear the handlers on `uvicorn` and `uvicorn.error` and set `propagate = True`
     (uvicorn configures them before it imports the app); `logging.getLogger("uvicorn.access").disabled = True`.
   - `httpx`, `httpcore`, `urllib3` (and any vendored httpx) loggers to WARNING.
3. **JSON formatter.** `ts` (UTC, ms, `Z`), `level` (`warn` not `warning`), `service`, `env`,
   `msg` (`record.getMessage()`), `logger`, then every record attribute that isn't a standard
   LogRecord attribute (that's what `extra=` added). Drop uvicorn's `color_message`. On
   `exc_info`: `error.type` and `exception`. `json.dumps(..., ensure_ascii=False, default=str)`.
4. **`instrument(app)`**, right after `app = FastAPI()`:
   - An `@app.middleware("http")` that times `call_next`, sets `X-Trace-Id` from the current
     span, and in `finally` logs `"request"` with `method`, `route` (`request.scope["route"].path`,
     the template), `status` (500 if `call_next` raised), `duration_ms`; level ERROR for 5xx.
   - `FastAPIInstrumentor.instrument_app(app, exclude_spans=["receive", "send"])`. It wraps the
     whole middleware stack, so the middleware above runs inside the server span.
5. **`carry(fn)`**: `ctx = contextvars.copy_context(); return lambda *a: ctx.copy().run(fn, *a)`.
   Use it for every `pool.map`/`submit` whose work makes model calls or logs.
6. **`job(name)`**: `tracer.start_as_current_span(f"job {name}", context=trace.set_span_in_context(trace.INVALID_SPAN))`
   so a job is a root even if started inside another span.
7. **Model calls**: `model_call(p, purpose, system, user)` context manager opening a CLIENT span
   `chat <model>` with `gen_ai.operation.name`, `gen_ai.provider.name`, `gen_ai.request.model`,
   `app.llm.purpose`; on exception set `error.type` (the app's error code if it has one) and
   re-raise (the SDK marks the span ERROR). `record_usage(meta, response_model)` sets
   `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `app.llm.cost_usd`, `app.llm.batch`,
   `gen_ai.response.model` on the current span; call it right where the service records spend.
   Content events only when `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`, clipped to 8 KB.

## Sentry (sentry-sdk 2.x)

2.x isn't built on OTel, so the two don't conflict. Keep `traces_sample_rate=0`, add
`environment=ENV`, `release=f"<service>@{VERSION}"`, and in `before_send` set
`event["tags"]["trace_id"]` from the current span. If the project moves to sentry-sdk 3.x
(OTel-based), revisit: use one tracer provider.

## Converting prints and unconfigured loggers

- `print("[thing] x failed: {e}")` → `log.warning("x failed", extra={"error.type": type(e).__name__, "detail": str(e)})`.
  Fixed `msg`, details in fields.
- **`extra=` keys must not be LogRecord attributes** (`msg`, `message`, `args`, `name`,
  `module`, `filename`, `lineno`, `created`, `process`, `thread`, `levelname`, ...): logging
  raises `KeyError`.
- Watch for a function parameter named `log` shadowing the module logger.
- Tests that read `capsys` for printed lines move to `caplog`, asserting on `record.message`
  and the `extra` attributes. Add `caplog.set_level("INFO")` for info lines.
- Hand-run CLI tools keep `print` for their human. Code that runs inside the service or its
  scheduled jobs logs.

## Tests to copy (arabayya `server/tests/test_telemetry.py`)

Line fields and extras; ids inside a span; `warn` and exception fields; a TestClient request
gets `X-Trace-Id` and one `request` line with the route template and no device id, auth header
or raw path; an incoming `traceparent` is continued; a model call is a CLIENT `chat` span with
usage and cost and no content events; a failed call carries `error.type`; a job is a root span;
`carry` keeps pool work in the caller's trace. Use `InMemorySpanExporter` with a
`SimpleSpanProcessor` added to the global provider.
