# Data and component licences

**Rule for this project: public-domain data only, fetched free.** Nothing here needs an account, an API key, a credit or a payment.
A licence, even an open one with attribution, was treated as a reason to remove a source, not to keep it (decision of 19 Sept 2026).

## Data in use (all public domain)

| Source | Status | What we use it for |
|---|---|---|
| USDA Agricultural Marketing Service, Grain Transportation Report, Figure 20: monthly ocean freight rates, US Gulf and Pacific NW to Japan (1996 to Aug 2026) | US government publication; USDA states it is non-confidential and non-copyrighted. The rates are compiled by O'Neil Commodity Consulting and credited on the sheet | The freight signal: forecasting, verdict momentum, risk fan, cost at risk. Because a private firm compiles the figures, confirm with USDA (GTRContactUs@usda.gov) before any commercial use |
| US Bureau of Labor Statistics producer price indices: deep-sea freight (`WPU30130101`) and coal (`WPU051`), via FRED | US government, public domain | Context and model inputs |
| US Energy Information Administration Brent crude spot price (`DCOILBRENTEU`), via FRED | US government, public domain | Fuel signal, the drift monitor |
| Federal Reserve H.10 exchange rates (rupee, Australian dollar, rand) and the broad dollar index, via FRED | US government, public domain | Currency conversion, hedge overlay, model inputs |
| NOAA IBTrACS tropical-cyclone tracks | US government, public domain | Storm exposure by port and month |
| Natural Earth land outlines | Public domain | Globe and map dots |
| Ministry of Ports, SAIL annual report, CAG audit, SAIL news | Public Indian-government documents | Quoted figures (turnaround, import share, demurrage cases), cited not copied |

Ship availability is **not** a downloaded dataset: it is the open-tonnage lists SAIL's own brokers send, uploaded by users. Ports, routes, distances and vessel classes are our own compilation of published specifications.

## Data removed in the licence purge (19 Sept 2026)

| Removed | Why |
|---|---|
| Baltic Capesize, Panamax, Supramax and Handysize indices (Mendeley copy labelled CC BY 4.0) | The Baltic Exchange indices are a proprietary index; a research copy's CC BY label cannot grant rights the uploader did not hold. Everything trained on them (forecasting, the LSTM/GRU/TCN/Transformer study, the Baltic nowcast) was removed or re-based |
| IMF PortWatch (port calls, chokepoint transits) | IMF data terms, not public domain; commercial reuse needs permission |
| IMF iron-ore price | IMF data terms |
| World Bank coal prices (Pink Sheet) | CC BY 4.0 (attribution condition) |
| SMP Kolkata daily Haldia vessel reports | No reuse licence stated |
| Open-Meteo weather and marine forecast | CC BY 4.0, free for non-commercial use only |
| Port Authority of NSW Newcastle vessel movements | Reuse terms could not be found |
| S&P 500 series | S&P terms on FRED |
| Baltic Dry Index | Removed earlier: no freely licensed daily source exists |

## Software components

| Component | Licence |
|---|---|
| three.js (including its `Water` and `OrbitControls` examples), cobe, React, Vite, Tailwind CSS, Recharts, Leaflet, lucide-react, framer-motion, motion | MIT / ISC / BSD |
| React Bits components (ParticleText, BorderGlow, Carousel, GlideSelect, FuseButton, LatticeLoader, Ripple) | MIT with the Commons Clause: free to use inside an application, not for reselling the components |
| FastAPI, SQLAlchemy, Alembic, pandas, NumPy, SciPy, statsmodels, scikit-learn, XGBoost, SHAP, PyTorch (offline training) | MIT / BSD / Apache 2.0 |
| fastembed and BAAI/bge-small-en-v1.5 sentence-embedding model (Hugging Face; optional) | Apache 2.0 and MIT; downloaded once, then runs locally with no key or API |

No code was copied from other teams' public repositories for this problem statement.
