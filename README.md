# ob4dev

## OpenObserve local development

This repository includes a local OpenObserve stack for validating backend telemetry during development.

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

Use the local example in `repos/hagicode-core/src/PCode.Web/appsettings.Local.example.yml` to point `PCode.Web` at this instance.

- UI access stays on host port `37652`
- OTLP export should use gRPC on host port `37653`
- The documented OTLP header uses the same administrator credentials shown above
