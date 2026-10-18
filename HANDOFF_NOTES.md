# Handoff Notes — Context for Continuing This Project

Read this first in a new conversation, then read `README.md` (the full technical detail). This file covers what the README doesn't: my goals, how we work together, current state, and environment details that are tedious to re-derive.

Last updated: 2026-10-17.

## My goals with this project

- **Real purpose:** a resume-ready portfolio project to support applications for **AI Engineer / Forward Deployed Engineer** roles. I have a Data Science background and I'm new to software engineering topics (Docker, AWS, React/TypeScript, git/shell). I'm learning all of this by building it.
- **No longer** preparing for a career fair demo. After this project is complete I'll update my resume and start applying.
- What it needs to show: multi-turn state persistence (LangGraph + Postgres checkpointing), non-deterministic/LLM reasoning, business-rule policy exceptions, human-in-the-loop guardrails (manager approval interrupts), and **full-stack cloud deployment**. I want to be able to honestly put AWS experience on my resume.
- Inspired by Databricks Genie / Genie Code, which I use at work: I wanted to understand what an agent architecture (orchestration, branching, human pauses) takes to build, at small scale.
- **Persona I want from you:** a senior Cloud/DevOps engineer and principal AI architect giving practical, production-minded advice to someone strong in data but new to infrastructure.

## How we work together — please follow this

- **I write the code myself.** You give high-level steps: which file, which concept/pattern, what to read in the official docs. **No full code blocks** unless I explicitly ask, or I've been stuck after a couple of attempts. Small snippets to illustrate a concept are okay.
- **I share what I wrote and ask "what do you think?"** Review it like a code review: confirm what's right, explain what's wrong and *why*, point to the line/concept, don't rewrite it for me.
- **I want to understand the why.** I ask a lot of "what's the difference between X and Y" questions (hooks, Promises/await, S3 vs CloudFront distributions, etc.). Answer them in depth, with concrete traces of the actual mechanism using real example data. I sometimes re-ask to solidify a concept; that's intentional.
- **One step at a time.** I get overwhelmed by long instruction lists. Give one task (or a small numbered set), have me do it, then I report back (often with files or error output) before the next. Re-summarize the remaining steps if I ask; I have lost track before.
- **Be honest about corrections.** If you were wrong, say so plainly (e.g. earlier wrong claims about NAT gateway costs and invalidation behavior were corrected). Verify facts rather than asserting; flag when something is from memory.
- **Cost-conscious about AWS.** Flag any new AWS resource with ongoing cost *before* I create it. I set AWS Budgets alerts at $5 increments up to $20.
- **README rule:** do not put dollar amounts in the README, but it should make clear that 24/7 hosting is expensive, so the backend is only re-activated for live demos. I asked you to hold README updates until we've made more progress; update it when I ask.
- **Fresh task list + test at each step:** I typically confirm each step with `npm run build`, `npm run lint`, a `console.log`, or `curl` before moving on.

### Sharing code between conversations
I push to GitHub (`MiscJose/ecommerce-return-agent`, branch `main`) and say so; you can read the latest files from the connected repo instead of me pasting or uploading files. If you can't see my latest changes, ask me to confirm I pushed. Claude can't push for me, so any file you produce (README, notes) I commit myself.

## Current state (see README for detail)

**Backend** (LangGraph + FastAPI + Postgres): functionally complete and proven live on AWS once. Currently **torn down on purpose**. No LLM yet; `reason_category` is unset.

**Frontend** (React + TypeScript + Vite + Tailwind v4, in `frontend/`):
- Table viewer, two-panel chat (manager + customer), table auto-refresh after a return finalizes: all done and styled.
- **Deployed** to S3 + CloudFront.
- API URL comes from a runtime `public/config.json` through a shared `src/config.ts` (`getApiUrl()` returns a cached Promise; callers must `await` it).
- "Backend is asleep" banner works for table fetches (`App.tsx`) and for the chat start-up request (`ChatPanel.tsx`, via an `onBackendError` prop).

**Hosting/LLM decisions made:**
- GitHub README is the always-on "front door" (demo GIF/video, Mermaid architecture diagram, AWS screenshots, key decisions, local run steps).
- Frontend permanently on S3 + CloudFront. Backend (ECS Express + RDS + ECR) stays torn down/stopped except for one final end-to-end verification and live demos/interviews.
- LLM: a **hosted API model** (cheap model; provider TBD, Bedrock possible), behind config; Ollama optional for local dev. I chose hosted because it's what the roles expect.

## Exactly where we stopped

Task in progress: **`handleFormSubmit` error handling in `frontend/src/ChatPanel.tsx`.** The start-up request is done (verified by code review; I was about to test with `docker compose stop backend`). For the resume/submit request the agreed design is:
1. Check `response.ok` and throw if false.
2. Wrap the awaits in `try/catch` (the `try/catch` must be *inside* the async function around the `await`s; around an un-awaited call it catches nothing).
3. Add an error-message state (`string | null`), set it in `catch` ("Something went wrong, please try again").
4. Clear it at the start of each submit.
5. Render it near the input.
6. Keep `setInputValue('')` at the end of the success path so the typed text survives a failure.
7. Don't flip to the whole-page banner for this case; keep the chat visible.

Test: stop the backend mid-chat, submit, see the inline error with text preserved; start the backend, resubmit, error clears. Worth noting what happens to the conversation thread after a backend restart.

**Open item for me to confirm in review:** `npm run build` and `npm run lint` after the latest changes (App now passes `onBackendError={() => setIsBackendUp(false)}`).

## Remaining roadmap (in order)

1. Finish `handleFormSubmit` error handling (above). Remove the obsolete `VITE_API_URL` line from `frontend/.env`. Rebuild, upload `dist/` to S3, invalidate `/index.html`.
2. Backend work before the next image build (build/push once): LLM reason classification in `eligibility_gate`; Langfuse; return-outcome messages (customer: "Your return request has been processed" + approved/denied; manager: "Thank you, the change has now been processed" only when it went through manager approval); give `finalize_return` and `abandon_session` messages a `channel` (currently never displayed); return real HTTP status codes instead of `{"Error": ...}` with 200; `finalize_return` DB-error path; optionally prevent repeat returns for the same order.
3. Final AWS deploy: fresh ECR image, stable security group allowed into RDS, start RDS, recreate ECS Express service, env vars (`DATABASE_URL`, `RESET_SECRET`, LLM key), add `https://d28vlix7afqcmm.cloudfront.net` to CORS `allow_origins`, upload new `config.json`, invalidate `/config.json`.
4. Verify end to end (include a manager-approval case), capture screenshots + screen recording.
5. Tear backend down again; write the re-activation runbook.
6. Polish README as the showcase (GIF/video, Mermaid diagram, AWS screenshots, engineering decisions, remove account-specific IDs).
7. Then update my resume.

Optional/later: type `Message`/`Row` to remove the `any` warnings; shared `MessageList` component; empty/loading states; auto-scroll; accessibility; data reset between visitors; fail loudly on bad `config.json`.

## Environment / account details

- **AWS:** region `us-east-1`. Account ID is in the AWS console (omitted from the README on purpose; the previous handoff recorded `356712071780`).
- **IAM user:** `Jose`, `AdministratorAccess` (once silently failed to attach; recheck if IAM errors appear).
- **S3 bucket (frontend):** `ecommerce-return-agent-frontend-356712071780-us-east-1-an` (general purpose, private).
- **CloudFront:** distribution name `ecommerce-return-agent-frontend`, ID `E36WJU47MTPAZ`, domain `d28vlix7afqcmm.cloudfront.net`. Deployed `config.json` in S3 currently should point at the live backend URL only while the backend is up; otherwise the banner shows.
- **RDS:** `returns-agent-db`, endpoint `returns-agent-db.c4jaa48uozmn.us-east-1.rds.amazonaws.com`, `db.t4g.micro`, gp2, 20 GiB, Single-AZ, master user `postgres`. **Currently stopped; AWS auto-restarts stopped instances after 7 days, so recheck around Oct 20** (and every ~6 days while the backend is down).
- **ECR repo:** `ecommerce-return-agent`; the pushed image is **stale** (predates the interrupt-channel restructuring and `/admin/*` endpoints).
- **ECS:** Express Mode service `ecommerce-return-agent-2b00` (cluster `default`) was deleted deliberately. Recreating generates a new security group and URL; plan is a stable security group allowed into RDS.
- **Cost facts from my Cost Explorer data (Sept 2026):** the Express stack (ALB, public IPv4, Fargate) was by far the biggest driver; RDS alone was much smaller; torn-down floor is small. No NAT gateway evidence. Deleting the Express service (not scaling to 0) is what stops its billing. Keep numbers out of the README.
- **Local dev:** Docker Compose (`db` + `backend`, healthcheck + `service_healthy`), credentials in an uncommitted root `.env` (`POSTGRES_*`, `MAIN_PORT`, `RESET_SECRET`). Frontend: `cd frontend && npm run dev` (port 5173). `docker compose down -v` then `up --build` for a full re-seed; returns-only reset via `POST /admin/reset-demo` with `X-Reset-Secret`.
- **Repo layout:** `backend/` and `frontend/` are siblings. `backend/reset/re_seed.sql` must stay **outside** `backend/db/` (that folder is auto-run by Postgres at init). `notes.txt` at the root is my personal scratch commands.
- **Frontend gotchas:** `npm run build` type-checks (catches unused variables, `noUnusedLocals`) but doesn't run ESLint; `npm run lint` separately. `no-explicit-any` and `set-state-in-effect` are intentionally warnings. StrictMode double-runs effects in dev only (two `/returns/start` calls locally). Tailwind classes need real shades (`text-green-600`).

## Concepts I've learned here (so you can build on them without re-teaching)

Rules of Hooks; `useEffect` and dependency arrays; state lifting and callback props; Promises, `.then`, `async/await` (await pauses only the enclosing function), caching an in-flight Promise; `fetch` only rejects on network failure, so check `response.ok`; Vite dev vs build, `public/` copying, hashed assets; S3 vs CloudFront distributions, OAC, invalidations; CORS vs mixed content; ECS Express/RDS/ECR basics and cost drivers.

## Things I might ask in the new conversation

- "What do you think of this file?": I'll expect a short review with the why.
- "Remind me what's next": give me the next one or two steps from the roadmap above, not the entire list.
