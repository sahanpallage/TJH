This is a [Next.js](https://nextjs.org) frontend for the TJH job search tool.

## Environment configuration

The API routes in `app/api/jsearch/route.ts` and `app/api/indeed/route.ts` forward requests to the FastAPI backend using the `BACKEND_URL` environment variable:

```ts
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";
```

For **local development**:

```bash
# .env.local (do not commit)
BACKEND_URL=http://localhost:8000
```

You can also copy `env.local.example` to `.env.local` as a starting point.

On **Vercel (production)**, set `BACKEND_URL` in the project settings to point to your deployed backend, for example:

```text
https://your-backend-on-railway.app
```

Make sure the backend CORS configuration in `backend/settings.py` (via `CORS_ORIGINS`) includes your Vercel domain (for example `https://your-frontend-domain.vercel.app`).

## Deployment (example: Vercel)

1. Push this repo to GitHub and import it into **Vercel**.
2. In Vercel project settings, add `BACKEND_URL` pointing to your deployed FastAPI backend.
3. Trigger a deploy; Vercel will run `next build` and host the app at your chosen domain.

## Getting Started (local)

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.
