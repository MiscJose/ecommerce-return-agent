# E-Commerce Return Negotiator Agent

A stateful AI agent built with LangGraph and FastAPI that walks a customer through an e-commerce return request, applying business rules (return window, VIP status, dollar thresholds) and pausing for human approval when needed. Backend has been proven live on AWS once (ECS Fargate + RDS Postgres + ECR); currently torn down to zero compute cost while frontend work continues locally. A React + TypeScript + Vite frontend exists, fully functional and styled locally (Tailwind), not yet deployed.

## Status

**Backend: functionally complete, proven on AWS once, not currently deployed.**
**Frontend: functionally complete and styled locally (table viewer + two-panel chat + auto-refresh), API URL moved to an environment variable, not yet deployed.**

All five graph nodes and both routing functions have real logic, tested locally and previously verified live on AWS:

- `order_finder`: asks for and validates an order ID, with a state-driven retry loop (up to 3 attempts).
- `eligibility_gate`: checks the return window (order date + 30/60 days depending on VIP status) and either auto-denies or asks for a return reason.
- `escalation_gate`: checks the return total against a flat $150 threshold and either auto-approves or pauses for human (manager) approval.
- `finalize_return`: writes the final outcome to the `returns` table in Postgres (commits correctly — see Bugs Found and Fixed).
- `abandon_session`: a terminal node for when a customer fails to provide a valid order ID after 3 attempts.
- `route_order_finder` (found / retry / exhausted) and `route_eligibility_gate` (eligible / ineligible) handle all conditional branching.

Frontend quality gates as of the last check: `npm run build` passes; `npm run lint` reports 0 errors and 3 warnings (all `no-explicit-any`, deliberately downgraded — see Frontend Tooling Notes).

## Tech Stack

- **Database:** Postgres. Locally via Docker Compose; previously RDS in AWS (torn down — see Deployment Progress). Four business tables (`users`, `orders`, `order_items`, `returns`) plus three LangGraph checkpoint tables (`checkpoints`, `checkpoint_writes`, `checkpoint_blobs`).
- **Backend:** FastAPI, containerized. `psycopg2` for business-logic queries, `psycopg` v3 (via `psycopg[binary]`) for the LangGraph checkpointer specifically — both coexist without conflict.
- **Agent framework:** LangGraph `StateGraph`, checkpointed via `AsyncPostgresSaver` (migrated off `InMemorySaver` — durability verified via a live ECS task-restart test mid-conversation).
- **Frontend:** React + TypeScript + Vite, in `frontend/` (sibling to `backend/`, not nested inside it). Styling: Tailwind CSS v4 (via the `@tailwindcss/vite` plugin and a single `@import "tailwindcss"` in `index.css`), applied as utility classes directly in the components. `App.css` has been deleted — all layout is Tailwind. Deliberately **not** using shadcn/ui, to keep the dependency surface small for a demo project. No dark mode (deliberate — the light look is the intended design).
- **Orchestration (local):** Docker Compose, `db` + `backend` services. `db` has a healthcheck (`pg_isready`) and `backend` waits on `condition: service_healthy`, to avoid a startup race condition that previously caused a connection-refused crash after a full volume reset.
- **LLM:** Not yet integrated. Planned for reason classification in `eligibility_gate`.

## Backend API

- `POST /returns/start` — begins a conversation, returns `{thread_id, question, additional_kwargs}`.
- `POST /returns/resume` — body `{thread_id, customer_answer}`, returns `{thread_id, result}` where `result` is the full LangGraph state (including `messages` and, if still paused, `__interrupt__`).
- `GET /orders?order_id=` — single order lookup (has a known SQL-injection issue, see Future Enhancements).
- `GET /admin/tables/` — returns all four business tables as `{table_name: [{column: value, ...}, ...]}`, for the frontend table viewer. No auth (read-only, low risk).
- `POST /admin/reset-demo` — gated by an `X-Reset-Secret` header (checked against the `RESET_SECRET` env var). Currently runs `TRUNCATE returns RESTART IDENTITY CASCADE` and then re-seeds `returns` from a dedicated SQL file (`backend/reset/re_seed.sql` — deliberately **outside** `backend/db/`, since Postgres's Docker image auto-runs every `.sql` file found in the directory mounted to `docker-entrypoint-initdb.d`, and this file is meant to run on-demand via the endpoint, not at container startup). Does **not** touch `users`/`orders`/`order_items`, and does **not** clear the LangGraph checkpoint tables (an earlier version of this README claimed it did; the code never did — see Future Enhancements).
- CORS middleware is enabled, currently allowing only `http://localhost:5173` (the local Vite dev server origin). **Will need the deployed frontend's origin added once that exists.**

## Resetting Data Locally

- **Why `docker compose up --build` does not re-seed:** the Postgres image only runs the scripts in `/docker-entrypoint-initdb.d` (`backend/db/schema.sql`, then `seed.sql`) when its data directory is empty, i.e. the first start on a fresh volume. `--build` only rebuilds the backend image; the existing database volume is kept, so edits to `seed.sql` do not take effect.
- **Full reset (everything, including users/orders/order_items and checkpoints):** `docker compose down -v` followed by `docker compose up --build`. If it still doesn't re-seed, check `docker volume ls` and remove the leftover volume with `docker volume rm`.
- **Returns-only reset (fast, no restart):** `curl -X POST http://localhost:8000/admin/reset-demo -H "X-Reset-Secret: <RESET_SECRET>"`.
- **Heads-up:** `re_seed.sql` currently inserts two `returns` rows, while `seed.sql` was trimmed to one. The endpoint will bring back both; edit `re_seed.sql` if they should match.
- **Nothing resets automatically.** A page refresh or a visitor leaving does not call the reset endpoint — a refresh only re-fetches the tables and starts a new chat thread. Completed demos keep adding rows to `returns` until a reset is run (see Future Enhancements).

## Interrupt Payload Shape

Every `interrupt(...)` call across the three pausing nodes (`order_finder`, `eligibility_gate`, `escalation_gate`) passes a **dict**, not a bare string:
```python
interrupt({"question": ai_msg, "additional_kwargs": {"channel": "customer"}})  # or "manager" in escalation_gate
```
This was a deliberate fix: the frontend's chat UI needs to know which panel (customer vs. manager) a *pending* question belongs to, before that question has been formally appended to `messages` server-side (which only happens once the node resumes). `main.py`'s `/returns/start` reads `result['__interrupt__'][0].value['question']` and `['additional_kwargs']` accordingly.

## PostgresSaver Migration (completed, prior session)

Replaced `InMemorySaver` with `AsyncPostgresSaver` (`langgraph-checkpoint-postgres` package), backed by the same Postgres instance as business data. Required: `build_graph.py` now only exports the uncompiled `builder` (compiling needs a live checkpointer connection, unavailable at import time); `main.py` opens the connection and compiles the graph inside a FastAPI `lifespan` context manager, storing the result on `app.state.graph`; both route handlers take an additional `Request` parameter (named `req`, to avoid colliding with `ResumeRequest` in `/returns/resume`) to reach it. Verified via a live durability test: paused a conversation at the manager-approval interrupt, manually stopped the running ECS task, waited for the replacement task, resumed with the same `thread_id` — completed correctly.

## Frontend — Structure and Behavior

Files, all in `frontend/src/`:

- **`App.tsx`** — top-level layout: a light page (`bg-white min-h-screen`) with a centered title and a two-column flex row (`flex gap-2`): chat panel on the left, tables panel on the right (both `flex-1`, so an even 50/50 split; the tables panel also has `overflow-x-auto`). Owns the `tables` state (`Record<string, Record<string, any>[]>`). Data fetching is split deliberately: a plain module-level `fetchData()` function does the `fetch` + `.json()` and **returns** the result without touching state; a `useEffect` with an empty dependency array calls `fetchData().then(...)` and sets state inside the `.then` callback (this is what satisfies the `react-hooks/set-state-in-effect` lint rule); and a separate `refreshTables()` calls `fetchData()` and sets state, and is passed down to `ChatPanel` as the `onReturnFinalized` prop so the tables refresh the moment a return is finalized. The effect runs once on mount; `refreshTables` is only ever called by `ChatPanel` — the two are independent paths sharing `fetchData`.
- **`Table.tsx`** — generic, reusable table component. Props: `name` (a heading, rendered as an `<h2>`) and `rows` (the row data for one table — renamed from the old misleading `tableName`). Renders column headers dynamically from `Object.keys()` of the first row and renders all values generically, converting each with `String(value)` (React renders nothing for `true`/`false`/`null`, so without this the `vip_status` column showed blank; note that `String(null)` shows the literal text `"null"`). Styled with `border-separate` (deliberately kept after comparing with `border-collapse`), a dark slate header row, and padding. Spacing between tables is controlled by the parent (`my-2` wrapper divs in `App.tsx`), not baked into the component.
- **`ChatPanel.tsx`** — owns its own state (`threadID`, `messages`, `inputValue`, `isComplete`). On mount, calls `/returns/start` and manually constructs the first message object (since that endpoint doesn't return a full `messages` array). On submit, calls `/returns/resume`; branches on whether `result.__interrupt__` is present: if so, builds one synthetic "pending question" message from the interrupt's `.value` and appends it to `result.messages`; if not, the conversation is done — sets `messages` directly from `result.messages` and flips `isComplete`, which also calls `onReturnFinalized()` to trigger a tables refresh. The root element is a wrapper `div` with `max-w-3/5 mx-auto`, which centers the chat inside its half of the page without changing the even split. Two independently filtered message lists (`additional_kwargs.channel === "customer"` vs `"manager"`) are rendered as stacked, titled panels ("Manager Chat" and "Customer Chat"), each a `ul` with a fixed height (`h-50` for manager, `h-70` for customer) and `overflow-y-auto`, so the panels keep a constant size from the start and scroll internally if a conversation runs long. Each message is a single `li` whose alignment and color come from one conditional class on `message.type`: AI bubbles are left-aligned orange in both panels; human bubbles are right-aligned blue (customer) or green (manager); bubbles are capped at `max-w-4/6`. One shared input/submit control sits beneath both panels; once the conversation is complete it is replaced by a "Thank you for using this demo!" message. The `ul`/`li` list markup was kept deliberately (a transcript is semantically a list).
  - An earlier `active_channel` variable (meant to highlight whichever panel was awaiting a reply) was removed: both panels are always visible and the pending question always appears as the newest bubble, so it was redundant — and being unused, it would have failed `tsc` (`noUnusedLocals`) in `npm run build`.

### Frontend Configuration (API URL)

- The backend base URL is no longer hardcoded. It lives in `frontend/.env` as `VITE_API_URL=http://localhost:8000` (no spaces around `=`, **no trailing slash**, since code appends paths like `/returns/start`) and is read with `import.meta.env.VITE_API_URL`. `App.tsx` and `ChatPanel.tsx` each read it into a local `base_url` constant (deliberately left per-file rather than shared).
- Vite only exposes `VITE_`-prefixed variables to the browser, and **everything exposed is public in the built JavaScript** — never put secrets (like `RESET_SECRET`) in a `VITE_` variable.
- The value is **baked in at build time**. A deployed build gets whatever the variable was when `npm run build` ran; changing it requires a rebuild.
- **`.env.production` has intentionally not been created yet**, because it needs the real deployed backend URL, which doesn't exist until the backend is redeployed. If it's missing at build time, the local `localhost:8000` value from `.env` gets baked into the build — it works locally and fails for every visitor. Verification step when the time comes: build, then search `dist/` for `localhost` and confirm zero matches. Decide deliberately whether to commit `.env.production` (a backend URL is public once built, so committing is fine; the root `.gitignore` covers `.env` and `.env.local` but not `.env.production`).

### Frontend Tooling Notes

- `npm run build` runs `tsc -b` and the Vite bundle but **does not run ESLint**; run `npm run lint` separately. Vite's dev server doesn't type-check either, so build errors (like unused variables) won't show up in `npm run dev`.
- ESLint config (`frontend/eslint.config.js`) has `@typescript-eslint/no-explicit-any` (and `react-hooks/set-state-in-effect`) downgraded from errors to warnings to reduce complexity on a first project. The `prefer-const` errors were fixed in code. The remaining 3 `no-explicit-any` warnings (`App.tsx`, `ChatPanel.tsx`, `Table.tsx`) are tracked under Future Enhancements.
- In development only, `<StrictMode>` (in `main.tsx`) runs each effect twice on mount, so locally `/returns/start` is called twice (creating an orphaned extra LangGraph thread/checkpoint per page load) and `/admin/tables/` is fetched twice. This does not happen in a production build.

## Deployment Progress (AWS) — currently torn down

Stack used: ECS Express Mode (Fargate) + RDS + ECR, in **us-east-1**, account `356712071780`.

**Backend was successfully deployed and fully verified live** earlier (full conversation flow via curl, the `PostgresSaver` durability test, the reset/tables endpoints all confirmed working against the live URL).

**The ECS Express service (`ecommerce-return-agent-2b00`, in the `default` cluster) was deliberately deleted**, since the career fair is still months out and ECS Express Mode's auto-provisioned NAT Gateway + Application Load Balancer were billing continuously (~$10.60/month combined) regardless of whether the ECS task itself was running — a real, easy-to-miss AWS cost pattern. Deleting the Express service cascades cleanup through the NAT Gateway, ALB, target group, security group, listener, CloudWatch log group, and the cluster itself. **RDS and ECR were left untouched** (RDS may have been separately stopped — check current state; ECR still holds the last-pushed image, which **predates** the interrupt-channel restructuring and the `/admin/tables`/`/admin/reset-demo` endpoints, so it is now stale).

**To redeploy later:** re-run ECS Express Mode pointed at a freshly-rebuilt-and-pushed ECR image (the current `backend/` code, not the stale one already in ECR), re-add the new ECS task's security group to RDS's inbound rules (a new SG ID is generated each time), and re-enter `DATABASE_URL` and `RESET_SECRET` as ECS environment variables. None of this is novel work — every bug previously hit in this process (platform mismatch, health-check route, driver version, password URI-encoding, security group wiring) is already fixed in the codebase; what's left is re-executing already-proven steps.

**Known cost-driver reference, for next time:** RDS alone (`db.t4g.micro`, gp2, Single-AZ) is cheap and largely covered by account credits. ECS Fargate compute scales with task uptime. The NAT Gateway + ALB are the ones that bill continuously regardless of task state — a reason to delete the whole Express service (not just scale tasks to 0) during any extended pause.

**Frontend hosting constraint to remember:** a frontend served over HTTPS cannot call a plain-HTTP backend (browsers block this as "mixed content"), so the backend endpoint must be HTTPS. ECS Express Mode provides an HTTPS endpoint, which is a point in its favor.

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
- **Frontend: boolean values rendered as blank table cells** — React doesn't render `true`/`false`/`null` in JSX, so `users.vip_status` showed empty; fixed by wrapping the cell value in `String(...)`.
- **Frontend: fetch call placed in the component body instead of an effect** — during the data-fetching refactor, `fetchData().then(setTables)` ended up directly in the component body, so every render re-fetched, and every response (via `setTables`) triggered another render: an infinite request loop. Fixed by moving the call into the `useEffect` with an empty dependency array. (Rendering should be a pure calculation; network requests are side effects and belong in effects.)
- **Frontend: unused variable would fail the production build** — the leftover `active_channel`/`latest_message` variables were never read, tripping `noUnusedLocals` in `tsc -b` (invisible in the dev server). Removed.

## Next Steps

1. **Decide frontend hosting** — the one piece with zero prior groundwork, so treat it as research before touching AWS. Options to compare: S3 + CloudFront (AWS-native standard for static sites; S3 and CloudFront bill separately — confirm line items before creating anything), AWS Amplify Hosting (more managed, deploys from GitHub), or a non-AWS static host (Vercel/Netlify/Cloudflare Pages: often free and fastest, but splits the stack across providers, which matters for the "full-stack cloud deployment" story). Flag costs of any new AWS resource before creating it.
2. **Redeploy backend to AWS** — rebuild and push a fresh ECR image from the current `backend/` code, recreate the ECS Express service, re-wire the RDS security group, re-set `DATABASE_URL` and `RESET_SECRET`. Untested against the post-restructuring code (interrupt channel shape, CORS, the two `/admin/*` endpoints). Consider making any small backend changes (e.g. the deferred message enhancements below) first, to avoid a second build/push cycle.
3. **Create `frontend/.env.production`** with the real backend URL, run `npm run build`, and confirm `dist/` contains no `localhost`.
4. **Update CORS** — add the deployed frontend's real origin to `main.py`'s `allow_origins`.
5. **Full dry-run rehearsal** — once frontend + backend + RDS are all live together, run the actual demo flow start to finish as its own dedicated session, not an afterthought squeezed in late. Use it to decide how data gets reset between visitors.

## Future Enhancements (lower priority / deferred)

### Newly added

- **Data reset between visitors** — nothing resets the demo automatically; every completed demo adds a `returns` row, so the table (and the right-hand panel's height) grows until someone runs the reset. Options to evaluate: keep running the reset `curl` manually; a reset button in the UI (note anything in the frontend bundle is public, so the `RESET_SECRET` can't live in the frontend — a narrowly scoped separate endpoint, or consciously accepting that a demo-database reset is low-risk, would be the trade-off to be able to explain); a "Start a new return" button that resets only the chat state (smoother consecutive visitors, but doesn't address table growth); capping the Returns table to the most recent N rows; or giving the tables panel its own max height with internal scroll. Also make `reset-demo` match its documentation (clear the LangGraph checkpoint tables too, or update the docs — currently it only truncates `returns`) and reconcile `re_seed.sql` (two rows) with `seed.sql` (one row).
- **Prevent repeat returns for the same order** — nothing currently stops a customer from submitting return after return for the same `order_id`; each completed run inserts another `returns` row. Possible fixes: check for an existing `returns` row for the order in `order_finder`/`eligibility_gate` and end the conversation with a clear message, and/or add a database-level uniqueness constraint on `returns.order_id`. Open design question: whether a *denied* return should allow a retry while an *accepted* one never can.

### Message and UX polish

- **Return-outcome messages** — after the final step, show the customer "Your return request has been processed" plus whether it was approved or denied (the outcome is already in state: `status`, and `auto_deny_reason` for window-expired denials; decide the wording for an auto-deny versus a manager denial). On the manager side, show a confirmation such as "Thank you, the change has now been processed," only when the return actually went through manager approval (total >= $150) — decide whether `escalation_gate` emits it right after the interrupt resumes (keeps each node responsible for its own channel) or `finalize_return` emits it conditionally. This touches the backend, so it is best done before the next ECR build/push.
- **Messages with no channel are never displayed** — `finalize_return` ("Have a good day!") and `abandon_session` ("end of retry attempts") create `AIMessage`s with no `additional_kwargs`, so they match neither frontend filter and never render. This includes the retries-exhausted message. Fix by giving them a channel.
- **Literal `null` in table cells** — `String(null)` renders the text "null"; this will first appear in `returns.return_reason` after a window-expired auto-deny. Decide what an empty cell should show (blank or a dash).
- **Empty-state and loading states** — the manager chat list is an empty dark box for any return under $150 (add a muted "No manager activity yet" placeholder); tables show "Table Not Found!" both while the initial fetch is in flight and when a table is genuinely empty (track a "not loaded yet" state).
- **Extract a shared `MessageList` component** — the customer and manager lists are near-duplicates differing only by title and human-bubble color; pass full Tailwind class strings (not fragments like `bg-${color}-400`, which Tailwind's source scanning won't detect).
- **Auto-scroll chat to the latest message** — with `useRef` plus an effect on `messages`, once a conversation overflows the fixed-height list. Likely unnecessary for short demo conversations.
- **Accessibility** — `role="log"` / `aria-live="polite"` on the chat lists.
- **Style cleanup** — the manager `li` class template literal still has a stray leading space and trailing whitespace (harmless).

### Code quality

- **Type the frontend** — define shared `Message` (`content`, `type: "ai" | "human"`, `additional_kwargs: { channel: "customer" | "manager" }`) and `Row` (`Record<string, unknown>`) types in a `types.ts` (imported with `import type` because `verbatimModuleSyntax` is on) and replace the three `any`s; then restore `no-explicit-any` to an error. The untyped `response.json()` results will surface follow-on errors to resolve.
- **Frontend error handling** — `fetchData` and the chat `fetch` calls have no `.catch`/`try`; a backend outage leaves the UI silently empty. `fetchData` is the single place to add it for the tables.
- **Fail loudly on a missing env variable** — throw if `VITE_API_URL` is undefined, so a bad build doesn't produce `undefined/returns/start` requests.
- **`finalize_return` error path** — returns `None` on a `psycopg2.Error`, but LangGraph expects a state-update dict (or `{}`), so a DB failure surfaces as a confusing graph error instead of a clean message.
- **SQL injection in `/orders`** — builds its query with an f-string instead of parameterizing. Low urgency while access is restricted, but should be fixed before any public exposure.

### Previously deferred

- **Langfuse integration** — observability and evals. Parked for time, not abandoned.
- **Itemized returns** — currently assumes a customer returns an entire order.
- **LLM-based reason classification** — `reason_category` remains unset; no LLM wired in yet.
- **Human escalation for exhausted order-ID lookups** — currently ends via `abandon_session` rather than pausing for human correction. Deliberate demo-scope simplification.
- **Manager-facing approval interface** — currently simulated via the same chat UI's manager panel, not a separate authenticated interface. A real version would need its own auth and a way to stay current (polling/SSE), deferred as non-core to demonstrating the agent architecture.
- **Migrate remaining `psycopg2` usage to `psycopg3`** — the checkpointer already uses `psycopg` v3; migrating `helper.py`/`finalize_return.py` too would make the DB layer genuinely async, consistent with the app's `async def` endpoints.
- **Secrets Manager for `DATABASE_URL`/`RESET_SECRET`** — currently plaintext ECS environment variables. Fine for a single-developer account; worth migrating before broader access, or as a "how I'd do this in production" talking point.