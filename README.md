# article-agent

An AI agent that turns meeting transcripts and form inputs into grounded,
source-backed articles. Two entry points (transcript upload and a structured
form) feed one shared enrichment-and-drafting pipeline backed by Claude,
Apollo, Exa, and Pinecone — with a built-in eval layer and stage-by-stage
trace so every output is explainable.

<!-- architecture diagram -->

<!-- demo GIF -->

## Run locally

**Prerequisites:** Python 3.12+, Node 20+

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env          # fill in keys you have; rest can stay as placeholders
uvicorn app.main:app --reload
# → http://localhost:8000/health
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local  # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
# → http://localhost:3000
```

## Deploy

See [DEPLOY.md](./DEPLOY.md) for exact Railway (backend) and Vercel (frontend)
steps.
