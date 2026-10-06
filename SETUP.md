# Week 1 setup

## What this gets you
A local Postgres and Redis, running in containers, with the
initial schema already loaded. No application code yet — this
week is just about having a solid foundation to build on.

## Run it

```bash
docker-compose up -d
```

This starts both containers in the background. First run will
take a minute or two while Postgres pulls the image and runs the
schema file.

## Confirm it worked

Check both containers are healthy:

```bash
docker-compose ps
```

You should see `postgres` and `redis` both listed as `healthy`
(may take ~10 seconds after starting).

Connect to Postgres and check the tables exist:

```bash
docker exec -it apigateway-postgres psql -U apigateway -d apigateway -c "\dt"
```

You should see `tenants`, `api_keys`, `request_logs`, and
`request_logs_default` listed.

Confirm Redis is responding:

```bash
docker exec -it apigateway-redis redis-cli ping
```

Should reply `PONG`.

## If something's wrong

- **Port already in use**: something else on your machine is
  using 5432 or 6379. Either stop that, or change the left-hand
  side of the port mapping in `docker-compose.yml` (e.g. `"5433:5432"`).
- **Schema didn't load**: the schema file only runs the *first*
  time a container is created with an empty data volume. If you
  edit `schema.sql` after the first run, you'll need to wipe the
  volume to reload it: `docker-compose down -v` then
  `docker-compose up -d` again. This deletes all local data, which
  is fine at this stage since there's nothing real in it yet.

## Next: week 2

Once this is confirmed working, we'll start the Spring Boot
project and build the key generation and verification flow on
top of this schema.

<!-- Initial Tenant ID: 2a16f5e5-b108-4c5f-b5ba-348fdca9d187 -->
