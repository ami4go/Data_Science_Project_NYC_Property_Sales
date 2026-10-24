"""Step 3 - 70 / 30 exploration / confirmation split, then data-learned outlier flags.

* Split unit = transaction (a multi-lot deal is one unit), so one deal never lands
  in both halves.
* Stratified by borough x sale year (50 strata) so both halves contain every
  borough-year: the COVID (P2) and toll (P3) questions compare years within boroughs.
* Seed 42; inside each stratum, transactions are shuffled with numpy's default_rng.
* Price-per-sq-ft outlier fences are LEARNED ON THE EXPLORATION SET ONLY and then
  applied unchanged to the confirmation set (like fitting a scaler on training data).

Writes split_assignment.csv, sales_exploration.pkl, sales_confirmation.pkl,
reports/split_strata.csv and reports/ppsf_fences.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import (CLEAN_PKL, CONFIRM_PKL, EXPLORATION_SHARE, EXPLORE_PKL, REPORTS, SEED,  # noqa: E402
                    SPLIT_CSV)

FENCE_K = 3.0       # Tukey "far out" fence on log price per sq ft
FENCE_MIN_N = 30    # categories with fewer exploration sales use the pooled fence
# Hard plausibility bounds on top of the fences. Categories that mix unit sales with
# building-level area (hotels, "other") have IQRs so wide that the Tukey fence alone
# would accept $0.01 or $10^8 per sq ft. No NYC building sold for under $10/sq ft in
# 2016-25, and the top of the residential market is ~$10,000/sq ft (we allow 2x).
PPSF_MIN, PPSF_MAX = 10.0, 20_000.0


def main():
    df = pd.read_pickle(CLEAN_PKL)
    tx = (df.groupby("transaction_id", sort=True)
            .agg(borough=("borough", "first"), sale_year=("sale_year", "first"))
            .reset_index())
    rng = np.random.default_rng(SEED)
    explore_ids = []
    for (b, y), g in tx.groupby(["borough", "sale_year"], sort=True, observed=True):
        ids = g["transaction_id"].to_numpy()
        ids = ids[rng.permutation(len(ids))]
        explore_ids.append(ids[: int(round(EXPLORATION_SHARE * len(ids)))])
    explore_ids = set(np.concatenate(explore_ids))
    df["split"] = np.where(df["transaction_id"].isin(explore_ids), "exploration", "confirmation")
    df[["row_id", "transaction_id", "split"]].to_csv(SPLIT_CSV, index=False)

    strata = (df.pivot_table(index=["borough", "sale_year"], columns="split", values="row_id",
                             aggfunc="size", observed=True).fillna(0).astype(int))
    strata["exploration_share"] = (strata["exploration"] / strata.sum(axis=1)).round(4)
    strata.to_csv(REPORTS / "split_strata.csv")
    assert (strata[["exploration", "confirmation"]] > 0).all().all(), "a stratum is empty in one half"
    print(f"rows: exploration {int((df.split == 'exploration').sum()):,}, "
          f"confirmation {int((df.split == 'confirmation').sum()):,}; "
          f"{len(strata)} borough-year strata, exploration share per stratum "
          f"{strata.exploration_share.min():.3f}-{strata.exploration_share.max():.3f}")

    # ---- outlier fences on log price per sq ft, learned on exploration only
    ex = df[(df["split"] == "exploration") & df["log_price_per_sqft"].notna()]

    def fence(x):
        q1, q3 = x.quantile([0.25, 0.75])
        return pd.Series({"n": len(x), "lo": q1 - FENCE_K * (q3 - q1), "hi": q3 + FENCE_K * (q3 - q1)})

    pooled = fence(ex["log_price_per_sqft"])
    fences = ex.groupby("building_category_code", observed=True)["log_price_per_sqft"].apply(fence).unstack()
    fences.loc[fences["n"] < FENCE_MIN_N, ["lo", "hi"]] = pooled[["lo", "hi"]].values
    fences["lo"] = fences["lo"].clip(lower=np.log(PPSF_MIN))
    fences["hi"] = fences["hi"].clip(upper=np.log(PPSF_MAX))
    pooled["lo"], pooled["hi"] = max(pooled["lo"], np.log(PPSF_MIN)), min(pooled["hi"], np.log(PPSF_MAX))
    fences["lo_usd_per_sqft"], fences["hi_usd_per_sqft"] = np.exp(fences["lo"]).round(2), np.exp(fences["hi"]).round(0)
    fences.to_csv(REPORTS / "ppsf_fences.csv")

    f = df["building_category_code"].astype(str).map(fences["lo"]).fillna(pooled["lo"]), \
        df["building_category_code"].astype(str).map(fences["hi"]).fillna(pooled["hi"])
    lp = df["log_price_per_sqft"]
    df["ppsf_outlier"] = lp.notna() & ((lp < f[0].astype(float)) | (lp > f[1].astype(float)))
    for s in ["exploration", "confirmation"]:
        part = df[df.split == s]
        print(f"{s}: price-per-sq-ft outliers {int(part.ppsf_outlier.sum()):,} of "
              f"{int(part.log_price_per_sqft.notna().sum()):,}")

    df[df.split == "exploration"].reset_index(drop=True).to_pickle(EXPLORE_PKL)
    df[df.split == "confirmation"].reset_index(drop=True).to_pickle(CONFIRM_PKL)


if __name__ == "__main__":
    main()
