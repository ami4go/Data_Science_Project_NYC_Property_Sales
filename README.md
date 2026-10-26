# NYC Property Sales: cleaning, EDA and hypothesis tests (CSE558, Monsoon 2026)

**Question (P1, primary):** within the same neighbourhood and building type, do pre-war buildings
(built before 1940) sell for more per square foot than newer ones?

## Data

| | |
|---|---|
| Source | NYC Department of Finance, *NYC Citywide Annualized Calendar Sales Update*, NYC Open Data, dataset `w2pb-icbu` |
| Original download | `https://data.cityofnewyork.us/api/views/w2pb-icbu/rows.csv?accessType=DOWNLOAD` |
| Downloaded | 2026-10-20 09:33 UTC (dataset last modified 2026-06-09) |
| Frozen file | `data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.csv`, 155,795,191 bytes |
| Frozen copy for re-running | [`data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip`](https://github.com/ami4go/Data_Science_Project_NYC_Property_Sales/blob/main/data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip) (36 MB, in this repo; the unzipped CSV is too big for GitHub) |
| SHA-256 | `cf8d76c13ed5774c6a04193147c24ebf3f3e118cd2b10eefc096c6d0800c24a8` (also in `data/raw/SHA256.txt`) |
| Shape | 845,607 rows x 29 columns; sales dated 2016-01-01 to 2025-12-31 |
| One row | one recorded property sale (deed), one tax lot |

The city keeps updating this dataset, so **use the frozen copy**, not a new download.
`01_audit_raw.py` stops unless the file's SHA-256 and its 845,607 x 29 shape match the frozen download.

## How to reproduce

Unzip the frozen data in place (`data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip` -> `data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.csv`; with Python: `python -m zipfile -e data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip data/raw/`), then:

```bash
pip install -r requirements.txt
```

```bash
python run_all.py
```

The full run takes about 3 minutes. Tested with Python 3.10.11 (pandas 2.2.3, numpy 2.1.3,
matplotlib 3.10.3): two runs give **byte-identical** reports, figures (PDF and PNG) and split. An
earlier version of the pipeline also gave identical CSV outputs under Python 3.14.7 (pandas 3.0.6).

## What each file does

| File | What it does | Writes | Report section |
|---|---|---|---|
| `src/common.py` | Shared paths, seed 42, price and year thresholds, the toll-zone line, figure style and print sizes | - | all |
| `src/01_audit_raw.py` | Checks the frozen file (SHA-256, shape), reads every column as text, counts every data problem | `reports/raw_profile.csv` (one row per raw column: blanks, zeros, commas, unique values, range), `reports/raw_problems.csv` (each problem with its row count) | 1, 3 (before) |
| `src/02_clean.py` | 16 fixed cleaning rules (no learned thresholds), flags instead of deletions | `data/processed/sales_clean.pkl`, `reports/cleaning_log.csv` (rule, rows affected, action, reason) | 2 |
| `src/03_split.py` | 70 / 30 exploration / confirmation split by transaction, stratified by borough x year, seed 42; learns the price-per-sq-ft outlier fences on the exploration set only | `data/processed/split_assignment.csv`, `sales_exploration.pkl`, `sales_confirmation.pkl`, `reports/split_strata.csv`, `reports/ppsf_fences.csv` | 4 |
| `src/04_tables.py` | Counts only (no prices compared against anything), all rows | `reports/before_after.csv`, `reports/analysis_funnel.csv` + `f00`, `reports/size_check.md`, `reports/data_dictionary.md`, `reports/multi_lot_null_model.csv` + `f00b` | 1, 2, 3 |
| `src/05_eda.py` | EDA on the exploration set only; every figure with a takeaway caption | `figures/f01`-`f12` (PDF for the report, PNG for this README), `reports/eda_findings.md` | 4 |
| `src/06_tests.py` | The four hypothesis tests of `reports/test_plan.md`, confirmation set only | `reports/test_results.md`, `reports/test_results.csv`, `figures/f13` | 5 |
| `run_all.py` | Runs steps 1-6 in order | - | - |
| `reports/run_log.txt` | Console output of the last full run (`python run_all.py > reports/run_log.txt`) | - | - |
| `report/main.tex` | The midterm report (course LaTeX template) | - | all |

Figures are drawn at the exact width they print in the two-column report (83.5 mm), with 6.5-7.5 pt
text, so nothing is shrunk by LaTeX.

## Exploration / confirmation split

* **70% exploration / 30% confirmation, seed 42**, stratified by **borough x sale year** (50 strata;
  the exploration share in every stratum is 0.698-0.710). P2 and P3 compare years within boroughs,
  so both halves need every borough-year.
* The unit of the split is the **transaction**: all lots of one multi-lot deal go to the same half.
* Split sizes: **590,043 exploration rows / 252,178 confirmation rows**. The assignment is saved in
  `data/processed/split_assignment.csv` (`row_id` = line position in the frozen CSV).
* All EDA uses the exploration set only (`05_eda.py` asserts this). The confirmation set is for the
  hypothesis tests.
* Cleaning rules with no learned parameters (step 2) run on all rows. The one data-learned rule, the
  price-per-sq-ft outlier fences, is **fitted on the exploration set only** and then applied unchanged
  to the confirmation set.

## Data preparation (report Section 2)

| Problem found (rows) | What we did | Why, and why not the alternative |
|---|---|---|
| `EASE-MENT` 100% blank (845,607) | Dropped the column | Carries no information. |
| Building category: 91 labels that are really 47 (89,769 rows with doubled spaces) | Trimmed, collapsed spaces, upper-cased | Otherwise one-hot encoding splits one category into two columns. A manual mapping would do the same job but is not reproducible. |
| Borough stored as code 1-5 | Decoded to names; kept the code too | Readable; nothing lost. |
| Square feet stored as text with commas ("55,000"; 400,608 rows) | Removed the commas and converted to numbers | Price per sq ft cannot be computed on text. |
| Gross sq ft blank or 0 (374,853 = 44.3%); land sq ft blank or 0 (363,663) | 0 set to missing; **not imputed** | No building has 0 sq ft, so 0 means "not recorded". Missing **by design**: 95% of condo/co-op unit sales lack it vs 5% of other sales (f03), because the area belongs to the building, not the unit. Imputing from neighbours would invent the response's denominator. |
| Condo units carry their own area almost only in 2018 (87% of condo sales that year, 7% in 2019, ~1% or less in every other year; 18,060 rows) | Area kept, but **no price per sq ft for condo units** | A measurement that exists in one year makes any per-sq-ft comparison across years or places depend on how many 2018 condo sales a group happens to contain. |
| Co-ops (09, 10, 17) and condo billing lots (11) carry the **whole building's** area (1,142 rows with area) | No price per sq ft for these | The sale is one apartment, but the area is the building's: the median comes out at $2-5 per sq ft. |
| Year built 0 / missing (63,344) or before 1800 (11) | Set to missing; excluded from P1 only | 0 is a placeholder; pre-1800 values are typos. The rows are still valid sales for the other questions. |
| Year built heaped on round years (61% of parcels end in 0 or 5; 1940 has 12,337 parcels vs 540 in 1939; f04) | Kept as recorded; flagged for a **sensitivity check** in T1 | These are assessor estimates. Dropping them would remove most pre-war stock; instead T1 is repeated without the years around the cutoff. |
| Residential + commercial units != total (6,638) | Flagged `units_inconsistent` | We cannot tell which of the three numbers is wrong. No total was blank while both parts were present, so nothing could be recomputed. |
| ZIP missing or 0 (2,864); no coordinates (23,278) | Set to missing; excluded from the toll-zone test only | The sale itself is valid. |
| BBL column blank or 0 (27,900), and differs from borough-block-lot for 209,488 rows | Kept the raw column as `bbl_building`; added `bbl_lot` = borough x 1e9 + block x 1e4 + lot | The raw BBL is **building-level** (the condo 75xx billing lot), so it cannot tell condo units apart. The context pack's "17,424 repeated BBL+apt+date+price rows" mostly came from blank BBLs matching each other. |
| Exact duplicate rows, all 29 columns equal (3,386) | Dropped the extra copies | The same sale counted twice inflates counts and shrinks p-values. |
| Same lot+unit+address+date+price but other columns differ (94) | Flagged `possible_duplicate`, kept | We cannot tell which copy is right; 94 rows do not move any statistic. |
| Price <= $100 (271,899 after dedup; 262,138 at $0 in raw) | Flagged `price_class = nominal`; excluded from price analyses, **kept for T4** | Deed transfers between relatives or entities are not market prices. Deleting them would make T4 (transfer share by borough) impossible. |
| Price $101-$10,000 (3,366) | Flagged `low`; excluded from price analyses | Not a credible NYC price for any property; mostly houses at a median of ~$2,500. 0.4% of rows, so the cutoff barely matters. |
| Price > $100M (1,083; max $2.4B) | Kept; prices analysed on a log scale | Real trophy or portfolio deals. Trimming them would delete real market sales; the log scale stops them dominating. |
| **Multi-lot deals:** one deed over several lots repeats the *total* price on every lot | Flagged `multi_lot_sale` (35,044 rows) when the same borough + date + exact price covers >= 2 lots on **one block**, or >= 6 lots anywhere; excluded from per-sq-ft analysis | Dividing a deal's total price by one lot's area inflates price per sq ft. **Justified with a null model** (f00b): with sale dates shuffled (seed 42), chance produces 543 same-block groups vs 12,473 observed (real deals), but 26,611 two-lot cross-block groups vs 24,557 observed (pure coincidence, e.g. two $650K co-ops on the same day), so those are **not** flagged. A naive "same borough + date + price" rule would have wrongly flagged 93,262 rows. |
| **Price statistics would count a multi-lot deal once per lot** (566,956 market rows = 545,669 deals) | Flagged `first_in_transaction`; every statistic of the price itself (medians, trends, tests on log price) uses **one row per deal** | One $170M condo-hotel deal over 280 lots would otherwise weigh as 280 sales. In the toll-zone EDA this flips the answer: counting lots, 2024-25 prices rose +10.4% inside vs +5.1% outside; counting deals, +1.6% inside vs +6.6% outside (f10). |
| Price per sq ft outliers (3,833) | Flagged `ppsf_outlier`: outside Tukey fences of 3 x IQR on log $/sq ft per building category, **fitted on the exploration set**, clipped to $10-$20,000 per sq ft | Area/price mismatches (e.g. one unit's price over a whole hotel's area). Per category because levels differ ($450 for houses, $1,250 for condos); on the log scale because of skew; k = 3 so only extreme values are flagged; the hard bounds cover categories whose IQR is so wide that the fence alone would accept $0.01 per sq ft. |
| Toll zone (Manhattan, 60th St and below) is a tilted line on a rotated grid | `toll_zone` from coordinates: lat <= 40.7656 - 0.4 x (lon + 73.9730) | Calibrated on parsed addresses: **all 24,072 sales on East/West 50th-70th St land on the correct side**. Using NTA codes instead would cut across 60th St. |
| Encoding | One-hot: borough (5), building category (47), tax class at sale (4); neighbourhood (261) optional | Tests and models need numbers. Label encoding would impose a fake order on nominal codes. |

New columns: `price_per_sqft`, `log_price_per_sqft`, `log10_price`, `prewar`, `building_age_at_sale`,
`sale_year/month/quarter`, `period` (pre-COVID 2016-19 / COVID 2020-21 / recovery 2022-23 / 2024-25),
`post_toll`, `toll_zone`, `transaction_id`, `first_in_transaction`, plus the flags above.

## What changed (report Section 3)

| Measure | Before | After |
|---|---:|---:|
| Rows | 845,607 | 842,221 |
| Columns | 29 | 55 (28 original kept + 27 derived/flags) |
| Exact duplicate rows | 3,386 | 0 |
| Building-category labels | 91 | 47 |
| Numeric columns stored as text | 2 | 0 |
| Blank cells excluding EASE-MENT | 1,793,579 | 2,097,690 missing |
| Hidden missing (0 meaning "not recorded": sq ft, year, ZIP, BBL) | 314,567 | 0 (now explicit) |
| Market-price rows (before: > $100; after: > $10,000, deduplicated) | 571,406 | 566,956 |
| Market deals (a multi-lot deal counted once) | - | 545,669 |
| Rows with a valid price per sq ft | - | 248,627 |

"Missing" goes **up** after cleaning because 314,567 zeros that meant "not recorded" are now marked
as missing; hiding them as 0 would bias every mean.

**What we lost** (`reports/analysis_funnel.csv`, f00):

| Step | Rows | % of raw |
|---|---:|---:|
| Raw | 845,607 | 100.0 |
| After exact duplicates | 842,221 | 99.6 |
| Market sales (> $10,000) | 566,956 | 67.0 |
| ... with floor area | 274,197 | 32.4 |
| ... not a multi-lot deal | 265,961 | 31.5 |
| ... area describes the unit sold | 265,098 | 31.4 |
| ... not a condo unit | 252,460 | 29.9 |
| ... not a price-per-sq-ft outlier | 248,627 | 29.4 |
| ... year built known (**P1 population**) | 248,409 | 29.4 |

**Size check** (`reports/size_check.md`): raw 845,607 x 29 = 24,522,603 cells. Encoded market-sales table:
566,956 rows x 71 columns (15 numeric/derived + 5 borough + 47 building category + 4 tax class)
= **40,253,876 cells, 13.4x the 3,000,000 minimum**. The smallest test population (P1) is
248,409 x 71 = 17.6M cells.

## Basic questions and our problem statements (report Section 4)

**Basic questions** anyone would ask, answered on the exploration set:

1. *Is Manhattan the most expensive borough?* Yes by median deal price ($1.2M vs $514K-$885K
   elsewhere), but the boxes overlap heavily (f11).
2. *Do bigger homes cost more?* Yes, moderately: Spearman rho = 0.49 for 1-3 family homes (f07).
3. *Have prices risen since 2016?* Yes in every borough: +22% in Manhattan, +48-71% elsewhere (f05).
4. *Which neighbourhood is the priciest per sq ft?* Greenwich Village-West, $2,020 (f09).

**Our problem statements** (each could come out either way):

* **P1 (primary).** Within the same neighbourhood and building type, do pre-war buildings (built before
  1940) sell for more per square foot than newer ones?
* **P2.** After the July 2019 mansion-tax step at $2M, do more residential deals land just below $2M
  than before?
* **P3.** Holding building type fixed, does the share of $0-$100 ownership transfers differ between
  boroughs?
* **P4.** Within the same neighbourhood and building type, do buildings with shops sell at a different
  price per square foot from purely residential ones?

**Why they are not on the basic list.** The basic questions read one column against price, and with
250K rows any such gap is "significant". Ours compare like with like: the same neighbourhood and type
(P1, P4), the same building mix (P3), or the same narrow price window before and after a tax change,
with placebo windows where the tax did not change (P2).

**Correlation is not causation.** P2 has a causal flavour (the tax pushed prices under $2M); the
pre-tax baseline and the $1.5M / $2.5M placebo windows support that reading, but the data cannot tell
a real price cut from money moved off the deed. P1, P3 and P4 are associations.

**Dropped during planning:** COVID and Manhattan (Manhattan's per-sq-ft sample is too thin) and the
congestion toll (before 2025 the inside-vs-outside yearly gap already swung from +9.2 to -3.6 pp, so a
before/after test would wrongly credit the toll).

## EDA highlights (exploration set; full captions in `reports/eda_findings.md`)

* **f01:** 32.3% of recorded sales are <= $100 transfers. Counting each deal once, market prices have
  a median of $738K (IQR $456K-$1.2M) and run up to $2.4B, so we work in logs.
* **f02 (P3):** nominal-transfer share runs from 21.2% (Manhattan) to 37.5% (Brooklyn) before holding
  building type fixed.
* **f03:** floor area is missing because of property type (condo/co-op), not at random, so per-sq-ft
  results describe houses, rental buildings and commercial buildings.
* **f04:** year built is heaped (61% end in 0 or 5); 1940 holds 12,337 parcels vs 540 in 1939, so T1
  needs a cutoff sensitivity check.
* **f05:** Manhattan is priciest every year but rose only 22% from 2016 to 2025, vs 48-71% in the
  other boroughs.
* **f06 (P1):** pooled, pre-war buildings are +6.6% per sq ft. Within the same neighbourhood and type
  the median gap is only +1.6% (383 cells, IQR -6% to +11%), close to the 5% threshold that matters.
* **f07:** floor area vs price for 1-3 family homes, Spearman rho = 0.49; price per sq ft falls with
  size (rho = -0.26).
* **f08:** market deals in Apr-Jun 2020 were 48% below Apr-Jun 2019.
* **f09:** the priciest neighbourhood per sq ft is Greenwich Village-West ($2,020); 8 of the top 15 are
  in Manhattan and 7 in Brooklyn.
* **f10:** counting each deal once, 2024 to 2025 median price rose +1.6% inside the toll zone vs
  +6.6% outside. Counting every lot of multi-lot deals would show +10.4% vs +5.1%, driven by one $170M
  deal repeated on 280 lots.
* **f11, f12:** borough medians ($1.2M Manhattan to $514K Bronx); rank correlations among the numeric
  features.

## Hypothesis tests (report Section 5)

Plan fixed before running: `reports/test_plan.md`. Run by `src/06_tests.py` on the 30% confirmation
set only, using tests taught in the course (z, t, paired t, F, chi-square), alpha = 0.05. Full numbers:
`reports/test_results.md` and `reports/test_results.csv`; figure f13.

| Test | Method | Result | Decision | Matters? |
|---|---|---|---|---|
| T1 (P1) pre-war premium | paired t on 367 neighbourhood x type cells | +0.4% (95% CI -1.7% to +2.6%), t = 0.39, d.f. 366, p = 0.35 | do not reject | no (inside +/-5%) |
| T2 (P2) bunching below $2M | two-proportion z | 47.0% -> 69.6% below the line, +22.6 pp (+16.5 to +28.7), z = 7.41, p < 1e-13 | reject | yes (> 10 pp); placebos $1.5M/$2.5M flat |
| T3 (P3) transfers by borough, building type fixed | chi-square goodness of fit | chi2 = 461.3, d.f. 4; Manhattan -0.2 pp, Bronx -4.9 pp, Staten Island -5.5 pp vs expected | reject | yes for Bronx and Staten Island |
| T4 (P4) buildings with shops | paired t on 225 cells | -15.5% (-19.5% to -11.2%), t = -6.74, d.f. 224, p < 1e-9 | reject | yes |

## Figures in the report

f00b (Section 2), f00 (Section 3), f03, f04, f06, f10 (Section 4) and f13 (Section 5). The other
figures are referenced from this README. The report uses the `.pdf` versions; the `.png` versions are
shown here.

## Data dictionary

Full table (type, unit, range, missing %, meaning for every column): `reports/data_dictionary.md`.
Raw-column profile (blanks, zeros, commas, unique values): `reports/raw_profile.csv`.

## Contributions

| Member | Part | Files |
|---|---|---|
| Raghav (2024450) | Dataset, raw audit and size check (Section 1); README | `README.md`, `src/common.py`, `src/01_audit_raw.py`, `requirements.txt`, `.gitignore`, `data/raw/*.txt`, `reports/raw_profile.csv`, `reports/raw_problems.csv` |
| Amit (2024064) | Cleaning, multi-lot rule and the 70/30 split; before and after (Sections 2, 3) | `src/02_clean.py`, `src/03_split.py`, `src/04_tables.py`, `reports/cleaning_log.csv`, `split_strata.csv`, `ppsf_fences.csv`, `before_after.csv`, `analysis_funnel.csv`, `multi_lot_null_model.csv`, `size_check.md`, `data_dictionary.md`, `figures/f00*` |
| Harsh (2024236) | EDA figures and problem statements (Section 4) | `src/05_eda.py`, `figures/f01`-`f12`, `reports/eda_findings.md` |
| Bhudeep (2024154) | Test plan; Tests 1-2: pre-war premium and mansion tax (Section 5) | `reports/test_plan.md`, `src/06_tests.py` |
| Parth (2024406) | Tests 3-4: transfers and mixed use; limitations and report (Sections 5, 6) | `reports/test_results.*`, `figures/f13*`, `run_all.py`, `reports/run_log.txt`, `report/main.tex`, `report/main.pdf` |
