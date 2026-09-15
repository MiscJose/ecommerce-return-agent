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

What remains is not core agent logic, but everything listed under Future Enhancements below: a real LLM integration, a frontend, and a deployment decision.

## Tech Stack

- **Database:** Postgres, containerized. Four tables (`users`, `orders`, `order_items`, `returns`) with real constraints, including foreign keys and a `CHECK` constraint on `return_status`. The `returns` table no longer references `item_id`, since the agent currently treats every return as the whole order (see Itemized returns below), and `return_reason` is nullable to accommodate auto-denied returns where no customer-given reason exists.
- **Backend:** FastAPI, containerized.
- **Agent framework:** LangGraph, using a `StateGraph` with `InMemorySaver` as the checkpointer.
- **Orchestration:** Docker Compose, running the `db` and `backend` services on a shared network. The backend connects to Postgres via the service name `db`, not `localhost`.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## State Design Notes

- `ReturnState.messages` accumulates a full, chronological transcript of every question asked and every answer received across the conversation, using LangGraph's `add_messages` reducer. Every message is tagged via `additional_kwargs={"channel": "customer"}` or `additional_kwargs={"channel": "manager"}`, so a future frontend can filter the transcript by audience (e.g., a customer-facing chat view would exclude "manager" channel messages).
- `auto_deny_reason` records why a return was denied automatically by policy (currently only the return-window-expired case in `eligibility_gate`), with no human involved.
- An earlier `escalation_reason` field (intended to record a human's approve/deny reasoning in `escalation_gate`) was considered and then removed: without actually asking the manager for their reasoning, the field would only have duplicated the `status` field's value, adding no real information.

## Future Enhancements

- **Persistent checkpointer:** Replace `InMemorySaver` with `PostgresSaver`. Since Postgres is already running in this stack, this is a natural next step. Currently, any backend restart loses all in-progress conversations, since `InMemorySaver` keeps state only in the backend process's memory.
- **Langfuse integration:** Observability and evals. Parked for time, not abandoned.
- **Frontend:** Not started. The project is currently backend-only, tested via `curl` and a local `test.py` script.
- **Itemized returns:** The agent currently assumes a customer wants to return an entire order. Asking which specific items are being returned, and computing `return_items_total` from that, is a deferred addition.
- **LLM-based reason classification:** The lenient-vs-needs-review judgment on a customer's stated return reason is not yet wired in. `reason_category` remains unset until this exists.
- **Human escalation for exhausted order-ID lookups:** When a customer fails to provide a valid order ID after three attempts, the session currently ends automatically via a dedicated terminal node (`abandon_session`), rather than pausing for a human to manually supply a corrected order ID. This was a deliberate simplification for demo scope.
- **Multi-interrupt resume handling:** The `/returns/resume` endpoint currently assumes a single resume call leads to graph completion. Now that `eligibility_gate` and `escalation_gate` are fully built and each owns its own `interrupt()`, a full conversation can involve several consecutive pauses in sequence (order ID, then return reason, then manager approval). This has been tested manually via repeated curl calls, but the endpoint itself has no special handling for this beyond simply returning whatever interrupt or result comes back from each call.
- **Manager-facing approval interface:** `escalation_gate` pauses via `interrupt()` when a return exceeds the auto-approval threshold, genuinely waiting on a human decision before proceeding. For now, that decision is simulated manually by calling `/returns/resume` directly (e.g., via curl or Postman) with the same `thread_id`, standing in for a manager's response. A real interface for this (a dashboard showing pending escalations, with its own approve/deny actions) is deferred, since it would require its own tracking mechanism for "threads awaiting human review," a way for that view to stay current (polling or a push-based mechanism like SSE/WebSockets), and likely authentication, none of which is core to demonstrating the agent architecture itself. The underlying mechanism, an agent correctly pausing and durably waiting on a human decision, already works end to end; only the human-facing interface around it is out of scope for now.
- **Migrate `psycopg2` to `psycopg3`:** `psycopg2` is now in maintenance mode (bug fixes only, no new features); the ecosystem (SQLAlchemy 2.0+, Django 4.2+, and others) has settled on `psycopg3` (published on PyPI as `psycopg`) as the recommended driver for new projects as of 2026. Not urgent, since `psycopg2` still works reliably, but worth doing so the stack reflects current practice. This migration would also be the natural point to address a related inconsistency: FastAPI's endpoints are declared `async def` and call `graph.ainvoke()`, but every database call inside the graph's nodes (`find_order`, `finalize_return`) currently uses synchronous, blocking `psycopg2` calls under the hood, which undercuts the benefit of the async endpoint declarations. `psycopg3` has native async support, which would let the database layer become genuinely async and consistent with the rest of the backend.

- **Deployment:** Process has begun. The project currently runs locally via Docker Compose and is tested through `curl` and a local `test.py` script; production deployment will use:
  - **ECS Express Mode** for the backend container. Amazon ECS's newer, simplified deployment mode (launched November 2025): given a container image and two IAM roles, it auto-provisions the Application Load Balancer, HTTPS, auto-scaling, and a working URL, while every underlying resource it creates remains fully visible and directly editable in the AWS account. This was chosen over AWS App Runner, which entered maintenance mode in April 2026 and is no longer accepting new customers; ECS Express Mode is AWS's own recommended successor, and unlike App Runner, it's built directly on ECS/Fargate, the standard, full-featured AWS container service, so it also leaves a natural path open to more advanced, manually configured ECS setups later if needed.
  - **RDS** for a managed Postgres instance, replacing the current Docker-based `db` service.
  - **ECR** as the container registry the backend image is pushed to before ECS Express Mode deploys it.
  - A frontend decision (likely a lightweight React app via Vite, to display the underlying Postgres tables and provide a chat-style interface to the agent) and its own hosting approach are still open, and will be addressed after the backend deployment is live and confirmed working.
