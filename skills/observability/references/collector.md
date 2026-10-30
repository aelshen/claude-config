# OpenTelemetry Collector

## Local check (any service)

`collector.yaml`:

```yaml
receivers:
  otlp:
    protocols:
      http:
        endpoint: 0.0.0.0:4318
exporters:
  debug:
    verbosity: detailed
  file:
    path: /out/telemetry.jsonl
service:
  pipelines:
    traces: {receivers: [otlp], exporters: [debug, file]}
    logs: {receivers: [otlp], exporters: [debug, file]}
```

```sh
mkdir -p out && chmod 777 out
docker run --rm -d --name otel-check -p 127.0.0.1:4318:4318 \
  -v "$PWD/collector.yaml:/etc/otelcol-contrib/config.yaml" -v "$PWD/out:/out" \
  otel/opentelemetry-collector-contrib:latest
# start the service with OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318, make a request, wait ~5 s
docker rm -f otel-check
```

`out/telemetry.jsonl` holds one OTLP JSON batch per line (`resourceSpans`, `resourceLogs`).
Check that the model-call spans' `parentSpanId` is the request span's `spanId`.

## Shared host

One collector container on the Docker network; every service sets
`OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318`. The collector config is the only place
that names a vendor. Sketch (fill in the vendor from its docs; the key comes from the
environment, never the file):

```yaml
receivers:
  otlp:
    protocols:
      http: {endpoint: 0.0.0.0:4318}
processors:
  batch: {}
  # Children's services: nothing from kid surfaces leaves the host (SKILL.md, Privacy).
  filter/kids:
    error_mode: ignore
    traces:
      span:
        - resource.attributes["service.name"] == "playpatch-web" and IsMatch(attributes["http.route"], "^/(child|profiles|api/child|api/watch|api/ai|api/video)")
    logs:
      log_record:
        - resource.attributes["service.name"] == "playpatch-web" and IsMatch(attributes["route"], "^/(child|profiles|api/child|api/watch|api/ai|api/video)")
exporters:
  otlphttp/vendor:
    endpoint: ${env:VENDOR_OTLP_ENDPOINT}
    headers: {Authorization: "${env:VENDOR_OTLP_AUTH}"}
service:
  pipelines:
    traces: {receivers: [otlp], processors: [filter/kids, batch], exporters: [otlphttp/vendor]}
    logs: {receivers: [otlp], processors: [filter/kids, batch], exporters: [otlphttp/vendor]}
```

The kid-route list must match the service's own list (playpatch `kid-surface.ts`). The
sketch above is out of date for playpatch: use its `infrastructure/otel/collector.yaml`, which
has the full list, a span-name rule, the worker-queue rule, and a test that keeps them in step.
`IsMatch` on a missing attribute is false, so guard `not IsMatch(...)` rules with `!= nil`. The
service drops those spans itself too; the collector filter is the second lock. To compare
two vendors, add a second exporter to the pipelines; to switch, change the env values.
