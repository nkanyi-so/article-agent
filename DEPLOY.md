# Deployment

Deploy the **backend first** (you need its URL to set the frontend env var and
to backfill CORS on the backend).

---

## Backend → Railway

1. Push this repo to GitHub (if not already).
2. Open [railway.app](https://railway.app) → **New Project** → **Deploy from
   GitHub repo** → select `nkanyi-so/article-agent`.
3. Railway detects `backend/railway.json`. Set the **Root Directory** to
   `backend/` in the service settings.
4. Railway reads `backend/.python-version` (3.12) and uses it automatically via
   Nixpacks.
5. Add environment variables in the Railway service dashboard:
   ```
   CORS_ORIGINS=https://<your-vercel-domain>.vercel.app
   ```
   (Use `*` temporarily if you don't have the Vercel URL yet; replace it once
   you do — never leave `*` in production.)
6. Trigger a deploy. Once live, copy the Railway **public URL**
   (e.g. `https://article-agent-production.up.railway.app`).
7. Verify: `curl https://<railway-url>/health` → `{"status":"ok",...}`

---

## Frontend → Vercel

1. Open [vercel.com](https://vercel.com) → **Add New Project** → import
   `nkanyi-so/article-agent`.
2. Set **Root Directory** to `frontend/`.
3. Add environment variables:
   ```
   NEXT_PUBLIC_API_URL=https://<your-railway-url>
   ```
4. Deploy. Once live, copy the Vercel URL.

---

## Backfill CORS

Go back to Railway → service env vars → update `CORS_ORIGINS` to the exact
Vercel URL you just copied (e.g. `https://article-agent.vercel.app`). Trigger
a redeploy.

---

## Smoke test

Load the Vercel URL in a browser — the landing page should show **Backend: ok**.
That confirms end-to-end connectivity. Phase 0 complete. ✅
