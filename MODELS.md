# Models — What We Use, What We Considered, and Why

One reference doc for every forecasting model touched in this project: what's
actually deployed, what was evaluated and rejected, the accuracy each achieved
on our real data, and the literature basis for each decision. See
`SECTIONS.md` for build-log detail and `FEATURES.md` for how models map to
user-facing features.

## Models in production (this codebase)

### 1. ARIMA (baseline)

- **What**: classical AutoRegressive Integrated Moving Average, order selected by an AIC grid search (p≤2, d≤1, q≤2) after an Augmented Dickey-Fuller stationarity test — `backend/app/ml/arima_model.py`.
- **Why chosen**: every reviewed paper (Baghel 2025; Sahu & Patil 2017; the arXiv empty-container paper; Su, Bae & Park 2025) uses ARIMA/SARIMA as the baseline every other model must beat. It's fast, well-understood, and — per Sahu & Patil (2017) — SARIMA outperformed OLS regression on Indian port cargo demand (avg. error 8% vs. 6-20%).
- **Accuracy achieved (real daily Baltic Panamax index, BPI, Aug 2012 to Jul 2019, 5 walk-forward splits)**: **6.54% MAPE** at 7 days (RMSE ≈69) and **14.2%** at 14 days (RMSE ≈146). The early splits are 3.6% to 5.1%; the later ones include the 2015-16 collapse and the 2016 recovery, where the 14-day error reaches 18% and 35%, which is what a random-walk-like market does to a linear model. Published comparison points (Luo et al. 2026, 5.26% MAPE on the BDI) are on a different index and window, so they are context, not a like-for-like benchmark.

### 2. XGBoost (primary ensemble partner)

- **What**: gradient-boosted trees on engineered features — lag (1/2/3/7/14-day), rolling-window mean/std (7/30-day), calendar (month/day-of-week/year), and exogenous macro features (S&P 500, US Dollar Index, Australian & South African coal prices) — `backend/app/ml/xgboost_model.py`, `features.py`. Hyperparameters (max_depth/learning_rate/n_estimators) selected via a small `TimeSeriesSplit` grid search.
- **Why chosen**: Baghel (2025) found XGBoost handles non-linear, short-term fluctuations in cargo data better than ARIMA, particularly around seasonal peaks. Kim, Kim & Choi (2025, PLOS ONE) — read in full — tested 10 ML models on BDI and found tree-ensemble methods (Extra Trees, CatBoost, Random Forest) substantially outperformed both classical models and XGBoost/LightGBM/AdaBoost/KNN/Elastic Net in their study (see "Models considered and rejected" below for why we picked XGBoost over their top pick, Extra Trees).
- **Accuracy achieved (BPI, paired ensemble backtest, 7-day, 35 paired forecasts)**: **3.75% MAPE**, RMSE ≈47, against ARIMA 3.90% on the same forecasts. (These 35 forecasts are a different, smaller sample than the 5-split figure above, which is why the MAPE differs.)
- **Real bug found and fixed**: exogenous features (S&P 500 from FRED only covers 2016+, but our BDI history starts 2012) were silently producing all-NaN columns for early training folds, causing XGBoost to train on zero rows and predict a flat 0.0 (RMSE 830 before the fix). Full detail in `SECTIONS.md` Section 6.

### 3. ARIMA + XGBoost Ensemble (inverse-RMSE weighted)

- **What**: `hybrid = w_arima × arima_forecast + w_xgb × xgb_forecast`, where `w_m = (1/RMSE_m) / Σ(1/RMSE_k)` — models with lower backtest error get proportionally more weight. Exact formula and validation approach from Baghel (2025) — `backend/app/ml/ensemble.py`.
- **Why chosen**: this is the one architecture in the literature we reviewed that is *proven statistically significant*, not just "seemed to work." Baghel validated it with a Wilcoxon signed-rank test (p=0.016 vs. ARIMA alone on Indian port cargo). We replicated that exact test on our own data.
- **Accuracy achieved (BPI, 7-day)**: hybrid **3.52% MAPE** (weights 51.4% ARIMA / 48.6% XGBoost), against ARIMA 3.90% and XGBoost 3.75%. **Wilcoxon hybrid vs. ARIMA: p = 0.0019, significant**, replicating Baghel's finding on this index; hybrid vs. XGBoost alone is not significant (p = 0.16), the honest expectation when one base model is already strong. Note this result is series-specific: an earlier run on the daily Baltic Dry Index (since removed from the project) found the hybrid not better than ARIMA, so the ensemble's advantage should not be assumed to carry over to other series.

### 4. Intent classifier for "Ask the Freight Desk"

- **What**: TF-IDF (word 1-2 grams plus character 2-4 grams) with entity-marker tokens, then logistic regression (`backend/app/ml/intent.py`). It routes a question to one of 11 engines; it does not generate text.
- **Why chosen**: with about 270 examples a linear model on sparse features is the sensible fit. Character n-grams tolerate typos and phrasings ("vizag", "capesize"), and marker tokens let it use the fact that a port or a horizon was named. A transformer or hosted LLM would need a provider, a key and data leaving the deployment.
- **Accuracy**: 75% ± 6% on held-out hand-written questions (5-fold; 17 intents, 204 hand-written and 140 template-generated examples, templates always in training). This is an in-distribution figure on our own questions, not an external benchmark. Low-confidence questions (under 35%) get a clarification instead of a guess.

### 5. Port-signal models (Section 14d)

- **Berth-slot forecaster** (`services/signals.py`): for each port, four simple models (last 14-, 28- and 90-day mean, ARIMA(1,1,1)) forecast the 7-day mean of PortWatch dry-bulk calls; the best by a 12-window rolling-origin backtest is used. An ARIMA(2,0,1) tried first was 48% worse than a naive forecast, which is why the selection exists. Best-model gain over naive is 0 to 9%, so it is a pressure indicator, not a schedule.
- **Congestion transfer**: Granger causality (F-test, best lag up to 10 days) between every ordered port pair on first-differenced 7-day means, Bonferroni-corrected. One pair survives (Haldia leads Visakhapatnam, about 6 days, adjusted p = 0.029).
- **Cyclone exposure**: empirical frequency from IBTrACS, not a model; expected delay uses two assumed parameters.
- **Demand estimator**: a single ratio (imported coking coal / crude steel = 0.865) from two annual points. No fitted model; the band is two standard deviations of two numbers.
- **Drift monitor**: ARIMA(2,1,2) trained on 800 days, then applied with frozen parameters; one-sided Mann-Whitney U on recent vs reference one-step errors, and PSI on daily returns.

### 6. Deep learning: LSTM, GRU, TCN, Transformer (`scripts/train_dl.py`, Model Lab page)

- **Why it was not in the first version**: the freight series are short (2,556 daily observations, Aug 2012 to Jul 2019), which is small for neural networks, and the free-tier deployment cannot hold PyTorch. It was added afterwards as an experiment, run offline, so we can say what deep learning does here rather than guess.
- **Setup**: 60-day windows of BPI log-returns plus S&P 500, dollar index and two coal-price returns; each model outputs the seven cumulative log-returns for the next week; Huber loss, AdamW, early stopping on the last 15% of each training set; 3 seeds per model, averaged; retrained at each of 5 walk-forward splits on data available at that point. The classical models ran through the *same* splits (`scripts/dl_baselines.py`, run in a separate process because PyTorch and XGBoost bundle conflicting OpenMP runtimes on macOS), so all 35 forecast errors are paired.
- **Results (7-day BPI, 35 paired forecasts, lower is better)**:

| Model | MAE | MAPE | vs ARIMA (one-sided Wilcoxon p) |
|---|---|---|---|
| Deep ensemble (mean of 4) | 25.8 | 2.79% | 0.17 |
| GRU | 26.0 | 3.01% | 0.16 |
| Transformer | 26.7 | 2.81% | 0.22 |
| LSTM | 26.8 | 3.01% | 0.41 |
| ARIMA + XGBoost hybrid | 29.0 | 3.52% | 0.0019 (significant) |
| XGBoost | 31.6 | 3.75% | 0.31 |
| ARIMA(2,1,2) | 31.9 | 3.90% | baseline |
| TCN | 37.6 | 4.01% | 0.39 |

- **Reading it honestly**: the deep ensemble has about 19% lower MAE than ARIMA and 11% lower than the hybrid, but with 35 highly autocorrelated forecasts that difference is *not* statistically significant (p = 0.17), while the hybrid's advantage over ARIMA is. The TCN is worst. The right conclusion is "promising, not proven": more data or more series would be needed to settle it.
- **Serving**: the LSTM and GRU are refitted on all data and exported as NumPy weights (`backend/app/ml/artifacts`); the API evaluates them with a hand-written NumPy forward pass (`app/ml/dl_infer.py`), so the deployed API needs no deep-learning framework. `GET /forecast-deep/BPI` returns their 7-day paths.
- **Does weather help? (`scripts/weather_experiment.py`)**: ridge regression for the next 14 days of port calls, with and without Open-Meteo wind, rain and wave height, over 12 walk-forward windows for each of five ports. Weather did **not** significantly help (pooled p = 0.88; it helped at Dhamra and Visakhapatnam and hurt at Haldia, Paradip and Gopalpur). We report that instead of shipping a weather feature that does not earn its place.

## Models considered and explicitly rejected (with reasons)

| Model | Why it was considered | Why rejected / deferred |
|---|---|---|
| **LSTM** | Standard deep-learning choice for sequential/time-series data; used in 2 of the 5 papers reviewed. | Baghel (2025) found LSTM badly overfits on small monthly Indian port cargo samples (only ~6-12 points per validation fold) — training loss dropped while validation loss flattened/rose after ~20-30 epochs, a textbook overfitting signature, and it had to be dropped from their final hybrid. **Deferred, not abandoned**: our dataset is daily (8,745 rows) rather than their ~100-160 monthly points, so LSTM is more viable for us — planned as a secondary model in a future section, not the primary one, specifically *because* we have enough data for it to make sense. |
| **Prophet** | Popular, easy-to-use decomposable trend+seasonality+holiday model; used as a baseline in the arXiv empty-container paper. | That same paper found Prophet **underperformed even a naive last-value baseline** on real terminal data (Mean RMSE 221 vs. Naive's 189), attributed to sensitivity to outliers/noise — a directly-reviewed, real result, not a guess. Not used anywhere in this project. |
| **Extra Trees / CatBoost / Random Forest** | Kim, Kim & Choi (2025) found these three outperformed XGBoost specifically on weekly BDI (Extra Trees: MAE 182.53, R²=0.88 — the best of 10 models tested; XGBoost was 7th of 10, R²=0.70 only). | Not swapped in for XGBoost despite the paper's own result being better, for a practical reason: XGBoost has first-class native SHAP `TreeExplainer` support, is the model both reviewed India-specific papers (Baghel; the arXiv paper by proxy) build their validated ensemble methodology around, and their study used *weekly* aggregated data with no autoregressive lag features of the target itself — a different setup from ours (daily, heavily lag-featured), so their exact model ranking doesn't directly transfer. **Worth a future experiment**: swap in Extra Trees as a second ensemble candidate and compare, since the paper's result is real and specific. |
| **RBF Neural Network** | Su, Bae & Park (2025) achieved R²=0.96 forecasting a container freight index (SCFI) with an RBF network, outperforming 8 other models (LR, RF, SVM, GBRT, MLP, SGD, XGBR, BP) in their comparison table. | No off-the-shelf, well-maintained Python RBF-network implementation exists the way XGBoost/statsmodels are maintained — would require a custom implementation under real time pressure. Noted as a credible future alternative, not pursued given the 2-3 day build window. |
| **VAR / GARCH / SARIMA variants** | Common in the freight-forecasting literature (Chen et al. 2012 found VAR beat ARIMA for multiple dry bulk routes; Koyuncu & Tavacıoğlu 2021 found SARIMA beat Holt-Winters for SCFI). | Plain ARIMA was sufficient as our baseline and already competitive with literature benchmarks (see above); GARCH/VAR extensions are a reasonable future enhancement for volatility-clustering-aware forecasting, not pursued given time constraints. |

## Novel adaptation (not a forecasting model, but model-adjacent)

- **Time-lag cross-correlation + Granger causality** (Su, Bae & Park 2025's "transfer effect" methodology) — planned for the Cross-Port Congestion Transfer feature (`FEATURES.md` #23), applying their exact statistical method (lagged correlation coefficient, Granger causality test) to our own East Coast port congestion data instead of their Shanghai/Busan/LA/NY container data.

## Datasets each model trains on

See `SECTIONS.md` Section 3 for full detail — summary: Mendeley Baltic sub-index dataset (8,745 real daily rows, 2012-2019), World Bank coal prices (1,152 rows, 1960-2024), FRED S&P 500 (2,513 rows, 2016-2026) and Trade-Weighted US Dollar Index (5,188 rows, 2006-2026).

## Negative result: can current public freight data stand in for the Baltic indices?

The Baltic indices end in July 2019. The only free current freight series found is the US BLS producer price index for deep-sea freight
(monthly, to August 2026). On the 84 overlapping months (Aug 2012 to Jul 2019) its month-to-month change has **0.00 correlation** with the
Panamax index change (levels correlate 0.49, which is mostly a shared trend), and a regression fitted on 2012 to 2016 scores an
**out-of-sample R² of -0.92** on 2017 to 2019 (adding coal and iron ore did not rescue it). A nowcast would therefore be invented, so none is
shown. The PPI is a mostly container and tanker-weighted price index; it is displayed as context only.

