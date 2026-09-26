# Feature List — Baseline vs. Differentiating

82 rows (76 live, 3 removed in the licence purge, 3 re-based; 10 baseline + 71 differentiating), split deliberately into two groups: things any competent
competing team (there are ~300 submissions per problem statement, and at least
two public GitHub repos already attempting near-identical ideas) would also
build, and things that are genuinely ours. This split is itself part of the
pitch — it shows the judges we know exactly what's "table stakes" versus what's
the real USP, rather than presenting everything as equally novel.

**Why 16 build sections for 80 features:** the sections in `SECTIONS.md` are
*build phases* (how the system gets implemented), not a 1:1 map to features
(what capabilities exist). Several features are delivered together within one
section because they share the same underlying subsystem — e.g. Section 7
alone delivered features #1 and #2 (compatibility engine + tidal optimizer);
Section 8 delivered #5; Section 9 delivered #6. The table below is the actual
per-feature tracker — updated every session, not just at section boundaries.

## Status tracker (all 80 features)

Legend: ✅ done & live in the UI · 🔧 partially built (backend exists, not fully surfaced, or vice versa) · ⬜ not started

### Baseline (10)

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Freight rate forecasting from historical data | ✅ | Section 5/6 — ARIMA+XGBoost ensemble |
| 2 | Dashboard showing forecast charts over time | ✅ | `Forecast.tsx` — real history + ARIMA forecast with 95% band, 5 indices, 7/14/30-day horizons |
| 3 | Basic vessel class reference data | ✅ | Section 3 seed + `/compatibility/vessel-classes` |
| 4 | "Which vessel class fits this cargo size" | ✅ | Section 8 `pick_vessel_class` + compatibility check |
| 5 | Historical freight-rate data visualization | ✅ | `Markets.tsx` + `LiveChart.tsx` — streaming replay of real history with spike/drop detection, plus regional boards |
| 6 | REST API serving model predictions | ✅ | `/forecast`, `/forecast/{index}/ensemble` |
| 7 | User authentication / login | ✅ | Backend (Section 4) + `Login.tsx`, `Register.tsx`, route guard, sign-out |
| 8 | Form to input cargo details, origin, destination | ✅ | `Recommendation.tsx` live form |
| 9 | Basic filtering/search over historical data | ✅ | `Explorer.tsx` + `/data/*`: filter any of 12 series by date and value, search series and disruption events, CSV export
| 10 | Historical fixture ledger & benchmarking | ✅ | `Ledger.tsx`: hash-chained fixtures benchmarked against the USDA monthly ocean rate (percentile in the trailing 12 months, cheaper month within one month either side, forward change) and against the illustrative route rate. Re-based in the licence purge (was the Baltic index) |

### Differentiating (29)

| # | Feature | Status | Where |
|---|---|---|---|
| 1 | Port–Vessel Compatibility Engine | ✅ | Section 7, live checker + matrix in `Ports.tsx` |
| 2 | Tidal-cycle-aware partial-load optimizer | ✅ | Section 7 `tidal_plan` logic |
| 3 | Multi-horizon ensemble forecasting (7/30/90-day) | ✅ | `MultiHorizon.tsx` on the Forecast page: 7/14/30/60/90-day outlook side by side with widening bands; per-split backtest table
| 4 | SHAP-based explainability panel | ✅ | Ensemble panel on `Forecast.tsx` shows SHAP driver bars next to the model comparison |
| 5 | Multi-origin comparative routing | ✅ | Section 8, live in `Recommendation.tsx` |
| 6 | Disruption/Risk Early-Warning composite score | ✅ | Section 9, live in `Risk.tsx` (on-demand score; push-style "early warning" alerting is #27, not yet built) |
| 7 | COA-vs-Spot Simulator | ✅ | Section 10, live in `Financial.tsx` |
| 8 | Idle-time/ballast-leg minimizer | ✅ | `Voyage.tsx` Demurrage & idle time tab: origins ranked by ballast plus laycan wait
| 9 | Demurrage risk estimator | ✅ | `Voyage.tsx`: expected demurrage from the port's real turnaround against your laytime
| 10 | Historical fixture ledger & benchmarking | ✅ | `Ledger.tsx`: add fixtures, benchmark timing against the real Panamax index, BPI (percentile, cheaper day within 30 days, forward move) and rate against the illustrative rate. No public fixture data exists, so only the six sample entries (marked) and your own entries are shown
| 11 | "Ask the Freight Desk" NL query assistant | ✅ | `Ask.tsx` + `/assistant/ask`: local TF-IDF + logistic-regression intent model (11 intents, 75% held-out accuracy on hand-written questions) routes to the forecast, origin, berth, risk, congestion, Haldia, COA and demand engines. No external LLM. |
| 12 | Scenario/stress-testing sandbox | ✅ | Section 11, live in `Scenario.tsx` (freight spike, port closure with reroute alternatives, Red Sea closure) |
| 13 | Monsoon/cyclone-adjusted ETA & laycan risk engine | ✅ | `Signals.tsx` Cyclone tab: IBTrACS 1990-2025 storm-day probability within 400 km of each port by month, expected delay for a laycan window (delay per storm day is an assumed parameter)
| 14 | WhatsApp/SMS disruption alerts | 🔧 | In-app alerts and https webhooks are live (`Alerts.tsx`). WhatsApp/SMS need a messaging-provider account and are not configured
| 15 | CII/carbon emissions estimator per voyage | ✅ | `Voyage.tsx` Carbon tab: round-trip CO2, IMO bulk-carrier CII rating for 2023-2026, speed sweep. Fuel burn per class is an assumed typical value
| 16 | INR/USD hedging cost overlay | ✅ | `Voyage.tsx` Hedge tab: real FRED INR/USD volatility, forward from the interest differential (assumed rates), cost of hedge vs worst-case saved, flags ratios above SAIL's 25% policy cap
| 17 | Rail-sea-rail coastal modal-shift recommender | ✅ | `Voyage.tsx` Rail-sea-rail tab: landed cost at five plants across five ports. Rail distances and tariff are approximate planning assumptions
| 18 | Hash-chained fixture ledger (audit trail) | ✅ | SHA-256 chain across ledger entries, verified on every load; editing any past entry breaks the chain at that entry (tested)
| 19 | AIS-lite vessel congestion heatmap | ✅ | `PortMap.tsx` — real port congestion rings + simulated vessels on sea lanes and simulated anchorage queues, clearly labelled as simulated (no free real AIS) |
| 20 | "Explain like a broker" auto-briefing narrative | ✅ | `BriefingCard.tsx` on Overview (market, outlook, ports, route risk) from `/briefing`, plus every assistant answer
| 21 | Macroeconomic Cargo Demand Estimator | ✅ | `Signals.tsx` Coal demand tab: imported coking coal as a share of crude steel (0.865, from FY24 and FY25 annual reports) applied to reported quarterly steel, with a growth slider and shipload count. Two calibration points only, so indicative
| 22 | Berth Slot Availability Forecaster | 🗑️ removed | Removed in the licence purge: it was built on IMF PortWatch call counts (IMF terms, not public domain). Berth risk is now covered by the Ministry of Ports turnaround figures, cyclone risk and the laytime calculator |
| 23 | Cross-Port Congestion Transfer / Rerouting Signal | ✅ | `Signals.tsx` Congestion transfer tab: Bonferroni-corrected Granger tests across five ports (Haldia leads Visakhapatnam by about 6 days) and a live rerouting signal
| 24 | Model Trust / Backtest Transparency Dashboard | ✅ | Forecast page: backtest metrics, per-split table, model comparison, weights, Wilcoxon tests, SHAP
| 25 | Automated Retraining Pipeline with Drift Detection | ✅ | `Monitor.tsx`: frozen-model error vs the prior year (Mann-Whitney), return-distribution PSI, manual retrain, scheduled retrain on drift, run history. Since row 74 the data refreshes itself every 6 hours, so a retrain can now see new observations
| 26 | Multi-Objective Pareto-Ranked Recommendations | ✅ | `ParetoCard.tsx` on Recommendation: cost, transit time and route risk, Pareto-optimal origins marked, adjustable weights
| 27 | Configurable Alerting | ✅ | `Alerts.tsx`: six rule types, in-app feed with unread badge, https webhook (public hosts only), 30-minute background evaluation
| 28 | Role personas (tailored starting point per user type) | ✅ | Backend personas + self-register validation (admin not self-selectable); persona picker at sign-up, persona-specific Overview quick actions and sidebar hints |
| 29 | Regional market boards with live-replay charts | ✅ | `Markets.tsx` — freight, coal, FX and equity series grouped by origin region; regions with no real series (Indonesia, Russia) are shown empty rather than invented |
| 30 | Haldia digital-twin landing scene (three.js) | ✅ | `HaldiaScene.tsx`: anchorage and lightering, river transit, the 330 x 39 m lock with animated gates, berth 4A unloaders, coal pile and rail, with labels and a step caption. Schematic, built from public port-trust figures |
| 31 | Real Haldia coal-vessel ledger from port-trust reports | 🗑️ removed | Removed in the licence purge: the SMP Kolkata reports state no reuse licence. Haldia's cargo ceiling is now a stated, editable assumption (35,000 t) |
| 32 | Account security: password policy, login lockout, change password, session expiry | ✅ | Backend policy (8+ chars, letter and number), 5-failure 10-minute lockout, `PATCH /auth/me`, `POST /auth/change-password`; frontend strength meter, show/hide, profile page, automatic sign-out on expired token |
| 33 | Role-based access control with per-port and per-row scoping | ✅ | `core/permissions.py`, `require()` on every route; port officers see only assigned ports (filtered in the query), analysts see only their own ledger rows. Roles are assigned by an admin, never chosen at sign-up |
| 34 | One-click demo accounts for every role | ✅ | `scripts/seed_demo_users.py`, `/auth/demo-login` (passwordless, demo-flagged accounts only, switchable off) |
| 35 | Chatbot and voice assistant that answer only within the caller's permissions | ✅ | 15 intents; refusals are explained and logged; ledger/alerts/access/user-admin intents query the database under the user's scope; browser voice input, spoken answers, voice navigation ("open the port map") |
| 36 | Access matrix, user administration and audit log | ✅ | `Access.tsx`, `/admin/*`: role matrix, assign roles and ports, denied-request log |
| 37 | Model Lab: ML and deep learning on public-domain data | ✅ | Re-based in the licence purge: `scripts/train_current.py` and `train_current_dl.py` (ARIMA, Ridge, XGBoost, hybrid, GRU) walk-forward tested on the USDA ocean rate with US BLS, EIA and Federal Reserve inputs; `services/current.py`, `ModelLab.tsx`. Honest results: only the 1-month Ridge and hybrid beat 'no change' (p = 0.016 and 0.04, four models compared); the GRU does not (p = 0.38). The Baltic LSTM/GRU/TCN/Transformer study was removed with the Baltic data |
| 38 | Trade Globe (three.js) | ✅ | `TradeGlobe.tsx`, `/lab/chokepoints`: sea lanes and chokepoint locations in 3D. Chokepoint traffic was removed in the licence purge (IMF PortWatch); the What-If Studio prices a Red Sea closure directly |
| 39 | Risk Lab: 3D forecast fan (three.js) and cost-at-risk Monte Carlo | ✅ | `RiskLab.tsx`: 400 bootstrap paths in 3D; 5,000-draw landed-cost distribution in INR crore with P50/P95 and variance shares |
| 40 | Market Terrain (three.js) | ✅ | `Terrain.tsx`: eight series over seven years as an interactive 3D landscape |
| 41 | Haldia lightering planner | ✅ | `/lab/lightering`: how much of a mother-vessel cargo is lightened at Sagar, using an assumed 35,000 t Haldia ceiling, barge capacity and cycle time (all editable). The data-fitted version used SMP Kolkata reports and was removed |
| 42 | Laycan timing coach | ✅ | `/lab/timing`: 60-day calendar of storm risk in the arrival week for a port and origin; freight direction is not scored because the indices end in 2019 |
| 43 | Unusual-moves feed | ✅ | `/lab/anomalies` on Markets: series whose latest move is 2 or more standard deviations out |
| 44 | Board pack (print-ready briefing, role-scoped) | ✅ | `Report.tsx` |
| 45 | Command palette (Ctrl/Cmd+K) | ✅ | Jump to any page the role may open, or send the text to the assistant |
| 46 | Fluid interface scaling from phones to 4K projectors | ✅ | rem-based layout, root size 16 px to 1920 px wide then 0.8333vw (32 px at 3840), pixel chart sizes routed through a scale helper, drawer menu below 1024 px |
| 47 | Live Desk: minute-by-minute ticks (simulated) | ✅ | `LiveDesk.tsx`, `/live/seed`: each daily series' last real close (Brent, rupee, Australian dollar, rand, dollar index) replayed as 390 one-minute Brownian-bridge steps with its real volatility; labelled SIMULATED |
| 48 | What-If Studio (last-minute price scenarios) | ✅ | `WhatIf.tsx`, `services/whatif.py`, `POST /whatif/run`: one landed-cost model with eight levers (freight, rupee, fuel, port delay, storm delay, reroute, speed, urgency premium), live recompute, cost breakdown, save and compare up to four scenarios |
| 49 | Tornado sensitivity and break-even | ✅ | `POST /whatif/sensitivity`, `/whatif/breakeven`: ranks levers by rupee swing; finds the freight move at which two origins cost the same (Australia equals Mozambique at about -36%) |
| 50 | One-click crisis playbooks | ✅ | Red Sea closes, cyclone, port strike, rupee fall, freight spike, need it in two weeks, perfect storm (`PLAYBOOKS`); assumed constants are named in code and returned with every result |
| 51 | Urgent Fixture Desk | ✅ | `UrgentDesk.tsx`, `POST /whatif/urgent`: 60 options (origin x vessel x speed), 2,000-draw arrival simulation, berth-fit and coking-grade filters, walk-away price, timeline vs deadline, 5-second-undo "Fix this vessel" into the ledger |
| 52 | What-if and urgent questions in Ask the Desk | ✅ | Two new intents (17 in total), percentage and day extraction, both gated by `financial:read`; also available by voice |
| 53 | Open Tonnage (ship availability from broker lists) | ✅ | `services/tonnage.py`, `api/tonnage.py`, `Tonnage.tsx`: users upload the CSV or Excel position lists their brokers send; the desk matches ships to a cargo by size (55% to 95% of deadweight), berth fit (the ship's own draft and length, part-laden aware), laycan and ETA, flags stale lists (over a week) and sample data, and feeds the Verdict and the Urgent Desk. Replaces the Newcastle live feed, which was removed because its reuse terms could not be confirmed |
| 54 | Part-laden berth fit | ✅ | `services/compatibility.py`: a ship whose full draft is too deep can still call part-laden; capacity is estimated from draft (light-ship draft assumed 28% of design draft). Reflects Paradip's first Capesize, 152,702 t at 16.5 m on 6 Sept 2026. The Urgent Desk marks such options "part-laden" and checks the cargo still fits |
| 55 | Laytime and demurrage claim calculator | ✅ | `services/laytime.py`, `POST /laytime`, `Laytime.tsx`: allowed laytime, time counted, excepted periods, "once on demurrage always on demurrage", despatch at half rate, every step written out. Tested. Not legal advice |
| 56 | Data Health (administrator) | ✅ | `services/datahealth.py`, `GET /admin/data-health`, `DataHealth.tsx`: freshness, age and status of every series and feed, and the reason an old one is old |
| 57 | Market Pulse (current public-domain data) | ✅ | `scripts/ingest_latest.py`, `services/pulse.py`, `GET /market/pulse`: USDA ocean rate, US BLS deep-sea freight and coal indices, US EIA Brent crude and Federal Reserve rates, all to 2026, with 3- and 12-month changes and percentiles |
| 58 | The Verdict: when to rent, and which ship | ✅ | `services/verdict.py`, `POST /verdict`, `Verdict.tsx`, assistant intent (18 intents). One call: RENT NOW / RENT WITHIN A WEEK / WAIT AND RECHECK / SPLIT INTO TWO PARCELS / CANNOT MEET THE DATE SAFELY, with the ship, act-by date, walk-away price, confidence, the signals that drove it and what would change it. Rule-based decision support (time pressure, Newcastle ship supply, storm season, coal momentum, rupee, port traffic), **not** a trained model; weights are judgement and the page says so |
| 59 | Model proof ("are the models real?") | ✅ | `services/mlproof.py`, `GET /lab/proof/{index}`: refits ARIMA and XGBoost live on ten walk-forward origins with measured timings (about 2 s for 20 fits), SHA-256 fingerprints of the saved deep-model weights, and a map of which results are cached, precomputed or live. Explains why answers arrive quickly |
| 60 | Annual freight programme planner (Finance) | ✅ | `services/insights.py`, `POST /finance/programme`: the year's landed-cost bill for a list of parcels, a P5/P50/P95 budget range from one shared freight draw, the amount to hold at 95%, and the saving from moving volume between origins |
| 61 | Sourcing resilience (Procurement) | ✅ | `POST /sourcing/resilience`: Herfindahl concentration and effective number of suppliers for the coking-coal mix, and the freight-cost effect of losing each origin. The default mix is an illustrative placeholder; enter SAIL's own |
| 62 | Usage and refusal analytics (Administrator) | ✅ | `GET /admin/analytics`: events, active users, denied rate, by role and action, top refusals, per-day counts from the audit log |
| 63 | Laytime claims for port officers | ✅ | The laytime calculator now needs `ports:read`, so Port and Logistics Officers (who hold the statement of facts) can use it, not only Finance |
| 64 | Current dry-bulk freight signal (USDA ocean rate) | ✅ | `scripts/ingest_usda_ocean.py`: the US government's monthly grain ocean rate to 2026, shown in Market Pulse and used as a freight-momentum vote in the Verdict. Tracked the Baltic indices closely in 2012 to 2019 (0.76 and 0.72 monthly-change correlation) |
| 74 | Automatic live data refresh | ✅ | `services/refresh.py`, `core/scheduler.py` (`refresh_loop`), `POST /admin/refresh-data`, `GET /admin/refresh-status`, Data Health panel: on start and every `REFRESH_HOURS` (default 6) it pulls the newest observations of all 9 series from FRED and the USDA report, adds only newer rows, and isolates a failing source. Tested live: 6 s, 25 new rows. "Live" means as fresh as each publisher: daily for Brent and exchange rates, monthly for the BLS and USDA series |
| 75 | Calibrated forecast bands | ✅ | `ml/intervals.py`, `scripts/eval_intervals.py`, `GET /lab/interval-calibration`, Model Lab card: walk-forward test over 144 past months showed ARIMA's own 95% band covers 98 to 100% of outcomes (too wide). The band now used is the quantile of actual 5-year moves: 95% target measured at 97%, 93%, 94% for 1, 3, 6 months with about half the width ($14.5 vs $22.4, $27 vs $52, $40 vs $78). Honest limit: coverage was measured on the same history it was tuned on (window choice), so treat it as approximately calibrated |
| 76 | Market-linked freight cost | ✅ | `services/recommendation.py::market_factor`: the $2.5/t/1000 nm rule of thumb is scaled by the live USDA ocean rate against its five-year median (bounded 0.6 to 1.6; 1.26 in Sept 2026), in the Recommendation, What-If, Urgent Desk, Verdict, Risk Lab, Voyage modal and Ledger benchmark (which uses the market at each fixture's own date). Costs are still illustrative, not quotes |
| 78 | Live USD to INR rate and converter | ✅ | `services/fx.py`, `GET /fx/rate`, `GET /fx/convert`, `FxBar.tsx` (bottom bar on every page): the latest ECB reference rate with its date and source, a 30-day trend, a two-way converter (₹ and crore), and the stored Federal Reserve rate the cost model uses, side by side. Falls back to the stored rate, labelled, if the live source is down |
| 77 | COA-versus-spot fixture spacing (fix) | ✅ | `services/financial.py::simulate_coa_vs_spot`: after the data moved to monthly, a 30-day interval was counted as 30 monthly steps, placing six fixtures in 2029 to 2041 and inflating the spread (about $951,000 instead of about $174,000). The interval now converts to months (30 days = 1 month), volatility is per month, and the rationale says months. Guarded by `tests/test_coa.py`. Found while preparing the submission documents |
| 65 | Models retrained on current data | ✅ | `scripts/train_current.py`, `train_current_dl.py`, `services/current.py`, `GET /lab/current`: rate forecasts with walk-forward tests. The Baltic nowcast was removed with the Baltic data |
| 66 | Sourcing allocation optimiser | ✅ | `services/optimiser.py`, `POST /sourcing/optimise`, `Optimiser.tsx`: a linear program (HiGHS) picks origin, port and plant for each tonne to minimise sea + port + rail cost within plant demand, port capacity and origin-share caps, and returns **shadow prices** (what one more kt of a port's capacity or an origin's cap is worth). Under assumed inputs it saves about 3% (₹11 crore a month) against the fixed current mix. Cost-only: coal quality and price differences are not modelled; every input is an assumption to replace |
| 67 | Live port weather | ✅ | `services/weather.py`, `GET /weather/ports`, `PortWeather.tsx` (Port signals, "Live port weather"): Open-Meteo wind, rain and wave height for the next five days at each discharge port, with a simple working-risk rule (gusts 40/55 km/h, waves 1.5/2.5 m, limits returned with the answer). Reinstated for this non-commercial prototype; attribution on the page; a port officer sees only assigned ports; a failed marine call still returns wind and rain |
| 68 | Verdict track record | ✅ | `services/verdict_eval.py`, `GET /verdict/evidence`, also inside every verdict: momentum tested on the USDA ocean rate (borderline edge, p = 0.04) and on Brent crude (none), so the signal carries a modest weight |
| 69 | Hugging Face embeddings in the assistant | ✅ | `app/ml/embed.py`: BAAI/bge-small-en-v1.5 (MIT), run locally through fastembed, averaged with the TF-IDF model. Intent accuracy 73.5% to 86.9% (15 held-out folds, p = 0.0007). Falls back to TF-IDF automatically; `INTENT_EMBEDDINGS=0` switches it off |
| 70 | Cross-checked feature honesty | ✅ | Every new feature ships with its limits: assumptions returned in the response, and negative results (GRU, deep-sea PPI, Capesize nowcast, momentum) kept in the documentation |
| 71 | Loading-terminal constraints | ✅ | `scripts/seed_origin_constraints.py`: published draft (and length or beam where available) for Hay Point / Dalrymple Bay, Hampton Roads, Nacala, Vostochny and Balikpapan, with sources; the Urgent Desk, Verdict and recommendation now require the ship to fit where it loads as well as where it discharges (a Capesize cannot load at Balikpapan; at Nacala it loads part-laden) |
| 72 | Real port map | ✅ | `PortMap.tsx`: Natural Earth coastline and 331 real ports (public domain, drawn directly, no map tiles); amber rings show ships from uploaded broker lists; simulated vessels and queues are off unless `SHOW_SIMULATED_FEEDS` is set |
| 73 | Broker email paste-in | ✅ | `POST /tonnage/parse-text`, `Tonnage.tsx`: paste position text, review the ships it read, save; unreadable lines are reported, never guessed |

**Running total: 56 done, 1 partial, 0 not started** (of 57) at the last full recount, plus rows 74 to 78 added afterwards (live refresh, calibrated bands, market-linked cost, the COA spacing fix, live USD to INR rate), all done, and row 67 reinstated as live port weather. Backend tests: 73 passing, 1 skipped. The one partial item is #14: in-app and webhook alerts work, but WhatsApp/SMS delivery needs a messaging-provider account. There is also an ROI calculator (live in `Financial.tsx`) from the original 20-feature plan that isn't separately numbered here.

## A. Baseline features (10) — expected of any serious attempt at this problem

These need to exist and work well, but they don't win the hackathon on their own.

1. Freight rate forecasting from historical BDI/sub-index data (some model, some horizon)
2. A dashboard showing forecast charts over time
3. Basic vessel class reference data (Handysize/Supramax/Panamax/Capesize specs)
4. A simple recommendation of "which vessel class fits this cargo size"
5. Historical freight-rate data visualization (charts, trend lines)
6. A REST API serving the model's predictions
7. User authentication / login
8. A form to input cargo details, origin, destination
9. Basic filtering/search over historical data
10. A results/output page presenting the recommendation

## B. Differentiating features (10+) — the actual competitive edge

Each of these maps to a specific gap our own research found in the literature
and in competing tools (Veson Nautical, Xeneta, Signal Ocean, Windward, and the
two public GitHub attempts at this exact problem statement) — see
`SIH2026_Research_and_References.docx`, Sections 5–6.

1. **Port–Vessel Compatibility Engine** — hard-constraint rules engine built from our own real draft/LOA/beam/tidal data for all 7 East Coast ports (Paradip, Vizag, Gangavaram, Dhamra, Gopalpur, Sagar/Sandheads, Haldia). No competitor or reviewed paper integrates this into the forecast itself.
2. **Tidal-cycle-aware partial-load optimizer** for Haldia/Sagar-Sandheads — models multi-tide loading, computes optimal parcel splits.
3. **Multi-horizon ensemble forecasting** (7/30/90-day) with automatic model selection via walk-forward backtesting, rather than one fixed model.
4. **SHAP-based explainability panel** — shows *why* a recommendation was made, not just the number.
5. **Multi-origin comparative routing** — ranks Australia/US/Mozambique/Russia/Indonesia simultaneously for one cargo requirement, instead of a single-route point forecast.
6. **Disruption/Risk Early-Warning composite score** — structured ingestion mapped to our four documented case studies (Red Sea, Panama Canal, Queensland cyclones, Russia sanctions).
7. **COA-vs-Spot Simulator** — backtests locking in a medium-term Contract of Affreightment vs. staying spot, directly answering the problem statement's stated Objective.
8. **Idle-time/ballast-leg minimizer** — suggests next-fixture timing to reduce ballast days, based on the AIS-derived research finding that pre-arranged fixtures reduce idle time.
9. **Demurrage risk estimator** — converts port-specific congestion data into an expected ₹/$ demurrage exposure per fixture.
10. **Historical fixture ledger & benchmarking** — lets the organisation import its own past charters and compares them against the model's counterfactual recommendation at the time — literally the "yardstick" our research found doesn't exist anywhere publicly.
11. **"Ask the Freight Desk" NL query assistant** — narrow, domain-specific question answering over our own model outputs and research, not a generic chatbot.
12. **Scenario/stress-testing sandbox** — "what if BDI spikes 50%" / "what if Paradip closes 3 days" with live recommendation recomputation.

## C. Round 2 — India-specific differentiators (added after competitor re-scan)

Researched specifically to answer: with ~300 teams on this exact problem
statement, what would a generic "BDI forecaster + vessel recommender" team
almost certainly *not* think of? These lean on things a purely technical team
without shipping-industry or Indian-logistics context would miss.

**Build first (cheapest to build, highest visual/story impact):**

13. **Monsoon/cyclone-adjusted ETA & laycan risk engine** — shifts predicted port dwell/ETA windows for Paradip/Vizag/Gangavaram using the Bay of Bengal cyclone season calendar (Jun–Sep SW monsoon, Oct–Dec NE monsoon/cyclone peak) and IMD's public historical cyclone-closure data. A rule-based ETA-variance multiplier keyed to month + port is enough — no live satellite feed needed. Single strongest "we understand Indian geography, not just generic shipping" signal available.
14. **WhatsApp/SMS disruption alerts** — pushes port congestion/demurrage-threshold/ETA-change alerts via Twilio's free WhatsApp sandbox. Directly reflects how Indian logistics managers actually work (WhatsApp, not dashboards) — high "field awareness" signal to judges, and live-demoable in front of them for strong wow-factor per unit of build effort.
15. **CII/carbon emissions estimator per voyage** — flags vessels likely to be penalized under IMO's live Carbon Intensity Indicator rating using a static g-CO2/tonne-mile-by-vessel-class table (pure arithmetic, no external API), letting the recommender optionally weight "lowest cost" vs. "lowest carbon" routing. Taps a real, current regulatory theme generic cost-only tools ignore.

**Build if time allows:**

16. **INR/USD hedging cost overlay** — since freight is quoted in USD but Indian budgets are in INR, overlay a simple forward-rate hedge-cost estimate onto the COA-vs-Spot simulator (RBI reference rate + configurable hedge premium %). Reframes freight as a treasury problem, not just a shipping problem.
17. **Rail-sea-rail coastal modal-shift recommender** — using our own port rail-linkage research, recommends discharging at a different port and moving cargo inland via rail when that beats direct berthing, using public Indian Railways freight tariff slabs. Plugs directly into the PM Gati Shakti multi-modal logistics narrative — strong "future potential / govt alignment" score.
18. **Hash-chained fixture ledger ("blockchain-style" audit trail)** — not real blockchain: each COA fixture entry hashes the previous one (SHA-256 chain) with a "verify integrity" check, framed as a tamper-proof audit trail for demurrage/laytime disputes (a real, common chartering pain point). Lets us credibly namedrop tamper-evident record-keeping for ~1 hour of implementation.
19. **AIS-lite vessel congestion heatmap** — a live (or clearly-labeled simulated) map of vessels queued at each East Coast port, turning the abstract Route Risk Score into something visibly moving on a map. High UX/wow value even as a simulated demo.
20. **"Explain like a broker" auto-briefing narrative** — beyond Q&A (#11), auto-generates a 3–4 sentence plain-English recommendation narrative combining forecast + SHAP + risk score into one always-on briefing card, rather than requiring the user to ask a question. Demonstrates synthesis across the whole pipeline at a glance.

## D. Round 3 — added after reviewing 3 academic papers (Sept 2026)

Three papers were reviewed directly (not secondhand search snippets): Baghel
(2025, NCI MSc thesis) on hybrid ARIMA+XGBoost+LSTM cargo forecasting at major
and non-major Indian ports; Sahu & Patil (2017, *Journal of Maritime Research*)
on regression vs. SARIMA cargo demand estimation at 12 major Indian ports
including Paradip; and an arXiv 2025 paper on Naive/ARIMA/Prophet/LSTM for
empty container availability forecasting. Two new features and one important
architecture decision came directly out of this reading.

21. **Macroeconomic Cargo Demand Estimator** — a companion regression module (GDP, GDP², coal production, steel production, crude oil/cement/fertilizer production as explanatory variables) estimating *demand* (tonnes) for coal at Indian ports, alongside our existing freight-*rate* ($/tonne) forecasting. Directly modelled on Sahu & Patil (2017), who found GDP and coal production together explain up to 87% of quarterly cargo-volume variance at Indian ports (R²=0.873 at Visakhapatnam) and that Paradip specifically grew 220% between 2002-03 and 2015-16 — the second-highest growth of any major Indian port. No competing tool we found forecasts demand and rate together; this pairs a price signal with a volume signal, which is what an actual chartering desk needs to size a fixture, not just time it.
22. **Berth Slot Availability Forecaster** — extends the Port–Vessel Compatibility Engine (#1) with a time dimension: rather than a static yes/no on whether a vessel class fits a port, forecast the *near-term windows* when a berth is actually likely to be free, adapted from the "Vehicle Booking System" slot-forecasting concept in the arXiv empty-container paper. Turns a static constraint table into a predictive scheduling aid.

**Architecture decision this reading validated** (see `SECTIONS.md` Section 5): Baghel's thesis found LSTM badly overfits on small monthly cargo samples (their data had only ~6-12 points per validation fold) and had to be dropped from the final hybrid, while an ARIMA+XGBoost ensemble with inverse-RMSE weighting was statistically proven better than either alone (Wilcoxon signed-rank test, p=0.016 vs. ARIMA). The arXiv paper separately found Prophet underperformed even a naive last-value baseline on real terminal data. Since our own dataset is daily (8,745 rows) rather than the ~100-160 monthly points these papers worked with, LSTM is more viable for us — but the validated, defensible core to build and cite first is the same ARIMA+XGBoost ensemble, backed by the same Wilcoxon significance test, with LSTM/Transformer added afterward as a secondary model rather than the primary one.

## E. Round 4 — added after reviewing 2 more papers directly (Sept 2026)

Kim, Kim & Choi (2025, *PLOS ONE*) — the SHAP/BDI paper we'd previously only
seen secondhand — was read in full, plus a new paper: Su, Bae & Park (2025,
*Frontiers in Marine Science*) on port congestion and container freight rate
dynamics using an RBF neural network.

**Concrete, evidence-backed change to the Section 6 model itself (not just a
new feature):** Kim et al. tested 10 models on BDI and found, via SHAP across
*every* model, that the **S&P 500 is the single strongest predictor of BDI**
— stronger than any shipping-specific variable — followed by the US Dollar
Index (DXY, negative correlation), then iron ore and coal prices (which
together account for ~50-53% of global dry bulk commodity volume); volatility
indices (VIX etc.) had negligible impact. We're acting on this directly: two
new real datasets were ingested from FRED (Federal Reserve, free, no API key)
— the S&P 500 daily close and the Trade-Weighted US Dollar Index
(DTWEXBGS, an official/arguably more rigorous DXY equivalent) — to use as
engineered features in the Section 6 XGBoost model alongside the coal prices
already ingested in Section 3. This is a literature-directed feature choice,
not a guess. Kim et al.'s own "future work" section explicitly names cargo
volume, weather, real-time AIS/satellite data, and IMO emissions policy as
things *they* didn't incorporate — all four map directly onto features we
already planned (#21 demand estimator, #1/#13 weather-adjusted ETA, #19
AIS-lite heatmap, #15 CII/carbon estimator), which is worth stating plainly in
the pitch: an independently-published paper's stated limitations are exactly
our differentiators.

23. **Cross-Port Congestion Transfer / Rerouting Signal** — Su, Bae & Park (2025) found a measurable **"transfer effect"**: congestion at one container port propagates to a correlated port/route with a ~14-day lag (confirmed via both time-lag cross-correlation and Granger causality, F=1.90, p<0.05 at lag 14), and some port pairs instead show a *substitution* effect (e.g. Shanghai vs. Busan congestion correlated at -0.08 to -0.16 — cargo reroutes away rather than queueing). Adapted to our context: model whether congestion building at one East Coast port (e.g. Paradip) is likely to (a) propagate to Vizag/Gangavaram with a lag, signalling "the same disruption is coming," or (b) trigger substitution, signalling "reroute here instead." This turns our existing single-port Route Risk Score (#6) into a network-aware one — a capability no competitor tool we reviewed has, and a genuinely novel adaptation since no prior work applies this specific transfer-effect method to Indian dry bulk ports.

## F. Round 5 — carried forward from the approved build plan (not yet listed here explicitly)

These were part of the original 20-feature plan approved before Section 1 began, but hadn't been folded into this consolidated list yet. Listed now so the feature count reflects everything actually committed to, not just the post-research additions.

24. **Model Trust / Backtest Transparency Dashboard** — surfaces the walk-forward backtest results (per-split RMSE/MAE/MAPE, the Wilcoxon significance test, ensemble weights) directly in the UI rather than only in API responses or docs — see `MODELS.md` for the actual numbers this will display. Most competing teams will show a single accuracy number, if any; showing the full backtest — including where the model *didn't* reach statistical significance (e.g. our own honest BCI result) — is a credibility signal judges rarely see.
25. **Automated Retraining Pipeline with Drift Detection** — scheduled re-fitting as new freight-rate data arrives, with a monitoring view flagging when live model error exceeds its backtested range (a sign the market regime has shifted, e.g. a disruption event). Demonstrates MLOps maturity beyond "trained a model once."
26. **Multi-Objective Pareto-Ranked Recommendations** — presents chartering recommendations as a small top-3 comparison across cost, time, and risk simultaneously rather than one single "best" answer, since real chartering decisions trade these off against each other.
27. **Configurable Alerting** — webhook/email-style notifications for "market entry window open," "port congestion threshold crossed," or "backtest error exceeded" events, so the tool pushes information out rather than requiring the user to keep checking a dashboard.

Full rationale for each, and the underlying research citation, is in the
approved plan file and the research compendium. See `SECTIONS.md` for what's
actually been built so far.

## G. Round 6 — decide-fast tools and interface rebuild

Also delivered (not counted as features): landing page rebuilt with React Bits components (ParticleText headline, BorderGlow cards, role Carousel, GlideSelect dropdowns, FuseButton with undo, LatticeLoader for every loading and "thinking" state, Ripple for the microphone), and a much richer Haldia scene (sky and clouds, foam wakes, tug, smoke, birds, buoys, a camera that follows the ship). `DEMO_GUIDE.md` lists ready-made inputs with the expected numbers.

## H. Round 7 — problems each persona faces, and what answers them

| Persona | Problem | Answered by | Still open |
|---|---|---|---|
| Administrator | Cannot tell whether the data behind a recommendation is current; users and access need governing | Data Health (#56), usage and refusal analytics (#62), Access & Audit | none |
| Finance & Treasury | Cost surprises: demurrage claims, rupee and freight moves | Annual programme planner (#60), laytime calculator (#55), What-If Studio, hedge overlay, cost at risk | Actual-versus-budget tracking against ledger entries |
| Procurement Manager | Is any ship actually available for this laycan, and will it fit the berth? What is the cheapest mix of origin, port and plant? | The Verdict (#58), sourcing optimiser (#66), Ship Supply Radar (#53), Urgent Desk, part-laden fit (#54), sourcing resilience (#61) | Named-vessel matching by size (needs a licensed fleet register); Hay Point and Richards Bay feeds |
| Chartering Analyst | Market context that is current, not 2019 | Market Pulse (#57), Forecast, Model Lab, model proof (#59) | A licensed live Baltic feed (Supramax and Panamax now have a validated nowcast; Capesize does not) |
| Port & Logistics Officer | Berth and queue risk for their own port | Port Signals, berth-slot forecast, cyclone risk, laytime claims (#63), port scoping | Berth-allocation planner (no berth counts are public); weather window (#67) covers the next seven days |
| Viewer | Public market context | Markets, Market Pulse | none |

Ship availability is the weakest link and is stated plainly: real public feeds name the ships arriving at Newcastle but give no size or
charter status; Indian port line-ups (Paradip, Visakhapatnam) are published as PDFs or scanned pages with no stable machine-readable
address, and Haldia's daily reports are already parsed. A licensed fleet register or AIS feed would close this gap.

## I. Round 8 — licence purge (Sept 2026)

Decision: **only public-domain data**, fetched free with no accounts, keys or credits. Removed: the Baltic indices (a proprietary index; the research copy's CC BY label cannot grant rights the uploader did not hold), IMF PortWatch (IMF terms), SMP Kolkata reports (no licence stated), World Bank coal (CC BY), IMF iron ore, Open-Meteo weather (CC BY, non-commercial), the Newcastle ship feed (terms unconfirmed) and the S&P 500 series. Kept: USDA AMS ocean rates, US BLS price indices, US EIA Brent, Federal Reserve rates and dollar index, NOAA IBTrACS, Natural Earth, and facts quoted from SAIL's annual report, the CAG audit and the Ministry of Ports.

What changed for users:
- Forecasting now runs on the USDA monthly ocean rate (a dry-bulk proxy, not a coal rate); horizons are in months.
- Ship availability comes from broker lists users upload (Open Tonnage), not from a scraped feed.
- Removed features: berth-slot forecast, congestion transfer, chokepoint traffic, Haldia real-vessel statistics, the Baltic deep-learning study and Baltic nowcast. (The weather planner was later reinstated as Live port weather, row 67.)
- Re-based: forecast and ensemble, model lab, monitor (on Brent), risk lab, cost at risk, terrain, live desk, ledger benchmark, verdict, briefing, assistant.
