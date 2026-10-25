# Test plan (written BEFORE any test is run)

Commit this file to git before `src/06_tests.py` exists. The commit time is our proof that
part (a) of every test was fixed before we saw the confirmation data.

## Common rules

* **Data:** only the 30% **confirmation set** (`data/processed/sales_confirmation.pkl`,
  252,178 rows). Ideas, cell rules and thresholds below come from the exploration set and are
  frozen here.
* **Methods:** only tests taught in CSE558 Lectures 5-8: z-tests (mean, proportion, two means,
  two proportions), t-tests (one-sample, two-sample pooled / Welch, paired, correlation),
  F-test for two variances, chi-square (variance, goodness of fit, independence).
  Untaught methods appear only in part (b) as "considered, not used".
* **Significance level:** alpha = 0.05 per test. We keep the list to four tests because every
  extra test is another chance of a false alarm (the guidelines' warning); the "matters" size,
  not the p-value alone, decides what we conclude.
* **Prices:** log price, because prices are right-skewed over five orders of magnitude.
  Price-level statistics use one row per deal (`first_in_transaction`); per-sq-ft statistics use
  rows with a valid `price_per_sqft` that are not `ppsf_outlier`.
* **Reporting (part c):** estimate, 95% confidence interval, test statistic, degrees of freedom,
  p-value, decision, and whether the interval clears the "matters" size.

---

## T1 (P1, primary). Pre-war premium per square foot

**Question.** Within the same neighbourhood and building type, do pre-war buildings (built before
1940) sell for more per square foot than newer ones?

**Rows.** Valid price per sq ft, year built known, building categories 01, 02, 03 (1-3 family),
07, 08, 14 (rental buildings). A **cell** = neighbourhood x building category. Cells with at least
**5** pre-war and **5** newer sales in the confirmation set are kept (the exploration set used 10;
the confirmation set is 3/7 the size). For each cell, d = mean log $/sq ft (pre-war) - mean log
$/sq ft (newer).

| (a) | |
|---|---|
| H0 | mu_d = 0 (no pre-war premium within cells) |
| H1 | mu_d > 0 (pre-war sells for more) |
| Side | one-sided (right): P1 claims a premium |
| alpha | 0.05 |
| Test | **paired t-test** on the cell differences, t = mean(d) / (s_d / sqrt(n)), d.f. = n_cells - 1 |
| Smallest difference that matters | **5%** (mu_d = ln 1.05 = 0.049): below that a buyer would not notice it against normal haggling |

**Why this test fits.** Each cell gives one matched pair (pre-war vs newer, same place and type),
sigma is unknown, and the number of cells is large enough for the mean difference to be roughly
normal (CLT). Pairing removes location and building type, which the EDA showed is most of the raw
gap (+6.6% pooled vs +1.6% within cells).

**(b) Other tests considered.**

| Test | Why not the main test |
|---|---|
| Two-sample t (pooled or Welch) on all pre-war vs newer sales | Ignores neighbourhood and type, so it measures location mix, not age. **Run anyway** to show how much the pooled answer differs. |
| Pooled two-sample t | Needs equal variances; we run the F-test for two variances first and report it. |
| z-test for two means | Needs the population sigma, which we do not know. |
| t-test on the correlation of year built with log $/sq ft | Sees only a straight-line trend across all years, not the pre-war / newer contrast, and ignores location. |
| Wilcoxon signed-rank (not taught) | A rank version of the paired test for non-normal differences; not covered in the course, and with this many cells the CLT makes the paired t adequate. |

**Robustness (reported, not separate hypotheses).** Repeat T1 without year built 1935-1945 (1940 is
heavily over-recorded: 12,337 parcels vs 540 in 1939).

---

## T2 (N1). Did the 2019 mansion-tax bracket push sales just below $2M?

**Background.** From 1 Jul 2019, NYC residential sales of $2M or more pay a higher transfer tax on
the **whole** price (1% to 1.25%; about $5,000 more for crossing $2M by one dollar).

**Rows.** Market deals, one row per deal, tax class at sale 1 or 2 (residential), price in the
window **[$1.95M, $2.05M)** (+/-2.5%). "Below" = [$1.95M, $2M). Pre = 2016-2018, post = 2020-2025;
**2019 is dropped** (old-contract grandfathering and the rush to close before July).
p = share of window deals that are below $2M.

| (a) | |
|---|---|
| H0 | p_post = p_pre |
| H1 | p_post > p_pre (more deals pile up just below $2M after the tax) |
| Side | one-sided (right): the tax only rewards being below the line |
| alpha | 0.05 |
| Test | **z-test for two proportions** with the pooled rate |
| Smallest difference that matters | **10 percentage points** more of the window below $2M: about one in ten buyers moving their price for the tax |

**Why this test fits.** Two independent groups of deals (before / after), a yes/no outcome
(below / above), large counts (projected ~340 pre and ~920 post deals in the window), and a
one-sided question. Pooling the rate is right under H0, which says both periods share one rate.

**Placebo checks (reported, not separate hypotheses).** The same z-test at $1.5M and $2.5M,
where the tax does not step, should show no rise (exploration: odds ratio x0.98 and x0.97 vs
x2.46 at $2M). The $3M step (another tax increase) is reported as a second window.

**(b) Other tests considered.**

| Test | Why not the main test |
|---|---|
| Chi-square test of independence on the 2x2 (period x side) | Gives the same answer (chi-square = z squared) but only two-sided; our question is one-sided. **Run anyway** as a check. |
| z-test for one proportion (post share vs 50%) | Compares with an arbitrary 50/50 split; round-number heaping at exactly $2,000,000 makes the pre-2019 split itself unequal (48% below), so the pre-period is the right baseline. |
| Fisher's exact test (not taught) | For small counts; ours are in the hundreds, where the z-test is accurate. |
| Logistic regression with placebo thresholds (not taught) | Would test "bunching at $2M minus bunching at placebos" in one model; we show the placebos side by side instead. |

---

## T3 (P4 upgraded). Do boroughs differ in $0-$100 transfers once building type is held fixed?

**Question.** Is a borough's number of $0-$100 ownership transfers what its building-type mix
alone predicts?

**Rows.** All confirmation rows with a known price class. For each building category c, the
citywide transfer rate r_c. Expected transfers in borough b: E_b = sum over c of r_c x n_bc
(n_bc = recorded deeds of category c in borough b). Observed O_b = transfers in borough b.

| (a) | |
|---|---|
| H0 | O_b = E_b for every borough (the borough adds nothing beyond its building mix) |
| H1 | at least one borough differs |
| Side | chi-square tests are one-tailed in the statistic (only large values reject) |
| alpha | 0.05 |
| Test | **chi-square goodness of fit**, sum (O_b - E_b)^2 / E_b, d.f. = 5 - 1 = 4 |
| Smallest difference that matters | a borough's transfer share **2 percentage points** above or below its expected share |

**Why this test fits.** The data are counts in 5 categories, compared with a claimed split, which is
exactly goodness of fit. Building the expected counts from category rates is how we "hold building
type fixed": exploration showed the raw borough spread of 16.5 pp shrinks to 5.1 pp after this
adjustment, because Manhattan sells mostly condos and co-ops. The effect size is O_b / E_b and the
standardised share for each borough.

**(b) Other tests considered.**

| Test | Why not the main test |
|---|---|
| Chi-square test of independence, borough x (transfer / market) | Taught and simple, but it mixes building type with borough (the 16.5 pp raw spread). **Run anyway** to show how much of the gap is building mix. |
| z-tests for two proportions between each pair of boroughs | 10 pairs means 10 more tests to correct for; reserved for explaining which borough drives a rejection. |
| Cochran-Mantel-Haenszel test or logistic regression with category fixed effects (not taught) | The textbook way to test borough "within category"; goodness of fit against category-based expected counts answers the same question with a taught test. |

Caveat: the expected counts use rates estimated from the same data, so d.f. = 4 is approximate
(we report this).

---

## T4 (N2). Do buildings with shops sell at a different price per square foot?

**Question.** Within the same neighbourhood and building type, do buildings with commercial units
(`commercial_units > 0`) sell for a different price per sq ft than purely residential ones?

**Rows.** Valid price per sq ft, not an outlier, categories 01, 02, 03, 07, 08, 14,
`commercial_units` known. Cell = neighbourhood x category with at least **3** mixed-use and
**3** residential-only sales in the confirmation set (mixed-use sales are rare: ~1,900 projected).
d = mean log $/sq ft (mixed-use) - mean log $/sq ft (residential-only).

| (a) | |
|---|---|
| H0 | mu_d = 0 |
| H1 | mu_d != 0 |
| Side | two-sided: shops could add rent (premium) or noise and busy streets (discount) |
| alpha | 0.05 |
| Test | **paired t-test** on the cell differences, d.f. = n_cells - 1 |
| Smallest difference that matters | **5%** either way (abs(mu_d) >= 0.049) |

**Why this test fits.** Same matched design as T1: one pair per cell, sigma unknown, enough cells
for the CLT. Exploration: pooled -8.0%, within cells -19.0% (267 cells).

**(b) Other tests considered.**

| Test | Why not the main test |
|---|---|
| Welch two-sample t on all mixed-use vs residential sales | Mixed-use buildings sit on commercial streets in different neighbourhoods; the unpaired test confounds that. **Run anyway** for comparison. |
| Pooled two-sample t | Needs equal variances (F-test reported). |
| t-test on the correlation of commercial units with log $/sq ft | Linear only, and most buildings have 0 or 1 commercial unit. |
| Wilcoxon signed-rank (not taught) | Robust alternative to the paired t, not covered in the course. |

Caveat (association, not cause): gross floor area includes the shop space, which may be valued
differently from homes.

---

## Reserve: P2 (only if its pre-trend check passes)

From 2019 to 2021, did Manhattan apartment prices fall relative to Brooklyn and Queens? Welch
two-sample t on the difference of changes in log price per deal, same building categories.
Used only if, on the **exploration** set, Manhattan and Brooklyn/Queens moved within 5% of each
other from 2016 to 2019. P3 (toll zone) is **not tested**: the zone already trailed by about 3 pp a
year before the toll, so a before/after comparison would wrongly credit the toll (reported in
Limitations).
