# Feature List — Baseline vs. Differentiating

62 features (10 baseline + 52 differentiating), split deliberately into two groups: things any competent
competing team (there are ~300 submissions per problem statement, and at least
two public GitHub repos already attempting near-identical ideas) would also
build, and things that are genuinely ours. This split is itself part of the
pitch — it shows the judges we know exactly what's "table stakes" versus what's
the real USP, rather than presenting everything as equally novel.

**Why 16 build sections for 62 features:** the sections in `SECTIONS.md` are
*build phases* (how the system gets implemented), not a 1:1 map to features
(what capabilities exist). Several features are delivered together within one
section because they share the same underlying subsystem — e.g. Section 7
alone delivered features #1 and #2 (compatibility engine + tidal optimizer);
Section 8 delivered #5; Section 9 delivered #6. The table below is the actual
per-feature tracker — updated every session, not just at section boundaries.

## Status tracker (all 62 features)

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
| 10 | Results/output page presenting the recommendation | ✅ | `Recommendation.tsx` ranked results grid |

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
| 22 | Berth Slot Availability Forecaster | ✅ | `Signals.tsx` Berth slots tab: 14-day pressure forecast from real PortWatch calls; best of four models by 12-window backtest (about 0-9% better than naive)
| 23 | Cross-Port Congestion Transfer / Rerouting Signal | ✅ | `Signals.tsx` Congestion transfer tab: Bonferroni-corrected Granger tests across five ports (Haldia leads Visakhapatnam by about 6 days) and a live rerouting signal
| 24 | Model Trust / Backtest Transparency Dashboard | ✅ | Forecast page: backtest metrics, per-split table, model comparison, weights, Wilcoxon tests, SHAP
| 25 | Automated Retraining Pipeline with Drift Detection | ✅ | `Monitor.tsx`: frozen-model error vs the prior year (Mann-Whitney), return-distribution PSI, manual retrain, scheduled retrain on drift, run history. The data is not refreshed automatically, so a retrain reproduces the same fit
| 26 | Multi-Objective Pareto-Ranked Recommendations | ✅ | `ParetoCard.tsx` on Recommendation: cost, transit time and route risk, Pareto-optimal origins marked, adjustable weights
| 27 | Configurable Alerting | ✅ | `Alerts.tsx`: six rule types, in-app feed with unread badge, https webhook (public hosts only), 30-minute background evaluation
| 28 | Role personas (tailored starting point per user type) | ✅ | Backend personas + self-register validation (admin not self-selectable); persona picker at sign-up, persona-specific Overview quick actions and sidebar hints |
| 29 | Regional market boards with live-replay charts | ✅ | `Markets.tsx` — freight, coal, FX and equity series grouped by origin region; regions with no real series (Indonesia, Russia) are shown empty rather than invented |
| 30 | Haldia digital-twin landing scene (three.js) | ✅ | `HaldiaScene.tsx`: anchorage and lightering, river transit, the 330 x 39 m lock with animated gates, berth 4A unloaders, coal pile and rail, with labels and a step caption. Schematic, built from public port-trust figures |
| 31 | Real Haldia coal-vessel ledger from port-trust reports | ✅ | `ingest_haldia_positions.py` parses SMP Kolkata's daily morning-position PDFs into 90+ distinct coal vessels (LOA, draft, cargo, importer); served at `/haldia/summary` and shown on the landing page |
| 32 | Account security: password policy, login lockout, change password, session expiry | ✅ | Backend policy (8+ chars, letter and number), 5-failure 10-minute lockout, `PATCH /auth/me`, `POST /auth/change-password`; frontend strength meter, show/hide, profile page, automatic sign-out on expired token |
| 33 | Role-based access control with per-port and per-row scoping | ✅ | `core/permissions.py`, `require()` on every route; port officers see only assigned ports (filtered in the query), analysts see only their own ledger rows. Roles are assigned by an admin, never chosen at sign-up |
| 34 | One-click demo accounts for every role | ✅ | `scripts/seed_demo_users.py`, `/auth/demo-login` (passwordless, demo-flagged accounts only, switchable off) |
| 35 | Chatbot and voice assistant that answer only within the caller's permissions | ✅ | 15 intents; refusals are explained and logged; ledger/alerts/access/user-admin intents query the database under the user's scope; browser voice input, spoken answers, voice navigation ("open the port map") |
| 36 | Access matrix, user administration and audit log | ✅ | `Access.tsx`, `/admin/*`: role matrix, assign roles and ports, denied-request log |
| 37 | Model Lab: deep learning vs classical models | ✅ | `scripts/train_dl.py` (LSTM, GRU, TCN, Transformer on the same walk-forward splits), NumPy serving, leaderboard, training curves, weather experiment (a reported negative result) |
| 38 | Trade Globe (three.js) and chokepoint monitor | ✅ | `TradeGlobe.tsx`, `/lab/chokepoints`: sea lanes, Suez/Bab el-Mandeb/Malacca/Cape/Lombok traffic against the pre-Oct-2023 level from PortWatch |
| 39 | Risk Lab: 3D forecast fan (three.js) and cost-at-risk Monte Carlo | ✅ | `RiskLab.tsx`: 400 bootstrap paths in 3D; 5,000-draw landed-cost distribution in INR crore with P50/P95 and variance shares |
| 40 | Market Terrain (three.js) | ✅ | `Terrain.tsx`: eight series over seven years as an interactive 3D landscape |
| 41 | Haldia lightering planner | ✅ | `/lab/lightering`: fitted to 87 real Haldia coal vessels; the fit is weak (R² 0.10), so the plan uses the observed 95th-percentile cargo as the ceiling and says so |
| 42 | Laycan timing coach | ✅ | `/lab/timing`: 60-day calendar of storm risk in the arrival week for a port and origin; freight direction is not scored because the indices end in 2019 |
| 43 | Unusual-moves feed | ✅ | `/lab/anomalies` on Markets: series whose latest move is 2 or more standard deviations out |
| 44 | Board pack (print-ready briefing, role-scoped) | ✅ | `Report.tsx` |
| 45 | Command palette (Ctrl/Cmd+K) | ✅ | Jump to any page the role may open, or send the text to the assistant |
| 46 | Fluid interface scaling from phones to 4K projectors | ✅ | rem-based layout, root size 16 px to 1920 px wide then 0.8333vw (32 px at 3840), pixel chart sizes routed through a scale helper, drawer menu below 1024 px |
| 47 | Live Desk: minute-by-minute ticks (simulated) | ✅ | `LiveDesk.tsx`, `/live/seed`: each series' last real trading day replayed as 390 one-minute Brownian-bridge steps with its real volatility; tiles, tape, chart, speed control; labelled SIMULATED everywhere. No free minute-level freight data exists; a real provider (Yahoo keyless or a Twelve Data key) can be added behind the same page if you choose one |
| 48 | What-If Studio (last-minute price scenarios) | ✅ | `WhatIf.tsx`, `services/whatif.py`, `POST /whatif/run`: one landed-cost model with eight levers (freight, rupee, fuel, port delay, storm delay, reroute, speed, urgency premium), live recompute, cost breakdown, save and compare up to four scenarios |
| 49 | Tornado sensitivity and break-even | ✅ | `POST /whatif/sensitivity`, `/whatif/breakeven`: ranks levers by rupee swing; finds the freight move at which two origins cost the same (Australia equals Mozambique at about -36%) |
| 50 | One-click crisis playbooks | ✅ | Red Sea closes, cyclone, port strike, rupee fall, freight spike, need it in two weeks, perfect storm (`PLAYBOOKS`); assumed constants are named in code and returned with every result |
| 51 | Urgent Fixture Desk | ✅ | `UrgentDesk.tsx`, `POST /whatif/urgent`: 60 options (origin x vessel x speed), 2,000-draw arrival simulation, berth-fit and coking-grade filters, walk-away price, timeline vs deadline, 5-second-undo "Fix this vessel" into the ledger |
| 52 | What-if and urgent questions in Ask the Desk | ✅ | Two new intents (17 in total), percentage and day extraction, both gated by `financial:read`; also available by voice |

**Running total: 56 done, 1 partial, 0 not started** (of 57), counted directly from the rows above. The one partial item is #14: in-app and webhook alerts work, but WhatsApp/SMS delivery needs a messaging-provider account. There is also an ROI calculator (live in `Financial.tsx`) from the original 20-feature plan that isn't separately numbered here.

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
