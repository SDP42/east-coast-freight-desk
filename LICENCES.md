# Data and component licences

The rule for this project: **only free sources with clear terms**. This is every external source and library, what its terms allow, and what we do.

## Data

| Source | Terms | What we do | Status |
|---|---|---|---|
| Baltic Capesize, Panamax, Supramax, Handysize indices (Mendeley Data, DOI 10.17632/t76ckh2ygg.1) | CC BY 4.0 | Used for forecasting; attribution in TECHSTACK.md | Clear |
| World Bank Commodity Markets "Pink Sheet" (coal) | CC BY 4.0 | Monthly coal prices to Aug 2026 | Clear |
| USDA AMS Grain Transportation Report, Figure 20: monthly ocean freight rates, US Gulf and Pacific Northwest to Japan (1996 to Aug 2026) | US government publication, stated by USDA to be non-confidential and non-copyrighted; the rates are compiled by O'Neil Commodity Consulting and credited on the sheet | Current dry-bulk freight proxy; forecasting and Baltic nowcast; attribute USDA AMS and O'Neil Commodity Consulting | Clear for a prototype; because a private firm compiles the figures, confirm with USDA (GTRContactUs@usda.gov) before any commercial use |
| US Bureau of Labor Statistics deep-sea freight PPI, via FRED | US government, public domain | Context series only | Clear |
| FRED exchange rates and S&P 500 | Public series from the St. Louis Fed; the S&P 500 series carries S&P terms on FRED | Exchange rates used; S&P 500 shown as context | Check S&P terms before any public redistribution |
| IMF iron-ore price, via FRED | IMF data terms: reuse and derivative works allowed with attribution; commercial reuse needs IMF permission | Context series | Clear for a non-commercial prototype; attribute "Source: International Monetary Fund" |
| IMF PortWatch (port calls, chokepoints) | IMF data terms (not Creative Commons): use, copy and derive with attribution and without altering meaning; commercial reuse needs IMF permission | Port and chokepoint traffic. AIS-derived estimates | Clear for a non-commercial prototype; attribute "Source: International Monetary Fund, PortWatch" |
| NOAA IBTrACS cyclone tracks | US government, public domain | Storm exposure by port and month | Clear |
| Open-Meteo weather | CC BY 4.0 for non-commercial use | Weather experiment only | Clear for non-commercial use |
| SMP Kolkata (Haldia) daily vessel position reports | Public government reports; no reuse licence stated | We extract facts (vessel, cargo, draft) and do not republish the documents; raw files are not in the repository | Low risk; do not redistribute the PDFs |
| Port Authority of NSW, Newcastle Harbour vessel movements | **Reuse terms not found** (its copyright and terms pages returned "not found") | Optional live view, **off by default** (`LIVE_SHIP_FEED=false`), rows cached 30 minutes and not stored | **Unconfirmed: keep off in any public deployment until the Port Authority confirms** |
| Natural Earth land dots | Public domain | Map dots | Clear |
| SAIL annual reports, CAG audit, SAIL news, Ministry of Ports statistics | Public documents; quoted figures cited, not copied wholesale | Figures and citations only | Clear |

Baltic Dry Index: removed, because no freely licensed daily source exists. The live Baltic Exchange feed is a paid licence.

## Software components

| Component | Licence | Note |
|---|---|---|
| three.js, its `Water` and `OrbitControls` examples | MIT | |
| cobe (globe) | MIT | |
| React, Vite, Tailwind CSS, Recharts, Leaflet, lucide-react, framer-motion, motion | MIT / ISC / BSD | |
| React Bits components (ParticleText, BorderGlow, Carousel, GlideSelect, FuseButton, LatticeLoader, Ripple) | MIT with the Commons Clause | Free for personal and commercial use in an application; not for reselling the components on their own |
| FastAPI, SQLAlchemy, Alembic, pandas, NumPy, SciPy, statsmodels, scikit-learn, XGBoost, SHAP | MIT / BSD / Apache 2.0 | |
| PyTorch (offline training only) | BSD | |

No code was copied from other teams' public repositories for this problem statement.
