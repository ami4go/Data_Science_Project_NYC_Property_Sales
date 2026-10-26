# Do pre-war buildings still sell at a premium? NYC property sales, 2016-2025

CSE558 Data Science (Monsoon 2026) midterm project, **Team Amigos**.
The full write-up is the report: [`report/main.pdf`](report/main.pdf).

## Data

* **Source:** NYC Department of Finance, *NYC Citywide Annualized Calendar Sales Update*
  (NYC Open Data, dataset `w2pb-icbu`), downloaded 20 Oct 2026.
* **Size:** 845,607 sales x 29 columns. One row = one recorded sale of one tax lot.
* **Frozen copy:** [`data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip`](data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip).
  The city keeps updating the dataset, so always use this copy; the code checks its SHA-256
  (`data/raw/SHA256.txt`) and stops on any other file.

## Results (30% confirmation set, alpha = 0.05)

| Test | Question | Result |
|---|---|---|
| T1 | Within the same neighbourhood and building type, do pre-war buildings sell for more per sq ft? | **No meaningful premium:** +0.4% (95% CI -1.7% to +2.6%), paired t, p = 0.35. The 7% citywide gap is location, not age. |
| T2 | After the 2019 mansion tax at $2M, do more deals land just below $2M? | **Yes:** 47% -> 70% of nearby deals sit just below $2M (z = 7.41). No change at $1.5M or $2.5M, where the tax did not step. |
| T3 | Holding building type fixed, do boroughs differ in $0 ownership transfers? | **Yes, but not Manhattan:** its low share is explained by its condos and co-ops; the Bronx and Staten Island are about 5 pp below expectation (chi-square). |
| T4 | Do buildings with shops sell at a different price per sq ft? | **Yes, about 15% less** (95% CI -19.5% to -11.2%), paired t. |

## How to run

```bash
pip install -r requirements.txt
```

```bash
python -m zipfile -e data/raw/NYC_Citywide_Annualized_Calendar_Sales_Update.zip data/raw/
```

```bash
python run_all.py
```

Takes about 3 minutes and regenerates every file in `reports/` and `figures/` byte for byte
(tested on Python 3.10).

## What is where

| Path | Contents |
|---|---|
| `src/01_audit_raw.py` | Checks the raw file and counts its problems |
| `src/02_clean.py` | Cleaning rules (flags rather than deletions) |
| `src/03_split.py` | 70% exploration / 30% confirmation split, seed 42 |
| `src/04_tables.py` | Before/after table, size check, data dictionary |
| `src/05_eda.py` | EDA figures, exploration set only |
| `src/06_tests.py` | The four hypothesis tests, confirmation set only |
| `src/common.py` | Shared paths, seed and settings |
| `reports/` | Tables and logs; `test_plan.md` (written before testing), `test_results.md`, `data_dictionary.md` |
| `figures/` | All figures (PDF for the report, PNG for viewing) |
| `report/` | The report (`main.tex`, `main.pdf`) |

## Team

| Member | Roll no. | Part |
|---|---|---|
| Raghav | 2024450 | Dataset, raw audit and size check; README |
| Amit | 2024064 | Cleaning, multi-lot rule and the 70/30 split; before and after |
| Harsh | 2024236 | EDA figures and problem statements |
| Bhudeep | 2024154 | Test plan; Tests 1-2 |
| Parth | 2024406 | Tests 3-4; limitations and report |
