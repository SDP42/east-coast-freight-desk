# East Coast Freight Desk

**AI/ML freight forecasting and dry-bulk chartering decision support for SAIL's coking-coal imports to India's East Coast ports.**
Smart India Hackathon 2026 · MVP

[Tech stack](TECHSTACK.md) · [Features](FEATURES.md) · [Build log](SECTIONS.md) · [Models](MODELS.md) · [Run locally](GETTING_STARTED.md) · [Deploy](DEPLOYMENT.md) · [Licences](LICENCES.md) · [Demo script](DEMO_SCRIPT.md) · [Demo guide with ready inputs](DEMO_GUIDE.md)

---

## 1. The problem

SAIL imports about 87% of its clean coking coal (16.92 of 19.37 MT in FY24; SAIL annual report). It arrives on dry-bulk
vessels at Paradip, Visakhapatnam, Gangavaram, Dhamra, Gopalpur, Sagar/Sandheads and Haldia, mostly on long-term
agreements (94% of imported coal in FY17 to FY23, CAG audit) and single-voyage spot fixtures. Three things make each
fixture hard:

1. **The freight market swings hard.** Dry-bulk freight is volatile: since 2010 the USDA ocean rate has changed by between -46% and +104% over twelve months, from $22.6 a tonne (Feb 2016) to $87.4 (Oct 2021).
2. **Ports are physically different.** Draft limits range from 9.5 m to 18 m, Haldia is an impounded dock behind a
   330 m by 39 m lock, and large ships are lightened at Sagar before they can enter. Coal vessels reach Haldia with about 35,000 t (an assumed planning ceiling) even when the ship could carry far more, because larger ships are lightened at Sagar.
3. **Delay is expensive and unevenly distributed.** Average turnaround was 69 h at Visakhapatnam and 45 h at Paradip in
   FY25; the CAG found 374 demurrage cases in four years.

Existing tools forecast a freight index or map ships. None of the ones we reviewed connects the forecast to what each
port can physically take, or to the spot-versus-contract decision the buyer actually has to make.

### What we found about SAIL's sourcing (with sources)

- Blast furnaces make about 70% of India's steel and need roughly 750 kg of coking coal per tonne of crude steel; India imports around 70 Mt a year, more than half from Australia, and mills are widening the blend with the US, Russia and Mozambique (S&P Global and industry reports, 2025).
- Mozambique is the newest lane: SAIL's own news item records the first Benga premium hard coking coal cargo arriving at Vizag (ICVL, 65% owned, with Tata Steel 35%); Mozambique is expected to become India's second-largest coking-coal supplier.
- Paradip berthed its first Capesize in September 2026 (152,702 t of coking coal from Hay Point at a 16.5 m draft, berth WD-1) and plans dredging to 18.5 m, so a ship that "cannot fit" may still call part-laden. The desk models this.
- Two other student projects for the same problem statement exist publicly; ours differs in port-physics feasibility, live ship availability, role-based access and a single verdict.

## 2. What we built

A working platform, not a slide: sign in, ask a question, get a number, and see where it came from.

| Area | What it does | Where |
|---|---|---|
| **Forecast** | ARIMA, XGBoost and a blended model on the public-domain USDA ocean rate (monthly), with 95% bands, per-split backtests, SHAP drivers and honest significance tests; a GRU neural network compared honestly. | Forecast, Model Lab, Model Monitor |
| **Recommend** | Ranks the five origins (Australia, US, Mozambique, Russia, Indonesia) by cost, transit time and route risk together, marks Pareto-optimal options, and refuses a vessel that will not fit the berth. | Chartering Recommendation |
| **Port fit** | Draft, LOA, beam and tidal-window checks for all seven ports, checked against real Haldia coal calls. | Port Compatibility, Port Map |
| **Signals** | Cyclone-adjusted arrival risk (35 years of NOAA storm tracks), laycan timing coach, coal demand estimate. | Port Signals |
| **Voyage economics** | CO₂ and IMO CII rating per voyage, INR/USD hedge overlay, rail-sea-rail landed cost, demurrage and idle time. | Voyage Economics |
| **Decide** | COA-versus-spot simulator, ROI calculator, scenario sandbox (freight spike, port closure, Red Sea). | Financial Tools, Scenario Sandbox |
| **Ask the Desk** | A chatbot and voice assistant that answers in plain English from the platform's own engines, and only with data the signed-in role may see. | Ask the Desk |
| **Govern** | Role-based access control enforced in the API and the database queries, per-port scoping, an audit log of every request and refusal, hash-chained fixture ledger, alerts, drift monitor. | Access & Audit, Fixture Ledger, Alerts |
| **See** | Four vanilla three.js scenes: the Haldia dock on the landing page, a trade globe of sea lanes and chokepoints, a 3D Monte-Carlo forecast fan, and a market terrain. A layout that scales from phones to 4K projectors. | Landing, Trade Globe, Risk Lab, Market Terrain |
| **Decide fast** | What-If Studio (eight levers, crisis playbooks, tornado, break-even, saved comparisons) and the Urgent Fixture Desk (what can arrive by the deadline, how likely, at what cost, and the walk-away price). Also askable in plain English. | What-If Studio, Urgent Fixture Desk, Ask the Desk |
| **Optimise and plan** | A sourcing optimiser (linear program with shadow prices: cheapest origin, port and plant mix), and a track record for the verdict's rules. | Sourcing Optimiser, Weather Window, The Verdict |
| **The verdict** | One plain call: when to rent a ship and which one (rent now, within a week, wait, split, or cannot meet the date), with the reasons and what would change it. Rule-based decision support, not a trained model. | The Verdict, Ask the Desk |
| **Ship availability and claims** | Open Tonnage (import the position lists your brokers send; the desk matches ships to a cargo by size, berth fit, laycan and ETA), part-laden berth fit, laytime and demurrage claim calculator, Market Pulse of current public data, and Data Health for the administrator. | Open Tonnage, Laytime, Market Pulse, Data Health |
| **Quantify risk** | Cost-at-risk Monte Carlo for a cargo (P50/P95 in INR crore), Haldia lightering planner (assumption-based), laycan timing coach, unusual-moves feed, a Live Desk of minute-by-minute simulated ticks. | Risk Lab, Port Signals, Markets, Live Desk |

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

## 6. Data: public domain only, fetched free

The rule is **no licensed data**: every series is a US-government or Federal Reserve work or NOAA/Natural Earth data, downloaded free with no account, key or credit ([LICENCES.md](LICENCES.md) lists every source).

**Real:** the USDA Agricultural Marketing Service monthly grain ocean freight rates (US Gulf and Pacific Northwest to Japan, 1996 to Aug 2026; a dry-bulk proxy, not a coal rate); US BLS producer price indices for deep-sea freight and coal; US EIA Brent crude; Federal Reserve exchange rates and dollar index; NOAA IBTrACS cyclone tracks (35 years); Ministry of Ports turnaround figures; SAIL annual-report and CAG-audit figures.

**Supplied by you:** ship availability. No free, licence-clean source of named ships exists, so the desk imports the open-tonnage lists your brokers already send (CSV or Excel) and matches them to a cargo.

**Simulated, and labelled as such:** vessel positions and queues on the port map, minute ticks on the Live Desk, cost figures (illustrative, not quotes), the sample tonnage list (invented ships) and the six sample ledger entries.

**Removed for licence reasons (Sept 2026):** the Baltic freight indices (a proprietary index), IMF PortWatch port and chokepoint traffic, SMP Kolkata Haldia reports, World Bank coal, IMF iron ore, Open-Meteo weather, the Newcastle ship feed and the S&P 500. The Baltic Dry Index was removed earlier for the same reason.

**Not available free:** a live freight index, real fixture or charter rates, AIS ship positions, and Indonesia or Russia price series.

## 7. Model results (honest)

All models are trained on the public-domain USDA ocean rate with US BLS, EIA and Federal Reserve inputs, tested expanding-window walk-forward (about 200 monthly forecasts, 2010 to 2026). Detail in [MODELS.md](MODELS.md).

| Model (1-month forecast) | MAE (US$/t) | p vs no-change |
|---|---|---|
| No change (naive) | 2.58 | |
| ARIMA(1,1,1) | 2.45 | 0.089 |
| ETS (damped trend) | 2.61 | 0.902 |
| Ridge on lags, coal, oil, rupee | **2.33** | 0.016 |
| ExtraTrees | 2.45 | 0.154 |
| XGBoost | 2.50 | 0.116 |
| ARIMA + XGBoost | 2.42 | 0.042 |
| Ridge + ARIMA | 2.34 | **0.0071** |
| GRU neural network (3 seeds) | 2.60 | 0.383 |

The rate is close to a random walk: at 3 months no model beats no-change (the damped-trend smoother is significantly worse), the neural network does not help, and with seven models compared only the Ridge + ARIMA blend is on the edge of significance after correction. The assistant's intent model scores about 87% ± 4% on held-out, hand-written questions using Hugging Face sentence embeddings (73.5% without them; an in-distribution figure, not an external benchmark).

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
