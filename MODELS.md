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
- **Accuracy achieved (our data, BDI, 7-day horizon, 5 walk-forward splits)**: **4.68% MAPE**, RMSE ≈100. Directly comparable to Luo et al. (2026)'s transformer-hybrid result of 5.26% MAPE on the same index — our plain ARIMA baseline is already competitive with a far more complex published model.

### 2. XGBoost (primary ensemble partner)

- **What**: gradient-boosted trees on engineered features — lag (1/2/3/7/14-day), rolling-window mean/std (7/30-day), calendar (month/day-of-week/year), and exogenous macro features (S&P 500, US Dollar Index, Australian & South African coal prices) — `backend/app/ml/xgboost_model.py`, `features.py`. Hyperparameters (max_depth/learning_rate/n_estimators) selected via a small `TimeSeriesSplit` grid search.
- **Why chosen**: Baghel (2025) found XGBoost handles non-linear, short-term fluctuations in cargo data better than ARIMA, particularly around seasonal peaks. Kim, Kim & Choi (2025, PLOS ONE) — read in full — tested 10 ML models on BDI and found tree-ensemble methods (Extra Trees, CatBoost, Random Forest) substantially outperformed both classical models and XGBoost/LightGBM/AdaBoost/KNN/Elastic Net in their study (see "Models considered and rejected" below for why we picked XGBoost over their top pick, Extra Trees).
- **Accuracy achieved (our data, BDI)**: **4.19% MAPE**, RMSE ≈93 — narrowly beats our own ARIMA baseline once real exogenous data was correctly available (see bug note below).
- **Real bug found and fixed**: exogenous features (S&P 500 from FRED only covers 2016+, but our BDI history starts 2012) were silently producing all-NaN columns for early training folds, causing XGBoost to train on zero rows and predict a flat 0.0 (RMSE 830 before the fix). Full detail in `SECTIONS.md` Section 6.

### 3. ARIMA + XGBoost Ensemble (inverse-RMSE weighted)

- **What**: `hybrid = w_arima × arima_forecast + w_xgb × xgb_forecast`, where `w_m = (1/RMSE_m) / Σ(1/RMSE_k)` — models with lower backtest error get proportionally more weight. Exact formula and validation approach from Baghel (2025) — `backend/app/ml/ensemble.py`.
- **Why chosen**: this is the one architecture in the literature we reviewed that is *proven statistically significant*, not just "seemed to work." Baghel validated it with a Wilcoxon signed-rank test (p=0.016 vs. ARIMA alone on Indian port cargo). We replicated that exact test on our own data.
- **Accuracy achieved (our data, BDI)**: **4.34% MAPE**, weights 47.6% ARIMA / 52.4% XGBoost. **Wilcoxon hybrid vs. ARIMA: p = 5.4×10⁻⁶ (highly significant)** — directly replicates Baghel's finding. Hybrid vs. XGBoost alone: not significant (p=0.99), an honest result — when one base model is already strong, blending in a weaker one doesn't help further, which is expected ensemble behaviour, not a flaw. On BCI, hybrid MAPE was best of the three (8.98%) though neither significance test reached p<0.05 there — reported as-is, not cherry-picked.

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
