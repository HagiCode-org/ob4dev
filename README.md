# ob4dev

## OpenObserve local development

This repository includes a local OpenObserve stack for validating backend, AI, agent, and shared runtime telemetry during development.

It also includes ready-to-import dashboard assets under `dashboards/` so you can review HagiCode observability signals inside OpenObserve instead of rebuilding charts by hand.

### Start the stack

Run the stack from `repos/ob4dev`:

```bash
docker compose up -d
```

OpenObserve becomes available at:

- UI: `http://127.0.0.1:37652`
- OTLP gRPC ingest: `http://127.0.0.1:37653`

### Stop the stack

```bash
docker compose down
```

To stop the container and remove the persisted local data as well:

```bash
docker compose down -v
rm -rf data
```

### Administrator access

The bootstrap administrator credentials are defined directly in `docker-compose.yml`:

- Email: `root@example.com`
- Password: `Complexpass#123`

OpenObserve only needs `ZO_ROOT_USER_EMAIL` and `ZO_ROOT_USER_PASSWORD` on first startup. After `./data` already contains initialized state, keep `repos/ob4dev/docker-compose.yml` and the backend OTLP header example aligned if you change these values.

### Data persistence

OpenObserve stores local state in `repos/ob4dev/data` through the `./data:/data` bind mount in `repos/ob4dev/docker-compose.yml`.

- Keep `data/` if you want dashboards, users, and local telemetry history to survive restarts.
- Remove `data/` only when you want a clean local reset.

### Backend wiring

Use the local example in `repos/hagicode-core/src/PCode.Web/appsettings.Local.example.yml` to point a host-run `PCode.Web` process at this instance.

- UI access stays on host port `37652`
- Host-run OTLP export should use gRPC on `http://127.0.0.1:37653`
- Containerized local deployment from `repos/hagicode-core/docker-compose.yml` should use `http://host.docker.internal:37653`
- The documented OTLP header uses the same administrator credentials shown above

For Docker-based local deployment in `repos/hagicode-core`, enable these environment variables before `docker compose up -d`:

```bash
export TELEMETRY_OTLP_ENABLED=true
export TELEMETRY_OTLP_ENDPOINT=http://host.docker.internal:37653
export TELEMETRY_OTLP_HEADERS='Authorization=Basic cm9vdEBleGFtcGxlLmNvbTpDb21wbGV4cGFzcyMxMjM='
```

The HagiCode Compose file already maps `host.docker.internal` to the Docker host so Linux containers can still reach this OpenObserve instance through the published host port.

### Dashboards and reports

Import the dashboard JSON from `repos/ob4dev/dashboards/` after the stack is running.

- Dashboard assets:
  - `repos/ob4dev/dashboards/hagicode-backend-overview.dashboard.json`
  - `repos/ob4dev/dashboards/hagicode-backend-runtime.dashboard.json`
  - `repos/ob4dev/dashboards/hagicode-backend-database.dashboard.json`
  - `repos/ob4dev/dashboards/hagicode-ai-overview.dashboard.json`
  - `repos/ob4dev/dashboards/hagicode-agent-runtime.dashboard.json`
- Import helper: `repos/ob4dev/scripts/import_dashboards.py`
- Import and alert guide: `repos/ob4dev/dashboards/README.md`

The bundled dashboards now cover four local troubleshooting views:

- Backend overview: HTTP throughput, latency, 5xx trends, top routes, and Orleans grain health
- Runtime: .NET memory, thread-pool pressure, GC activity, and traffic context
- Database: EF Core command latency, failures, busiest collections, write pressure, and top slow SQL category/table combinations
- AI and agent runtime: request volume, latency percentiles, token usage, blended cost estimates, normalized errors, tool outcomes, and `Hagicode.Libs` ACP pool pressure

Validate the dashboard bundle before import:

```bash
cd repos/ob4dev
python scripts/import_dashboards.py --validate-only
```

Import or refresh the dashboards through the API:

```bash
cd repos/ob4dev
python scripts/import_dashboards.py
```

All dashboards default to `Last 1 hour` to keep local troubleshooting consistent right after import.
