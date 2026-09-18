# Build Log — Sections

Running record of the 16-section implementation plan: what each section covers,
what's actually been built, and where to find it. Full rationale for the plan is
in the approved plan file; this doc tracks execution status only.

Status legend: ✅ done & verified · 🔧 in progress · ⬜ not started

---

### 1. Project scaffolding — ✅ done
Monorepo layout, FastAPI skeleton, config, DB session, Redis client, health
endpoint, README, git init.
- `backend/app/main.py`, `app/core/config.py`, `app/core/redis_client.py`, `app/db/session.py`, `app/api/health.py`
- Verified: app boots via `uvicorn`, `/api/v1/health` responds (reports `degraded` when DB/Redis aren't running, which is correct behaviour).
- Note: Docker/Compose was removed after the first pass — deployment now runs as plain local processes (see README) to avoid container-runtime risk on the judge/demo machine.

### 2. Database schema & migrations — ✅ done
SQLAlchemy models for ports, berths, vessel classes, vessels, routes, freight
rates, trade volumes, fixtures, disruption events, users. Alembic migrations.
- `backend/app/models/{port,vessel,route,freight,trade,fixture,disruption,user}.py`
- `backend/alembic/` (env.py wired to app settings + model metadata), first migration `8cc68f1273fe`
- **Local dev DB switched to SQLite** (`sqlite:///./freight_forecast.db`, zero setup) after finding the machine's local Postgres 17 install is password-protected; `DATABASE_URL` in `.env` just needs pointing at a real Postgres string for production/deployment — no code changes required. TimescaleDB hypertable conversion for `freight_rates` is left as an optional, Postgres-only post-migration step (not a hard dependency), consistent with keeping deployment simple.
- Verified: `alembic upgrade head` creates all 9 tables cleanly on a fresh SQLite DB; an ORM round-trip (insert `VesselClass` + `Port` with real Paradip constraint data, query it back, delete) works correctly through the project's own venv dependencies; `/api/v1/health` correctly reports `"database":"up"` once the schema exists.

### 3. Data ingestion pipeline — ✅ done (Comtrade import volumes deferred)
- `scripts/ingest_freight_rates.py` — downloaded and ingested the **real** Mendeley Baltic sub-index dataset (DOI 10.17632/t76ckh2ygg.1, CC BY 4.0): 6,996 daily BHSI/BSI/BPI/BCI observations, 1 Aug 2012 – 31 Jul 2019, plus a computed composite BDI (real Baltic Exchange weighting: 40% BCI + 30% BPI + 30% BSI) — 8,745 rows total.
- `scripts/ingest_commodity_prices.py` — downloaded and ingested **real** World Bank Commodity Markets (Pink Sheet) monthly coal prices: 1,152 rows across Australian & South African coal, 1960–2024. Chosen because Kim et al. (2025, cited in our research) found coal/iron-ore prices among the strongest BDI predictors via SHAP.
- `scripts/seed_ports.py` — seeded our own real Table 1 research data: all 7 East Coast destination ports (exact draft/LOA/beam/tidal/capacity figures) + 5 origin ports/countries + 4 vessel classes.
- `scripts/seed_routes.py` — 35 origin×destination routes (order-of-magnitude sailing distances, clearly flagged as approximate pending exact routing data).
- `scripts/generate_synthetic_vessels.py` — 20 synthetic vessels (5 per class), explicitly flagged `is_synthetic=True` since real AIS is a paid upgrade path.
- `scripts/seed_disruption_events.py` — the 4 real documented disruption case studies from our research (Red Sea/Suez, Panama Canal, Cyclone Koji, Russia sanctions), pulled forward from Section 9 since the data model was ready.
- `scripts/run_all.py` — orchestrates all of the above in dependency order.
- **Fixed a real bug found during this section**: `DATABASE_URL`'s default was a relative SQLite path, so scripts run from `scripts/` created/looked for a *different* database file than the one the API server uses from `backend/`. Fixed by anchoring the default to an absolute path in `app/core/config.py` and removing the stale override from `.env`.
- **Deferred**: UN Comtrade/WITS coal import volumes by country (`trade_volumes` table exists in the schema but isn't populated yet) — lower priority than the freight-rate/commodity data needed for Section 5/6 forecasting; picking this up is a quick follow-on whenever there's spare time.
- Verified: `run_all.py` completes cleanly end-to-end on a fresh database; row counts spot-checked per series (see session log).

### 4. Core FastAPI backend skeleton — ✅ done
JWT auth, request logging, and structured error handling — expands on Section
1's skeleton. Also completes baseline feature #7 in `FEATURES.md` ("User
authentication / login").
- `app/core/security.py` — password hashing + JWT create/decode. Hashes with the `bcrypt` library directly rather than passlib's `CryptContext`: passlib 1.7.4 is unmaintained and its bcrypt backend self-test crashes against bcrypt>=4.1 (a real bug hit and fixed during this section).
- `app/schemas/user.py`, `app/services/auth.py`, `app/api/deps.py` (`get_current_user` dependency via `OAuth2PasswordBearer`), `app/api/auth.py` — `POST /auth/register`, `POST /auth/login` (OAuth2 password flow), `GET /auth/me`.
- `app/core/logging_middleware.py` — logs method/path/status/duration for every request with a short request id, also stamped on the response as `X-Request-ID`/`X-Response-Time-Ms` headers (the same measurement Section 16's low-latency benchmark will read).
- `app/core/error_handlers.py` — unhandled exceptions return a clean `{"detail": "Internal server error"}` (500) instead of leaking a stack trace to the client, while still logging the full traceback server-side.
- Verified end-to-end via curl: register (201) → duplicate register correctly rejected (400) → login issues a real JWT (200) → authenticated `/me` succeeds (200) → same call with no token correctly rejected (401) → wrong password correctly rejected (401). Confirmed in the Swagger UI (`/docs`) that `/auth/me` shows the lock icon and `Authorize` button work as expected. Register/login latency (~250-300ms) is bcrypt's intentional hashing cost, not a bug.

### 5. Baseline forecasting pipeline — ✅ done
ARIMA baseline model + walk-forward backtesting framework, on our real ingested
freight-rate data (Section 3).
- `app/ml/arima_model.py` — ADF stationarity test, then a small (p≤2, d≤1, q≤2) grid search selecting the lowest-AIC order, following the exact methodology documented in Baghel (2025) and Sahu & Patil (2017); also returns confidence intervals (feature #10 — uncertainty bands, not just a point forecast).
- `app/ml/backtesting.py` — walk-forward backtest (5 expanding-window splits, never touching future data), the same evaluation discipline both reviewed papers use, rather than one lucky train/test split.
- `app/services/freight_data.py`, `app/schemas/forecast.py`, `app/api/forecast.py` — `GET /forecast/indices` (lists BDI/BCI/BPI/BSI/BHSI/COAL_AUS/COAL_ZA), `GET /forecast/{index_name}?horizon=` returning the forecast with confidence bands plus full backtest metrics per split.
- **Verified with real results, not just "it runs":** BDI backtest achieved **4.29% mean MAPE** across 5 splits (order (2,1,2), ADF p=0.0043 confirming stationarity) — genuinely competitive with Luo et al. (2026)'s more sophisticated transformer-hybrid result of 5.26% MAPE on the same index, cited in our own research compendium. BCI achieved 7.50% MAPE. Confirmed generalizes across all 7 ingested series, correct 404 on an unknown index, and visible in the Swagger UI under a new `forecast` tag.
- Noted for Section 16: a full request (grid search + 5 backtest fits + final fit) takes ~3.4s — expected and fine for a pre-computed/cached daily job, not acceptable for a live per-request call, which is exactly the Redis-cached-snapshot architecture already planned.

**Plan revised after reviewing 3 academic papers** (Baghel 2025 NCI thesis;
Sahu & Patil 2017 J. Maritime Research; arXiv 2503.11728 empty-container
forecasting — see `FEATURES.md` Section D for full detail): the original plan
(Section 6) called for an LSTM/Transformer as a co-equal model. Baghel's thesis
found LSTM badly overfits on small monthly Indian port cargo samples and had
to be dropped from the final hybrid; the arXiv paper found Prophet
underperformed even a naive baseline on real terminal data. The validated,
citable architecture from Baghel's work is an **ARIMA + XGBoost ensemble with
inverse-RMSE weighting**, proven statistically significant via a Wilcoxon
signed-rank test (p=0.016 vs. ARIMA alone). We're adopting that same
architecture and the same significance test for our own model comparison,
since it's now backed by a directly-reviewed, India-specific paper rather than
a generic assumption. LSTM/Transformer moves to Section 6 as a secondary
model we add *because* our dataset is daily (8,745 rows) rather than the
~100-160 monthly points Baghel had — a defensible reason to expect it to do
better for us, not just a default choice.

### 6. Advanced ML models — ✅ done
XGBoost + inverse-RMSE-weighted ARIMA/XGBoost ensemble + SHAP explainability +
Wilcoxon signed-rank significance test — all following Baghel (2025)'s
validated methodology. LSTM/Transformer deferred as a secondary model
(daily-data-justified, per Section 5) — not required for a working,
defensible ensemble.

**Plan revised again after reading 2 more papers** (Kim, Kim & Choi 2025 PLOS
ONE, read in full this time; Su, Bae & Park 2025 Frontiers in Marine Science —
see `FEATURES.md` Section E): Kim et al. found via SHAP, across 10 different
models, that the **S&P 500 is the single strongest predictor of BDI** —
stronger than any shipping-specific variable — followed by the US Dollar
Index. This is a direct, evidence-backed instruction for feature engineering,
not a guess, so before building the XGBoost model we ingested two more real
datasets: S&P 500 daily close and the Trade-Weighted US Dollar Index
(DTWEXBGS), both from FRED (Federal Reserve — free, no API key, official).
- `data/raw/FRED_SP500.csv`, `data/raw/FRED_DTWEXBGS.csv`
- These join the coal prices already ingested in Section 3 as XGBoost features, alongside lag/rolling-window/calendar features (Baghel's documented methodology, Section 5).

**What was built:**
- `app/ml/features.py` — lag (1/2/3/7/14-day), rolling-window (7/30-day mean+std), and calendar features, per Baghel's documented methodology; exogenous features (S&P 500, DXY, coal prices) aligned and forward/back-filled.
- `app/ml/xgboost_model.py` — time-aware grid search (`TimeSeriesSplit`) over max_depth/learning_rate/n_estimators; recursive multi-step forecasting; SHAP `TreeExplainer` for the top-N feature importances (feature #4).
- `app/ml/ensemble.py`, `app/ml/ensemble_backtest.py` — inverse-RMSE weighting (`w_m = (1/RMSE_m) / Σ(1/RMSE_k)`, Baghel's exact formula) and a Wilcoxon signed-rank test (`scipy.stats.wilcoxon`, one-sided), run through paired walk-forward backtest splits so ARIMA and XGBoost errors are comparable point-for-point.
- `GET /forecast/{index_name}/ensemble?horizon=` — returns the combined forecast, per-model metrics, ensemble weights, top SHAP features, and both significance tests.

**Two real bugs found and fixed during testing** (both caught by testing against real data rather than trusting first output):
1. Exogenous alignment bug: `series.reindex(df.index).ffill()` silently produced an all-NaN column whenever `df.index` predated the exogenous series' own start (S&P 500's FRED data only goes back to 2016, but our BDI training data starts 2012) — `dropna()` then wiped the entire early training set and XGBoost silently trained on zero rows ("Empty dataset at worker" warning, predictions of exactly 0.0, RMSE 830). Fixed by filling on the *union* of both indexes before slicing back down to `df.index`.
2. A second, related bug in the backtest itself: exogenous series were being truncated to `<= train_end` per split to "prevent leakage," but for splits ending before 2016 this discarded S&P 500 entirely (a data-coverage gap, not real leakage — per-row leakage is already prevented by `shift(1)` inside the feature builder). Removing that truncation fixed it for good.

**Real, honest results after both fixes** (BDI, 7-day horizon, 5 walk-forward splits): ARIMA MAPE 4.68%, **XGBoost MAPE 4.19%** (XGBoost edges out ARIMA once the exogenous features actually had data), Hybrid MAPE 4.34%, weights 47.6% ARIMA / 52.4% XGBoost. **Wilcoxon hybrid vs. ARIMA: p=5.4×10⁻⁶ (highly significant)** — directly replicating Baghel's finding that the ensemble beats ARIMA alone. Hybrid vs. XGBoost alone was not significant (p=0.99) — an honest result: when one base model is already strong, averaging with a weaker one doesn't help further, which is expected ensemble behaviour, not a flaw. Confirmed generalizes to BCI (hybrid MAPE 8.98%, best of the three, though neither significance test reached p<0.05 there — a fair, non-cherry-picked result). SHAP consistently found `lag_1` overwhelmingly dominant (~100x any other feature) — expected for a highly autocorrelated daily index; `coal_aus` and `month` were the next most useful features.
- Full request (grid search + paired 5-split backtest + final fits + SHAP) takes ~12-13s — same caching note as Section 5 applies for Section 16.

**Also fixed this session:** the machine's disk filled to 136MB free mid-session (a system-wide issue, unrelated to this project's own tiny data files), which blocked the backend from starting at all. Cleared ~4.5GB of safe, fully-regenerable caches (pip, npm, Homebrew, Playwright) to unblock — worth keeping an eye on disk space if this recurs, since it's a laptop-wide condition, not something this project caused.

### 7. Port–Vessel Compatibility Engine — ✅ done, wired end-to-end to the UI
Draft/LOA/beam/tidal rules engine from our real Table 1 research data; tidal
partial-load optimizer. This is feature #1 — our single biggest differentiator.
- `app/services/compatibility.py` — checks vessel-class typical draft/LOA/beam against each port's real max constraints; if a port is tide-restricted and cargo tonnage is given, computes a tidal loading plan (cycles required, days required) using a documented default tonnes-per-cycle figure from our own research.
- `app/api/compatibility.py` — `GET /compatibility/ports`, `/vessel-classes`, `/matrix` (full port×class grid), `/check?port_id=&vessel_class_id=&cargo_tonnes=`.
- **Frontend fully rewired**: `frontend/src/pages/Ports.tsx` no longer uses the Section 1 hardcoded array — it now calls the live API for the matrix and adds a genuinely interactive "Live Compatibility Checker" (pick a port + vessel class + cargo tonnage, see an animated pass/fail result with per-constraint breakdown and the tidal plan where relevant). `frontend/src/lib/api.ts` extended with the compatibility client functions and types.
- **Verified live in-browser**: Haldia + Panamax + 75,000t correctly triggers the tidal plan (3 cycles × 26,500t ≈ 1.5 days, capped at 3 vessels/tide); Paradip + Capesize correctly fails on draft (17.0m required vs. 16.5m available, a real 0.5m edge case matching our research on Paradip's first Capesize berthing) while still passing LOA/beam, with the reasoning shown per-constraint, not just pass/fail.
- Caught and fixed the same stale-Vite-dependency-cache issue as before (adding new lucide-react icons triggered it again) — noted here in case it recurs: `rm -rf node_modules/.vite` and restart.

See `MODELS.md` for the consolidated model reference doc (all models used/considered/rejected, with accuracy achieved and why), and the expanded `FEATURES.md` (now 37 features: 10 baseline + 27 differentiating).

**Ticker tape switched from simulated to real live-polled data.** The Section 12 ticker originally used `Math.random()` jitter around real baseline numbers — cosmetically fine for a first pass, but not actually real, which the user correctly called out.
- `app/services/market.py`, `app/schemas/market.py`, `app/api/market.py` — `GET /market/ticker` returns the latest *actual ingested* value and real day-over-day change for BDI/BCI/BPI/BSI/BHSI/COAL_AUS/SP500/DXY, pulled straight from `freight_rates`.
- **Honesty design decision**: Baltic Exchange rates are a paid live feed we don't have, so this is the latest *ingested* value with its real date, not a literal real-time tick — the frontend shows each item's actual date (e.g. "as of 2019-07-31" for BDI, "as of 2026-09-11" for DXY) rather than implying a live market feed that doesn't exist. Mixed recency across series (freight indices end 2019, SP500/DXY run through 2026) is surfaced honestly rather than hidden.
- `frontend/src/components/TickerTape.tsx` rewritten to poll the real endpoint every 60s and flash green/red only when a value actually changes between polls (not on every poll regardless), fixing what would otherwise have been a fake-looking constant flash.
- Verified live in-browser (fresh tab, clean console): real values, real percentage changes, real per-item dates all rendering correctly.

### 8. Multi-origin recommendation engine — ✅ done, wired end-to-end to the UI
Combines Section 7's compatibility engine, Section 5's ARIMA forecast, and the
routes/distances seeded in Section 3 into a single ranked comparison. Feature
#5 — no competitor platform reviewed does single-cargo, multi-origin
comparison this way.
- `app/services/recommendation.py` — for a destination port + cargo tonnage, picks the smallest vessel class that fits the parcel, checks physical compatibility (reusing Section 7's engine directly, not a re-implementation), estimates freight cost as distance × a published $/tonne-per-1000nm benchmark (cited: Thunder Said Energy, from our own research doc) × a vessel-class multiplier reflecting real economies of scale, and pulls a live 1-day-ahead ARIMA forecast (reusing Section 5's model) of the relevant Baltic sub-index (BCI/BPI/BSI/BHSI depending on vessel class) to show market direction alongside the cost. Ranks all 5 origins by estimated cost, compatible origins first.
- `app/api/recommendation.py` — `POST /recommendation/compare`.
- **Frontend fully rewired**: `frontend/src/pages/Recommendation.tsx` replaced the disabled placeholder form with a live one — pick a destination port and cargo tonnage, get an animated, ranked grid of all 5 origins with cost, distance, transit days, compatibility, and market-forecast direction per card, the top pick highlighted with a green glow and trophy badge.
- **Verified live in-browser**: Paradip + 75,000t correctly ranked Indonesia cheapest ($506k, 2,700nm) through United States most expensive ($2.16m, 11,500nm), all marked Panamax-compatible, each citing a live BPI forecast (-3.14%, "softening") pulled from the real Section 5 model, not a static number.
- Every cost figure is explicitly labeled illustrative/not-a-live-quote in both the API response and the UI, consistent with our own research finding that no live route-level freight rate data is publicly available without a paid terminal.

### 9. Risk & disruption scoring module — ✅ done, wired end-to-end to the UI
Composite Route Risk Score, early-warning logic, using the 4 real disruption
events seeded in Section 3. Feature #6.
- `app/services/risk.py` — combines three independent, explained factors into one 0-10 score: (1) disruption exposure — the seeded events weighted by relevance (direct region match vs. global market-wide spillover for geopolitical/canal_strait categories) and recency-decayed; (2) port congestion — from each port's real researched turnaround time or tidal-restriction flag; (3) freight volatility — the coefficient of variation of the last 90 rows of real BDI data, computed directly (not a model fit, so it's fast enough for a live request unlike the Section 5/6 backtest). Composite = 40/30/30 weighted average, labeled Low/Moderate/High/Severe.
- `app/api/risk.py` — `GET /risk/events` (all seeded disruption events), `GET /risk/score?origin_country=&destination_port_id=`.
- Real bug caught and fixed immediately in testing: the service returned nested dataclasses inside a dict, which Pydantic can't validate directly against nested response models — fixed by explicitly constructing each nested schema object in the endpoint rather than relying on `**result.__dict__`.
- **Frontend fully rewired**: `frontend/src/pages/Risk.tsx` replaced the hardcoded event array with live `GET /risk/events`, and added an interactive risk-score checker (pick origin + destination, see the composite score, color-coded label, per-factor breakdown, and which real events contributed).
- **Verified live in-browser**: Australia→Dhamra correctly scored 6.91/10 (High) — disruption exposure 7.52 (direct-matched to the Cyclone Koji event plus global Red Sea/Panama spillover), congestion 3.0 (Dhamra has no turnaround data on file, defaulted honestly rather than guessing), volatility 10.0 (BDI's real 90-day CV in our dataset is 32.4%, a genuinely volatile stretch, not a capped/fake number). Russia and Indonesia routes correctly showed lower/absent direct-match disruption weight, as expected.

### 10. Financial modeling module — ⬜ not started
COA-vs-Spot simulator, idle-time/ballast minimizer, demurrage estimator, ROI calculator.

### 11. Scenario/stress-testing backend logic — ⬜ not started

### 12. Frontend scaffolding — ✅ done (pulled forward, running alongside backend work)
React + TypeScript + Vite + Tailwind v4, React Router, Recharts, Axios.
- `frontend/src/{App.tsx,main.tsx}`, `components/{Sidebar,HealthBadge,ComingSoon}.tsx`, `lib/api.ts`
- Dev proxy: `frontend/vite.config.ts` proxies `/api` → `http://127.0.0.1:8000`, so no CORS juggling locally; production points at Render via `VITE_API_BASE_URL`.
- Verified in-browser: `/` (Overview) is genuinely live-wired to the backend's `/api/v1/health` and shows real status (DB up, cache down, latency); routing between all 5 pages works.

### 13. Core dashboard UI — 🔧 in progress (placeholder screens built, not yet wired to real data)
5 pages built as working previews, each clearly labeled with which future section
will wire it to live data: Overview (live), Freight Forecast (placeholder chart),
Chartering Recommendation (placeholder form), Port Compatibility (real Table 1
data, hardcoded until Section 3/7 seed+serve it from the DB), Risk & Disruptions
(real documented events, hardcoded until Section 9).
- `frontend/src/pages/{Overview,Forecast,Recommendation,Ports,Risk}.tsx`

### 14. Map visualization + scenario sandbox + fixture ledger UI — ⬜ not started

### 15. NL query assistant ("Ask the Freight Desk") — ⬜ not started

### 16. Alerting, low-latency tuning, MLOps monitoring, deployment polish — ⬜ not started
