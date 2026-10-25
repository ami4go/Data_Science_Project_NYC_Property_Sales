# Hypothesis test results (confirmation set, 30%, seed 42)

Plan fixed in advance: `reports/test_plan.md`. Rows: 252,178. alpha = 0.05.

## T1 (P1, primary): pre-war premium per sq ft, within neighbourhood x type
* Rows: 71,036 confirmation sales with a valid price per sq ft and year built (1-3 family and rental buildings); 367 cells with >= 5 pre-war and >= 5 newer sales (58,139 sales).
* **Estimate:** mean within-cell premium +0.43% (95% CI -1.68% to +2.58%); mean d = 0.0043 log points, s_d = 0.2068.
* **Paired t-test (one-sided):** t = 0.394, d.f. = 366, p = 0.347 -> do not reject H0 at alpha = 0.05.
* **Does it matter (5%)?** does not matter: the whole interval is inside +/- the threshold.
* Robustness, without year built 1935-1945: +2.06% (95% CI -0.32% to +4.49%), t = 1.698, d.f. = 346, p = 0.0452 (347 cells).
* Alternatives on all 71,036 sales, ignoring neighbourhood: F = 1.600 (p = 0) for equal variances; pooled t = 16.28, d.f. = 71034, p = 8.24e-60, gap +7.11%; Welch t = 16.75, d.f. = 71025, p = 3.61e-63, gap +7.11%.

## T2 (N1): bunching just below $2M after the July 2019 mansion-tax step
* Rows: residential market deals (tax class 1-2, one row per deal), 2016-18 vs 2020-25, 2019 dropped; window = price within 2.5% of the threshold.
* **main: $2M (tax step):** below-line share 47.0% (157/334) -> 69.6% (673/967); difference +22.6 pp (95% CI +16.5 to +28.7); z = 7.41, one-sided p = 6.49e-14.
* **second window: $3M (tax step):** below-line share 45.9% (102/222) -> 63.5% (330/520); difference +17.5 pp (95% CI +9.8 to +25.3); z = 4.43, one-sided p = 4.72e-06.
* **placebo: $1.5M (no step):** below-line share 36.2% (195/539) -> 37.8% (509/1345); difference +1.7 pp (95% CI -3.1 to +6.5); z = 0.68, one-sided p = 0.25.
* **placebo: $2.5M (no step):** below-line share 39.2% (114/291) -> 39.6% (268/676); difference +0.5 pp (95% CI -6.2 to +7.2); z = 0.14, one-sided p = 0.445.
* Does it matter (10 pp) at $2M? matters: the whole interval is beyond the threshold.
* Check: chi-square 2x2 at $2M = 54.85 (= z^2), d.f. = 1, two-sided p = 1.3e-13.

## T3 (P4 upgraded): $0-$100 transfers by borough, holding building type fixed
* Rows: 252,178 confirmation deeds; citywide transfer rate per building category (47 categories) gives each borough's expected transfers.
* **Chi-square goodness of fit:** chi2 = 461.3, d.f. = 4, p = 1.54e-98 -> reject H0. Smallest expected count 7,873 (>= 5).
  * Bronx: observed 32.1% vs expected 37.0% -> -4.9 pp (95% CI -5.5 to -4.3); O/E = 0.867.
  * Brooklyn: observed 37.7% vs expected 35.8% -> +2.0 pp (95% CI +1.6 to +2.3); O/E = 1.055.
  * Manhattan: observed 21.1% vs expected 21.3% -> -0.2 pp (95% CI -0.5 to +0.2); O/E = 0.992.
  * Queens: observed 35.4% vs expected 34.0% -> +1.4 pp (95% CI +1.1 to +1.7); O/E = 1.041.
  * Staten Island: observed 32.6% vs expected 38.1% -> -5.5 pp (95% CI -6.1 to -4.9); O/E = 0.855.
* Does it matter (2 pp)? 2 of 5 boroughs are 2 pp or more from their expected share.
* Alternative, raw chi-square of independence (ignores building type): chi2 = 4,472.5, d.f. = 4, p = 0; raw shares Bronx 32.1%, Brooklyn 37.7%, Manhattan 21.1%, Queens 35.4%, Staten Island 32.6% (spread 16.6 pp).
* Caveat: expected counts use rates estimated from the same data, so d.f. = 4 is approximate.

## T4 (N2): buildings with shops vs purely residential, within neighbourhood x type
* Rows: 71,077 confirmation sales (3,231 mixed-use); 225 cells with >= 3 of each (41,093 sales).
* **Estimate:** mean within-cell gap -15.45% (95% CI -19.50% to -11.20%).
* **Paired t-test (two-sided):** t = -6.738, d.f. = 224, p = 1.34e-10 -> reject H0.
* **Does it matter (5%)?** matters: the whole interval is beyond the threshold.
* Alternatives on all 71,077 sales: F = 2.227 (p = 1.58e-278); pooled t = -9.74, d.f. = 71075, p = 2.1e-22, gap -9.34%; Welch t = -6.79, d.f. = 3370, p = 1.31e-11, gap -9.34%.

