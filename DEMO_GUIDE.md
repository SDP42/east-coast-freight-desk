# Demo guide: what each feature does, and the exact inputs to show it

Every number below was produced by the running system with the inputs shown, so you can read them out. Costs are
illustrative estimates (distance-based, not quotes). The freight signal is the USDA grain ocean rate, a public-domain dry-bulk proxy; say so once, early. Every data source is free and public domain (LICENCES.md).

**Before you start:** backend on port 8000, frontend on 5173, demo accounts seeded (`python scripts/seed_demo_users.py`).
Sign in with one click on the sign-in page. Use **Chrome or Edge** if you want voice. Press **Ctrl/Cmd + K** anywhere to jump to a page.

---

## 1. The landing page (30 seconds)

**What it does:** shows the problem physically. A real-layout 3D scene of Haldia Dock Complex loops through the five stages a coal ship goes through: anchorage and lightering at Sagar, the river, the lock, berth 4A, rail. The camera follows the ship. The numbers underneath are real.

**Show:**
- Move the mouse over the big headline: the particles scatter and re-form.
- Watch the scene: tug boat leading the ship, gates opening, grabs working, a train leaving.
- Point at the four stat cards: **87%** of SAIL's clean coking coal is imported (16.92 of 19.37 MT, FY24), **94%** of imported coal on long-term agreements, **374** demurrage cases in four years (CAG), **69 h** average turnaround at Visakhapatnam vs 45 h at Paradip (Ministry of Ports).

**Say:** "The port, not the market, sets the parcel size at Haldia: about 35,000 t reaches the dock. That is why generic freight tools don't fit."

---

## 2. Urgent Fixture Desk (the last-minute call) — sign in as **Procurement Manager**

**What it does:** given a port, tonnes and a deadline, it costs every origin × vessel class × speed (60 options), simulates 2,000 arrivals per option (real average port turnaround plus cyclone delay), and tells you what arrives in time, how likely it is, the cost, and the most you should pay ("walk-away price"). Options that do not fit the berth, or whose origin ships mostly thermal coal, are listed but never recommended.

| Try this input | Port | Tonnes | Deadline | You will see |
|---|---|---|---|---|
| A. Comfortable | Paradip | 60,000 | 20 days | **8 of 60** options safe. Best: **Panamax from Mozambique at 12 kn**, 15.3 days, 100% on time, **₹5.155 crore**, walk away above **$8.4/t** |
| B. Tight | Paradip | 60,000 | 14 days | **0 of 60** safe. Fastest: Panamax from Mozambique at 14 kn, 13.8 days, **49% on time**: the banner turns red |
| C. Impossible | Haldia | 60,000 | 12 days | **0 of 60**. Fastest 16.9 days, 0% on time. "Consider a partial cargo, stock from another source, or a later date" |
| D. Big cargo | Visakhapatnam | 75,000 | 30 days | 12 of 60 safe. Best: **Capesize from Mozambique**, 16.3 days, ₹4.861 crore |

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

**What it does:** a local intent model (87% ± 4% accuracy on held-out questions, 18 intents; Hugging Face sentence embeddings plus TF-IDF) routes plain English to the engines. It answers with the figures used, states its assumptions, and **refuses anything the signed-in role may not see**, logging the refusal.

**Type or say these as Finance & Treasury:**

| Ask | Answer you will get |
|---|---|
| What if freight rises 30%? | ₹9.758 crore → **₹12.284 crore (+25.9%)**, trip length unchanged |
| What if the Red Sea closes? | ₹9.758 → **₹18.252 crore (+87.0%)**, **+12.1 days** |
| What if the rupee falls 6% for Australia to Paradip? | ₹8.42 → **₹8.926 crore (+6.0%)** |
| We need 60000 t at Paradip within 20 days | Panamax from Mozambique at 12 kn, 15.3 days, 100% on time, ₹5.155 crore, walk away above $8.4/t |
| How risky is Australia to Haldia? | **5.5/10, high**; biggest driver disruption exposure (7.5/10: Red Sea / Suez rerouting) |
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

**Freight Forecast:** choose the Gulf-to-Japan ocean rate, 3 months, press *Run ensemble* (about 10 seconds the first time, then cached). Shows a 95% band, per-split backtest, SHAP drivers and two significance tests. Blend vs ARIMA: p = 0.053, so say "borderline, not proven".

**Model Lab:** the retrained models on the same walk-forward test (about 200 monthly forecasts).
- 1-month MAE: no change **$2.58/t**, ARIMA 2.45, XGBoost 2.50, blend 2.42, Ridge **2.33** (p = 0.016; about 0.06 after correcting for four models). GRU neural network **2.60** (p = 0.38): it does not help.
- At 3 months nothing beats "no change". Say it before anyone asks: "The rate is close to a random walk, and our tests say so."
- The "Proof the models are real" panel refits models live (20 fits in about 2 seconds) and lists saved artifacts with fingerprints.

---

## 7. The three.js views

| Page | What it shows | Try |
|---|---|---|
| **Trade Globe** | Sea lanes from five origins to the East Coast and the chokepoints they pass | Click a chokepoint: location and why it matters. There is no traffic data (licence); the What-If Studio prices a Red Sea closure at **+87%** |
| **Risk Lab → 3D forecast fan** | 400 simulated futures of the ocean rate in depth, with a 5–95% ribbon | Drag to orbit; 12 months: 5% **$46.9/t**, median **$74.2**, 95% **$111.2** (from $72.9) |
| **Risk Lab → Cost at risk** (Finance) | 5,000 simulated landed costs for one cargo | Australia → Haldia, 75,000 t, Panamax: median **₹8.43 crore**, 95th percentile **₹9.34 crore**, cost at risk **₹0.91 crore**; 36% chance of demurrage; freight is about 97% of the variance |
| **Market Terrain** | Eight public series since 2010 as a 3D landscape | Hover to read values |

---

## 8. Port signals

- **Cyclone ETA risk** (NOAA tracks): Haldia, laycan 20 Oct to 5 Nov, 20 sailing days → about a **20% chance** of a storm in the arrival window.
- **Timing coach:** a 60-day calendar of storm risk per loading date with the five calmest starts.
- **Haldia lightering:** drag cargo to **150,000 t**: about **115,000 t** is lightened at Sagar against an assumed 35,000 t ceiling (editable; the page says it is an assumption).
- **Laytime and demurrage** (Port Officers too): 75,000 t at 20,000 t/day, 120 h, 10 h of rain, $20,000/day → **on demurrage, $11,667**, every step shown.

---

## 9. Voyage economics, ledger, alerts, monitor

- **Voyage Economics → Carbon:** Panamax, 6,000 nm, 12 kn: **3,742 t CO₂**, rating **C** for 2026; 10 kn improves it to **A**, 13 kn drops it to **E**.
- **Voyage Economics → INR/USD hedge:** ₹95.55 per dollar (Federal Reserve); above a 25% hedge it warns that SAIL's annual report caps hedging at 25%.
- **Fixture Ledger:** hash-chained. As **Finance**: "Chain verified: 6 entries intact". The benchmark compares each fixture with the USDA ocean rate in its month.
- **Alerts:** create a *route risk* rule (Australia to Haldia, threshold 6) and press **Check now**.
- **Model Monitor** (on daily Brent crude, a fuel proxy): frozen ARIMA against newer data; on the build date it flags **drift** (error ratio 1.46, PSI 0.44), which is what the monitor is for.
- **Board Pack:** prints a one-page briefing limited to what the role may see.

---

## 10. Quick answers to likely questions

- **Is the data live?** Real public data replayed; monthly series lag by weeks. There is no free live freight index. The Live Desk's minute ticks are **simulated** and labelled so.
- **Are costs real quotes?** No, illustrative distance-based estimates.
- **Where are the Baltic indices?** Removed: a proprietary index. We use only public-domain data, so the freight signal is the USDA grain ocean rate.
- **Where does ship availability come from?** From the position lists your brokers send, uploaded by users. There is no free licence-clean source of named ships.
- **Does the chatbot use ChatGPT?** No. A local model with Hugging Face sentence embeddings chooses an engine; nothing leaves the deployment.
- **Can someone give themselves admin?** No. New accounts are Viewers; only an administrator assigns roles.
- **Why is the deep-learning result "not significant"?** About 300 monthly points is too few for a neural network, and the series is close to a random walk.

---

## 11. The verdict: one answer for people who will not read the charts

Sign in as **Finance & Treasury** or **Procurement Manager**, open **The Verdict**. It reads current public data and any broker lists, so the call can change day to day; these are the results on the build date with no broker list uploaded.

| Set | You will see |
|---|---|
| Paradip, 60,000 t, needed within 20 days | **RENT NOW** (High): Panamax from Mozambique at 12 knots, about 15 days, ₹5.16 crore |
| Paradip, 60,000 t, needed within 45 days | **RENT WITHIN A WEEK**: the same ship, ₹4.47 crore |
| Haldia, 60,000 t, needed within 12 days | **CANNOT MEET THE DATE SAFELY**: fastest Panamax is about 17 days |
| Paradip, 150,000 t, needed within 40 days | **SPLIT INTO TWO PARCELS**: no single ship can carry it into Paradip |

Say: "Every bar is a reason. It is rule-based decision support, not a black box." Under it: the track record of the momentum signal (borderline in USDA rates, none in Brent). Ask in words: "Should we rent a ship now or wait for Paradip?"

## 12. Open tonnage: ship availability

Open **Open Tonnage**, press **Load a sample list** (ten invented ships, clearly labelled), then set Paradip, 60,000 t, 30 days: **5 of 10** listed ships could carry it in time; the others fail for stated reasons (too small, too big, arrives after the deadline). Then **Upload broker list** with a real CSV or Excel file. The Verdict and the Urgent Desk read the same lists. Say: "No free source of named ships is licence-clean, so we use what your brokers already send you." Lists older than a week are flagged.

## 13. Sourcing optimiser (Procurement or Finance)

Open **Sourcing Optimiser**: 1,400 kt a month to five plants through five ports and four origins. About **₹361 crore a month**, **3% (₹11 crore) cheaper** than the fixed current mix, about ₹132 crore a year. The "What each limit costs you" table shows shadow prices (Mozambique's cap is worth about ₹20 lakh per extra kt a month). Every input is an assumption on screen.

## 14. Annual programme (Finance)

`POST /finance/programme`: 24 parcels a year cost **₹239 crore**; hold **₹297 crore** for a 95% budget (range ₹189 to ₹297 crore); moving half the Australian Paradip parcels to Mozambique saves about ₹15 crore (cost only).
