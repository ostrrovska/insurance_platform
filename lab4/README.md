# Lab 4 — Event-Driven Architecture with Transactional Outbox

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT / HTTP                               │
└────────────────┬───────────────────────────┬────────────────────────┘
                 │                           │
         POST /customers             POST /policies
                 │                           │
    ┌────────────▼──────────┐   ┌────────────▼──────────┐
    │   Customer Service    │   │    Policy Service      │
    │   :8001               │──▶│   :8002                │
    │                       │   │   (validates customer) │
    │  ┌─────────────────┐  │   │                        │
    │  │  customers DB   │  │   │  ┌─────────────────┐  │
    │  │  + outbox table │  │   │  │  policies DB     │  │
    │  └────────┬────────┘  │   │  │  + outbox table  │  │
    │           │ same TX   │   │  └────────┬─────────┘  │
    │  ┌────────▼────────┐  │   │           │ same TX    │
    │  │  Outbox Relay   │  │   │  ┌────────▼─────────┐  │
    │  │  (polls every   │  │   │  │  Outbox Relay    │  │
    │  │   2 seconds)    │  │   │  │  (polls every    │  │
    │  └────────┬────────┘  │   │  │   2 seconds)     │  │
    └───────────┼───────────┘   └──┴────────┬──────────┘
                │                           │
                └─────────────┬─────────────┘
                              │  publishes to
                    ┌─────────▼──────────┐
                    │     RabbitMQ        │
                    │   Topic Exchanges:  │
                    │   • customers       │
                    │   • policies        │
                    └─────────┬──────────┘
                              │ queue: notification_service.events
                    ┌─────────▼──────────┐
                    │  Notification Svc  │
                    │  :8003             │
                    │  (async consumer)  │
                    │  ┌──────────────┐  │
                    │  │notifications │  │
                    │  │     DB       │  │
                    │  └──────────────┘  │
                    └────────────────────┘
```

## Key Concepts

### Transactional Outbox Pattern
Instead of publishing directly to RabbitMQ (which could leave DB and broker out of sync), each service writes the event to an `outbox_messages` table **in the same database transaction** as the business operation.

```
BEGIN TRANSACTION
  INSERT INTO customers (name, email) VALUES (...)  ← business op
  INSERT INTO outbox_messages (event_type, payload, status='PENDING') ← event
COMMIT
```

A background **relay** process polls the outbox table every 2 seconds and forwards `PENDING` messages to RabbitMQ, then marks them `SENT`.

### Why this solves the dual-write problem
- If the app crashes before committing → **neither** row is saved (atomic rollback)
- If the app crashes after committing but before publishing → the relay **retries** on next poll
- If RabbitMQ is down → events stay `PENDING` in DB and are delivered **automatically** when the broker comes back

## Quick Start

```bash
# 1. Start all services
docker compose up --build

# 2. Open RabbitMQ Management UI
open http://localhost:15672   # guest / guest

# 3. Run tests from tests.http (or use curl)
```

## Reliability Test (Step-by-step)

```bash
# 1. Stop RabbitMQ
docker compose stop rabbitmq

# 2. Create a policy — it will succeed (saved to DB)
curl -X POST http://localhost:8002/api/v1/policies/ \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1, "policy_type": "Life Insurance"}'

# 3. Check outbox — event is PENDING
docker exec -it policy_db psql -U user -d policy_db \
  -c "SELECT id, event_type, status FROM outbox_messages;"

# 4. Restart RabbitMQ
docker compose start rabbitmq

# 5. Wait ~5 seconds, then check notifications
curl http://localhost:8003/api/v1/notifications
# → The event appears! Delivered automatically by the relay.
```

## Outbox Table Schema

| Column       | Type        | Description                        |
|--------------|-------------|------------------------------------|
| id           | int PK      | Auto-increment                     |
| event_type   | varchar     | e.g. "CustomerCreated"             |
| exchange     | varchar     | RabbitMQ exchange name             |
| routing_key  | varchar     | e.g. "policies.created"            |
| payload      | text (JSON) | Full event envelope                |
| status       | enum        | PENDING → SENT (or FAILED)         |
| created_at   | timestamptz | When the business op happened      |
| sent_at      | timestamptz | When the relay published it        |
| error        | text        | Error message if FAILED            |

## Event Envelope Format (JSON)

```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "PolicyCreated",
  "occurred_at": "2025-01-15T10:30:00.000000+00:00",
  "data": {
    "policy_id": 1,
    "customer_id": 1,
    "policy_type": "Health Insurance",
    "status": "ACTIVE",
    "correlation_id": "trace-alice-health-001"
  }
}
```

## Service Ports

| Service              | Port  | Purpose                        |
|----------------------|-------|--------------------------------|
| customer_service     | 8001  | REST API + Outbox Relay        |
| policy_service       | 8002  | REST API + Outbox Relay        |
| notification_service | 8003  | REST API + RabbitMQ Consumer   |
| RabbitMQ AMQP        | 5672  | Message broker                 |
| RabbitMQ Management  | 15672 | Web UI (guest/guest)           |
| customer_db          | 5433  | PostgreSQL                     |
| policy_db            | 5434  | PostgreSQL                     |
| notification_db      | 5435  | PostgreSQL                     |
