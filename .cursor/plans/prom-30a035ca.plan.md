<!-- 30a035ca-c091-4d99-b1e1-c81486d0a1e6 940ed43d-e7be-4c97-b0b0-12a9e1767180 -->
# Production Readiness Assessment

From the code and config you shared, **the project is close to MVP level but not yet production‑ready**. Functionally it will work for ~4 users, but there are gaps in **deployment setup, environment/config handling, security hardening, performance/robustness, and monitoring** that you should address before calling it "production".

Below is a practical checklist tailored to your stack: FastAPI backend + Next.js 16 frontend, deployed as **frontend on Vercel + backend on a separate host**.

---

## 1. Backend Deployment & Runtime

- **Choose a backend host**
- For your case, prefer **Railway, Render, Fly.io, or a small VPS** to run FastAPI.
- Run with **Uvicorn behind a process manager** (or their equivalent) instead of `uvicorn` alone.

- **App entrypoint**
- Confirm a clear startup command, e.g. `uvicorn main:app --host 0.0.0.0 --port 8000` with `--proxy-headers` when behind a proxy.
- Configure the host/port via **env vars** on the platform, not hard‑coded.

- **Python dependencies & version**
- Align `requirements.txt` and `pyproject.toml` (right now versions differ and Python 3.13 is quite new).
- Pick a **stable Python version** (e.g. 3.11 or 3.12) and lock dependencies with a requirements file or lock file that your host uses.

---

## 2. Environment Variables & Secrets

- **Use real environment variables on the host** for:
- `RAPID_API_KEY`, `THEIRSTACK_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, and any others in `settings.py`.
- Never commit `.env` with real keys; keep a `.env.example` documenting required variables.

- **CORS & Allowed origins**
- Update `settings.CORS_ORIGINS` to include your **real Vercel domain** and any staging domain.
- Avoid `[*]` CORS in production unless you have a specific reason.

---

## 3. Frontend–Backend Integration (Vercel + FastAPI)

- **Environment config**
- On Vercel, set `BACKEND_URL` (e.g. `https://api.yourdomain.com` or the host you choose).
- Ensure API routes (`/api/jsearch`, `/api/theirstack`) use that `BACKEND_URL` (they already do; just need a correct value in prod).

- **Network & routing**
- Decide if the backend will be exposed as `api.yourdomain.com` via DNS + reverse proxy, or via the hosting provider URL.
- If you use a custom domain, configure HTTPS certificates (most hosts manage this automatically).

---

## 4. Data Layer & Caching

- **Supabase cache table**
- The `JobCache` assumes a Supabase **`job_cache`** table with the documented schema.
- Before prod, actually **create that table and index** in Supabase, and test cache hits/misses in a staging environment.

- **Database URL / other storage**
- If you plan to use `DATABASE_URL` beyond caching (e.g., future user accounts, history), decide on **Postgres** (Supabase / RDS / Railway) and ensure migrations and backups.

---

## 5. Reliability, Timeouts, and Error Handling

- **External API calls (RapidAPI, TheirStack)**
- Add **timeouts** to `requests.get`/`post` calls (e.g. `timeout=10`) consistently in `job_scanner`, `JobCache`, and TheirStack utilities.
- Ensure all external calls are wrapped with proper exception handling and **don’t crash the whole request**; return a user‑friendly error instead.

- **Rate limits and retries**
- For JSearch and TheirStack, implement **basic retry with backoff** for transient errors (429, 5xx) or at least log and surface a helpful message.
- Consider minimal **per‑IP or per‑session throttling** (e.g. “no more than X searches per minute”) to avoid exhausting your RapidAPI quota.

- **Logging**
- Replace `print` statements with **structured logging** (e.g. `logging` module) including request IDs, service, and error details.
- Configure log level via env (`LOG_LEVEL`), and make sure your host collects logs.

---

## 6. Testing, Quality, and CI

- **Automated tests**
- You already have backend tests (e.g. `test_accuracy.py`, `test_job_scanner.py`).
- Add at least one **API-level test** for `/api/jobs/jsearch` and `/api/jobs/theirstack` to verify the FastAPI endpoints and caching integration.

- **Continuous Integration (CI)**
- Set up a simple CI workflow (GitHub Actions):
- Install backend deps; run tests.
- Install frontend deps; run `next lint` and optionally `next build`.
- CI should run on pull requests to your `feature/UI` or main branch.

- **Type checking & linting**
- Backend: add a lightweight linter (e.g. `ruff`) and optional type checker (`mypy`), at least for critical modules (`main.py`, `job_scanner.py`, `cache_service.py`).
- Frontend: `eslint` is configured; ensure it runs clean before deploy.

---

## 7. Security Basics

- **Secret management**
- Store API keys only in your deployment platform’s **secret store / env vars**.
- Rotate keys if they were ever committed to git.

- **Input validation & abuse protection**
- FastAPI models already validate structure; add **simple constraints** (max length for strings, basic limits for salary) to avoid absurd inputs.
- Add **rate limiting** or a minimal gateway (reverse proxy or WAF) if you anticipate public exposure.

- **HTTPS everywhere**
- Ensure the backend is only reachable via **HTTPS**, either directly (managed host) or via a reverse proxy like Nginx/Caddy.

- **Headers**
- Consider setting security headers (e.g. via proxy or middleware): `X-Frame-Options`, `X-Content-Type-Options`, basic `Content-Security-Policy`.

---

## 8. Performance & Scaling (for ~4 active users)

- **Concurrency**
- Run FastAPI with multiple workers (e.g. `uvicorn`/`gunicorn` with 2–4 workers) so a slow external API call doesn’t block others.
- Your current logic is CPU‑light and network‑heavy, so small instances are fine.

- **Caching behaviour**
- Verify cache TTL (currently 60 minutes) and adjust based on quotas vs freshness.
- Consider additional **in‑memory caching** if Supabase latency becomes a bottleneck, though for 4 users it’s likely unnecessary.

- **Pagination and result limits**
- You already cap results (~15 jobs per service). That’s good for frontend performance; just confirm this is acceptable UX.

---

## 9. Observability: Monitoring & Alerts

- **Metrics & health checks**
- You already have `/health`; configure your host’s health checks to use it.
- Add basic **request logging** (status, path, latency) and track errors.

- **Monitoring service**
- Plug in something like **Sentry** (frontend + backend) or your host’s error tracking so you can see exceptions and performance issues.
- Configure at least one low‑noise alert (e.g. error rate spike, repeated 5xx from backend).

---

## 10. Operational Practices

- **Environments**
- Have **at least two environments**: staging (for tests and key checks) and production.
- Use separate API keys / Supabase projects or at least separate schemas for staging vs prod.

- **Backups & migration plan**
- For Supabase, enable automated **database backups**.
- If you later add persistent user data, introduce migrations (Alembic, SQL migrations, or Supabase SQL migration files).

- **Runbooks**
- Keep a short internal doc: how to deploy, where logs are, what to check if users report “search is broken” (e.g. check RapidAPI quota, TheirStack status, Supabase health).

---

## 11. Frontend UX/Robustness

- **User feedback**
- You already handle loading and error states. Confirm that timeouts or backend 500s show **clear, friendly messages**.

- **Validation on the client**
- Add simple client‑side checks (e.g. salary min/max sanity, required job title) and prevent obviously bad inputs.

- **Production build and static assets**
- Ensure `next build` runs cleanly and Vercel uses the production build.
- Verify that your Tailwind (or other styling) setup produces consistent UI in dark/light modes.

---

## 12. Minimal “Production‑Ready” Checklist for This Project

For your first real deployment with a few concurrent users, I’d define “production‑ready” for this app as:

- **Backend**
- Deployed on a managed host with HTTPS, multiple workers, and `/health` wired to the platform’s health checks.
- All secrets set as env vars; Supabase cache table created and working; external API calls have timeouts and basic error handling.
- Basic logging + at least one monitoring tool (or host logs) you know how to use.

- **Frontend**
- Deployed on Vercel with `BACKEND_URL` pointing to the backend, CORS configured correctly, and `next build` passing.

- **Process**
- A simple CI pipeline running backend tests + frontend lint/build on each push.
- A short internal doc describing deployment steps, env vars, and how to debug common failures.

If you’d like, next step I can translate this into **concrete changes in the repo** (env examples, minor code tweaks for timeouts/logging, sample GitHub Actions workflow, and deployment instructions for one specific platform like Railway for the backend and Vercel for the frontend).

### To-dos

- [ ] Align Python version and dependencies (requirements vs pyproject) and define a stable backend runtime for deployment.
- [ ] Introduce a documented env var setup (.env.example) and configure secrets for RapidAPI, TheirStack, and Supabase across backend and Vercel.
- [ ] Create and verify the Supabase job_cache table and ensure JobCache works end-to-end in staging.
- [ ] Add timeouts, better error handling, and logging around external API calls and cache calls in FastAPI backend.
- [ ] Set up a simple CI pipeline to run backend tests and frontend lint/build on pushes and pull requests.
- [ ] Document and/or script the exact deployment steps for backend (e.g. Railway) and frontend (Vercel), including health checks, domains, and CORS.