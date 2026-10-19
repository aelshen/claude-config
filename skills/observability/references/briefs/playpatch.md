# Brief: PlayPatch adopts the observability standard

**For:** the PlayPatch session (repo `~/Work/playpatch/playpatch`). **From:** the owner's
arabayya session, 2026-10-18. Open a PlayPatch issue for this first (project-tracking rule).

## Goal

PlayPatch logs and traces the way `skills/observability/SKILL.md` describes, so that on the
shared Hetzner host (`internal-notes/HANDOFF.md` plans one box for arabayya, checkpoint and
playpatch) one collector takes everything, and the owner picks a vendor by configuration.
**PlayPatch's COPPA rule wins over everything here: nothing from kid surfaces leaves the host.**
Read SKILL.md, `references/node.md` and `references/collector.md` first.

## What's there now (survey, 2026-10-18; re-check before acting)

- Next.js 15 web app (`apps/web`) and a BullMQ workers process (`src/workers/index.ts`), both
  in Docker Compose (`infrastructure/compose/docker-compose.prod-app.yml`).
- pino logger in `apps/web/src/lib/logger.ts` with level labels and a redact list; 369
  `logger.*` calls and 7 client-side `console.*`. **This is already close to the standard.**
- Sentry `@sentry/nextjs` v10. Server `tracesSampleRate` is 0.1 in production
  (`sentry.server.config.ts:14`); workers 0. `sendDefaultPii: false`, no replay, and kid events
  dropped by `isKidServerEvent` / `kid-surface.ts`.
- No request ids, no OpenTelemetry exporter, no analytics.

## Do

1. **pino fields** (`node.md`, Logs): `base` = `service` (`playpatch-web` / `playpatch-workers`
   from `OTEL_SERVICE_NAME`) and `env`, ISO `ts`, and a `mixin` adding `trace_id`/`span_id` from
   the active span. Keep the redact list. Check the log line for a request on a kid route: it
   must carry no child id, profile id, name or session id.
2. **Traces through Sentry's OpenTelemetry**, option A in `node.md` if it works with the
   installed v10 (an extra OTLP span processor on Sentry's own setup), otherwise option B. Only
   when `OTEL_EXPORTER_OTLP_ENDPOINT` is set. Sentry's own tracing: decide with the owner
   whether transactions keep going to Sentry at 0.1 or stop (the standard says traces go
   through OTel, and Sentry is for errors).
3. **Kid-surface filter in-process:** a filtering span processor in front of the OTLP exporter
   that drops spans whose route `isKidPath()` matches, using the same function the Sentry filter
   uses. Also drop worker spans for jobs that process a child's data. List those queues in the
   code, next to `kid-surface.ts`. The pino OTLP transport, if added, applies the same filter;
   otherwise leave log export off and logs stay on the host's stdout.
4. **Request line:** a span processor that logs `request` (`method`, `route`, `status`,
   `duration_ms`) for root server spans (`node.md`). Kid routes: log locally (stdout) without
   ids, or skip.
5. **X-Trace-Id** on API responses, through the shared route-handler wrapper if there is one.
6. **Workers:** the same provider setup in the workers process, and `traceparent` carried in
   BullMQ job data from the enqueueing request (`node.md`, Workers).
7. **Model calls** (the AI-safety and `api/ai` paths are kid surfaces): spans for them never
   leave the host. Don't add GenAI content capture to PlayPatch at all.
8. **Docs:** a "Logs and traces" section in PlayPatch's docs, and update `SENTRY_SETUP.md` if
   step 2 changes Sentry's tracing. The privacy summary (`lib/privacy/summary.ts`) changes
   only when a vendor is actually turned on, and then it must say parent pages only.

## Done when

The SKILL.md checks pass, plus the COPPA check: with a local collector (`collector.md`),
browse a parent page and a kid page. The collector shows the parent page's spans and **nothing**
from the kid page, worker jobs for child data, or `/api/ai`. Then turn on the collector's
`filter/kids` and confirm it's a second lock, not the only one (disable the in-process filter
in a test and see the collector drop them). Tests pass, with no network calls when `OTEL_*`
isn't set.

## Don't

- Don't pick or wire a vendor; export stays off.
- Don't send anything from kid surfaces anywhere, including Sentry, which is already right.
  Keep it that way.
- Don't restructure the pino call sites; their shape (fields, then message) already fits.
