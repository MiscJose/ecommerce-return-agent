# E-Commerce Return Negotiator Agent

A deployed, stateful AI agent built with LangGraph and FastAPI that walks a customer through an e-commerce return request, applying business rules (return window, VIP status, dollar thresholds) and pausing for human approval when needed. Deployed end to end on AWS (ECS Fargate + RDS Postgres + ECR).

## Status

The backend agent is functionally complete and **fully deployed and verified live on AWS**, including a durability test proving conversation state survives a task restart mid-conversation (see "Deployment Progress" below).

All five graph nodes and both routing functions have real logic and have been tested end to end, both locally and against the deployed AWS environment:

- `order_finder`: asks for and validates an order ID, with a state-driven retry loop (up to 3 attempts).
- `eligibility_gate`: checks the return window (order date + 30/60 days depending on VIP status) and either auto-denies or asks for a return reason.
- `escalation_gate`: checks the return total against a flat $150 threshold and either auto-approves or pauses for human (manager) approval.
- `finalize_return`: writes the final outcome to the `returns` table in Postgres (now correctly commits the transaction — see Bugs Found and Fixed below).
- `abandon_session`: a terminal node for when a customer fails to provide a valid order ID after 3 attempts.
- `route_order_finder` (found / retry / exhausted) and `route_eligibility_gate` (eligible / ineligible) handle all conditional branching.

What remains is primarily frontend work: a table viewer, a chat interface, and a demo-reset mechanism (see Next Steps).

## Tech Stack

- **Database:** Postgres. Locally, containerized via Docker Compose; in AWS, a managed **RDS** instance (`db.t4g.micro`, Single-AZ, gp2, 20 GiB, us-east-1) — live, seeded, and serving the deployed backend. Four business tables (`users`, `orders`, `order_items`, `returns`) plus three LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`, added by the `PostgresSaver` migration — see below).
- **Backend:** FastAPI, containerized, deployed to **AWS ECS (Express Mode)** running on Fargate (1 vCPU / 2 GB, `desiredCount` pinned to min=max=1). Image built and pushed to **ECR**. Live Application URL fronted by an auto-provisioned load balancer.
- **Agent framework:** LangGraph, using a `StateGraph`. **Checkpointer migrated from `InMemorySaver` to `AsyncPostgresSaver`** (see "PostgresSaver Migration" below) — conversation state now persists in Postgres rather than in-process memory, and has been verified to survive an ECS task restart mid-conversation.
- **Orchestration (local):** Docker Compose, running the `db` and `backend` services on a shared network. Note: the current `docker-compose.yml` only mounts `backend/db` into `/docker-entrypoint-initdb.d` and does not mount a persistent volume for Postgres's own data directory, so local data does not survive a full container teardown/recreate. A named volume (e.g. `pgdata:/var/lib/postgresql/data`) would fix this if local persistence becomes useful.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## PostgresSaver Migration (completed)

Replaced `InMemorySaver` (a plain in-process Python dict — lost on any task restart, and incompatible with running more than one task) with `AsyncPostgresSaver` from the `langgraph-checkpoint-postgres` package, backed by the same RDS instance used for business data.

Key structural changes this required:

- **`build_graph.py`** no longer compiles the graph. It now only constructs and exports the uncompiled `builder` (the graph's structure/nodes/edges) — compiling requires a live checkpointer connection, which doesn't exist yet at import time.
- **`main.py`** now opens the Postgres connection and compiles the graph inside a FastAPI `lifespan` context manager, so the connection opens once on app startup, stays open for the life of the process, and closes cleanly on shutdown. The compiled graph is stored on `app.state.graph`, and both route handlers now take an additional `Request` parameter (named `req` to avoid colliding with the existing `ResumeRequest` Pydantic body parameter in `/returns/resume`) to access it.
- Used **`AsyncPostgresSaver`** (from `langgraph.checkpoint.postgres.aio`), not the sync `PostgresSaver` — required for compatibility with the app's `async def` / `await ...ainvoke(...)` endpoints; pairing an async app with the sync checkpointer would have silently blocked the event loop on every DB call.
- `requirements.txt` gained two new entries: `langgraph-checkpoint-postgres` (the checkpointer package, which depends on `psycopg` v3 — a separate driver from the `psycopg2-binary` already used elsewhere in the app; both coexist without conflict) and `psycopg[binary]` — required explicitly, since plain `psycopg` has no bundled `libpq` implementation and fails at runtime with `ImportError: no pq wrapper available` otherwise (mirrors the existing reason `psycopg2-binary` rather than plain `psycopg2` is used).
- `checkpointer.setup()` (awaited, since using the async saver) runs on every app startup — idempotent, creates the three checkpoint tables if they don't already exist, analogous to how `schema.sql` was run once manually for the business tables.

**Verified via a live durability test against the deployed AWS environment:** started a conversation, paused it at the manager-approval `interrupt()`, manually stopped the running ECS task, waited for the replacement task (from `desiredCount: 1`) to come up, then sent the resume call with the same `thread_id` against the new task. It completed correctly — confirming conversation state now genuinely survives a process restart, which `InMemorySaver` could never have done. This directly strengthens the "multi-turn state persistence" claim for the demo: it's now true across restarts/scaling, not just within one process's uptime.

## State Design Notes

- `ReturnState.messages` accumulates a full, chronological transcript of every question asked and every answer received across the conversation, using LangGraph's `add_messages` reducer. Every message is tagged via `additional_kwargs={"channel": "customer"}` or `additional_kwargs={"channel": "manager"}`, so a future frontend can filter the transcript by audience.
- `auto_deny_reason` records why a return was denied automatically by policy (currently only the return-window-expired case in `eligibility_gate`), with no human involved.
- An earlier `escalation_reason` field (intended to record a human's approve/deny reasoning in `escalation_gate`) was considered and then removed: without actually asking the manager for their reasoning, the field would only have duplicated the `status` field's value.

## Deployment Progress (AWS)

Stack: **ECS Express Mode** (backend, Fargate) + **RDS** (Postgres) + **ECR** (image registry), chosen over AWS App Runner (sunset April 2026) and over a full manual ECS+VPC+ALB build.

**Fully live and verified end to end**, including:

- IAM (`Jose`, `AdministratorAccess` — an initial attachment that silently failed to save was caught and fixed via the root user).
- RDS instance created, region-matched to ECS (us-east-1), security group opened for both local dev (`/32` IP) and the ECS task's security group.
- Schema and seed data loaded into RDS, after finding and fixing a real bug in `seed.sql` (mismatched `user_id`/`order_id` values causing FK violations) and trimming an unreachable seeded `'pending'` return row (no code path ever writes that status — it's only the initial placeholder before a real outcome is decided).
- Backend image built (`--platform linux/amd64`, required since local builds on Apple Silicon default to arm64, which Fargate can't run) and pushed to ECR.
- Deployed via ECS Express Mode, `desiredCount` pinned to min=max=1 (required while conversation state lived in a single process — now less critical post-`PostgresSaver`, but still sensible to keep at 1 given cost and the demo's scale).
- Full conversation flow (order lookup → return reason → auto-approve/auto-deny/manager-escalation → finalize) verified live against the deployed URL via curl, for both under- and over-threshold orders.
- `finalize_return`'s missing `conn.commit()` (see Bugs Found and Fixed) confirmed fixed by checking `returns` row counts in RDS directly before/after a live test.
- `PostgresSaver` migration verified via the live task-restart durability test described above.

**Known, deliberately deferred:**

- RDS master password is a plaintext ECS environment variable rather than a Secrets Manager reference. Fine for this single-developer account; worth migrating before broader access to the account, or as a "how I'd do this in production" talking point.
- RDS billing: the account was created after AWS's July 2025 free-tier model change, so this account uses a $100 credit balance rather than always-free resource allowances — RDS usage is billed normally and drawn from credits, not free by default. Config itself (`t4g.micro`, gp2, Single-AZ, Standard-mode monitoring) is already the cheapest reasonable shape; RDS can be stopped between work sessions to pause compute billing (auto-restarts after 7 days if left stopped). ECS Fargate has no free tier at all and is the larger ongoing cost driver — Express Mode enforces a minimum of 1 task, so it cannot be scaled to zero without deleting and later recreating the service.

## Bugs Found and Fixed Along the Way

- **`abandon_session.py` bad import:** imported `AIMessage` from `.state` (only `AnyMessage` is exported there); should import `AIMessage` directly from `langchain.messages`, matching the pattern used correctly in every other node. This crashed the app at import time and was the cause of ECS repeatedly failing to start any task on first deploy.
- **`finalize_return.py` missing commit:** the `INSERT` into `returns` executed but was never committed (`psycopg2` defaults to `autocommit=False`), and the connection was never closed on the success path. Completed returns were silently not persisted. Fixed with an explicit `conn.commit()` and a `finally` block closing `cur`/`conn`; the bare `except: return None` should still be replaced with proper logging/re-raise so a node failure doesn't silently return `None` into the graph's state merge.
- **`seed.sql` FK mismatch:** the `orders` table's seed `INSERT` had `user_id` values that didn't correspond to any real user (only 3 users exist, but `user_id` values 1–5 were used) — the row comments' intent ("order_id 1", "order_id 2"...) had been placed in the wrong column. Fixed by correcting `user_id` to `1, 1, 2, 3, 3` (Emma: orders 1 & 2, James: order 3, Sofia: orders 4 & 5).
- **RDS password with a `%` character:** a percent sign in the master password was being interpreted by `DATABASE_URL`'s URI parsing as the start of a percent-encoded byte sequence, causing a `UnicodeDecodeError` deep in `psycopg2`. Fixed by choosing a new password avoiding URI-reserved characters (`% @ : / ? # [ ]`).
- **Missing root health-check route:** ECS Express Mode's load balancer health-checks `/`, which had no handler, causing persistent `503 Service Temporarily Unavailable` responses even once the container was otherwise healthy. Fixed by adding a simple `GET /` health-check route.
- **`os.get` → `os.getenv`:** an early draft of the `PostgresSaver` migration used the nonexistent `os.get(...)`; `os` has no `.get()` method (that's a dict method) — corrected to `os.getenv("DATABASE_URL")`.
- **`psycopg[binary]` missing:** `langgraph-checkpoint-postgres` pulls in plain `psycopg` (v3) with no bundled Postgres driver implementation, causing `ImportError: no pq wrapper available` at runtime inside the container (the slim base image has no system `libpq`, and no C/binary extension was installed). Fixed by adding `psycopg[binary]` explicitly to `requirements.txt`.

## Next Steps

1. **Demo reset mechanism:** A scoped `POST /admin/reset-demo`-style endpoint to reset the `returns` table and the LangGraph checkpoint tables back to a clean state between demo runs — via `TRUNCATE ... RESTART IDENTITY` plus re-seeding, not a full schema rebuild, and not touching `users`/`orders`/`order_items`. Should be gated (e.g. a shared secret) so it isn't triggerable by an arbitrary visitor to the public URL.
2. **Frontend table viewer:** Read-only endpoints/views to display all four business tables, so career-fair visitors can see real data and know what order IDs to try.
3. **Frontend chat interface:** The actual conversational UI wrapping `/returns/start` and `/returns/resume`.

## Future Enhancements (lower priority / deferred)

- **Langfuse integration:** Observability and evals. Parked for time, not abandoned.
- **Itemized returns:** The agent currently assumes a customer wants to return an entire order. Asking which specific items are being returned, and computing `return_items_total` from that, is a deferred addition.
- **LLM-based reason classification:** The lenient-vs-needs-review judgment on a customer's stated return reason is not yet wired in. `reason_category` remains unset until this exists.
- **Human escalation for exhausted order-ID lookups:** currently ends the session automatically via `abandon_session` rather than pausing for a human to supply a corrected order ID. Deliberate simplification for demo scope.
- **Manager-facing approval interface:** manager decisions are still simulated via direct `curl`/Postman calls to `/returns/resume`. A real dashboard (pending escalations, its own approve/deny actions, and a way to stay current — polling or SSE/WebSockets — plus likely authentication) is deferred as non-core to demonstrating the agent architecture itself.
- **Migrate remaining `psycopg2` usage to `psycopg3`:** `psycopg2` is now in maintenance mode; the checkpointer already uses `psycopg` v3, so the rest of the app (`helper.py`, `finalize_return.py`) migrating too would let the database layer become genuinely async, consistent with the app's `async def` endpoints and `graph.ainvoke()` calls (which currently wrap synchronous, blocking `psycopg2` calls under the hood).
- **SQL injection in `/orders`:** builds its query with an f-string (`f"select * from orders where order_id={order_id}"`) instead of parameterizing like `find_order` correctly does. Low urgency while RDS is locked to a known security group, but should be parameterized before any public exposure.
- **Secrets Manager for `DATABASE_URL`:** move the RDS password out of a plaintext ECS environment variable, per the note under Deployment Progress above.