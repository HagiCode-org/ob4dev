# Dashboard assets

This directory stores repository-managed OpenObserve dashboard JSON for local backend, AI, agent, and shared runtime telemetry validation.

## Included dashboards

- `hagicode-backend-overview.dashboard.json`
  - HTTP throughput, average latency, 5xx rate, top routes, and Orleans grain health.
- `hagicode-backend-runtime.dashboard.json`
  - .NET working set, GC footprint, thread-pool pressure, and traffic context.
- `hagicode-backend-database.dashboard.json`
  - Database latency, error trends, busiest collections, and write pressure.
- `hagicode-ai-overview.dashboard.json`
  - AI request throughput, failure rate, p95/p99 latency, token volume, blended estimated-cost example, and top project token consumers.
- `hagicode-agent-runtime.dashboard.json`
  - Agent lifecycle outcomes, agent latency, tool outcomes, normalized error breakdown, and shared ACP pool pressure from `Hagicode.Libs`.

## Import into OpenObserve

1. Start the local stack from `repos/ob4dev`:
   ```bash
   docker compose up -d
   ```
2. Open `http://127.0.0.1:37652` and sign in with the bootstrap account from `repos/ob4dev/docker-compose.yml`.
3. Go to Dashboards.
4. Import the five JSON files from `repos/ob4dev/dashboards/`.
5. Start a backend host from `repos/hagicode-core`, trigger a few AI requests or agent runs, then refresh the dashboards.

All dashboards default to `Last 1 hour`.

## Scripted import and validation

Validate the dashboard bundle, normalized metric names, and import coverage before touching OpenObserve:

```bash
cd repos/ob4dev
python scripts/import_dashboards.py --validate-only
```

Import or update every dashboard in the local stack:

```bash
cd repos/ob4dev
python scripts/import_dashboards.py
```

Import or validate only one dashboard asset:

```bash
cd repos/ob4dev
python scripts/import_dashboards.py --dashboard hagicode-ai-overview.dashboard.json --validate-only
python scripts/import_dashboards.py --dashboard hagicode-agent-runtime.dashboard.json
```

The script validates three things before any API call:

- every `*.dashboard.json` file in `repos/ob4dev/dashboards/` is listed in `scripts/import_dashboards.py`
- every panel query keeps `fields.stream` aligned with the normalized PromQL metric name used in the query
- every dashboard file is valid JSON with non-empty panels and unique panel ids

## Metric normalization assumptions

OpenObserve PromQL uses normalized metric names derived from dotted OpenTelemetry instruments.

| OpenTelemetry instrument | OpenObserve / PromQL stream |
| --- | --- |
| `pcode.ai.request` | `pcode_ai_request` |
| `pcode.ai.request.duration` | `pcode_ai_request_duration` |
| `pcode.ai.token.usage` | `pcode_ai_token_usage` |
| `pcode.ai.error` | `pcode_ai_error` |
| `pcode.agent.lifecycle` | `pcode_agent_lifecycle` |
| `pcode.agent.duration` | `pcode_agent_duration` |
| `pcode.agent.tool.outcome` | `pcode_agent_tool_outcome` |
| `hagicode.cli_acp_session_pool.active_entries` | `hagicode_cli_acp_session_pool_active_entries` |
| `hagicode.cli_acp_session_pool.leased_entries` | `hagicode_cli_acp_session_pool_leased_entries` |
| `hagicode.cli_acp_session_pool.indexed_keys` | `hagicode_cli_acp_session_pool_indexed_keys` |

If your ingestion pipeline rewrites names differently, update the PromQL expressions and `fields.stream` values together, then rerun `python scripts/import_dashboards.py --validate-only`.

## Estimated cost assumptions

The AI overview dashboard ships with a blended cost panel that multiplies prompt and completion token rates by example coefficients.

- Treat the shipped query as a placeholder, not billing-grade truth.
- Replace the coefficients with your environment-specific model pricing before using it for alerts or reporting.
- When pricing data is unavailable, use the token panels as the fallback optimization signal.

## Alert query examples

These examples are designed for OpenObserve PromQL-style alerting and reuse the same normalized metric names as the dashboards.

### AI p95 latency by model

```promql
histogram_quantile(0.95, sum by (le, model) (rate(pcode_ai_request_duration_bucket[10m]))) > 4000
```

### AI p99 latency by provider and operation

```promql
topk(5, histogram_quantile(0.99, sum by (le, provider, operation) (rate(pcode_ai_request_duration_bucket[10m])))) > 8000
```

### AI failure-rate spike

```promql
100 * sum(rate(pcode_ai_request{outcome=~"failure|cancelled"}[10m])) / clamp_min(sum(rate(pcode_ai_request[10m])), 0.001) > 5
```

### Token anomaly by project

```promql
topk(5, sum by (project_id) (rate(pcode_ai_token_usage{token_type="total", project_id!="unknown"}[15m]))) > 5000
```

### Agent p95 duration regression

```promql
histogram_quantile(0.95, sum by (le, agent_name) (rate(pcode_agent_duration_bucket[10m]))) > 15000
```

### ACP pool pressure threshold

```promql
100 * sum by (provider) (hagicode_cli_acp_session_pool_leased_entries{provider!=""}) / clamp_min(sum by (provider) (hagicode_cli_acp_session_pool_active_entries{provider!=""}), 1) > 80
```

## Local validation flow

A practical end-to-end local check looks like this:

1. `cd repos/ob4dev && docker compose up -d`
2. `cd repos/ob4dev && python scripts/import_dashboards.py --validate-only`
3. `cd repos/ob4dev && python scripts/import_dashboards.py`
4. Start `PCode.Web` or another backend host from `repos/hagicode-core` with OTLP export pointing at the local `ob4dev` stack.
5. Trigger at least one AI request, one streaming run, and one agent flow so the new panels receive data.
6. Verify that the AI overview and agent runtime dashboards populate without manual query rewiring.
