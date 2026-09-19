# Five-minute demo script

Start both servers first (see GETTING_STARTED.md), open http://localhost:5173, and sign in with any account.
Each step says what to click and the one sentence to say.

1. **Landing (30 s).** "This is Haldia. A coking-coal ship waits at Sandheads, is lightened by a floating crane, sails
   six hours up the Hooghly and passes a 330 by 39 metre lock to berth 4A. The numbers underneath are real: 94 coal
   vessels we parsed from the port trust's daily reports, median cargo 33,000 tonnes."
2. **Overview (30 s).** "The desk briefing is written from the live engines every time it opens, and states where the data ends."
3. **Ask the Desk (60 s).** Click "How risky is Australia to Haldia?", then type "Should we use a COA or stay spot?".
   "A local intent model, 87% accurate on held-out questions, routes each question to the same engines the dashboard uses.
   Nothing is sent to an outside service."
4. **Freight Forecast (60 s).** Open the USDA ocean rate, 3 months, click Run ensemble. "The rate is close to a random walk: the blend is borderline against ARIMA (p = 0.053)
   and no model reliably beats no-change. We show that instead of hiding it." Point at the per-split table and the widening bands under Multi-horizon.
5. **Chartering Recommendation (45 s).** Rank origins, then the trade-off card. "Cost, time and risk together; Pareto-optimal
   origins are marked. It also refuses a vessel that will not fit the berth."
6. **Port Signals (45 s).** Cyclone tab for Haldia in October to November; Congestion transfer. "Storm exposure comes
   from 35 years of tracks. Only one port pair survives multiple-testing correction: Haldia leads Visakhapatnam by about six days."
7. **Voyage Economics (30 s).** Carbon tab: drag the speed from 12 to 10 knots in the sweep. "Slowing down moves a Panamax
   from a C to an A."
8. **Fixture Ledger (30 s).** Load the samples. "Hash-chained: change any old entry and the chain reports exactly where it broke."
9. **Alerts and Model Monitor (30 s).** Create a rule, Check now. "The monitor separates model drift from data drift, and
   retrains on drift."

Questions to expect and honest answers:
- *Is the price feed live?* No. Real public-domain history, current to 2026, replayed; there is no free live freight index, and the pages say so.
- *Are the costs real quotes?* No. They are labelled illustrative distance-based estimates.
- *Where are the real fixtures?* None are public; the ledger takes your own entries.
- *Why is the demand estimate rough?* It rests on two annual data points.
