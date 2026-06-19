# ob4dev - Agent Configuration

## Root Configuration

Inherits all behavior from `/AGENTS.md` at the monorepo root. Local rules extend or override the root file for this repository.

## Project Context

`ob4dev` provides a local OpenObserve stack for validating backend, AI, agent, and shared runtime telemetry during development. Includes ready-to-import dashboard assets under `dashboards/`.

## Working Directory

Run commands from `repos/ob4dev/`.

## Key Commands

```bash
docker compose up -d
docker compose down
```

## Key Paths

- `docker-compose.yml`: OpenObserve stack definition
- `dashboards/`: ready-to-import dashboard JSON assets

## Agent Guidelines

- This is a local development tooling repository; do not add application code.
- OpenObserve UI becomes available at `http://127.0.0.1:37652` after startup.
- OTLP gRPC ingest at `http://127.0.0.1:37653`.
- Dashboard assets under `dashboards/` are for manual import into OpenObserve; keep them up to date with monitoring needs.

## References

- `README.md`
