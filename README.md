# East Coast Freight Desk

**AI/ML freight forecasting and dry-bulk chartering decision support for SAIL's coking-coal imports to India's East Coast ports.**
Smart India Hackathon 2026 · MVP

[Tech stack](TECHSTACK.md) · [Features](FEATURES.md) · [Build log](SECTIONS.md) · [Models](MODELS.md) · [Run locally](GETTING_STARTED.md) · [Deploy](DEPLOYMENT.md) · [Demo script](DEMO_SCRIPT.md) · [Demo guide with ready inputs](DEMO_GUIDE.md)

---

## 1. The problem

SAIL imports about 87% of its clean coking coal (16.92 of 19.37 MT in FY24; SAIL annual report). It arrives on dry-bulk
vessels at Paradip, Visakhapatnam, Gangavaram, Dhamra, Gopalpur, Sagar/Sandheads and Haldia, mostly on long-term
agreements (94% of imported coal in FY17 to FY23, CAG audit) and single-voyage spot fixtures. Three things make each
fixture hard:

1. **The freight market swings hard.** In our own data the Panamax index fell 86% between December 2013 and February 2016.
2. **Ports are physically different.** Draft limits range from 9.5 m to 18 m, Haldia is an impounded dock behind a
   330 m by 39 m lock, and large ships are lightened at Sagar before they can enter. In the port trust's daily reports,
   coal vessels at Haldia carry a median 33,000 t even when the ship could carry far more.
3. **Delay is expensive and unevenly distributed.** Average turnaround was 69 h at Visakhapatnam and 45 h at Paradip in
   FY25; the CAG found 374 demurrage cases in four years.

Existing tools forecast a freight index or map ships. None of the ones we reviewed connects the forecast to what each
port can physically take, or to the spot-versus-contract decision the buyer actually has to make.

## 2. What we built

A working platform, not a slide: sign in, ask a question, get a number, and see where it came from.

| Area | What it does | Where |
|---|---|---|
| **Forecast** | ARIMA, XGBoost and a blended model on real daily freight indices, with 95% bands, per-split backtests, SHAP drivers and honest significance tests. LSTM, GRU, TCN and Transformer trained offline and compared honestly. | Forecast, Model Lab, Model Monitor |
| **Recommend** | Ranks the five origins (Australia, US, Mozambique, Russia, Indonesia) by cost, transit time and route risk together, marks Pareto-optimal options, and refuses a vessel that will not fit the berth. | Chartering Recommendation |
| **Port fit** | Draft, LOA, beam and tidal-window checks for all seven ports, checked against real Haldia coal calls. | Port Compatibility, Port Map |
| **Signals** | Cyclone-adjusted arrival risk (35 years of storm tracks), 14-day berth-slot pressure, cross-port congestion transfer, coal demand estimate. | Port Signals |
| **Voyage economics** | CO₂ and IMO CII rating per voyage, INR/USD hedge overlay, rail-sea-rail landed cost, demurrage and idle time. | Voyage Economics |
| **Decide** | COA-versus-spot simulator, ROI calculator, scenario sandbox (freight spike, port closure, Red Sea). | Financial Tools, Scenario Sandbox |
| **Ask the Desk** | A chatbot and voice assistant that answers in plain English from the platform's own engines, and only with data the signed-in role may see. | Ask the Desk |
| **Govern** | Role-based access control enforced in the API and the database queries, per-port scoping, an audit log of every request and refusal, hash-chained fixture ledger, alerts, drift monitor. | Access & Audit, Fixture Ledger, Alerts |
| **See** | Four vanilla three.js scenes: the Haldia dock on the landing page, a trade globe with chokepoint traffic, a 3D Monte-Carlo forecast fan, and a market terrain. A layout that scales from phones to 4K projectors. | Landing, Trade Globe, Risk Lab, Market Terrain |
| **Decide fast** | What-If Studio (eight levers, crisis playbooks, tornado, break-even, saved comparisons) and the Urgent Fixture Desk (what can arrive by the deadline, how likely, at what cost, and the walk-away price). Also askable in plain English. | What-If Studio, Urgent Fixture Desk, Ask the Desk |
| **Quantify risk** | Cost-at-risk Monte Carlo for a cargo (P50/P95 in INR crore), Haldia lightering planner fitted to real vessel data, laycan timing coach, unusual-moves feed, a Live Desk of minute-by-minute simulated ticks. | Risk Lab, Port Signals, Markets, Live Desk |

## 3. Who it is for, and what each role sees

Access is decided by a role that an administrator assigns. Choosing a persona when registering only changes the
greeting and shortcuts, so nobody can grant themselves access. New accounts start as **Viewer**.

| Role | Level | Sees |
|---|---|---|
| Administrator | 5 | Everything, plus users, roles, port assignments and the audit log |
| Finance & Treasury | 4 | All commercial and financial data including hedging, demand and every fixture |
| Procurement Manager | 3 | Sourcing, freight, cost, demand and every fixture; no hedging |
| Chartering Analyst | 2 | Markets, forecasts, recommendations; only their own fixtures; no cost, hedging or volume data |
| Port & Logistics Officer | 1 | Only the ports assigned to them: berth fit, congestion, cyclone and slot signals, risk into those ports |
| Viewer | 0 | Public market data |

The same rules apply to the assistant. Ask "How much coking coal does SAIL import?" as a port officer and it refuses,
says why, and logs the attempt; ask as Finance and it answers. Row-level scoping is applied in the query itself
(for example, an analyst asking "show my fixtures" gets only the rows they created).

## 4. Try it in a minute

**Demo accounts** (one click on the sign-in page, sample data only): Administrator, Finance & Treasury, Procurement
Manager, Chartering Analyst, and two Port & Logistics Officers (Haldia and Paradip). Switch between them to see the
same question answered differently. [FLOW.md](FLOW.md) has a guided walk-through.

```bash
# backend
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
cd ../scripts && python run_all.py            # loads the real datasets (needs data/raw, see DATA below)
python seed_demo_users.py                     # demo accounts and sample fixtures
cd ../backend && uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Full beginner steps are in [GETTING_STARTED.md](GETTING_STARTED.md); hosting on Neon, Render and Vercel is in
[DEPLOYMENT.md](DEPLOYMENT.md).

## 5. How it works

```
 Browser (React, three.js, Web Speech)
        │  JWT
        ▼
 FastAPI ── require(permission) ── audit log
   │  routers: forecast · recommendation · ports · risk · financial · signals · voyage · ledger · alerts · assistant · admin
   │
   ├── services   forecasting, risk, compatibility, signals, ledger, monitor, alerts, assistant
   ├── ml         ARIMA · XGBoost + SHAP · ensemble · intent model · deep-model inference (NumPy)
   ├── cache      Redis, or process memory
   ▼
 SQLAlchemy ── SQLite (local) / PostgreSQL (Neon)     freight_rates · ports · port_activity · haldia_coal_calls ·
                                                       cyclone_exposure · ledger_entries · alert_* · users · audit_log
```

One shared time-series table (`freight_rates`) holds every market series; ports, vessels, routes and disruption
events have their own tables. The assistant does not generate free text: a small intent model chooses an engine, the
engine queries the database under the caller's permissions, and the answer is assembled from the returned numbers.

## 6. Data: real, simulated, and missing

**Real:** Baltic Capesize, Panamax, Supramax and Handysize indices (daily, Aug 2012 to Jul 2019, CC BY 4.0); coal, iron
ore, FX, equity and dollar-index series; IMF PortWatch daily dry-bulk port calls and chokepoint transits; Ministry of
Ports turnaround figures; NOAA cyclone tracks; SAIL annual-report and audit figures; and 90+ coal vessels parsed from
SMP Kolkata's public daily Haldia reports (median cargo 33,000 t, draft 7.3 to 8.5 m).

**Simulated, and labelled as such in the interface:** vessel positions and anchorage queues on the map (real AIS is a
paid feed), cost figures (illustrative distance-based estimates, not quotes), and the six sample ledger entries.

**Not available:** a free daily freight index after July 2019 (the Baltic Exchange feed is paid), real fixture or
charter-rate data (none is public), and Indonesia or Russia price series. The Baltic Dry Index was removed because no
freely licensed daily source exists. Every page states where its data ends.

## 7. Model results (honest)

Measured on the Panamax index, 7-day horizon, walk-forward with 35 paired forecasts (`MODELS.md` has the detail):

| Model | MAE (index points) | MAPE |
|---|---|---|
| ARIMA(2,1,2) | 31.9 | 3.90% |
| XGBoost | 31.6 | 3.75% |
| ARIMA + XGBoost hybrid | 29.0 | 3.52% |

The hybrid is significantly better than ARIMA (Wilcoxon p = 0.0019) and not significantly better than XGBoost
(p = 0.16). Results are series-specific: on a daily Baltic Dry Index we briefly tested, the hybrid did not beat ARIMA.
**Deep learning** on the same 35 forecasts: the deep ensemble has the lowest error (MAE 25.8 vs ARIMA 31.9) but the gap is not statistically significant (p = 0.17); the hybrid is the only model significantly better than ARIMA. A test of whether weather helps predict port traffic found no significant gain (p = 0.88). Both are reported in the Model Lab page and [MODELS.md](MODELS.md). Other measured results: the assistant's intent model scores
75% ± 6% on held-out, hand-written questions (an in-distribution figure, not an external benchmark); every read
endpoint has a warm p95 under 200 ms; 24 unit tests pass.

## 8. Security and privacy

Passwords are bcrypt-hashed and must contain a letter and a number; five failed sign-ins lock an address for ten
minutes; sessions expire and the client signs out on a rejected token. Roles are checked on the server for every
route, port scoping is applied in the query, and refusals are recorded. Alert webhooks accept only public https hosts
(no internal addresses). The assistant runs locally with no external language-model service, so questions never leave
the deployment; browser voice input uses the browser vendor's own speech service (Chrome and Edge), which the
interface says. Demo sign-in is passwordless and only for accounts flagged as demo; switch it off with
`ALLOW_DEMO_LOGIN=false`. With `ENVIRONMENT=production` the API refuses to start without a real JWT secret.

## 9. Repository layout

```
backend/        FastAPI app (app/api, app/services, app/ml, app/models), Alembic migrations, tests
frontend/       React + TypeScript + three.js interface
scripts/        data ingestion, model training (train_dl.py), demo seeding, latency benchmark
data/           raw/ and processed/ are git-ignored (licences differ; see TECHSTACK.md)
render.yaml     Render Blueprint for the API
DEPLOYMENT.md   Neon + Render + Vercel steps
```

## 10. Known limitations

- Freight indices end in July 2019, so forecasts illustrate the method rather than today's market.
- Costs are illustrative; rail distances and vessel fuel burn are labelled assumptions.
- The demand estimate rests on two annual data points.
- The schema has been run on SQLite locally; the first Neon load is its first Postgres run.
- Render's free tier (512 MB, sleeps when idle) may struggle with the heaviest ensemble call.
- WhatsApp/SMS alerts need a messaging-provider account and are not configured.

## 11. Credits and licence

Built for the Smart India Hackathon 2026. Data attribution is listed in [TECHSTACK.md](TECHSTACK.md); please keep it if
you reuse the datasets. Code licence to be confirmed with the organisers before any public release.
