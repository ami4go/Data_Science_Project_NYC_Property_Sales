"""Step 2 - deterministic cleaning of every raw row.

Only fixed rules live here (no thresholds learned from the data), so the same
rules apply to the exploration and confirmation sets alike. Rows are *flagged*
rather than deleted wherever a later test still needs them (e.g. $0 transfers
are kept for T4). The only rows removed are exact duplicate records.

Writes:
    data/processed/sales_clean.pkl   cleaned rows + flags + derived columns
    reports/cleaning_log.csv         one line per rule: rows affected, action
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import (BOROUGHS, CLEAN_PKL, LOW_PRICE_MAX, MEGA_PRICE_MIN, MIN_YEAR_BUILT,  # noqa: E402
                    NOMINAL_MAX, PREWAR_CUTOFF, RAW_CSV, REPORTS, TOLL_START, toll_line_lat)

RENAME = {
    "BOROUGH": "borough_code", "NEIGHBORHOOD": "neighborhood",
    "BUILDING CLASS CATEGORY": "building_category",
    "TAX CLASS AS OF FINAL ROLL": "tax_class_final_roll", "BLOCK": "block", "LOT": "lot",
    "EASE-MENT": "easement", "BUILDING CLASS AS OF FINAL ROLL": "building_class_final_roll",
    "ADDRESS": "address", "APARTMENT NUMBER": "apartment_number", "ZIP CODE": "zip_code",
    "RESIDENTIAL UNITS": "residential_units", "COMMERCIAL UNITS": "commercial_units",
    "TOTAL UNITS": "total_units", "LAND SQUARE FEET": "land_sqft",
    "GROSS SQUARE FEET": "gross_sqft", "YEAR BUILT": "year_built",
    "TAX CLASS AT TIME OF SALE": "tax_class_at_sale",
    "BUILDING CLASS AT TIME OF SALE": "building_class_at_sale", "SALE PRICE": "sale_price",
    "SALE DATE": "sale_date", "Latitude": "latitude", "Longitude": "longitude",
    "Community Board": "community_board", "Council District": "council_district",
    "BIN": "bin", "BBL": "bbl", "Census Tract 2020": "census_tract_2020",
    "Neighborhood Tabulation Area (NTA) (2020)": "nta_2020",
}

# Generous box around the five boroughs; points outside it are geocoding errors.
NYC_LAT, NYC_LON = (40.49, 40.92), (-74.27, -73.68)
# Co-ops (09, 10, 17) sell shares in one apartment, and special condo billing lots (11)
# carry the whole condominium, yet GROSS SQUARE FEET is the entire building's area.
AREA_IS_BUILDING_CATS = ["09", "10", "11", "17"]

log = []


def note(step, problem, rows, action, why):
    log.append({"step": step, "problem": problem, "rows_affected": int(rows),
                "action": action, "why": why})
    print(f"[{step:>2}] {problem}: {int(rows):,} rows -> {action}")


def num(s):
    return pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")


def main():
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False, na_values=[])
    n_raw = len(raw)
    df = raw.rename(columns=RENAME)
    df.insert(0, "row_id", np.arange(n_raw))  # position in the frozen CSV, for traceability

    # 1. whitespace: strip every text cell, empty string -> missing
    text_cols = [c for c in df.columns if c != "row_id"]
    for c in text_cols:
        df[c] = df[c].str.strip().replace("", pd.NA)

    # 2. empty column
    note(2, "EASE-MENT column empty", df["easement"].isna().sum(), "drop column",
         "carries no information (100% blank)")
    df = df.drop(columns="easement")

    # 3. labels written several ways
    before_cat = df["building_category"].nunique()
    df["building_category"] = df["building_category"].str.upper().str.replace(r"\s+", " ", regex=True)
    note(3, f"building category: {before_cat} raw labels -> {df['building_category'].nunique()}",
         (raw["BUILDING CLASS CATEGORY"].str.strip() != raw["BUILDING CLASS CATEGORY"]
          .str.strip().str.replace(r"\s+", " ", regex=True)).sum(),
         "collapse repeated spaces, upper-case",
         "otherwise one-hot encoding splits one category into two columns")
    df["building_category_code"] = df["building_category"].str.extract(r"^(\d+[A-Z]?)")[0]
    before_nb = df["neighborhood"].nunique()
    df["neighborhood"] = df["neighborhood"].str.upper().str.replace(r"\s+", " ", regex=True)
    note(3, f"neighbourhood: {before_nb} raw labels -> {df['neighborhood'].nunique()}", 0,
         "collapse repeated spaces, upper-case", "same reason as building category")

    # 4. borough code -> name
    df["borough_code"] = pd.to_numeric(df["borough_code"], errors="coerce").astype("Int64")
    bad_boro = ~df["borough_code"].isin(list(BOROUGHS))
    note(4, "borough stored as code 1-5", n_raw, "decode to names",
         f"readable; {int(bad_boro.sum())} codes outside 1-5")
    df.insert(1, "borough", df["borough_code"].map(BOROUGHS).astype("string"))

    # 5. numbers stored as text
    for c in ["land_sqft", "gross_sqft", "residential_units", "commercial_units",
              "total_units", "year_built", "sale_price", "latitude", "longitude"]:
        df[c] = num(df[c])
    for c in ["block", "lot", "tax_class_at_sale"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    note(5, "square feet stored as text with commas", raw["GROSS SQUARE FEET"].str.contains(",").sum(),
         "strip commas, convert to numbers", "cannot compute price per sq ft on text")

    # 6. zero floor / land area = not recorded
    for c in ["gross_sqft", "land_sqft"]:
        z = (df[c] == 0) | df[c].isna()
        note(6, f"{c} blank or 0", z.sum(), "set to missing",
             "no building has 0 sq ft; 0 means 'not recorded' (condo/co-op units carry no floor area)")
        df.loc[df[c] == 0, c] = np.nan

    # 7. sale date
    df["sale_date"] = pd.to_datetime(df["sale_date"], format="%m/%d/%Y", errors="coerce")
    note(7, "sale date unparseable", df["sale_date"].isna().sum(), "left missing", "-")
    df["sale_year"] = df["sale_date"].dt.year.astype("Int64")
    df["sale_month"] = df["sale_date"].dt.month.astype("Int64")
    df["sale_quarter"] = df["sale_date"].dt.to_period("Q").astype("string")

    # 8. year built
    yb = df["year_built"]
    note(8, "year built missing or 0", (yb.isna() | (yb == 0)).sum(), "set to missing",
         "0 is a placeholder, not a year")
    imp = (yb > 0) & (yb < MIN_YEAR_BUILT)
    note(8, f"year built 1-{MIN_YEAR_BUILT - 1} (impossible)", imp.sum(), "set to missing",
         "typos; no such building stock in NYC")
    df.loc[(yb == 0) | imp, "year_built"] = np.nan
    future = df["year_built"] > df["sale_year"] + 3
    note(8, "year built > 3 years after the sale", future.sum(), "flag (year_built_suspect)",
         "off-plan condo sales happen before completion, but >3 years is implausible")
    df["year_built_suspect"] = future

    # 9. units
    res, com, tot = df["residential_units"], df["commercial_units"], df["total_units"]
    fill = tot.isna() & res.notna() & com.notna()
    note(9, "total units blank but parts present", fill.sum(), "total = residential + commercial",
         "recovers a value the data already implies")
    df.loc[fill, "total_units"] = res[fill] + com[fill]
    tot = df["total_units"]
    incons = res.notna() & com.notna() & tot.notna() & (res + com != tot)
    note(9, "residential + commercial != total", incons.sum(), "flag (units_inconsistent)",
         "cannot tell which of the three numbers is wrong, so keep and flag")
    df["units_inconsistent"] = incons

    # 10. ZIP and coordinates
    df.loc[df["zip_code"].isin(["0", "00000"]), "zip_code"] = pd.NA
    note(10, "ZIP missing or 0", df["zip_code"].isna().sum(), "set to missing", "0 is not a ZIP code")
    out = (df["latitude"].notna() & (~df["latitude"].between(*NYC_LAT) | ~df["longitude"].between(*NYC_LON)))
    note(10, "coordinates outside NYC", out.sum(), "set to missing", "geocoding error")
    df.loc[out, ["latitude", "longitude"]] = np.nan
    note(10, "no latitude / longitude", df["latitude"].isna().sum(), "keep; excluded from toll-zone test only",
         "cannot place the sale on a map, but the sale itself is valid")

    # 11. Two different identifiers hide in the data. The BBL column is the *building*
    # BBL (for condos it is the 75xx billing lot shared by every unit), while borough-
    # block-lot identifies the individual unit/parcel. Keep both, under honest names.
    bbl_lot = (df["borough_code"].astype("Int64") * 1_000_000_000 + df["block"] * 10_000
               + df["lot"]).astype("string")
    blank_bbl = df["bbl"].isna() | (df["bbl"] == "0")
    note(11, "BBL blank or 0", blank_bbl.sum(), "set to missing (bbl_building)",
         "0 is not a BBL; borough-block-lot still identifies the parcel")
    df.loc[blank_bbl, "bbl"] = pd.NA
    mism = df["bbl"].notna() & (df["bbl"] != bbl_lot)
    note(11, "BBL differs from borough-block-lot (condo billing lot)", mism.sum(),
         "keep as bbl_building; add bbl_lot from borough-block-lot",
         "the BBL column is building-level, so it cannot separate condo units")
    df = df.rename(columns={"bbl": "bbl_building"})
    df["bbl_lot"] = bbl_lot

    # 12. duplicates
    dup_full = df.drop(columns="row_id").duplicated(keep="first")
    note(12, "exact duplicate rows (every column equal)", dup_full.sum(), "drop extra copies",
         "the same sale recorded twice would be counted twice")
    df = df[~dup_full].copy()
    key = ["bbl_lot", "apartment_number", "address", "sale_date", "sale_price"]
    dup_key = df.duplicated(key, keep=False)
    note(12, "same lot+unit+address+date+price but other columns differ", dup_key.sum(),
         "flag (possible_duplicate), keep", "differences (e.g. units, class) mean we cannot tell which copy is right")
    df["possible_duplicate"] = dup_key

    # 13. price classes
    p = df["sale_price"]
    df["price_class"] = pd.Series(np.select(
        [p.isna(), p <= NOMINAL_MAX, p <= LOW_PRICE_MAX], ["missing", "nominal", "low"], "market"),
        index=df.index, dtype="string")
    note(13, f"sale price <= ${NOMINAL_MAX} (ownership transfer)", (df.price_class == "nominal").sum(),
         "flag nominal; exclude from price analysis, keep for transfer-share test (T4)",
         "a deed transfer between relatives/entities is not a market price")
    note(13, f"sale price ${NOMINAL_MAX + 1}-${LOW_PRICE_MAX:,}", (df.price_class == "low").sum(),
         "flag low; exclude from price analysis", "not a credible NYC market price for any property")
    df["is_market"] = df["price_class"] == "market"
    df["is_mega"] = p > MEGA_PRICE_MIN
    note(13, "sale price > $100M", df["is_mega"].sum(), "keep, analyse on log scale",
         "real portfolio / trophy deals; log scale stops them dominating")

    # 14. multi-lot transactions: one deed covering several lots repeats the TOTAL price on
    # every lot. Rule: same borough + date + exact price AND (>= 2 lots on the same block,
    # or >= MULTI_LOT_CROSS_BLOCK lots overall). A date-shuffled null model (seed 42) gives
    # ~550 same-block groups by chance vs 12,473 observed, but as many 2-lot cross-block
    # groups by chance as observed (~26,800 vs 24,557): those are coincidences
    # (two $650,000 co-ops on the same day), so they are not flagged.
    MULTI_LOT_CROSS_BLOCK = 6
    m = df[df["is_market"]]
    deal = ["borough_code", "sale_date", "sale_price"]
    lots_in_block = m.groupby(deal + ["block"])["lot"].transform("nunique")
    lots_in_deal = m.groupby(deal)["bbl_lot"].transform("nunique")
    same_block = lots_in_block >= 2
    big_cross = lots_in_deal >= MULTI_LOT_CROSS_BLOCK
    df["multi_lot_sale"] = False
    df.loc[m.index, "multi_lot_sale"] = same_block | big_cross
    deal_id = m.groupby(deal).ngroup().astype(str)
    block_id = m.groupby(deal + ["block"]).ngroup().astype(str)
    tx = pd.Series("R" + df["row_id"].astype(str), index=df.index)
    tx.loc[m.index[same_block.values]] = "B" + block_id[same_block.values]
    tx.loc[m.index[big_cross.values]] = "D" + deal_id[big_cross.values]
    df["transaction_id"] = tx
    note(14, "multi-lot deal: same borough+date+price on >= 2 lots of one block", same_block.sum(),
         "flag multi_lot_sale; exclude from per-sq-ft analysis",
         "the price is the total for several lots, so price / one lot's area is inflated")
    note(14, f"multi-lot deal: same borough+date+price on >= {MULTI_LOT_CROSS_BLOCK} lots", big_cross.sum(),
         "flag multi_lot_sale; exclude from per-sq-ft analysis",
         "portfolio deals; below 6 lots across blocks, chance matches explain most groups")
    # A multi-lot deal repeats its total price on every lot, so any statistic of the
    # price itself (medians, trends, tests on log price) must count the deal once.
    # One $170M condo-hotel deal over 280 lots would otherwise weigh as 280 sales.
    df["first_in_transaction"] = ~df.duplicated("transaction_id", keep="first")
    n_deals = int((df["is_market"] & df["first_in_transaction"]).sum())
    note(14, f"price statistics: {int(df['is_market'].sum()):,} market rows = {n_deals:,} market deals",
         int((df["is_market"] & ~df["first_in_transaction"]).sum()),
         "flag first_in_transaction; price-level statistics use one row per deal",
         "the repeated rows carry the deal's total price, not their own")

    # 15. area that describes the building, not the unit that was sold
    mismatch = df["building_category_code"].isin(AREA_IS_BUILDING_CATS) & df["gross_sqft"].notna()
    note(15, "co-op / condo-billing-lot sale with the whole building's floor area", mismatch.sum(),
         "no price per sq ft for these rows",
         "the sale is one apartment (or co-op shares) but the area is the whole building "
         "(median $2-5 per sq ft)")
    df["area_unit_mismatch"] = mismatch
    # Condo units carry their own floor area only in 2018 (and early 2019); in every other
    # year it is blank. Keeping it would make any per-sq-ft comparison across years or
    # places depend on how many 2018 condo sales happen to be in a group.
    condo = (df["building_category"].astype(str).str.contains("CONDO") & ~mismatch
             & df["gross_sqft"].notna())
    by_year = (df[df["building_category"].astype(str).str.contains("CONDO")]
               .groupby("sale_year")["gross_sqft"].apply(lambda s: round(100 * s.notna().mean(), 1)))
    note(15, "condo unit with floor area (% of condo sales with area, by year: "
         + ", ".join(f"{y} {v}%" for y, v in by_year.items() if v > 0) + ")", condo.sum(),
         "keep area, but no price per sq ft for condo units",
         "the measurement exists for one year only, so it is not comparable over time")
    df["condo_area_one_year"] = condo

    # 16. derived columns
    df["log10_price"] = np.where(df["is_market"], np.log10(df["sale_price"].where(df["is_market"])), np.nan)
    ok = (df["is_market"] & df["gross_sqft"].notna() & ~df["multi_lot_sale"] & ~df["area_unit_mismatch"]
          & ~df["condo_area_one_year"])
    df["price_per_sqft"] = np.where(ok, df["sale_price"] / df["gross_sqft"], np.nan)
    df["log_price_per_sqft"] = np.log(df["price_per_sqft"])
    df["prewar"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    has_yb = df["year_built"].notna()
    df.loc[has_yb, "prewar"] = df.loc[has_yb, "year_built"] < PREWAR_CUTOFF
    df["building_age_at_sale"] = df["sale_year"] - df["year_built"]
    df["period"] = pd.Series(np.select(
        [df["sale_year"] <= 2019, df["sale_year"] <= 2021, df["sale_year"] <= 2023],
        ["pre-COVID 2016-19", "COVID 2020-21", "recovery 2022-23"], "2024-25"),
        index=df.index, dtype="string")
    df["post_toll"] = df["sale_date"] >= pd.Timestamp(TOLL_START)
    man = (df["borough"] == "Manhattan") & df["latitude"].notna()
    df["toll_zone"] = pd.Series(pd.NA, index=df.index, dtype="boolean")
    df.loc[man, "toll_zone"] = df.loc[man, "latitude"] <= toll_line_lat(df.loc[man, "longitude"])
    # check the line on sales whose address names a cross street (e.g. "10 EAST 60TH STREET")
    street = df.loc[man, "address"].str.extract(
        r"^\S+\s+(?:EAST|WEST)\s+(\d+)(?:ST|ND|RD|TH)?\s+STREET\b")[0].astype(float)
    near = street.between(50, 70)
    agree = (df.loc[man, "toll_zone"][near] == (street[near] <= 60)).mean()
    note(16, "toll-zone line check: Manhattan sales on East/West 50th-70th St", near.sum(),
         f"line agrees with the street number for {100 * agree:.2f}% of them",
         "validates the coordinate approximation of '60th St and below'")

    # tidy dtypes
    for c in ["borough", "neighborhood", "building_category", "building_category_code",
              "tax_class_final_roll", "building_class_final_roll", "building_class_at_sale",
              "zip_code", "community_board", "council_district", "nta_2020", "census_tract_2020"]:
        df[c] = df[c].astype("category")

    df = df.reset_index(drop=True)
    df.to_pickle(CLEAN_PKL)
    pd.DataFrame(log).to_csv(REPORTS / "cleaning_log.csv", index=False)
    print(f"\nclean: {len(df):,} rows x {df.shape[1]} columns -> {CLEAN_PKL.name}")


if __name__ == "__main__":
    main()
