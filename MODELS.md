# Models: what was trained, on what, and how well it works

All models use **public-domain data only** (see [LICENCES.md](LICENCES.md)). Every test is expanding-window walk-forward: a model sees only data before the month it predicts. Where a model does not help, this file says so.

## Data

The freight signal is the USDA monthly grain ocean rate, US Gulf to Japan (US$ per tonne, 296 usable months from 2002 after dropping an early gap, to Aug 2026): a dry-bulk proxy, not a coal rate. Inputs: the Pacific NW rate, US BLS coal and deep-sea freight indices, US EIA Brent crude, and the Federal Reserve rupee rate and dollar index. It is a random-walk-like series, and the results below show it.

## Forecasting the ocean rate (`scripts/train_current.py`, `train_current_dl.py`)

About 200 monthly forecasts, Jan 2010 to Jul 2026. Wilcoxon signed-rank test on absolute errors against "no change".

| Model | 1-month MAE (US$/t) | p | 3-month MAE (US$/t) | p |
|---|---|---|---|---|
| No change (naive) | 2.58 | | 5.27 | |
| ARIMA(1,1,1) | 2.45 | 0.089 | 5.27 | 0.848 |
| ETS (damped trend) | 2.61 | 0.902 | 5.93 | **0.0008 (worse)** |
| Ridge on lags, coal, oil, rupee | **2.33** | 0.016 | 5.13 | 0.328 |
| ExtraTrees | 2.45 | 0.154 | 5.32 | 0.986 |
| XGBoost | 2.50 | 0.116 | 5.49 | 0.936 |
| ARIMA + XGBoost | 2.42 | 0.042 | 5.20 | 0.586 |
| Ridge + ARIMA | 2.34 | **0.0071** | 5.09 | 0.177 |
| GRU neural network (3 seeds, retrained every 24 months) | 2.60 | 0.383 | not run | |

Reading it honestly: seven models were compared against "no change", so p-values need a correction (Bonferroni: multiply by 7). At one month only the Ridge + ARIMA blend (0.0071 x 7 = 0.05) is on the edge of significance; Ridge alone (0.016 x 7 = 0.11) is not. At three months nothing beats no change, and the damped-trend smoother is significantly worse. The neural network does not help: about 300 monthly points is too few. Guidance: treat the direction of the forecast with caution and use the bands.

Live ensemble on the Forecast page (ARIMA + XGBoost + SHAP, 5 walk-forward splits, 3-month horizon): ARIMA MAE 4.62, XGBoost 4.03, blend 4.25 (blend vs ARIMA p = 0.053). SHAP shows last month's rate and the rupee as the main drivers. (SHAP uses XGBoost's own exact tree-SHAP if the shap library cannot read the installed XGBoost.)

## Model proof (`GET /lab/proof/{series}`)

Refits ARIMA and XGBoost live on ten walk-forward origins with measured timings (about 2 seconds for 20 fits) and lists saved artifacts with SHA-256 fingerprints, so the models can be shown to be real. Forecast pages are quick because results are cached for six hours.

## Assistant intent model

TF-IDF + logistic regression averaged with a logistic regression on **BAAI/bge-small-en-v1.5** sentence embeddings (Hugging Face, MIT, run locally through fastembed; automatic fallback to TF-IDF). 216 hand-written questions, 5-fold, three seeds, 140 template questions always in training (`scripts/eval_intent_embeddings.py`):

| Method | Accuracy |
|---|---|
| TF-IDF + logistic regression | 73.5% ± 6.4% |
| Sentence embeddings + logistic regression | 86.6% ± 4.9% |
| Both averaged (used) | **86.9% ± 3.9%** (p = 0.0007 vs TF-IDF) |

In-distribution on our own questions, not an external benchmark. Below 35% confidence the assistant asks for clarification.

## Rule-based and optimisation engines (not trained models)

- **The Verdict** (`services/verdict.py`): weighted votes from time pressure, open ships on the uploaded broker lists, storm season, freight, fuel, coal and rupee momentum. The weights are judgement, not fitted. Its track record (`verdict_eval.py`): momentum shows a borderline edge in the USDA series (p = 0.04) and none in Brent crude, so it carries a modest weight.
- **Urgent Desk**: 60 options costed with a deterministic landed-cost model and 2,000 simulated arrivals each.
- **Sourcing optimiser**: a linear program (HiGHS) with shadow prices; inputs are assumptions.
- **Cost at risk and forecast fan**: Monte Carlo and block bootstrap of real monthly moves of the USDA rate.

## What was removed with the licensed data

The Baltic LSTM, GRU, TCN and Transformer study, the Baltic nowcast and the weather experiment were removed because they rested on the Baltic indices, IMF PortWatch and Open-Meteo. Git history keeps them; they are not in the current tree.

## Forecast bands (`scripts/eval_intervals.py`, `GET /lab/interval-calibration`)

A 95% band should contain the real outcome 95 times in 100. Walk-forward over 144 past months of the USDA ocean rate, ARIMA(2,1,2) refitted at each origin:

| Horizon | ARIMA's own 95% band: coverage / width (US$/t) | Calibrated 95% band: coverage / width | Calibrated 80% coverage |
|---|---|---|---|
| 1 month | 98% / 22.4 | 97% / 14.5 | 80% |
| 3 months | 100% / 51.7 | 93% / 27.3 | 78% |
| 6 months | 100% / 77.7 | 94% / 40.2 | 80% |

The calibrated band is the finite-sample quantile of how far the rate actually moved over the same number of months during the previous 60 months (`ml/intervals.py`). It is inspired by conformal prediction but is a simpler rule. Limit: the 60-month window was chosen on the same history it was tested on, so the band is approximately, not exactly, calibrated. Mean absolute error of the point forecast in the same test: ARIMA 2.24, 5.39 and 8.09 against 2.49, 5.58 and 8.07 for "no change" at 1, 3 and 6 months.

## Cost model market factor

Freight estimates use 2.5 US$ per tonne per 1,000 nm scaled by the USDA ocean rate divided by its median over the previous 60 months, limited to 0.6 to 1.6 (1.26 in September 2026). The $2.5 is taken to be right when the market sits at its five-year median. Costs remain illustrative estimates, not quotes.

