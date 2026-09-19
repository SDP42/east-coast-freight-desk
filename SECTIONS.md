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
- **Verified with real results, not just "it runs":** BDI backtest achieved **4.29% mean MAPE** on the earlier computed BDI (re-measured on the real BDI in Section 14b: 3.08% at 7 days) across 5 splits (order (2,1,2), ADF p=0.0043 confirming stationarity) — genuinely competitive with Luo et al. (2026)'s more sophisticated transformer-hybrid result of 5.26% MAPE on the same index, cited in our own research compendium. BCI achieved 7.50% MAPE. Confirmed generalizes across all 7 ingested series, correct 404 on an unknown index, and visible in the Swagger UI under a new `forecast` tag.
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

**Real, honest results after both fixes** (BDI, 7-day horizon, 5 walk-forward splits): ARIMA MAPE 4.68%, **XGBoost MAPE 4.19%** (XGBoost edges out ARIMA once the exogenous features actually had data), Hybrid MAPE 4.34%, weights 47.6% ARIMA / 52.4% XGBoost. **Wilcoxon hybrid vs. ARIMA: p=5.4×10⁻⁶** on the computed BDI. **Withdrawn**: that BDI was computed from sub-indices and biased; on the real BDI the hybrid does not beat ARIMA (see Section 14b). Hybrid vs. XGBoost alone was not significant (p=0.99) — an honest result: when one base model is already strong, averaging with a weaker one doesn't help further, which is expected ensemble behaviour, not a flaw. Confirmed generalizes to BCI (hybrid MAPE 8.98%, best of the three, though neither significance test reached p<0.05 there — a fair, non-cherry-picked result). SHAP consistently found `lag_1` overwhelmingly dominant (~100x any other feature) — expected for a highly autocorrelated daily index; `coal_aus` and `month` were the next most useful features.
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

### 10. Financial modeling module — ✅ backend done for all 4 tools; 2 of 4 wired to UI
COA-vs-Spot simulator, idle-time/ballast minimizer, demurrage estimator, ROI
calculator. Features #7, #8, #9, plus an ROI calculator (from the original
approved plan).
- `app/services/financial.py` — all four tools:
  - **COA-vs-Spot**: fits ARIMA on the target index (reusing Section 5), projects a spot-rate path for N future fixtures by scaling the user's known current $/tonne rate by the forecast/current index ratio, compares total cost against locking today's rate flat, and sizes the spot path's $ uncertainty from real historical daily-return volatility. Recommends "Lock in COA" / "Stay spot" / "Marginal" with a plain-English rationale.
  - **Idle-time/ballast minimizer**: ranks candidate next fixtures by total idle days (ballast transit + laycan wait), reusing Section 3's route data; the ballast-leg approximation (laden-route transit time as a proxy, since we have no separate ballast-route distances) is explicitly flagged in the response.
  - **Demurrage estimator**: `max(0, actual_turnaround − contractual_laytime) × real researched demurrage-rate benchmark` (Panamax/Capesize rates directly cited in our research; Supramax/Handysize extrapolated and flagged as such).
  - **ROI calculator**: annual savings = cargo tonnes × assumed $/tonne × (real historical coefficient-of-variation × a user-adjustable "captured %" assumption), explicitly labeled illustrative.
- `app/api/financial.py` — `POST /financial/coa-vs-spot`, `/financial/ballast-options`, `/financial/demurrage`, `/financial/roi`.
- Real bug caught in testing: none this time — all four endpoints worked correctly on first test after the nested-dataclass lesson learned in Section 9 was applied proactively (explicit schema construction, not `**result.__dict__`).
- **Frontend**: new `frontend/src/pages/Financial.tsx` (routed at `/financial`, added to the sidebar) with live, working UI for the COA-vs-Spot simulator and ROI calculator. Demurrage estimator and ballast-leg minimizer are backend/API-only for now (verified via curl, not yet given a UI) — a fast follow-on, not a gap in the underlying logic.
- **Verified live in-browser**: COA-vs-Spot (BPI, $15/t, 75,000t × 6 fixtures) correctly recommended "Stay spot" (model forecasts BPI falling 6.7% over 180 days, so locking today's rate would forgo ~$449k) — matches the curl test exactly. ROI calculator correctly computed $13.7M/year illustrative savings from BDI's real 38.2% historical CV. Noted honestly: ARIMA's point forecast flattens toward a constant for long multi-fixture horizons (expected behavior for a differenced series, not a bug) — the confidence interval still widens even though the central estimate doesn't move much fixture-to-fixture.

### 11. Scenario/stress-testing engine — ✅ done, wired end-to-end to the UI
Feature #12. Re-runs the Section 8 multi-origin comparison under user-defined
shocks and reports what changed.
- `app/services/scenario.py` — four shock types: `freight_spike` (multiplies all costs, e.g. "BDI +50%"), `port_closure` (destination unavailable N days; delay priced at the vessel class's Section 10 demurrage rate, and the other 6 East Coast ports are ranked as reroute alternatives), `red_sea_closure` (+3,500nm for Russia and US routes — the figure from the documented Section 3 case study), and generic `origin_disruption`. Returns per-origin baseline vs. scenario cost/rank, whether the best origin flipped, and a plain-English summary.
- Small refactor to Section 8's `compare_origins`: now accepts a pre-computed `market_signal` (so a scenario fits ARIMA once instead of once per port — 8 comparisons would otherwise be ~20s) and an `extra_distance_nm` map for rerouting.
- `app/api/scenario.py` — `POST /scenario/run`; unknown shock types return a clear 422.
- **Frontend**: new `frontend/src/pages/Scenario.tsx` at `/scenario` (sidebar entry added) — toggles/sliders for freight spike (−30% to +150%), port closure (1-14 days), and Red Sea closure; before/after table with rank changes, a summary banner, and a reroute-alternatives panel.
- **Verified**: Red Sea + 50% spike → Russia +100.0% / US +95.7% (distance effect stacked on the rate effect), Indonesia +50% and still best; 5-day Paradip closure → +$57,500 (5 × $11,500 Panamax rate) with reroute options surfaced; UI-run combined scenario $506,250 × 1.5 + 3 × $11,500 = $793,875 matched to the dollar.
- **Known limitation, stated plainly**: route distances are seeded per origin *country* to all destination ports (Section 3), so the reroute alternatives (Vizag/Gangavaram/Dhamra) tie on cost — the ranking among alternative ports reflects compatibility only, not real port-to-port distance differences. Real per-port distances would sharpen this.

### 12. Frontend scaffolding — ✅ done (pulled forward, running alongside backend work)
React + TypeScript + Vite + Tailwind v4, React Router, Recharts, Axios.
- `frontend/src/{App.tsx,main.tsx}`, `components/{Sidebar,HealthBadge,ComingSoon}.tsx`, `lib/api.ts`
- Dev proxy: `frontend/vite.config.ts` proxies `/api` → `http://127.0.0.1:8000`, so no CORS juggling locally; production points at Render via `VITE_API_BASE_URL`.
- Verified in-browser: `/` (Overview) is genuinely live-wired to the backend's `/api/v1/health` and shows real status (DB up, cache down, latency); routing between all 5 pages works.

### 13. Core dashboard UI — ✅ done (landing, auth, personas, live charts, real forecast)
The first UI pass (Section 12) left most pages as placeholders and the app felt
flat. This pass rebuilt the front of the product.
- **Landing page** (`Landing.tsx`, route `/`): hero with a streaming BDI chart, a "problem in numbers" strip (figures from our research compendium: BDI -94% May→Dec 2008, -91% Oct 2021→Feb 2023; ~84% of SAIL's coking coal imported per the CAG audit), capability grid, how-it-works, persona cards pulled from the backend, and a footer that states plainly that prices are replayed real data, not a live feed.
- **Auth pages** (`Login.tsx`, `Register.tsx`, `lib/auth.tsx`): JWT kept in localStorage and attached by an axios interceptor; `AppShell` guards everything under `/app` and redirects signed-out visitors to `/login`; clear error messages (wrong password, unreachable backend).
- **Personas** (`app/core/personas.py`, `lib/personas.ts`): Procurement Manager, Chartering Analyst, Port & Logistics Officer, Finance & Treasury, stored in the existing `users.role` column. Chosen at sign-up; shapes the Overview greeting, three quick-action cards, and a dot on the sidebar tools suggested for that role. **`admin` cannot be chosen at self-registration** (validator rejects it, verified with a 422) so nobody can grant themselves elevated access. It is a starting point, not a permission wall — every role can use every tool.
- **Live market charts** (`LiveChart.tsx`, `Markets.tsx`): replays real ingested history one observation at a time with play/pause and 1x/3x/8x speed. A move is flagged as a spike or drop when it exceeds 2σ of that series' own daily changes. **Honest by design**: the UI states this is a replay, not a live feed (Baltic Exchange rates are a paid subscription; our freight series end July 2019). Region boards group series by origin region with sparklines; clicking a row charts it.
- **Regional data** (`/market/history/{index}`, `/market/regions`): added real FRED series — INR/USD, AUD/USD, ZAR/USD — alongside the coal, S&P 500 and dollar-index series. Indonesia and Russia have no free real series, so they are shown empty with a note rather than filled with invented numbers.
- **Forecast page rewritten** (`Forecast.tsx`): real history plus the ARIMA forecast with a 95% band, five indices, 7/14/30-day horizons, real backtest metrics, and an ensemble panel (ARIMA vs XGBoost vs hybrid, weights, both Wilcoxon tests, SHAP driver bars).
- **Verified in the browser**: register → auto sign-in → personalised Overview; wrong password shows an error; correct password lands on `/app`; sign-out clears the token and the guard redirects; Markets switches series (INR chart confirmed); Forecast renders real data (BDI 14-day, computed-BDI era; superseded by Section 14b).
- `npx tsc -b` passes with no errors.

### 14. Port map — ✅ done (map view; fixture ledger not started)
Feature #19 (AIS-lite congestion view). Originally scoped together with a fixture
ledger UI; the ledger is not built yet and stays in FEATURES.md as ⬜.
- `app/services/portmap.py`, `app/api/portmap.py` — `GET /map/overview`: the 7 East Coast ports (real coordinates, berth fit per vessel class from Section 7, congestion score from Section 9), representative origin terminals, 18 sea-lane routes with hand-placed waypoints (Australia, Indonesia, Mozambique → six destination ports), and 15 simulated vessels positioned from the wall clock so refreshes stay consistent.
- `scripts/seed_port_coordinates.py` — approximate coordinates for all 12 ports (also added to `run_all.py`).
- `frontend/src/pages/PortMap.tsx` (Leaflet + react-leaflet): port rings coloured by congestion and sized by capacity, vessels animated along the lanes (coloured by class), a ports panel sorted by risk that flies the map to a port, popups with draft/turnaround/accepted classes.
- **Simulation is labelled everywhere**: ports, berth fit and congestion are real; vessel positions and anchorage queue counts are simulated because real AIS is a paid feed. Russia and US routes run via Suez or the Cape and fall outside the map frame, so they are not animated.
- **Tile provider decision**: the first attempt used CARTO's dark basemap, which now overlays "API KEY REQUIRED" on its free tiles. Rather than wire in a key, the map uses keyless OpenStreetMap tiles darkened with a CSS filter. OSM's tile policy suits a demo like this; a production deployment should use a paid or self-hosted tile source.
- Verified in the browser: dark basemap with coastline, Paradip green / Haldia and Sagar red, vessels moving along lanes, ports panel populated.

### 14b. Data expansion and correction — ✅ done
Triggered by the request for more official and third-party data. A helper agent downloaded 33 files into `data/raw/candidates/` (see `MANIFEST.md` there); this section records what was verified and used.
- **Real BDI replaces the computed BDI.** Our earlier BDI was computed as 0.4·BCI + 0.3·BPI + 0.3·BSI from the Mendeley sub-indices. Checked against a real daily BDI (2006-02-23 to 2026-02-20), the computed series ran about 15% high (real/computed ratio 0.85, correlation 0.98; on 2019-07-31 real 1,868 vs computed 2,325). The real series hits the known checkpoints (11,793 in May 2008, 663 in Dec 2008, 5,650 in Oct 2021, 530 in Feb 2023). `scripts/ingest_real_bdi.py` swaps it in (4,989 rows); `ingest_freight_rates.py` no longer computes a BDI. The file is Investing.com data via a GitHub mirror with no licence: internal use only, gitignored, not to be redistributed. BCI/BPI/BSI/BHSI still end July 2019 (no free source found).
- **Models re-measured on the real BDI (honest result).** ARIMA(2,1,2): 3.08% MAPE at 7 days, 4.54% at 14 days. In the paired ensemble backtest (7 days, 35 forecasts) ARIMA is 2.88%, XGBoost 4.10%, hybrid 3.17%. **Hybrid vs ARIMA Wilcoxon p = 0.998: not significant. The ensemble does not beat ARIMA on the real BDI.** The earlier p = 5.4×10⁻⁶ and p = 0.0008 results came from the smoother computed series and are withdrawn. The hybrid does beat XGBoost alone (p ≈ 8×10⁻⁸). Daily BDI is close to a random walk, so short-horizon gains over ARIMA are hard.
- **PortWatch** (`ingest_portwatch.py`, tables `port_activity`, `chokepoint_transits`, migration `f15254280991`): 11,244 port-day rows for Paradip, Visakhapatnam, Haldia, Dhamra and Gopalpur, and 19,691 chokepoint-day rows (Suez, Bab el-Mandeb, Malacca, Cape, Lombok, Sunda, Torres), 2019 to Sept 2026. Tonnes are AIS estimates. Licence still to be confirmed. Gangavaram and Sagar/Sandheads are not separate PortWatch ports.
- **Risk uses it**: the port-congestion factor now adjusts the turnaround-based score by how last-30-day dry-bulk calls compare with the port's own history since 2019, and says so in the factor detail.
- **Ministry of Ports turnaround** (`ingest_port_turnaround.py`): FY2024-25P average turn-round now set for Paradip 44.88 h, Visakhapatnam 69.19 h, Haldia 46.79 h (parsed from the PDF; spot-checked). Non-major ports (Gangavaram, Dhamra, Gopalpur) remain without data.
- **SAIL facts verified from the annual reports**: imported share of clean coking coal is about 87% (16.92 of 19.37 MT in FY24; 16.32 of 18.74 MT in FY25). The landing page said 84%; corrected to 87%. The CAG report lists Visakhapatnam, Gangavaram, Paradip, Dhamra and Haldia as discharge ports, and gives 374 demurrage cases in 2017-18 to Oct 2021.
- **Downloaded, not yet used**: IBTrACS cyclone tracks (feature #13), Comtrade India HS 2701 by partner (`trade_volumes`; HS 270119 mixes coking and thermal), World Bank Pink Sheet to Aug 2026, FRED Brent/WTI/iron ore, CAG demurrage terms, port commodity traffic tables.
- **Still not obtainable**: real fixtures or charter rates (SAIL tender portals are Captcha-gated), post-2019 sub-indices, Indonesia/Russia prices, bunker prices, HBA/API2.

### 14c. Haldia study, light redesign, proper authentication — ✅ done
- **Haldia study** (public sources: Wikipedia, SMP Kolkata, port-technology and ICRA notes, plus the port's own daily reports). Facts used: an impounded dock entered through a 330 m by 39 m lock; 14 berths and 3 oil jetties; about 130 km from Sandheads and 45 km above the Sagar pilot station, roughly six hours' passage; floating cranes lighten large ships at Sagar and Sandheads; coal berth 4A (build-operate-transfer terminal) with two grab unloaders at about 14,000 t/day; Adani's berth 2 bulk terminal commissioned March 2026.
- **Real vessel data**: SMP Kolkata publishes a daily Haldia "Morning Position" PDF. `scripts/ingest_haldia_positions.py` parses 84 of them (June to September 2026) into `haldia_coal_calls`: 94 distinct coking- and PCI-coal vessels, median cargo 33,000 t (range 13,335 to 35,710), expected draft about 7.3 to 8.5 m, LOA about 229 m, 59 bound for SAIL. This is the clearest evidence in the project of the partial-load reality at Haldia. Two report layouts exist; the parser is regex-based and spot-checked, not exhaustive. Served at `GET /haldia/summary`.
- **SAIL website data** (`data/raw/sail_site/`, fetched by verifying the incomplete certificate chain rather than disabling TLS checks): quarterly performance highlights (Q3 FY25 to Q1 FY27), the September 2026 investor presentation and the SAIL Handbook 2025. Quarterly crude steel: Q1 FY26 4.854 MT, H1 FY26 9.503 MT, FY26 19.434 MT, Q1 FY27 4.757 MT. sail.co.in has no machine-readable press feed or import-by-origin data; tender portals are Captcha-gated. The large SAIL News PDF was deleted unread to save disk.
- **Light theme**: the whole app moved from dark navy to a light palette by remapping tokens in `index.css` (new `strong`, `body`, `on-accent` tokens) and re-colouring charts and the map. Components in the style of reactbits.dev, reimplemented locally: split-text reveal, tilt card, magnet button, marquee, shiny text, aurora backdrop.
- **Landing page rewritten** around a vanilla three.js Haldia scene (`HaldiaScene.tsx`, code-split into its own 568 kB chunk): ships queue at the anchorage beside a lightering barge, one vessel sails the river, passes the lock (gates animate, chamber level rises), discharges at berth 4A while grabs work and the coal pile grows, then a loaded train leaves. Five-step captions and labels follow the action; the panel below shows the real Haldia numbers. Respects `prefers-reduced-motion`. Marked schematic.
- **Authentication**: password policy (8 to 72 characters, letter and number), a login lockout (5 failures in 10 minutes for an email or address, HTTP 429; in-memory, single instance), `PATCH /auth/me` and `POST /auth/change-password`; frontend redesign with show/hide and a strength meter, a profile page, and automatic sign-out with a message when the token expires. The JWT secret is still the development default: it must be replaced with a real secret in the deployment environment (to be done with the user in Section 16).

### 15. NL query assistant ("Ask the Freight Desk") — ✅ done
- `app/ml/intent.py`: TF-IDF (word 1-2 grams and character 2-4 grams) plus entity-marker tokens plus logistic regression, trained at start-up on 132 hand-written questions across 11 intents plus 140 template-generated ones. Held-out accuracy on hand-written questions (5-fold, templates always in training): **75% ± 9%**. It is a small in-distribution test, not an external benchmark; below 35% confidence the assistant asks for clarification instead of guessing. Rule-based entity extraction finds the index, port, origin, horizon and cargo size.
- `app/services/assistant.py`: 11 handlers call the same engines as the dashboard (market series, quick ARIMA, origin comparison, berth fit, route risk, congestion, Haldia ledger). Answers are short broker-style briefings with the figures used, stated assumptions ("no port named, so I assumed Haldia"), stale-data warnings for series that stop early, and a caveat that the freight-only origin ranking ignores coal quality (Indonesian coal is mainly thermal). `services/quick_forecast.py` fits a fixed ARIMA(2,1,2) on the last ~3 years and caches it, so a question does not pay for the 11-second order search.
- `POST /assistant/ask` and `GET /assistant/info` (both need sign-in). Frontend `Ask.tsx`: suggestion chips, chat bubbles, figure chips, deep links, intent and confidence tags, and the model's own accuracy statement.
- No external LLM was used, so nothing is sent off the deployment. A hosted LLM could be added later for free-text phrasing; that would need a provider and key chosen with the user.


### 16. Alerting, low-latency tuning, MLOps monitoring, deployment polish — ⬜ not started
