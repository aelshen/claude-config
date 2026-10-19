# Node services (Next.js, workers)

No Node service has been built to this standard yet, so treat this as a plan: check each step
against the library docs for the installed versions, and prove it with the collector check
(`collector.md`) before calling it done. When one is done, record what actually worked here.

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
