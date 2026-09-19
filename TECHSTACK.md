# Tech stack: what we used, and why

Everything below runs as plain processes (no Docker) and on free tiers. "Runtime" means it ships with the deployed
app; "offline" means it is only used on a developer machine to train or prepare things.

## At a glance

| Layer | Choice | Where it runs |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS v4 | Vercel (static) |
| 3D and motion | three.js (vanilla, no wrapper), framer-motion | Browser |
| Backend API | Python 3.12, FastAPI, Uvicorn | Render (free web service) |
| Database | SQLite locally, PostgreSQL (Neon) deployed, SQLAlchemy 2 + Alembic | Neon |
| Classical ML | statsmodels (ARIMA), XGBoost, SHAP, scikit-learn, SciPy | Runtime |
| Deep learning | PyTorch (LSTM, GRU, TCN, Transformer) trained offline, served with NumPy | Offline + runtime (NumPy only) |
| Auth and access | JWT (python-jose), bcrypt, role-based access control, audit log | Runtime |
| Cache | Redis when available, in-process fallback | Runtime |
| Voice | Web Speech API (browser built-in) | Browser |

## Frontend

| Tool | Used for |
|---|---|
| React 19 + TypeScript | The whole interface, with strict typing across the API boundary (`src/lib/api.ts`). |
| Vite 8 | Dev server and production build; code-splits the three.js scenes so the first load stays light. |
| Tailwind CSS v4 | Design tokens (light palette, `strong`/`body` text colours) and a rem-based layout. The root font size scales fluidly from laptops (16 px) to QHD and 4K TVs (up to 44 px), so nothing looks tiny on a projector. |
| react-router | Public pages (landing, sign-in, register) and the guarded `/app` area; each route declares the permission it needs. |
| three.js (vanilla) | The Haldia port scene on the landing page and the other 3D views. Plain `three` with our own render loop, label projection and disposal; no React wrapper. |
| framer-motion | Page and card transitions, the split-text headline. |
| React Bits components (`components/rb/`) | ParticleText, BorderGlow, Carousel (uses the `motion` package), GlideSelect, FuseButton, LatticeLoader, Ripple; copied into the repo and restyled for the light theme. |
| Recharts | Time-series, bar and area charts (forecast bands, backtests, drift, signals). |
| Leaflet + react-leaflet | The port map (OpenStreetMap tiles). |
| lucide-react | Icons. |
| axios | API client with a JWT interceptor and automatic sign-out on an expired token. |
| Web Speech API | Voice input and spoken answers in "Ask the Desk" (browser built-in; no service to run). |
| Components in the style of reactbits.dev | Tilt card, magnet button, marquee, spotlight card, shiny text, aurora backdrop, reimplemented locally so there is no extra dependency. |

## Backend

| Tool | Used for |
|---|---|
| FastAPI + Pydantic | REST API with automatic OpenAPI docs at `/docs`, request validation, dependency-injected permissions. |
| Uvicorn | ASGI server. |
| SQLAlchemy 2 | ORM; every query, including role and port scoping, is built here so it runs in the database. |
| Alembic | Schema migrations (SQLite and Postgres safe). |
| python-jose + bcrypt | Signed JWT access tokens; bcrypt password hashing (used directly, since passlib is unmaintained). |
| httpx | Alert webhooks (https only, public hosts only) and the latency benchmark. |
| Redis client | Optional response cache; falls back to process memory. |
| asyncio background tasks | Alert evaluation every 30 minutes, scheduled retraining on drift, start-up warm-up. |

## Machine learning

| Tool | Used for |
|---|---|
| statsmodels | ARIMA with AIC order search and ADF stationarity test; Granger causality between ports; frozen-model drift monitoring. |
| XGBoost | Gradient-boosted trees on lag, rolling, calendar and exogenous features (S&P 500, dollar index, coal). |
| SHAP | TreeExplainer feature attributions shown on the forecast page. |
| scikit-learn | TF-IDF + logistic regression intent model for the assistant; cross-validation. |
| SciPy | Wilcoxon signed-rank and Mann-Whitney tests. |
| pandas / NumPy | Series handling, feature building, the NumPy inference path for the deep models. |
| PyTorch (offline) | Trains the LSTM, GRU, TCN and Transformer models in `scripts/train_dl.py`. It is not a runtime dependency: weights are exported to `.npz` and evaluated with NumPy, which keeps the free-tier deployment small. |

## Data sources and licences

| Data | Source | Licence / terms |
|---|---|---|
| Daily Baltic Capesize, Panamax, Supramax, Handysize indices, Aug 2012 to Jul 2019 | Mendeley Data, DOI 10.17632/t76ckh2ygg.1 | CC BY 4.0 |
| Coal, iron ore, crude oil monthly prices | World Bank Commodity Markets ("Pink Sheet") | CC BY 4.0 |
| S&P 500, dollar index, INR, AUD, ZAR, Brent | FRED (Federal Reserve Bank of St. Louis) | Public data; attribution to the underlying agencies |
| Daily port calls and chokepoint transits | IMF PortWatch | Free with attribution (confirm terms before a public launch) |
| Cyclone tracks | NOAA IBTrACS | Public domain |
| Port turnaround and traffic | Ministry of Ports, Shipping and Waterways publications | Government of India open data |
| Haldia vessel positions | SMP Kolkata daily "Morning Position" reports | Public port-authority publication |
| Weather and waves for the ports (used in one experiment) | Open-Meteo (ERA5 based) | CC BY 4.0, non-commercial use |
| Land outlines for the trade globe | Natural Earth 110m (dots generated from it) | Public domain |
| SAIL figures | SAIL annual reports, investor presentations; CAG audit reports | Public documents |
| Coordinates, lanes, vessel positions on the map | Hand-placed and simulated | Labelled as simulated in the interface |

The Baltic Dry Index itself is **not** used: no freely licensed daily source was found, so it was removed.

## Quality and operations

| Tool | Used for |
|---|---|
| pytest | Unit tests: password policy, lockout, intent routing, ledger tamper detection, CII maths, webhook guard, role scoping. |
| oxlint + `tsc` | Frontend linting and type checks. |
| `scripts/benchmark_latency.py` | Measures cold and warm p50/p95 for every read endpoint against a 200 ms target. |
| Render Blueprint (`render.yaml`) | One-file deployment of the API. |
| `vercel.json` | Single-page-app rewrites for the frontend. |
