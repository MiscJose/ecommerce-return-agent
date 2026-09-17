# E-Commerce Return Negotiator Agent

A deployed, stateful AI agent built with LangGraph and FastAPI that walks a customer through an e-commerce return request, applying business rules (return window, VIP status, dollar thresholds) and pausing for human approval when needed.

## Status

The backend agent is functionally complete. All five graph nodes and both routing functions have real logic (not stubs) and have been tested live end to end via curl:

- `order_finder`: asks for and validates an order ID, with a state-driven retry loop (up to 3 attempts).
- `eligibility_gate`: checks the return window (order date + 30/60 days depending on VIP status) and either auto-denies or asks for a return reason.
- `escalation_gate`: checks the return total against a flat $150 threshold and either auto-approves or pauses for human (manager) approval.
- `finalize_return`: writes the final outcome to the `returns` table in Postgres.
- `abandon_session`: a terminal node for when a customer fails to provide a valid order ID after 3 attempts.
- `route_order_finder` (found / retry / exhausted) and `route_eligibility_gate` (eligible / ineligible) handle all conditional branching.

AWS deployment is in progress (see "Deployment Progress" below). What remains beyond that is not core agent logic, but everything listed under Future Enhancements below: a real LLM integration, a frontend, and a persistent checkpointer.

## Tech Stack

- **Database:** Postgres. Locally, containerized via Docker Compose; in AWS, a managed **RDS** instance (see Deployment Progress). Four tables (`users`, `orders`, `order_items`, `returns`) with real constraints, including foreign keys and a `CHECK` constraint on `return_status`. The `returns` table no longer references `item_id`, since the agent currently treats every return as the whole order (see Itemized returns below), and `return_reason` is nullable to accommodate auto-denied returns where no customer-given reason exists.
- **Backend:** FastAPI, containerized. Locally run via Docker Compose; in AWS, the image is built and pushed to **ECR** for deployment via **ECS Express Mode**.
- **Agent framework:** LangGraph, using a `StateGraph` with `InMemorySaver` as the checkpointer (to be replaced — see Future Enhancements).
- **Orchestration (local):** Docker Compose, running the `db` and `backend` services on a shared network. The backend connects to Postgres via the service name `db`, not `localhost`. Note: the current `docker-compose.yml` only mounts `backend/db` into `/docker-entrypoint-initdb.d` and does not mount a persistent volume for Postgres's own data directory, so local data does not survive a full container teardown/recreate. A named volume (e.g. `pgdata:/var/lib/postgresql/data`) would fix this if local persistence becomes useful.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## State Design Notes

- `ReturnState.messages` accumulates a full, chronological transcript of every question asked and every answer received across the conversation, using LangGraph's `add_messages` reducer. Every message is tagged via `additional_kwargs={"channel": "customer"}` or `additional_kwargs={"channel": "manager"}`, so a future frontend can filter the transcript by audience (e.g., a customer-facing chat view would exclude "manager" channel messages).
- `auto_deny_reason` records why a return was denied automatically by policy (currently only the return-window-expired case in `eligibility_gate`), with no human involved.
- An earlier `escalation_reason` field (intended to record a human's approve/deny reasoning in `escalation_gate`) was considered and then removed: without actually asking the manager for their reasoning, the field would only have duplicated the `status` field's value, adding no real information.

## Deployment Progress (AWS)

Decision made: **ECS Express Mode** (backend) + **RDS** (Postgres) + **ECR** (image registry), chosen over AWS App Runner (which entered maintenance mode/sunset in April 2026) and over a full manual ECS+VPC+ALB build.

Completed:

- New AWS account created and secured; IAM user `Jose` created. (Note: an initial `AdministratorAccess` attachment did not actually save — the user had only `IAMUserChangePassword` attached, causing `AccessDenied` errors on basic calls like `iam:GetUser`. Fixed by re-attaching `AdministratorAccess` via the **root** user in the console, since a user without IAM permissions cannot fix its own policy attachment.)
- Zero-spend billing alarm created and confirmed firing correctly.
- RDS instance created via Full Configuration (not Express — Express is Aurora Serverless with IAM-only auth, wrong fit for this project): Free Tier, Single-AZ, gp3, 20GB, in **us-east-1** (an earlier console session had defaulted to us-east-2/Ohio, which caused a brief "where's my database" confusion — RDS instances are region-scoped, and the console's active region must match).
- RDS security group configured with a single inbound rule: PostgreSQL/TCP/5432 from the developer's IP (`/32`, via "My IP") — scoped for personal dev access only, not for the eventual public app (the deployed backend's own security group should be the source once ECS is live).
- Connected to RDS via local `psql` client (installed via `brew install postgresql`), confirmed TLS-encrypted connection.
- Loaded `schema.sql` and `seed.sql` into RDS. In the process, found and fixed a real bug in `seed.sql`: the `orders` table INSERT had `user_id` values (1–5) that didn't match the actual `user_id`s in `users` (only 3 users exist), causing foreign key violations. The row comments ("order_id 1", "order_id 2", etc.) were correct in intent but had been placed in the wrong column. Corrected to `user_id` values `1, 1, 2, 3, 3` (Emma has orders 1 & 2, James has order 3, Sofia has orders 4 & 5). This bug exists identically in the local Docker Compose path, not just RDS — worth fixing there too.
- Also trimmed the seeded `returns` row that had `return_status = 'pending'`: no code path in the graph ever writes a `returns` row while still `pending` (that value only exists as the initial placeholder in `default_return_state` before `eligibility_gate` or `escalation_gate` resolve a real outcome), so a seeded `pending` row didn't correspond to any reachable agent state and risked confusing demo visitors. `seed.sql` now seeds only `accepted` and `denied` example rows.
- Backend Docker image built (`docker build --platform linux/amd64 ...` — explicit platform flag needed since local builds on Apple Silicon default to arm64, which Fargate can't run) and pushed to a new ECR repository (`ecommerce-return-agent`).

Next steps:

1. Deploy the pushed ECR image via **ECS Express Mode**, with `DATABASE_URL` pointed at the RDS endpoint (not `db`, which only resolves inside the local Compose network). Explicitly set `desiredCount: 1` for now — running more than one task would break `InMemorySaver`, since conversation state currently lives only in a single process's memory (see Future Enhancements).
2. Prefer AWS Secrets Manager or SSM Parameter Store for the RDS password in the ECS task definition rather than a plaintext environment variable.
3. Verify the deployed backend with the same curl sequence used throughout local testing (`/returns/start`, `/returns/resume`), confirming rows land correctly in the RDS `returns` table.
4. Frontend work begins only after the above is confirmed live.

## Future Enhancements

- **Persistent checkpointer:** Replace `InMemorySaver` with `PostgresSaver`, pointed at the same RDS instance. This is now the top-priority follow-up, not just a nice-to-have — `InMemorySaver` means conversation state (including pending manager escalations) is lost on any task restart and breaks entirely if ECS ever runs more than one task. `PostgresSaver` also directly strengthens the "multi-turn state persistence" demo claim, since it makes that true across restarts/scaling rather than only within one process's uptime.
- **Demo reset mechanism:** A scoped `POST /admin/reset-demo`-style endpoint to reset the `returns` table (and, once `PostgresSaver` lands, the checkpoint table) back to a clean seeded state between demo runs — via `TRUNCATE ... RESTART IDENTITY` plus re-seeding, not a full schema rebuild, and not touching `users`/`orders`/`order_items`. Should be gated (e.g. a shared secret) so it isn't triggerable by an arbitrary visitor to the public URL.
- **Frontend table viewer:** Read-only endpoints/views to display all four tables (`users`, `orders`, `order_items`, `returns`) in the frontend, so career-fair visitors can see real data and know what order IDs to try.
- **Langfuse integration:** Observability and evals. Parked for time, not abandoned.
- **Itemized returns:** The agent currently assumes a customer wants to return an entire order. Asking which specific items are being returned, and computing `return_items_total` from that, is a deferred addition.
- **LLM-based reason classification:** The lenient-vs-needs-review judgment on a customer's stated return reason is not yet wired in. `reason_category` remains unset until this exists.
- **Human escalation for exhausted order-ID lookups:** When a customer fails to provide a valid order ID after three attempts, the session currently ends automatically via a dedicated terminal node (`abandon_session`), rather than pausing for a human to manually supply a corrected order ID. This was a deliberate simplification for demo scope.
- **Multi-interrupt resume handling:** The `/returns/resume` endpoint currently assumes a single resume call leads to graph completion. Now that `eligibility_gate` and `escalation_gate` are fully built and each owns its own `interrupt()`, a full conversation can involve several consecutive pauses in sequence (order ID, then return reason, then manager approval). This has been tested manually via repeated curl calls, but the endpoint itself has no special handling for this beyond simply returning whatever interrupt or result comes back from each call.
- **Manager-facing approval interface:** `escalation_gate` pauses via `interrupt()` when a return exceeds the auto-approval threshold, genuinely waiting on a human decision before proceeding. For now, that decision is simulated manually by calling `/returns/resume` directly (e.g., via curl or Postman) with the same `thread_id`, standing in for a manager's response — and once deployed, this works identically against the live ECS URL instead of `localhost`. A real interface for this (a dashboard showing pending escalations, with its own approve/deny actions) is deferred, since it would require its own tracking mechanism for "threads awaiting human review," a way for that view to stay current (polling or a push-based mechanism like SSE/WebSockets), and likely authentication, none of which is core to demonstrating the agent architecture itself.
- **Migrate `psycopg2` to `psycopg3`:** `psycopg2` is now in maintenance mode (bug fixes only, no new features); the ecosystem (SQLAlchemy 2.0+, Django 4.2+, and others) has settled on `psycopg3` (published on PyPI as `psycopg`) as the recommended driver for new projects as of 2026. Not urgent, since `psycopg2` still works reliably, but worth doing so the stack reflects current practice. This migration would also be the natural point to address a related inconsistency: FastAPI's endpoints are declared `async def` and call `graph.ainvoke()`, but every database call inside the graph's nodes (`find_order`, `finalize_return`) currently uses synchronous, blocking `psycopg2` calls under the hood, which undercuts the benefit of the async endpoint declarations. `psycopg3` has native async support, which would let the database layer become genuinely async and consistent with the rest of the backend.
- **`finalize_return` transaction bug:** The current implementation executes the `INSERT` into `returns` but never calls `conn.commit()`, and has no `finally` block closing the connection on the success path. Since `psycopg2` defaults to `autocommit=False`, the insert is effectively rolled back when the connection object goes out of scope — meaning completed returns are not actually persisted. Needs `conn.commit()` after the `execute()` call, a `finally` block closing `cur`/`conn`, and the bare `except: return None` replaced with proper logging/re-raise so a node failure doesn't silently return `None` into the graph's state merge.
- **SQL injection in `/orders`:** The `GET /orders` endpoint in `main.py` builds its query with an f-string (`f"select * from orders where order_id={order_id}"`) instead of parameterizing like `find_order` in `helper.py` correctly does. Low urgency while RDS is locked to a single dev IP, but should be parameterized before any public exposure.

- **Deployment (in progress — see Deployment Progress above for current state):**
  - **ECS Express Mode** for the backend container. Amazon ECS's newer, simplified deployment mode (launched November 2025): given a container image and two IAM roles, it auto-provisions the Application Load Balancer, HTTPS, auto-scaling, and a working URL, while every underlying resource it creates remains fully visible and directly editable in the AWS account.
  - **RDS** for a managed Postgres instance — live and seeded, replacing the local Docker-based `db` service for deployment purposes (local Docker Compose is retained for day-to-day dev).
  - **ECR** as the container registry the backend image is pushed to before ECS Express Mode deploys it — image built and pushed.
  - A frontend decision (likely a lightweight React app via Vite, to display the underlying Postgres tables and provide a chat-style interface to the agent) and its own hosting approach are still open, and will be addressed after the backend deployment is live and confirmed working.