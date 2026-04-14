# Dashboard assets

This directory stores importable OpenObserve dashboard JSON files for local development.

## Included dashboards

- `hagicode-backend-overview.dashboard.json`
  - HTTP throughput, average latency, and 5xx rate
  - Top routes by traffic
  - Orleans grain latency and error trends
- `hagicode-backend-runtime.dashboard.json`
  - .NET working set and GC memory footprint
  - Thread-pool queue pressure and thread count
  - GC collections plus traffic context
- `hagicode-backend-database.dashboard.json`
  - Database command latency and error trends
  - Busiest collections and write-heavy activity
  - HTTP error context for correlation
  - Top slow SQL category/table combinations

## Import into OpenObserve

1. Start the local stack from `repos/ob4dev`:
   ```bash
   docker compose up -d
   ```
2. Open `http://127.0.0.1:37652` and sign in with the bootstrap account from `docker-compose.yml`.
3. Go to Dashboards.
4. Use the dashboard import action and import the three JSON files from `repos/ob4dev/dashboards/`.
5. Trigger a few backend requests from `repos/hagicode-core`, then refresh the dashboards.

## Scripted import

You can also import or update the dashboards directly through the OpenObserve API:

```bash
python scripts/import_dashboards.py
```

The script defaults to the local `ob4dev` stack credentials and updates dashboards by title when they already exist.

All imported dashboards default to `Last 1 hour`.

## Metric assumptions

The dashboard queries use PromQL metric names normalized from OpenTelemetry semantic names, for example:

- `http.server.request.duration` -> `http_server_request_duration`
- `dotnet.process.memory.working_set` -> `dotnet_process_memory_working_set`
- `pcode.orleans.grain.duration` -> `pcode_orleans_grain_duration`
- `pcode.database.command.duration` -> `pcode_database_command_duration`

If your local ingestion pipeline rewrites metric names differently, adjust the PromQL expressions in the JSON file before importing.
