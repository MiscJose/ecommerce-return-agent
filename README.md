# E-Commerce Return Negotiator Agent

A deployed, stateful AI agent built with LangGraph and FastAPI that walks a customer through an e-commerce return request, applying business rules (return window, VIP status, dollar thresholds) and pausing for human approval when needed.

## Tech Stack

- **Database:** Postgres, containerized. Four tables (`users`, `orders`, `order_items`, `returns`) with real constraints, including foreign keys and a `CHECK` constraint on `return_status`.
- **Backend:** FastAPI, containerized.
- **Agent framework:** LangGraph, using a `StateGraph` with `InMemorySaver` as the checkpointer.
- **Orchestration:** Docker Compose, running the `db` and `backend` services on a shared network. The backend connects to Postgres via the service name `db`, not `localhost`.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## Future Enhancements

- **Persistent checkpointer:** Replace `InMemorySaver` with `PostgresSaver`. Since Postgres is already running in this stack, this is a natural next step. Currently, any backend restart loses all in-progress conversations, since `InMemorySaver` keeps state only in the backend process's memory.
- **Langfuse integration:** Observability and evals. Parked for time, not abandoned.
- **Frontend:** Not started. The project is currently backend-only, tested via `curl` and a local `test.py` script.
- **Itemized returns:** The agent currently assumes a customer wants to return an entire order. Asking which specific items are being returned, and computing `return_items_total` from that, is a deferred addition.
- **LLM-based reason classification:** The lenient-vs-needs-review judgment on a customer's stated return reason is not yet wired in. `reason_category` remains unset until this exists.
- **Human escalation for exhausted order-ID lookups:** When a customer fails to provide a valid order ID after three attempts, the session currently ends automatically via a dedicated terminal node (`abandon_session`), rather than pausing for a human to manually supply a corrected order ID. This was a deliberate simplification for demo scope.
- **Multi-interrupt resume handling:** The `/returns/resume` endpoint currently assumes a single resume call leads to graph completion. It does not yet handle the case where the next node in the graph also immediately pauses on its own `interrupt()` call, which will happen once `eligibility_gate` and `escalation_gate` are fully built out.
- **Manager-facing approval interface:** `escalation_gate` pauses via `interrupt()` when a return exceeds the auto-approval threshold, genuinely waiting on a human decision before proceeding. For now, that decision is simulated manually by calling `/returns/resume` directly (e.g., via curl or Postman) with the same `thread_id`, standing in for a manager's response. A real interface for this (a dashboard showing pending escalations, with its own approve/deny actions) is deferred, since it would require its own tracking mechanism for "threads awaiting human review," a way for that view to stay current (polling or a push-based mechanism like SSE/WebSockets), and likely authentication, none of which is core to demonstrating the agent architecture itself. The underlying mechanism, an agent correctly pausing and durably waiting on a human decision, already works end to end; only the human-facing interface around it is out of scope for now.

- **Deployment and frontend:** Not yet decided. The project currently runs locally via Docker Compose and is tested through `curl` and a local `test.py` script. A future decision is needed on:
  - A frontend (likely a lightweight React app via Vite) to display the underlying Postgres tables (orders, users, returns) and provide a chat-style interface to the agent.
  - Whether the frontend and backend are deployed as separate services (frontend calls the backend over the network) or the backend serves the frontend's static files directly.
  - A hosting platform. Options considered so far:
    - Railway or Render: managed platforms that deploy directly from a Dockerfile/Compose setup and provision managed Postgres with minimal configuration. Lower setup effort.
    - AWS (ECS on Fargate for the backend, RDS for Postgres, ECR for the container image, S3/CloudFront or Amplify for the frontend): the more manual, AWS-native path, requiring wiring together networking (VPC, security groups, load balancer) directly. Higher setup effort, but more directly relevant experience for AWS-centric job postings.
    - AWS App Runner: a middle ground, giving real AWS deployment experience while still handling scaling, load balancing, and HTTPS automatically, closer in spirit to Railway/Render.