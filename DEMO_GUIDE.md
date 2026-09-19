# Demo guide: what each feature does, and the exact inputs to show it

Every number below was produced by the running system with the inputs shown, so you can read them out. Costs are
illustrative estimates (distance-based, not quotes), and the freight indices end in July 2019; say so once, early.

**Before you start:** backend on port 8000, frontend on 5173, demo accounts seeded (`python scripts/seed_demo_users.py`).
Sign in with one click on the sign-in page. Use **Chrome or Edge** if you want voice. Press **Ctrl/Cmd + K** anywhere to jump to a page.

---

## 1. The landing page (30 seconds)

**What it does:** shows the problem physically. A real-layout 3D scene of Haldia Dock Complex loops through the five stages a coal ship goes through: anchorage and lightering at Sagar, the river, the lock, berth 4A, rail. The camera follows the ship. The numbers underneath are real.

**Show:**
- Move the mouse over the big headline: the particles scatter and re-form.
- Watch the scene: tug boat leading the ship, gates opening, grabs working, a train leaving.
- Point at the four stat cards: **94** coal vessels, **33,000 t** median cargo, **8.2 m** median draft, **59** bound for SAIL (parsed from the port trust's public daily reports).

**Say:** "The port, not the market, sets the parcel size at Haldia. That is why generic freight tools don't fit."

---

## 2. Urgent Fixture Desk (the last-minute call) — sign in as **Procurement Manager**

**What it does:** given a port, tonnes and a deadline, it costs every origin × vessel class × speed (60 options), simulates 2,000 arrivals per option (real average port turnaround plus cyclone delay), and tells you what arrives in time, how likely it is, the cost, and the most you should pay ("walk-away price"). Options that do not fit the berth, or whose origin ships mostly thermal coal, are listed but never recommended.

| Try this input | Port | Tonnes | Deadline | You will see |
|---|---|---|---|---|
| A. Comfortable | Paradip | 60,000 | 20 days | **12 of 60** options safe. Best: **Panamax from Mozambique at 12 kn**, 15.3 days, 100% on time, **₹5.155 crore**, walk away above **$8.4/t** |
| B. Tight | Paradip | 60,000 | 14 days | **0 of 60** safe. Fastest: Panamax from Mozambique at 14 kn, 13.8 days, **49% on time**: the banner turns red |
| C. Impossible | Haldia | 60,000 | 12 days | **0 of 60**. Fastest 16.9 days, 0% on time. "Consider a partial cargo, stock from another source, or a later date" |
| D. Big cargo | Visakhapatnam | 75,000 | 30 days | 24 of 60 safe. Best: **Capesize from Mozambique**, 16.3 days, ₹4.861 crore |

**Do this live:** start with A, then drag the **Deadline** slider from 20 down to 14 and watch the banner flip from green to red. Then press **Fix this vessel** (Procurement or Finance): a fuse burns around the button for 5 seconds; press **Undo** to cancel, or let it finish and the fixture is written to the Fixture Ledger.

**Say:** "This is the 6 pm call: the plant is short. In seconds we know what can physically arrive, how sure we are, and where to stop negotiating."

---

## 3. What-If Studio — sign in as **Finance & Treasury**

**What it does:** one landed-cost model with eight levers (freight, rupee, fuel, port delay, storm delay, reroute distance, speed, urgency premium). Results update as you drag. It shows a cost breakdown, a **tornado chart** ranking which lever matters most, lets you **save up to four scenarios** to compare, and has one-click **crisis playbooks**.

Base case (Australia → Haldia, 75,000 t, Panamax, everything at zero): **₹9.758 crore, 25.5 days**.

| Click this playbook | Landed cost | vs base | Trip |
|---|---|---|---|
| Red Sea closes | ₹18.252 crore | **+87.0%** | 37.6 days (+12.1) |
| Cyclone off the coast | ₹10.357 crore | +6.1% | 31.5 days (+6.0), demurrage $62,670 |
| Port strike (5-day delay) | ₹10.247 crore | +5.0% | 30.5 days (+5.0), demurrage $51,170 |
| Rupee falls 6% | ₹10.344 crore | +6.0% | unchanged |
| Freight spikes 30% | ₹12.284 crore | +25.9% | unchanged |
| Need it in two weeks | ₹11.461 crore | +17.5% | 23.7 days (−1.8) |
| Perfect storm | ₹21.493 crore | **+120.3%** | 40.6 days (+15.1) |

**The tornado (base case):** the biggest bars are **Reroute (Red Sea)** (swing ₹6.27 crore), **Freight rate** (₹4.21 crore), **Speed** (₹1.96 crore), **Fuel price** (₹1.77 crore). Say: "A Red Sea closure hurts more than a 25% freight swing."

**Do this live:** click *Red Sea closes* → **Save this scenario**; click *Reset*; click *Perfect storm* → **Save**; now the comparison table shows base-vs-crisis side by side. Then change **Origin** to Mozambique with the GlideSelect dropdown and watch the cost fall.

**Break-even fact for questions:** Australia costs the same as Mozambique only if Australian freight were about **36% cheaper**.

---

## 4. Ask the Desk: chat, voice, and role-aware answers

**What it does:** a local intent model (75% ± 6% accuracy on held-out questions, 17 intents) routes plain English to the engines. It answers with the figures used, states its assumptions, and **refuses anything the signed-in role may not see**, logging the refusal.

**Type or say these as Finance & Treasury:**

| Ask | Answer you will get |
|---|---|
| What if freight rises 30%? | ₹9.758 crore → **₹12.284 crore (+25.9%)**, trip length unchanged |
| What if the Red Sea closes? | ₹9.758 → **₹18.252 crore (+87.0%)**, **+12.1 days** |
| What if the rupee falls 6% for Australia to Paradip? | ₹8.42 → **₹8.926 crore (+6.0%)** |
| We need 60000 t at Paradip within 20 days | Panamax from Mozambique at 12 kn, 15.3 days, 100% on time, ₹5.155 crore, walk away above $8.4/t |
| How risky is Australia to Haldia? | **6.8/10, high**; biggest driver disruption exposure (Red Sea / Suez rerouting) |
| Show my fixtures | **6 fixtures**, every entry in the ledger |

**Voice:** press the microphone, say "What if freight rises thirty percent", and switch the speaker on to hear the answer. Say **"open the port map"** to navigate by voice. (Chrome and Edge send audio to their own speech service: mention that.)

---

## 5. The role switch: the moment that shows the access control

Open a second (private) window and click these demo accounts, asking the **same** question:

| Account | Ask | Result |
|---|---|---|
| **Port Officer, Haldia** | Should we use a COA or stay spot? | **Refused**: role lacks COA vs spot. Logged. |
| Port Officer, Haldia | How risky is Australia to Paradip? | **Refused**: "Paradip is outside the ports assigned to your account (Haldia)". |
| Port Officer, Haldia | How much coking coal does SAIL import? | **Refused**: no access to volumes. |
| **Chartering Analyst** | Should we use a COA or stay spot? | **Refused** (no financial data). |
| Chartering Analyst | Show my fixtures | **2 fixtures**, "only the ones you created". |
| Finance & Treasury | Show my fixtures | **6 fixtures**, "every entry". |
| **Administrator** | How many users have accounts? | Counts by role, plus the number of denied requests. |

Also try typing `/app/financial` into the address bar as the Port Officer: a "This page is outside your access" screen appears. The sidebar is short for low roles and long for high ones.

**Say:** "Same database, same question, different answers. The restriction is applied inside the query, not by hiding buttons, and every refusal is in the audit log." Then, as **Administrator**, open **Access & Audit**, filter to **Denied only**, and show the refusals you just caused.

---

## 6. Forecasting and the honest model comparison

**Freight Forecast:** choose **BPI** (Panamax index), 14 days, press *Run ensemble* (about 20 to 30 seconds the first time, then cached). Shows a 95% band, per-split backtest, SHAP drivers and two significance tests.
- ARIMA + XGBoost hybrid vs ARIMA: **p = 0.0019** (significant). Hybrid MAE **29.0** vs ARIMA **31.9**.

**Model Lab** (deep learning): LSTM, GRU, TCN and Transformer on the same 35 forecasts.
- **Deep ensemble MAE 25.8** (lowest), GRU 26.0, Transformer 26.7, LSTM 26.8, hybrid 29.0, XGBoost 31.6, ARIMA 31.9, **TCN 37.6** (worst).
- The deep ensemble is **not significantly** better than ARIMA (**p = 0.17**). Say it before anyone asks.
- Weather test on the same page: adding wind, rain and waves did **not** improve port-call forecasts (**p = 0.88**).

---

## 7. The three.js views

| Page | What it shows | Try |
|---|---|---|
| **Trade Globe** | Sea lanes from five origins and chokepoint traffic vs the pre-October-2023 level | Click **Bab el-Mandeb**: **56%** of its old traffic; Suez **61%**; the Red Sea note explains ships are still diverting |
| **Risk Lab → 3D forecast fan** | 400 simulated futures for the index in depth, with a 5–95% ribbon | Drag to orbit; set horizon to 60 days: 5% **1,295**, median **1,990**, 95% **3,097** (from a starting 1,891) |
| **Risk Lab → Cost at risk** (Finance) | 5,000 simulated landed costs for one cargo | Australia → Haldia, 75,000 t, Panamax: median **₹8.62 crore**, 95th percentile **₹12.44 crore**, cost at risk **₹3.82 crore**; 36% chance of demurrage. Freight is ~99.8% of the variance |
| **Market Terrain** | Eight series over seven years as a 3D landscape | Hover to read values; the four freight indices rise and fall together |

---

## 8. Port signals and the Haldia planner

**Port Signals** tabs (any role with ports; the Haldia officer sees only Haldia):
- **Cyclone ETA risk:** Haldia, laycan 20 Oct to 5 Nov, 20 sailing days → about a **20% chance** of a storm in the arrival window (a "Moderate" risk).
- **Timing coach:** Haldia from Australia: a 60-day calendar of storm risk per loading date, with the five calmest starts.
- **Haldia lightering:** drag cargo to **150,000 t**: the practical Haldia ceiling is about **35,000 t** (95th percentile of real vessels), so about **115,000 t** is lightened at Sagar. The fit of cargo against draft is weak (R² 0.10) and the page says so.
- **Congestion transfer:** one port pair survives multiple-testing correction: **Haldia leads Visakhapatnam by about 6 days**.

---

## 9. Voyage economics, ledger, alerts, monitor

- **Voyage Economics → Carbon:** Panamax, 6,000 nm, 12 kn: **3,742 t CO₂**, rating **C** for 2026; at 10 kn it improves to **A**, at 13 kn it falls to **E**.
- **Voyage Economics → INR/USD hedge:** ₹95.55 per dollar; a 25% hedge on a $5 million bill costs about ₹13 lakh and removes about ₹65 lakh from the 95% worst case; above 25% it warns that SAIL's annual report caps hedging at 25%.
- **Fixture Ledger:** hash-chained. As **Finance**: "Chain verified: 6 entries intact". (To show tamper detection you would need database access: mention that editing any old entry breaks the chain at that entry, covered by a unit test.)
- **Alerts:** create a *port congestion* rule for Visakhapatnam at threshold **7**, press **Check now**: it fires ("congestion 10.0/10").
- **Model Monitor (BPI):** status "Stable" (error ratio 1.09, return PSI 0.22).
- **Board Pack:** prints a one-page briefing limited to what the role may see.

---

## 10. Quick answers to likely questions

- **Is the data live?** Real history replayed. The Baltic freight indices end in **July 2019** (the live feed is paid); the Live Desk's minute ticks are **simulated** and labelled so.
- **Are costs real quotes?** No, illustrative distance-based estimates.
- **Where is the Baltic Dry Index?** Removed: no freely licensed daily source exists.
- **Does the chatbot use ChatGPT?** No. A local model chooses an engine; nothing leaves the deployment.
- **Can someone give themselves admin?** No. New accounts are Viewers; only an administrator assigns roles.
- **Why is the deep-learning result "not significant"?** About 2,500 daily points is little for neural networks; the report says so instead of claiming a win.
