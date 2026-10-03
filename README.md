# E-Commerce Return Negotiator Agent

A stateful AI agent built with LangGraph and FastAPI that walks a customer through an e-commerce return request, applying business rules (return window, VIP status, dollar thresholds) and pausing for human approval when needed. Backend has been proven live on AWS once (ECS Fargate + RDS Postgres + ECR); currently torn down to zero compute cost while frontend work continues locally. A React + TypeScript + Vite frontend now exists, fully functional locally, not yet deployed.

## Status

**Backend: functionally complete, proven on AWS once, not currently deployed.**
**Frontend: functionally complete locally (table viewer + two-panel chat + auto-refresh), not yet deployed, not yet styled.**

All five graph nodes and both routing functions have real logic, tested locally and previously verified live on AWS:

- `order_finder`: asks for and validates an order ID, with a state-driven retry loop (up to 3 attempts).
- `eligibility_gate`: checks the return window (order date + 30/60 days depending on VIP status) and either auto-denies or asks for a return reason.
- `escalation_gate`: checks the return total against a flat $150 threshold and either auto-approves or pauses for human (manager) approval.
- `finalize_return`: writes the final outcome to the `returns` table in Postgres (commits correctly — see Bugs Found and Fixed).
- `abandon_session`: a terminal node for when a customer fails to provide a valid order ID after 3 attempts.
- `route_order_finder` (found / retry / exhausted) and `route_eligibility_gate` (eligible / ineligible) handle all conditional branching.

## Tech Stack

- **Database:** Postgres. Locally via Docker Compose; previously RDS in AWS (torn down — see Deployment Progress). Four business tables (`users`, `orders`, `order_items`, `returns`) plus three LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`).
- **Backend:** FastAPI, containerized. `psycopg2` for business-logic queries, `psycopg` v3 (via `psycopg[binary]`) for the LangGraph checkpointer specifically — both coexist without conflict.
- **Agent framework:** LangGraph `StateGraph`, checkpointed via `AsyncPostgresSaver` (migrated off `InMemorySaver` — durability verified via a live ECS task-restart test mid-conversation).
- **Frontend:** React + TypeScript + Vite, in `frontend/` (sibling to `backend/`, not nested inside it). Styling: Tailwind CSS v4 just set up (via `@tailwindcss/vite` plugin + a single `@import "tailwindcss"` in `index.css`) — application of utility classes to components has not yet begun. Deliberately **not** using shadcn/ui, to keep the dependency surface small for a demo project.
- **Orchestration (local):** Docker Compose, `db` + `backend` services. `db` has a healthcheck (`pg_isready`) and `backend` waits on `condition: service_healthy`, to avoid a startup race condition that previously caused a connection-refused crash after a full volume reset.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## Backend API

- `POST /returns/start` — begins a conversation, returns `{thread_id, question, additional_kwargs}`.
- `POST /returns/resume` — body `{thread_id, customer_answer}`, returns `{thread_id, result}` where `result` is the full LangGraph state (including `messages` and, if still paused, `__interrupt__`).
- `GET /orders?order_id=` — single order lookup (has a known SQL-injection issue, see Future Enhancements).
- `GET /admin/tables/` — returns all four business tables as `{table_name: [{column: value, ...}, ...]}`, for the frontend table viewer. No auth (read-only, low risk).
- `POST /admin/reset-demo` — gated by an `X-Reset-Secret` header (checked against the `RESET_SECRET` env var). Truncates `returns` + the three checkpoint tables (`RESTART IDENTITY CASCADE`), then re-seeds `returns` from a dedicated SQL file (`backend/reset/re_seed.sql` — deliberately **outside** `backend/db/`, since Postgres's Docker image auto-runs every `.sql` file found in the directory mounted to `docker-entrypoint-initdb.d`, and this file is meant to run on-demand via the endpoint, not at container startup). Does **not** touch `users`/`orders`/`order_items`.
- CORS middleware is enabled, currently allowing only `http://localhost:5173` (the local Vite dev server origin). **Will need the deployed frontend's origin added once that exists.**

## Interrupt Payload Shape (important recent change)

Every `interrupt(...)` call across the three pausing nodes (`order_finder`, `eligibility_gate`, `escalation_gate`) now passes a **dict**, not a bare string:
```python
interrupt({"question": ai_msg, "additional_kwargs": {"channel": "customer"}})  # or "manager" in escalation_gate
```
This was a deliberate fix: the frontend's chat UI needs to know which panel (customer vs. manager) a *pending* question belongs to, before that question has been formally appended to `messages` server-side (which only happens once the node resumes). Previously the interrupt's `.value` was a bare question string with no channel info, which only allowed inferring the channel one submission late. `main.py`'s `/returns/start` was updated to match — it now reads `result['__interrupt__'][0].value['question']` and `['additional_kwargs']` instead of treating `.value` as the question text directly.

## PostgresSaver Migration (completed, prior session)

Replaced `InMemorySaver` with `AsyncPostgresSaver` (`langgraph-checkpoint-postgres` package), backed by the same Postgres instance as business data. Required: `build_graph.py` now only exports the uncompiled `builder` (compiling needs a live checkpointer connection, unavailable at import time); `main.py` opens the connection and compiles the graph inside a FastAPI `lifespan` context manager, storing the result on `app.state.graph`; both route handlers take an additional `Request` parameter (named `req`, to avoid colliding with `ResumeRequest` in `/returns/resume`) to reach it. Verified via a live durability test: paused a conversation at the manager-approval interrupt, manually stopped the running ECS task, waited for the replacement task, resumed with the same `thread_id` — completed correctly.

## Frontend — Structure and Behavior

Files, all in `frontend/src/`:
- **`App.tsx`** — top-level layout (two-column flex: `#chat-panel` left, `#tables-panel` right, via `App.css`). Owns `tables` state (`Record<string, Record<string, any>[]>`) and a named, reusable `refreshTables()` function — called once on mount via `useEffect`, and passed down to `ChatPanel` as the `onReturnFinalized` prop so the tables panel can refresh itself automatically the moment a return is finalized, with no manual page reload.
- **`Table.tsx`** — generic, reusable table component. Takes `tableName: Record<string, any>[]` as a prop (rows of one table — note: the prop name is a holdover and actually holds row *data*, not a name string; worth renaming to something like `rows` during the Tailwind pass). Renders column headers dynamically from `Object.keys()` of the first row, and renders all values generically — no table-specific logic, works identically for all four tables.
- **`ChatPanel.tsx`** — owns its own state (`threadID`, `messages`, `inputValue`, `isComplete`). On mount, calls `/returns/start` and manually constructs the first message object (since that endpoint doesn't return a full `messages` array). On submit, calls `/returns/resume`; branches on whether `result.__interrupt__` is present: if so, builds one synthetic "pending question" message from the interrupt's `.value` and appends it to `result.messages`; if not, the conversation is done — sets `messages` directly from `result.messages` and flips `isComplete`, which also calls `onReturnFinalized()` (the prop from `App`) to trigger a tables refresh. Renders two independently filtered message lists (`additional_kwargs.channel === "customer"` vs `"manager"`) side by side, so the human-in-the-loop manager-approval exchange is visually distinct from the customer conversation, with one shared input/submit control beneath both.

Known rough edges, not yet addressed:
- No visual styling at all yet beyond the basic two-column flex layout — this is the immediate next step (Tailwind).
- No visual indicator of which panel (customer/manager) is currently "active"/awaiting a reply — discussed as a nice-to-have, not yet built.
- `Table`'s `tableName` prop name is misleading (see above).
- No loading state distinct from "no rows yet" — `Table Not Found!` fires both while the initial fetch is in flight and if a table is genuinely empty.

## Deployment Progress (AWS) — currently torn down

Stack used: ECS Express Mode (Fargate) + RDS + ECR, in **us-east-1**, account `356712071780`.

**Backend was successfully deployed and fully verified live** earlier (full conversation flow via curl, the `PostgresSaver` durability test, the reset/tables endpoints all confirmed working against the live URL).

**The ECS Express service (`ecommerce-return-agent-2b00`, in the `default` cluster) was deliberately deleted**, since the career fair is still months out and ECS Express Mode's auto-provisioned NAT Gateway + Application Load Balancer were billing continuously (~$10.60/month combined) regardless of whether the ECS task itself was running — a real, easy-to-miss AWS cost pattern. Deleting the Express service cascades cleanup through the NAT Gateway, ALB, target group, security group, listener, CloudWatch log group, and the cluster itself. **RDS and ECR were left untouched** (RDS may have been separately stopped — check current state; ECR still holds the last-pushed image, which **predates** the interrupt-channel restructuring and the `/admin/tables`/`/admin/reset-demo` endpoints, so it is now stale).

**To redeploy later:** re-run ECS Express Mode pointed at a freshly-rebuilt-and-pushed ECR image (the current `backend/` code, not the stale one already in ECR), re-add the new ECS task's security group to RDS's inbound rules (a new SG ID is generated each time), and re-enter `DATABASE_URL` and `RESET_SECRET` as ECS environment variables. None of this is novel work — every bug previously hit in this process (platform mismatch, health-check route, driver version, password URI-encoding, security group wiring) is already fixed in the codebase; what's left is re-executing already-proven steps.

**Known cost-driver reference, for next time:** RDS alone (`db.t4g.micro`, gp2, Single-AZ) is cheap and largely covered by account credits. ECS Fargate compute scales with task uptime. The NAT Gateway + ALB are the ones that bill continuously regardless of task state — a reason to delete the whole Express service (not just scale tasks to 0) during any extended pause.

## Bugs Found and Fixed Along the Way

- **`abandon_session.py` bad import** — imported `AIMessage` from `.state` instead of `langchain.messages`; crashed the app at import time.
- **`finalize_return.py` missing commit** — `INSERT` into `returns` was never committed (`psycopg2` defaults to `autocommit=False`); fixed with explicit `conn.commit()` and proper `finally` cleanup.
- **`seed.sql` FK mismatch** — `orders`' seed `user_id` values didn't match real users; fixed to `1, 1, 2, 3, 3`.
- **RDS password with a `%` character** — interpreted as a URI percent-encoding escape, causing a `UnicodeDecodeError`; fixed by choosing a password avoiding `% @ : / ? # [ ]`.
- **Missing root health-check route** — ECS's load balancer health-checks `/`, which had no handler, causing persistent 503s; fixed with a simple `GET /` route.
- **`psycopg[binary]` missing** — `langgraph-checkpoint-postgres` pulls in plain `psycopg` with no bundled driver implementation; fixed by adding `psycopg[binary]` explicitly.
- **Docker Compose startup race condition** — `depends_on` without a health condition let `backend` start before Postgres was ready, especially after a full `-v` volume reset; fixed with a `pg_isready` healthcheck and `condition: service_healthy`.
- **`re_seed.sql` auto-running at container init** — initially placed inside `backend/db/`, which is entirely mounted into Postgres's auto-run init-script directory; ran (and failed) before `schema.sql` had created any tables. Fixed by relocating it outside that mounted path, to `backend/reset/`.
- **Frontend: stray `<ul>` created per-row instead of once** — several early table/list renders nested a new `<ul>` inside each `.map()` iteration instead of wrapping the `.map()` output in one `<ul>`; fixed by moving the wrapping element outside the `.map()` call.
- **Frontend: `useEffect`/hooks called outside a component or nested inside other functions** — multiple early attempts (data fetching, and later the chat submit handler) tried to call `useEffect` from inside a plain function or an event handler, violating React's Rules of Hooks; fixed by inlining an `async` helper function directly inside the effect (or, for the submit handler, making the handler itself directly `async` with no `useEffect` involved at all).
- **Frontend: `fetch` body sent without `Content-Type: application/json`** — caused FastAPI to fail to parse the request as the expected Pydantic model, returning a validation-error shape that didn't match what the frontend expected, surfacing as a confusing `Cannot read properties of undefined` error.
- **Frontend: chat panel showed the previous question, one submission late** — `result.messages` from `/returns/resume` only reflects state *already committed* server-side; a newly-posed question that caused the current pause hasn't been appended yet (interrupt happens before that node's own message-construction code runs). Fixed by branching on `result.__interrupt__`: if present, manually construct one synthetic "pending" message from its `.value` and append it to `result.messages` before rendering.

## Next Steps

1. **Tailwind styling** — in progress. Plan: utility classes directly in `Table.tsx` (borders, padding, header styling, per-table titles via a new `name` prop) and `ChatPanel.tsx` (chat-bubble styling, left/right alignment, a visual distinction between customer- and manager-channel messages), plus spacing between the four stacked tables in `App.tsx`. Deliberately scoped to be quick — not chasing pixel-perfect design, animations, or a component library.
2. **Decide frontend hosting** — not yet explored at all. Options to evaluate: static hosting (S3 + CloudFront is the common AWS-native choice), a second small container/service, or something simpler. This is the one piece of the whole project with zero prior groundwork — worth not underestimating.
3. **Redeploy backend to AWS** — recreate the ECS Express service from the current (updated) code, re-wire the RDS security group, re-set environment variables. Mechanical, but untested against the post-restructuring code (interrupt channel shape, CORS, the two `/admin/*` endpoints).
4. **Update CORS** — add the deployed frontend's real origin to `main.py`'s `allow_origins` once step 2 is decided and live.
5. **Full dry-run rehearsal** — once frontend + backend + RDS are all live together, run the actual demo flow start to finish as its own dedicated session, not an afterthought squeezed in late.

## Future Enhancements (lower priority / deferred)

- **Langfuse integration** — observability and evals. Parked for time, not abandoned.
- **Itemized returns** — currently assumes a customer returns an entire order.
- **LLM-based reason classification** — `reason_category` remains unset; no LLM wired in yet.
- **Human escalation for exhausted order-ID lookups** — currently ends via `abandon_session` rather than pausing for human correction. Deliberate demo-scope simplification.
- **Manager-facing approval interface** — currently simulated via the same chat UI's manager panel, not a separate authenticated interface. A real version would need its own auth and a way to stay current (polling/SSE), deferred as non-core to demonstrating the agent architecture.
- **Migrate remaining `psycopg2` usage to `psycopg3`** — the checkpointer already uses `psycopg` v3; migrating `helper.py`/`finalize_return.py` too would make the DB layer genuinely async, consistent with the app's `async def` endpoints.
- **SQL injection in `/orders`** — builds its query with an f-string instead of parameterizing. Low urgency while access is restricted, but should be fixed before any public exposure.
- **Secrets Manager for `DATABASE_URL`/`RESET_SECRET`** — currently plaintext ECS environment variables. Fine for a single-developer account; worth migrating before broader access, or as a "how I'd do this in production" talking point.