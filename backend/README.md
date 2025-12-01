Backend for the TJH job search tool (FastAPI).

### Runtime

- **Python**: 3.11–3.12
- **App entrypoint** (example):
  - `uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers`

### Required environment variables

Configure these as environment variables on your host (Railway/Render/Fly/VPS) or in a local `.env` file (not committed to git):

- `RAPID_API_KEY` – RapidAPI key for JSearch
- `LINKEDIN_API_KEY` – Optional, if you later use the LinkedIn scraper
- `SUPABASE_URL` – Supabase project URL (used by `JobCache`)
- `SUPABASE_KEY` – Supabase key (service role or anon, depending on your setup)
- `DATABASE_URL` – Optional Postgres URL for additional data
- `MODEL_API_KEY` – Optional model provider key
- `APIFY_API_KEY` – Optional Apify key
- `CORS_ORIGINS` – Comma‑separated list of allowed origins for CORS

Example env file (do **not** commit real values). You can copy `env.example` to `.env` locally:

```bash
RAPID_API_KEY=your-rapidapi-key-here
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-key-here
CORS_ORIGINS=http://localhost:3000,https://your-frontend-domain.vercel.app
```

The `Settings` class in `settings.py` is already configured to read from a `.env` file in this directory when running locally.

### Supabase cache table

The `JobCache` service in `services/cache_service.py` uses a `job_cache` table in Supabase to store cached responses.

- SQL definition: see `db/job_cache.sql`.
- Run that script once in your Supabase project (via the SQL editor) before relying on caching in staging or production.

### Deployment (example: Railway)

1. Create a new **Railway** project and deploy from this repo, using the `backend` folder as the working directory.
2. Set the Python version to 3.11 and install dependencies from `requirements.txt`.
3. Add the environment variables listed above in Railway’s settings.
4. Use the start command (for example):  
   `uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers`
5. Configure a health check on `/health` so Railway can automatically restart unhealthy instances.

Make sure your frontend (Vercel) uses the Railway backend URL via `BACKEND_URL`, and that `CORS_ORIGINS` includes your Vercel domain.
