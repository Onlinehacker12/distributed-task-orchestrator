# Distributed Task Orchestrator

A production-minded distributed task orchestration system designed to demonstrate backend systems design, reliability engineering, and clean service architecture.

This project models how real-world services manage asynchronous work using an API-driven submission layer, durable state, background workers, retries, and observability. It is intentionally scoped as a **synthetic demo** and does not process real user or financial data.

---

## Project Overview

The Distributed Task Orchestrator provides a structured framework for submitting, executing, retrying, and monitoring asynchronous tasks. Rather than optimizing for scale or throughput, the system prioritizes **correctness, durability, and clarity of execution**, making design decisions explicit and easy to reason about.

A core principle of the system is that **persistent state is the source of truth**. Queues are treated strictly as transport mechanisms, while the database owns task state, scheduling decisions, and execution history. This approach mirrors many production-grade systems where reliability and recoverability are more important than raw performance.

---

## System Architecture

The system is composed of four primary components, each with a clearly defined responsibility:

### API Service (FastAPI)
- Accepts task submissions from clients
- Enforces strict input validation and request size limits
- Provides idempotent task creation using optional idempotency keys
- Persists task metadata and lifecycle state
- Exposes task status endpoints, health checks, and system metrics

### Database (SQLite)
- Acts as the authoritative source of truth
- Stores task metadata, current status, retry scheduling, execution results, and errors
- Records state transitions to enable inspection, debugging, and recovery
- Allows tasks to be replayed or inspected independently of the queue

### Queue & Distributed Locking (Redis)
- Provides lightweight task transport from the API to workers
- Coordinates execution without owning task state
- Uses distributed locks to prevent concurrent execution of the same task across workers

### Workers & Scheduler
- Workers execute tasks asynchronously based on task type
- Scheduler identifies tasks eligible for execution and re-enqueues them
- Retry logic applies exponential backoff with jitter to failed tasks
- Execution decisions are always validated against persisted task state

This separation of concerns ensures that **state management, coordination, and execution are cleanly isolated**, improving reliability and debuggability.

---

## Task Execution Model

Tasks move through a durable, well-defined state machine:

```
PENDING → QUEUED → RUNNING → COMPLETED
                    │   └→ FAILED
                    └→ (retry) QUEUED

PENDING / QUEUED / RUNNING → CANCELED
```

### Execution Guarantees

- **At-least-once execution**  
  Tasks may be retried, but are never silently dropped.

- **Idempotent task creation**  
  Duplicate submissions using the same idempotency key return the original task.

- **Durable state transitions**  
  All task state changes are persisted to the database.

- **Bounded retries**  
  Failed tasks retry with exponential backoff and jitter up to a configurable limit.

- **Distributed locking**  
  Redis locks prevent multiple workers from executing the same task concurrently.

Workers perform CAS-style checks to ensure tasks are only executed when in the expected state and eligible for processing.

---

## Supported Task Types

The system includes several built-in task handlers that simulate realistic backend workloads:

- **cpu_burn**  
  Simulates bounded CPU-intensive work for a specified duration.

- **data_transform**  
  Performs controlled JSON transformations such as field selection and renaming.

- **http_fetch**  
  Executes safe outbound HTTP GET requests with strict timeouts and guards against localhost and private network targets.

Task handlers are registered dynamically and resolved by workers at execution time.

---

## Reliability and Safety

Reliability and defensive design are first-class concerns:

- Idempotent task creation to prevent duplicate work
- Distributed locking to avoid concurrent execution
- CAS-style state transitions to reduce race conditions
- Strict schema validation using Pydantic
- Basic API key authentication
- Request size limits and outbound network safety checks

These safeguards ensure predictable behavior even under failure conditions.

---

## Observability

The system includes lightweight observability features inspired by production environments:

- Structured JSON logging with task-level context
- Prometheus-style metrics endpoint
- Counters for task creation, completion, retries, failures, cancellations, and worker exceptions

These features provide visibility into system behavior without requiring direct database access.

---

## Running Locally

```bash
docker compose up -d
pip install -r requirements.txt
python -m app.db.migrate
uvicorn app.main:app --reload
python -m app.core.scheduler
python -m app.workers.worker
```

---

## Design Tradeoffs

- **Redis Lists vs Streams**  
  Redis Lists were chosen for simplicity and clarity. Redis Streams would enable consumer groups and acknowledgements but introduce additional operational complexity.

- **SQLite vs PostgreSQL**  
  SQLite simplifies local development while maintaining portable schema and access patterns suitable for migration.

- **Database as Source of Truth**  
  Persisting task state enables recovery, inspection, and replay independent of queue state.

---

## Future Improvements

Potential enhancements that would further align this system with production-grade orchestration platforms:

- Replace Redis Lists with **Redis Streams** for stronger delivery guarantees
- Introduce **task priorities and rate limiting**
- Add **per-task-type concurrency limits** and execution timeouts
- Persist execution artifacts and logs to external storage
- Replace SQLite with **PostgreSQL** and introduce schema migrations
- Add **OpenTelemetry tracing** for end-to-end visibility
- Implement **role-based authentication** and scoped API access

---

## Intended Use

This project is intended as a **portfolio and learning system** demonstrating how distributed background processing services are designed, reasoned about, and operated. It is not production-hardened and is not intended for real workloads.
