# East Coast Freight Forecasting & Vessel Chartering Platform

Smart India Hackathon 2026 — AI/ML-driven freight forecasting and dry bulk vessel
chartering recommendation system for coal procurement to India's East Coast ports
(Paradip, Visakhapatnam, Gangavaram, Dhamra, Gopalpur, Sagar/Sandheads, Haldia),
sourced from Australia, the US, Mozambique, Russia and Indonesia.

Background research, cited data and the full literature review backing the design
decisions below live in `SIH2026_Research_and_References.docx` (compiled separately).

## Project layout

```
backend/    FastAPI application (API, ML models, business logic)
frontend/   React + TypeScript + three.js dashboard
data/       raw/, processed/, seed/ datasets used to train and seed the platform
infra/      deployment/infra config
scripts/    one-off data-fetching and utility scripts
```

## Running locally

No Docker — everything runs as plain local processes, which keeps the deployment
story simple (no container runtime dependency, easier to run on a judge's machine
or a bare cloud VM).

Prerequisites: Python 3.11+ and Node 20+. The database defaults to a local SQLite
file, so nothing else is required; Postgres (Neon) is used when deployed, and
Redis is optional (without it the response cache runs in process memory).

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env   # edit DATABASE_URL / REDIS_URL for your local setup

alembic upgrade head          # create the database schema

uvicorn app.main:app --reload --port 8000
```

- API: http://localhost:8000
- Interactive API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Build plan

This project is being built in 16 sections, tracked in the approved implementation
plan. See the plan file for the full rationale, tech-stack justification, and the
20 differentiating features being implemented. **See [SECTIONS.md](SECTIONS.md)**
for a running log of what's been built in each section and where to find it.


## Where to look

- [GETTING_STARTED.md](GETTING_STARTED.md): run it locally, step by step.
- [DEPLOYMENT.md](DEPLOYMENT.md): Neon + Render + Vercel, step by step (`render.yaml`, `frontend/vercel.json`).
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md): a five-minute walkthrough with honest answers to likely questions.
- [FEATURES.md](FEATURES.md), [SECTIONS.md](SECTIONS.md), [MODELS.md](MODELS.md): what is built, how, and how well the models perform.
- Tests: `cd backend && pip install -r requirements-dev.txt && pytest -q`.
- Latency: `backend/.venv/bin/python scripts/benchmark_latency.py` against a running API.
