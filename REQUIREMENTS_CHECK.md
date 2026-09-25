# Problem statement check (19 Sept 2026)

Each requirement of the SAIL problem statement, what the platform does about it, and what is still missing. Verified against the running system (about 100 routes, 66 automated backend tests). Last updated 25 Sept 2026.

**Objective: move from many single spot contracts to short or medium-term multi-voyage contracts.**
| | Status |
|---|---|
| COA versus spot for a run of voyages (rate, tonnes per voyage, number of voyages, interval) | Done: `Financial Tools`, `POST /financial/coa-vs-spot`; returns expected saving and a recommendation. Fixture spacing corrected on 25 Sept 2026 (a 30-day interval had been counted as 30 monthly steps) |
| A single "recommended contract length" (spot, 3, 6 or 12 months) | **Partial**: you set the number of voyages and interval and compare; the Verdict does not yet recommend a duration |

**Expected solution**
| Requirement | Status | Notes |
|---|---|---|
| a. Optimal market entry timing | Done, with an honest limit | The Verdict (rent now / within a week / wait / split) from time pressure, open ships, storm season, freight, fuel, coal and rupee momentum. The freight forecast is weak (no model reliably beats "no change") and the Verdict says so |
| b. Vessel type per cargo, origin and port limits | Done | Handysize to Capesize picked per parcel; checked against draft, length, beam and part-laden loading at the **discharge port** (all 7 East Coast ports) and, since today, the **loading terminal** in all five origins (published limits, with sources, in `ports.source`) |
| c. Idle scenario management | **Partial** | Ballast and idle-day ranking of employment options exists; ballast time is approximated from the laden route. No forecast of low-demand periods (the freight forecast is too weak) and no repositioning advice beyond ranking |
| d. Early warnings | Done, with limits | Alerts for route risk, cyclone probability, congestion score, model drift and market moves; disruption events. Congestion uses official average turnaround, not a live queue |
| Dashboard: cargo, origin, destination, contract duration in; forecasts and recommendations out | Done | Verdict, Urgent Desk, What-If Studio, Recommendation, Financial Tools, Sourcing Optimiser; six role views |

**Data the statement asks for**
| Input | Status |
|---|---|
| Historical freight rates for each vessel size and route | **Missing (by decision)**: no free, licence-clean per-size or per-route series exists. One public-domain proxy (USDA grain ocean rate) drives forecasts; per-class and per-route rates come from a cost model that is labelled illustrative |
| Global economic indicators | Done: Federal Reserve rupee, Australian dollar, rand and dollar index |
| Commodity price trends | Partial: US BLS coal price index and EIA Brent crude (public domain); no coking-coal price series is freely licensed |
| Seasonal variations | Partial: cyclone seasonality by port and month (NOAA); freight-rate seasonality is not modelled |
| Real-time port congestion, origin and destination | **Missing (by decision)**: no free feed. Destination congestion uses Ministry of Ports average turnaround (four ports have no official figure and use a default) |
| Destination port limits (LOA, beam, draft, handling rates) | Done for draft, length and beam; **cargo handling rates are an editable assumption** (20,000 t/day default; Haldia berth 4A figure is published), not per-berth data |
| Loading-port limits (Australia, US, Mozambique, Indonesia, Russia) | Done today: draft, and length or beam where published, for Hay Point / Dalrymple Bay, Hampton Roads, Nacala, Vostochny and Balikpapan |
| Ship availability | Done via broker lists (upload CSV or Excel, or paste an email); no free named-ship feed exists |

**Mock or demo data:** none is shown in a deployment by default. Simulated vessels, anchorage queues and minute ticks are behind `SHOW_SIMULATED_FEEDS` (off). Demo accounts, the six sample ledger entries, the sample tonnage list and 20 synthetic vessels are removed by `scripts/prepare_production.py --apply`. Remaining illustrative inputs are labelled in every response: the landed-cost model, demurrage benchmarks, rail distances, Haldia's 35,000 t ceiling, the optimiser's plant demand, port capacity and origin caps, and the Verdict's weights.

**Changes since 19 Sept 2026:** the nine market series now refresh themselves every six hours (row 74 of FEATURES.md), forecast bands are calibrated on 144 past months (row 75), and freight cost estimates follow the live USDA ocean rate against its five-year median (row 76). These improve the freshness and honesty of the inputs; they do not change any status above.
