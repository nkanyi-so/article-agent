# article-agent

An AI agent that produces **grounded articles** from two entry points:

1. **Transcript** — paste in a meeting/interview transcript.
2. **Form** — provide a person or company's details; the pipeline enriches them
   with real data (Apollo, Exa, Pinecone) before writing.

Both paths feed **one shared pipeline** that outputs a grounded article (no
hallucination — every claim is sourced). The pipeline includes an **eval layer**
and a **stage-by-stage trace** so you can inspect exactly what happened at each
step.

## Architecture intent

```
[transcript]   [form input]
      \               /
       ▼             ▼
     normalise & validate
            │
     enrich (Apollo · Exa · Pinecone)
            │
     draft article (Claude)
            │
     ground & fact-check
            │
     eval layer (scored output)
            │
        [article]  +  [trace]
```

## Stack

| Layer     | Tech                                      |
|-----------|-------------------------------------------|
| Backend   | Python 3.12, FastAPI, Pydantic, Uvicorn   |
| Frontend  | Next.js 16, TypeScript (strict), Tailwind, App Router |
| AI        | Claude (Anthropic API)                    |
| Retrieval | Pinecone (vector store), Voyage (embeddings) |
| Enrichment| Apollo (people/company data), Exa (web)   |
| Deploy    | Railway (backend) · Vercel (frontend)     |

## Conventions

- **Commits:** Conventional Commits (`type(scope): summary`). Feature branches;
  squash-merge to `main`.
- **Python:** type hints throughout; `async` handlers by default; Pydantic for all
  request/response models.
- **TypeScript:** strict mode assumed; explicit types on all public API surfaces.
- **Tests:** run them if they exist; flag their absence if they don't.
- **Schema changes:** when a backend response shape changes, update the matching
  TypeScript types manually (not generated).
- **Env vars:** never commit `.env`; always keep `.env.example` up to date.
