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
frontend/   React + TypeScript dashboard (added in Section 12)
data/       raw/, processed/, seed/ datasets used to train and seed the platform
infra/      deployment/infra config
scripts/    one-off data-fetching and utility scripts
```

## Running locally

No Docker — everything runs as plain local processes, which keeps the deployment
story simple (no container runtime dependency, easier to run on a judge's machine
or a bare cloud VM).

Prerequisites: Python 3.11+, PostgreSQL 14+ running locally (the TimescaleDB
extension is used opportunistically for the freight-rate time-series table if
available, but the schema works on plain Postgres too), and Redis (optional —
the app degrades gracefully without it, just without caching).

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
