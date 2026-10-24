"""Step 1 - audit the frozen raw CSV (the "before" side of the report).

Checks the file's SHA-256 against data/raw/SHA256.txt and its shape against the
frozen download, reads every column as text so nothing is silently converted,
profiles every column for the data dictionary and counts each data problem. Writes:
    reports/raw_profile.csv      one row per raw column (type, missing, range ...)
    reports/raw_problems.csv     each data problem with its row count
"""
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import EXPECTED_RAW_COLS, EXPECTED_RAW_ROWS, RAW_CSV, REPORTS  # noqa: E402


def to_num(s):
    """Text -> number, removing thousands separators; '' -> NaN."""
    t = s.str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(t.where(t != ""), errors="coerce")


def check_sha256():
    """Stop unless the raw CSV is byte-for-byte the frozen download."""
    expected = (RAW_CSV.parent / "SHA256.txt").read_text().split()[0].lower()
    h = hashlib.sha256()
    with open(RAW_CSV, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    print(f"SHA-256 {h.hexdigest()}")
    assert h.hexdigest() == expected, (
        "raw CSV differs from the frozen copy (the city updates this dataset); "
        "use the frozen file linked in the README")


def main():
    check_sha256()
    raw = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False, na_values=[])
    n, k = raw.shape
    print(f"raw shape: {n:,} rows x {k} columns  (= {n * k:,} cells)")
    assert (n, k) == (EXPECTED_RAW_ROWS, EXPECTED_RAW_COLS), "download differs from the frozen copy"

    # ---------------------------------------------------------- column profile
    rows = []
    for c in raw.columns:
        s = raw[c]
        blank = s.str.strip().eq("")
        num = to_num(s)
        numeric_share = num.notna().sum() / max((~blank).sum(), 1)
        rec = {
            "column": c,
            "blank": int(blank.sum()),
            "blank_pct": round(100 * blank.mean(), 2),
            "zero": int((num == 0).sum()),
            "n_unique": int(s[~blank].nunique()),
            "has_commas": int(s.str.contains(",", regex=False).sum()),
            "parses_as_number_pct": round(100 * numeric_share, 2),
            "min": num.min() if numeric_share > 0.99 else None,
            "max": num.max() if numeric_share > 0.99 else None,
            "example": s[~blank].iloc[0] if (~blank).any() else "",
        }
        rows.append(rec)
    profile = pd.DataFrame(rows)
    profile.to_csv(REPORTS / "raw_profile.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(profile.to_string(index=False))

    # ---------------------------------------------------------- data problems
    price = to_num(raw["SALE PRICE"])
    gsf, lsf = to_num(raw["GROSS SQUARE FEET"]), to_num(raw["LAND SQUARE FEET"])
    yb = to_num(raw["YEAR BUILT"])
    res, com, tot = (to_num(raw[c]) for c in ["RESIDENTIAL UNITS", "COMMERCIAL UNITS", "TOTAL UNITS"])
    cat_raw = raw["BUILDING CLASS CATEGORY"]
    cat_norm = cat_raw.str.strip().str.upper().map(lambda x: re.sub(r"\s+", " ", x))
    nb_norm = raw["NEIGHBORHOOD"].str.strip().str.upper().map(lambda x: re.sub(r"\s+", " ", x))
    zip_ = to_num(raw["ZIP CODE"])
    lat = to_num(raw["Latitude"])
    key = ["BBL", "APARTMENT NUMBER", "SALE DATE", "SALE PRICE"]
    key_dup = raw.duplicated(key, keep="first")
    full_dup = raw.duplicated(keep="first")

    problems = [
        ("Sale price $0", (price == 0).sum()),
        ("Sale price $1-$100", ((price > 0) & (price <= 100)).sum()),
        ("Sale price <= $100 (total nominal)", (price <= 100).sum()),
        ("Sale price $101-$10,000", ((price > 100) & (price <= 10_000)).sum()),
        ("Sale price > $100M", (price > 100_000_000).sum()),
        ("Sale price missing / not numeric", price.isna().sum()),
        ("Gross sq ft blank or 0", (gsf.isna() | (gsf == 0)).sum()),
        ("Land sq ft blank or 0", (lsf.isna() | (lsf == 0)).sum()),
        ("Sq ft stored as text with commas (gross)", raw["GROSS SQUARE FEET"].str.contains(",").sum()),
        ("Total units blank", tot.isna().sum()),
        ("Residential + commercial != total (all three present)",
         (res.notna() & com.notna() & tot.notna() & (res + com != tot)).sum()),
        ("Year built missing or 0", (yb.isna() | (yb == 0)).sum()),
        ("Year built 1-1799 (impossible)", ((yb > 0) & (yb < 1800)).sum()),
        ("No latitude/longitude", lat.isna().sum()),
        ("ZIP missing or 0", (zip_.isna() | (zip_ == 0)).sum()),
        ("Building category raw labels", cat_raw.nunique()),
        ("Building category labels after whitespace fix", cat_norm.nunique()),
        ("Neighbourhood raw labels", raw["NEIGHBORHOOD"].nunique()),
        ("Neighbourhood labels after whitespace fix", nb_norm.nunique()),
        ("EASE-MENT non-blank", raw["EASE-MENT"].str.strip().ne("").sum()),
        ("Exact duplicate rows (all 29 columns), extra copies", full_dup.sum()),
        ("Repeated BBL+apartment+date+price, extra copies", key_dup.sum()),
        ("Market sales (> $100)", (price > 100).sum()),
    ]
    prob = pd.DataFrame(problems, columns=["problem", "rows"])
    prob["pct_of_raw"] = (100 * prob["rows"] / n).round(2)
    prob.loc[prob["problem"].str.contains("labels"), "pct_of_raw"] = np.nan
    prob.to_csv(REPORTS / "raw_problems.csv", index=False)
    print()
    print(prob.to_string(index=False))


if __name__ == "__main__":
    main()
