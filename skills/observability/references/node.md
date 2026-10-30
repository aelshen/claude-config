# Node services (Next.js, workers)

**Reference implementation: PlayPatch** (Side-Quest-Nexus/playpatch #159 web, #160 workers,
2026-10-30, `@sentry/nextjs` 10.73, OTel SDK 2.11, OTLP exporter 0.222). What worked, verified
against a collector:

- **Option A works.** Pass the processors through `openTelemetrySpanProcessors`; Sentry then
  builds a `BasicTracerProvider` with them next to its own. Run `Sentry.init` on every Node
  start, **with or without a DSN**: without one it sends nothing but still registers the
  provider, so trace ids exist in dev and self-hosted installs.
- **Sampling:** spans are only recorded when Sentry's sampler keeps them, so set
  `tracesSampleRate: 1` (otherwise the request line and the export see only a sample) and
  keep Sentry's own tracing off as the standard says: `beforeSendTransaction: () => null`.
  PlayPatch is an owner-approved exception (2026-10-30): it keeps 25% of web transactions in
  Sentry, chosen by a hash of the trace id in `beforeSendTransaction`. Don't copy that
  without the owner's say-so.
- **Sampling later:** with Sentry owning the provider, `OTEL_TRACES_SAMPLER` /
  `OTEL_TRACES_SAMPLER_ARG` are ignored. Lower `tracesSampleRate` (or use `tracesSampler`)
  instead; it samples what OTLP exports, and Sentry gets nothing either way while
  transactions are dropped. Unsampled requests still get a valid trace id, so log lines and
  `X-Trace-Id` keep working; only their spans aren't recorded. If OTel sampling must differ
  from Sentry's (e.g. a Sentry share as in PlayPatch), use option B.
- **Sentry's resource pins `service.version` to its SDK version.** Override it in your export
  wrapper (`span.resource.merge(...)`). It does honour `OTEL_SERVICE_NAME` and
  `OTEL_RESOURCE_ATTRIBUTES`.
- **Pick the OTLP exporter version whose `@opentelemetry/sdk-trace` matches Sentry's**, or pnpm
  installs a second copy. pnpm 8 rewrites a prettier-formatted lockfile: run prettier on it.
- **Request line and X-Trace-Id from a Node `http.Server.prototype.emit` hook** (patch
  `res.writeHead` to read the active span; log on `close`), not a span processor: one place,
  sees cookies, independent of sampling. Route template: Next's request meta
  (`Symbol.for('NextInternalRequestMeta')`, `match.definition.pathname`).
- **Sanitise before export, not only filter.** Sentry's http spans carry `url.full`,
  `http.target`, query strings, client IP and user agent. Export an allow-list of attributes,
  scrub ids and queries from span names, drop span events and status messages
  (`exportView` in playpatch `telemetry.ts`). Codex caught this; the plan below didn't.
- **Kid filter = hold the trace until its local root ends**, then forward or drop it whole;
  mark traces from a request hook for things spans can't see (cookies); drop stuck and
  oversized traces. Children that start after the root settled are judged alone.
- **Workers:** `traced(queue, fn)` wraps each processor in a CONSUMER span; enqueue with
  `propagation.inject` into `data._trace` (Sentry's propagator writes `sentry-trace` and
  `baggage`, which is fine). Allow-list the queues that may export, with a test that every
  queue is in one list.
- Tests: no global context manager in jest; spy `trace.getActiveSpan`, or register a small
  AsyncLocalStorage `ContextManager`.

The original plan follows; where it differs from the notes above, the notes win.

## Logs: pino

pino already writes one JSON object per line. Make its fields the standard's:

```ts
import pino from 'pino';
import { trace } from '@opentelemetry/api';

export const logger = pino({
  level: process.env.LOG_LEVEL || (process.env.NODE_ENV === 'development' ? 'debug' : 'info'),
  base: { service: process.env.OTEL_SERVICE_NAME, env: deploymentEnv() }, // not pid/hostname
  timestamp: () => `,"ts":"${new Date().toISOString()}"`,
  formatters: { level: (label) => ({ level: label }) },
  mixin() { // ids at log time, from the active span
    const c = trace.getActiveSpan()?.spanContext();
    return c ? { trace_id: c.traceId, span_id: c.spanId } : {};
  },
  redact: { paths: [/* keep the service's list */], remove: true },
});
```

`msg` is pino's default message key, so it already matches. Use `logger.info({ route, status }, 'request')`:
fields first, a fixed message second.

**Export to OTLP** only when `OTEL_EXPORTER_OTLP_ENDPOINT` is set: add a pino transport that
writes OTel log records (`pino-opentelemetry-transport`, which reads the standard `OTEL_*`
variables) next to stdout, via `pino.transport({ targets: [stdout, otlp] })`. Or use
`@opentelemetry/instrumentation-pino`, which injects ids and forwards to the OTel Logs SDK. Pick
one and check it against its README.

## Traces: Sentry already owns OpenTelemetry

`@sentry/nextjs` v8+ is built on OpenTelemetry and registers the tracer provider itself. Don't
register a second one. Two ways to add an OTLP exporter:

- **A. Keep Sentry's setup and add a span processor** (fewer moving parts). Pass the OTLP
  `BatchSpanProcessor` through Sentry's option for extra span processors
  (`openTelemetrySpanProcessors` in the v8–v10 Node SDK; confirm the name in the docs for the
  installed version). Spans are only recorded if Sentry samples them. So when exporting, set
  `tracesSampleRate: 1`, and drop transactions from Sentry in `beforeSendTransaction`
  (`return null`) unless you want them in both places.
- **B. `skipOpenTelemetrySetup: true`** and register the provider yourself
  (`NodeTracerProvider` with `SentrySampler`, `SentryPropagator`, `SentryContextManager`, then
  the OTLP processor). Sentry documents this as "Using your existing OpenTelemetry setup"
  (Next.js v10 guide). Use it if A can't do what you need.

Either way, Sentry keeps reporting errors, and its events carry the trace id because they're
the same spans.

Next.js emits its own spans for requests, route handlers, rendering and fetch once a provider
is registered. Check that the root server span has `http.route` (the route template).

## The request line and X-Trace-Id

- **Request line:** a `SpanProcessor` whose `onEnd` logs `request` for root SERVER spans
  (`method`, `route` from `http.route`, `status` from `http.response.status_code`,
  `duration_ms` from the span's start and end). This avoids middleware hacks and covers every
  route. Skip kid-surface routes, or log them locally only; never export them (Privacy).
- **X-Trace-Id:** set it where the service builds API responses (a shared handler wrapper, if
  there is one) from `trace.getActiveSpan()?.spanContext().traceId`. Pages don't need it.

## Kid surfaces (playpatch)

Wrap the OTLP processor in a filtering processor that drops any span whose root route is a kid
surface. Use `isKidPath` from the service's `kid-surface.ts`, the same list its Sentry filter
uses, so there's one list. The collector filters again (`collector.md`). Log lines from kid
routes stay on stdout, which stays on the host. The pino OTLP transport must apply the same
route filter, or be off for that service.

## Workers (BullMQ)

The worker process initialises its own provider the same way (Sentry's Node SDK if it uses
it, option A or B). When enqueueing, inject the active context into the job data
(`propagation.inject(context.active(), job.data._otel = {})`). In the worker, extract it and
start the job's span with it as the parent, so a queued job joins the request that queued it.
Jobs not started by a request get a root span named after the queue.

## Model calls

If the service calls a model provider, wrap the one place it does so in a `chat <model>`
CLIENT span with the GenAI attributes from SKILL.md. No prompt or output text from a children's
service, ever.
