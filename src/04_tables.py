"""Step 4 - report tables: before/after, encoding + 3M size check, data dictionary,
and the funnel of rows that reach each analysis.

Counts only (no prices compared against anything), so this may use all rows.
Writes reports/before_after.csv, reports/size_check.md, reports/data_dictionary.md,
reports/analysis_funnel.csv and figures/f00_analysis_funnel.png.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import (COL_W, CONFIRM_PKL, EXPLORE_PKL, INK_2, RAW_CSV, REPORTS, SERIES, save,  # noqa: E402
                    setup_style)
import matplotlib.pyplot as plt  # noqa: E402

NUMERIC_FEATURES = [  # 15 numeric / derived model inputs
    "residential_units", "commercial_units", "total_units", "land_sqft", "gross_sqft",
    "year_built", "building_age_at_sale", "sale_year", "sale_month", "latitude", "longitude",
    "log10_price", "log_price_per_sqft", "prewar", "toll_zone",
]
ONE_HOT = ["borough", "building_category", "tax_class_at_sale"]

# column -> (type, unit / format, real-world meaning)
DICTIONARY = {
    "borough": ("Nominal", "name (from code 1-5)", "Borough of the property"),
    "neighborhood": ("Nominal", "text", "DOF assessor neighbourhood"),
    "building_category": ("Nominal", "code + text", "Building class category (e.g. 01 ONE FAMILY DWELLINGS)"),
    "tax_class_final_roll": ("Nominal", "code", "Tax class on the final roll (present)"),
    "block": ("Identifier", "integer", "Tax block"),
    "lot": ("Identifier", "integer", "Tax lot"),
    "building_class_final_roll": ("Nominal", "code", "Building class on the final roll (present)"),
    "address": ("Identifier", "text", "Street address (co-op unit often appended)"),
    "apartment_number": ("Identifier", "text", "Unit number (condos)"),
    "zip_code": ("Nominal", "5 digits", "Postal code"),
    "residential_units": ("Discrete", "count", "Residential units on the lot"),
    "commercial_units": ("Discrete", "count", "Commercial units on the lot"),
    "total_units": ("Discrete", "count", "Total units"),
    "land_sqft": ("Continuous", "sq ft", "Lot area"),
    "gross_sqft": ("Continuous", "sq ft", "Total floor area of the building(s)"),
    "year_built": ("Discrete", "year", "Year the structure was built (assessor estimate)"),
    "tax_class_at_sale": ("Nominal", "code 1-4", "Tax class at the time of sale"),
    "building_class_at_sale": ("Nominal", "code", "Building class at the time of sale"),
    "sale_price": ("Continuous", "US$", "Recorded sale price (RESPONSE)"),
    "sale_date": ("Date", "YYYY-MM-DD", "Date the deed was recorded"),
    "latitude": ("Continuous", "degrees", "Geocoded latitude"),
    "longitude": ("Continuous", "degrees", "Geocoded longitude"),
    "community_board": ("Nominal", "code", "Community board"),
    "council_district": ("Nominal", "code", "City council district"),
    "bin": ("Identifier", "code", "Building identification number"),
    "bbl_building": ("Identifier", "code", "Raw BBL column: building-level (condo billing lot)"),
    "census_tract_2020": ("Nominal", "code", "2020 census tract"),
    "nta_2020": ("Nominal", "code", "2020 Neighbourhood Tabulation Area"),
    "bbl_lot": ("Identifier", "code", "DERIVED borough*1e9 + block*1e4 + lot (unit/parcel)"),
    "price_class": ("Nominal", "nominal / low / market", "DERIVED <=$100, $101-$10k, >$10k"),
    "multi_lot_sale": ("Nominal", "bool", "DERIVED one deed over several lots (price is the total)"),
    "transaction_id": ("Identifier", "code", "DERIVED one id per deal (R = single lot, B/D = multi-lot)"),
    "first_in_transaction": ("Nominal", "bool", "DERIVED first row of its deal; price statistics use these rows"),
    "price_per_sqft": ("Continuous", "US$ / sq ft", "DERIVED sale_price / gross_sqft (valid rows only)"),
    "log10_price": ("Continuous", "log10 US$", "DERIVED, market sales only"),
    "prewar": ("Nominal", "bool", "DERIVED year_built < 1940"),
    "building_age_at_sale": ("Discrete", "years", "DERIVED sale_year - year_built"),
    "period": ("Nominal", "4 levels", "DERIVED pre-COVID / COVID / recovery / 2024-25"),
    "toll_zone": ("Nominal", "bool", "DERIVED Manhattan, 60th St and below (from coordinates)"),
    "post_toll": ("Nominal", "bool", "DERIVED sale on/after 5 Jan 2025"),
}


def multi_lot_null_model(df):
    """Justify the multi-lot rule: observed same-price/same-day lot groups vs a null
    model where sale dates are shuffled within borough x year (seed 42)."""
    m = df[df["is_market"]][["borough_code", "block", "bbl_lot", "sale_date", "sale_price", "sale_year"]]

    def kinds(d):
        g = d.groupby(["borough_code", "sale_date", "sale_price"]).agg(
            nlots=("bbl_lot", "nunique"), nblocks=("block", "nunique"))
        g = g[g["nlots"] >= 2]
        return pd.Series({
            "Same block, 2+ lots": int((g.nblocks == 1).sum()),
            "Different blocks, 2 lots": int(((g.nblocks > 1) & (g.nlots == 2)).sum()),
            "Different blocks, 3-5 lots": int(((g.nblocks > 1) & g.nlots.between(3, 5)).sum()),
            "Different blocks, 6+ lots": int(((g.nblocks > 1) & (g.nlots >= 6)).sum()),
        })

    rng = np.random.default_rng(42)
    shuffled = m.copy()
    shuffled["sale_date"] = (shuffled.groupby(["borough_code", "sale_year"])["sale_date"]
                             .transform(lambda x: x.to_numpy()[rng.permutation(len(x))]))
    t = pd.DataFrame({"observed": kinds(m), "expected_by_chance": kinds(shuffled)})
    t["flagged"] = ["yes", "no", "no", "yes"]
    t.to_csv(REPORTS / "multi_lot_null_model.csv")
    print(t)

    fig, ax = plt.subplots(figsize=(COL_W, 1.95))
    y = np.arange(len(t))[::-1]
    ax.barh(y + 0.19, t["observed"], height=0.36, color=SERIES[0], label="Observed")
    ax.barh(y - 0.19, t["expected_by_chance"], height=0.36, color="#c3c2b7", label="By chance (dates shuffled)")
    for yi, (o, e) in zip(y, t[["observed", "expected_by_chance"]].to_numpy()):
        ax.text(max(o, e) + 500, yi, f"{o:,} vs {e:,}", va="center", fontsize=6.5, color=INK_2)
    ax.set_yticks(y, [f"{i}\n({'flagged' if f == 'yes' else 'not flagged'})" for i, f in zip(t.index, t.flagged)])
    ax.set_xlim(0, t.to_numpy()[:, :2].astype(float).max() * 1.45)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
    ax.set_xlabel("Lot groups: same borough, day and price")
    ax.grid(axis="y", visible=False)
    fig.legend(*ax.get_legend_handles_labels(), loc="outside lower center", ncol=2)
    save(fig, "f00b_multi_lot_null_model")


def main():
    setup_style()
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False, na_values=[])
    raw_missing = int(raw.apply(lambda s: s.str.strip().eq("")).sum().sum())
    df = pd.concat([pd.read_pickle(EXPLORE_PKL), pd.read_pickle(CONFIRM_PKL)], ignore_index=True)
    multi_lot_null_model(df)

    # -------------------------------------------------------------- funnel
    steps = [("Raw rows", len(raw))]
    m = pd.Series(True, index=df.index)
    steps.append(("After dropping exact duplicates", int(m.sum())))
    for label, cond in [
        ("Market sales (> $10,000)", df["is_market"]),
        ("... with floor area recorded", df["gross_sqft"].notna()),
        ("... not a multi-lot deal", ~df["multi_lot_sale"]),
        ("... area describes the unit sold", ~df["area_unit_mismatch"]),
        ("... not a condo unit (area recorded mainly in 2018)", ~df["condo_area_one_year"]),
        ("... price per sq ft not an outlier", ~df["ppsf_outlier"]),
        ("... year built known (P1 population)", df["year_built"].notna()),
    ]:
        m &= cond
        steps.append((label, int(m.sum())))
    funnel = pd.DataFrame(steps, columns=["step", "rows"])
    funnel["pct_of_raw"] = (100 * funnel["rows"] / len(raw)).round(1)
    funnel.to_csv(REPORTS / "analysis_funnel.csv", index=False)
    print(funnel.to_string(index=False))

    short = ["Raw rows", "Exact duplicates removed", "Market sales (> $10K)", "+ floor area recorded",
             "+ not a multi-lot deal", "+ area is the unit's own", "+ not a condo unit",
             "+ not a $/sq ft outlier", "+ year built known (P1)"]
    fig, ax = plt.subplots(figsize=(COL_W, 2.15))
    y = np.arange(len(funnel))[::-1]
    ax.barh(y, funnel["rows"], height=0.6, color=SERIES[0])
    for yi, (_, r) in zip(y, funnel.iterrows()):
        ax.text(r["rows"] + 10_000, yi, f"{r['rows']:,} ({r['pct_of_raw']:.0f}%)", va="center",
                fontsize=6.5, color=INK_2)
    ax.set_yticks(y, short)
    ax.set_xlim(0, len(raw) * 1.42)
    ax.xaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
    ax.set_xlabel("Rows")
    ax.grid(axis="y", visible=False)
    save(fig, "f00_analysis_funnel")

    # -------------------------------------------------------------- encoding / size check
    mk = df[df["is_market"]].copy()
    X = mk[NUMERIC_FEATURES].astype(float)
    dummies = pd.get_dummies(mk[ONE_HOT].astype(str), dtype=np.uint8)
    levels = {c: int(mk[c].astype(str).nunique()) for c in ONE_HOT}
    n_rows, n_cols = len(mk), X.shape[1] + dummies.shape[1]
    nb = int(mk["neighborhood"].nunique())
    lines = [
        "# Size check (rows x columns >= 3,000,000)", "",
        f"* Raw: {len(raw):,} rows x {raw.shape[1]} columns = {len(raw) * raw.shape[1]:,} cells.",
        f"* Cleaned (all rows, flags kept): {len(df):,} rows x {df.shape[1] - 1} columns.",
        f"* Encoded model table (market sales only): {n_rows:,} rows x {n_cols} columns "
        f"({len(NUMERIC_FEATURES)} numeric/derived + " + " + ".join(f"{v} {k}" for k, v in levels.items())
        + f" one-hot) = {n_rows * n_cols:,} cells = {n_rows * n_cols / 3e6:.1f} x the 3,000,000 minimum.",
        f"* Adding neighbourhood one-hot ({nb} levels) gives {n_cols + nb} columns = "
        f"{n_rows * (n_cols + nb):,} cells.",
        f"* Step that clears 3M: already the raw table does; encoding the 3 categoricals adds "
        f"{dummies.shape[1] - len(ONE_HOT)} columns.",
    ]
    p1 = int(funnel["rows"].iloc[-1])
    lines.append(f"* Smallest test population (P1, price per sq ft with year built): {p1:,} x {n_cols} = "
                 f"{p1 * n_cols:,} cells.")
    (REPORTS / "size_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))

    # -------------------------------------------------------------- before / after
    zero_placeholders = sum(int(pd.to_numeric(raw[c].str.replace(",", ""), errors="coerce").eq(0).sum())
                            for c in ["LAND SQUARE FEET", "GROSS SQUARE FEET", "YEAR BUILT", "ZIP CODE", "BBL"])
    original = ["neighborhood", "building_category", "tax_class_final_roll", "block", "lot",
                "building_class_final_roll", "address", "apartment_number", "zip_code",
                "residential_units", "commercial_units", "total_units", "land_sqft", "gross_sqft",
                "year_built", "tax_class_at_sale", "building_class_at_sale", "sale_price", "sale_date",
                "latitude", "longitude", "community_board", "council_district", "bin", "bbl_building",
                "census_tract_2020", "nta_2020", "borough"]
    cleaned_missing = int(df[original].isna().sum().sum())
    ba = pd.DataFrame([
        ("Rows", len(raw), len(df)),
        ("Columns", raw.shape[1], df.shape[1] - 1),  # minus the 'split' helper column
        ("Blank cells (raw) / missing cells in the 28 kept original columns (cleaned)", raw_missing, cleaned_missing),
        ("  of which EASE-MENT (column dropped)", len(raw), 0),
        ("  hidden missing: 0 used as 'not recorded' (sq ft, year, ZIP, BBL)", zero_placeholders, 0),
        ("Exact duplicate rows", len(raw) - len(df), 0),
        ("Building-category labels", int(raw["BUILDING CLASS CATEGORY"].nunique()),
         int(df["building_category"].nunique())),
        ("Numeric columns stored as text", 2, 0),
        ("Market-price rows (before: > $100 raw; after: > $10,000, deduplicated)", int((pd.to_numeric(raw["SALE PRICE"]) > 100).sum()), int(df["is_market"].sum())),
        ("Market deals (a multi-lot deal counted once; used for price statistics)", None,
         int((df["is_market"] & df["first_in_transaction"]).sum())),
        ("Rows with a valid price per sq ft", None, int(df["price_per_sqft"].notna().sum() - df["ppsf_outlier"].sum())),
        ("Flagged multi-lot deal rows", None, int(df["multi_lot_sale"].sum())),
        ("Flagged price-per-sq-ft outliers", None, int(df["ppsf_outlier"].sum())),
    ], columns=["measure", "before", "after"])
    ba.to_csv(REPORTS / "before_after.csv", index=False)
    print(ba.to_string(index=False))

    # -------------------------------------------------------------- data dictionary
    rows = []
    for c, (typ, unit, meaning) in DICTIONARY.items():
        s = df[c]
        miss = 100 * s.isna().mean()
        if pd.api.types.is_bool_dtype(s) or str(s.dtype) == "boolean":
            rng = f"True {100 * s.astype('float').mean():.1f}%"
        elif pd.api.types.is_numeric_dtype(s):
            rng = f"{s.min():,.4g} to {s.max():,.4g}"
        elif pd.api.types.is_datetime64_any_dtype(s):
            rng = f"{s.min():%Y-%m-%d} to {s.max():%Y-%m-%d}"
        else:
            rng = f"{s.nunique():,} values"
        rows.append(f"| `{c}` | {typ} | {unit} | {rng} | {miss:.1f}% | {meaning} |")
    md = ["| column | type | unit / format | range (cleaned, all rows) | missing | meaning |",
          "|---|---|---|---|---|---|", *rows]
    (REPORTS / "data_dictionary.md").write_text("\n".join(md) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
