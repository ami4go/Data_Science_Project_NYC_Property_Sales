"""Step 5 - exploratory data analysis on the 70 % EXPLORATION set only.

The 30 % confirmation set is never opened here; it is reserved for the hypothesis
tests. Every figure gets a one-line takeaway caption with its numbers, collected in
reports/eda_findings.md (paste-ready for report Section 4).

Figures are drawn at the width they print in the two-column report (COL_W), so the
text is 6.5-7.5 pt on paper. Statistics of the sale price itself count each
multi-lot deal once (`deals`); a deal repeats its total price on every lot.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, ListedColormap  # noqa: E402
from matplotlib.ticker import FuncFormatter, NullFormatter  # noqa: E402

from common import (BOROUGH_COLORS, BOROUGH_ORDER, COL_W, EXPLORE_PKL, GRID, INK, INK_2,  # noqa: E402
                    MUTED, PREWAR_CUTOFF, REPORTS, SEQ_BLUE, SERIES, TOLL_START, save,
                    setup_style, toll_line_lat)

GRAY = "#c3c2b7"
SEQ = LinearSegmentedColormap.from_list("seq_blue", SEQ_BLUE)
DIVERGING = ListedColormap(
    ["#104281", "#256abf", "#5598e7", "#9ec5f4", "#f0efec", "#f2b8b5", "#ea8a88", "#e34948", "#a32c2b"])
RES_CATS = {"01": "1-family", "02": "2-family", "03": "3-family",
            "07": "Walk-up rental", "14": "Rental 4-10 units", "08": "Elevator rental"}

findings = []


def caption(fig_name, title, text):
    findings.append((fig_name, title, text))
    print(f"\n{fig_name}: {text}")


def usd(v):
    for div, suf in [(1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if abs(v) >= div:
            return f"${v / div:,.{1 if v / div < 10 else 0}f}{suf}"
    return f"${v:,.0f}"


def log_dollar_axis(ax, axis="x", ticks=(4, 5, 6, 7, 8, 9)):
    labels = [usd(10 ** t) for t in ticks]
    (ax.set_xticks if axis == "x" else ax.set_yticks)(ticks, labels)


def short_cat(label):
    """'13 CONDOS - ELEVATOR APARTMENTS' -> 'Condos - Elevator Apts'."""
    s = re.sub(r"^\S+\s+", "", label).title()
    for long, short in [("Apartments", "Apts"), ("Dwellings", "Homes"), ("Residential", "Resid."),
                        ("Tax Class 1 ", "Class 1 ")]:
        s = s.replace(long, short)
    return s[:24]


def usd_m(v):
    return f"${v / 1e6:.2f}M"


def no_ygrid(ax):
    ax.grid(axis="y", visible=False)


# ------------------------------------------------------------------------- figures
def f01_price_classes(ex, deals):
    p = ex["sale_price"]
    classes = pd.Series({
        "$0": (p == 0).mean(), "$1 - $100": ((p > 0) & (p <= 100)).mean(),
        "$101 - $10,000": ((p > 100) & (p <= 10_000)).mean(), "> $10,000 (market)": (p > 10_000).mean()})
    fig, (a, b) = plt.subplots(2, 1, figsize=(COL_W, 3.0), height_ratios=[1, 1.45])
    y = np.arange(4)[::-1]
    a.barh(y, classes.values * 100, height=0.55, color=[GRAY, GRAY, GRAY, SERIES[0]])
    for yi, v in zip(y, classes.values):
        a.text(v * 100 + 1.5, yi, f"{100 * v:.1f}%", va="center", color=INK_2, fontsize=6.5)
    a.set_yticks(y, classes.index)
    a.set_xlim(0, 85)
    a.set_xlabel("% of recorded sales")
    no_ygrid(a)
    a.set_title("(a) Recorded sales by price class")

    lp = deals["log10_price"]
    b.hist(lp, bins=np.arange(4, 9.6, 0.05), color=SERIES[0])
    med = lp.median()
    b.axvline(med, color=INK, lw=0.8)
    b.text(med + 0.35, b.get_ylim()[1] * 0.88, f"median {usd(10 ** med)}", color=INK, fontsize=6.5)
    log_dollar_axis(b)
    b.set_xlabel("Price per market deal (log scale)")
    b.set_ylabel("Deals")
    b.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
    b.set_title("(b) Price per market deal")
    save(fig, "f01_price_classes")
    q1, q3 = deals["sale_price"].quantile([0.25, 0.75])
    caption("f01_price_classes", "Sale price classes and the market-price distribution",
            f"{100 * classes.iloc[0]:.1f}% of recorded sales are $0 and {100 * classes.iloc[:2].sum():.1f}% are "
            f"<= $100 (deed transfers, not prices), so price statistics must exclude them. Counting each "
            f"multi-lot deal once ({len(deals):,} market deals), prices have median {usd(10 ** med)}, IQR "
            f"{usd(q1)}-{usd(q3)} and max {usd(deals['sale_price'].max())}: right-skewed over five orders of "
            f"magnitude, so we analyse log price and use rank-based alternatives.")


def f02_transfer_share(ex):
    g = ex.groupby("borough", observed=True)["price_class"].apply(lambda s: (s == "nominal").mean())
    n = ex.groupby("borough", observed=True).size()
    se = np.sqrt(g * (1 - g) / n)
    g = g.reindex(BOROUGH_ORDER)
    fig, ax = plt.subplots(figsize=(COL_W, 1.6))
    y = np.arange(len(g))[::-1]
    ax.barh(y, 100 * g.values, height=0.55, color=SERIES[0],
            xerr=196 * se.reindex(BOROUGH_ORDER).values, error_kw={"ecolor": INK_2, "lw": 0.8, "capsize": 0})
    for yi, v, k in zip(y, g.values, n.reindex(BOROUGH_ORDER).values):
        ax.text(100 * v + 1.2, yi, f"{100 * v:.1f}%  (n = {k:,})", va="center", fontsize=6.5, color=INK_2)
    ax.set_yticks(y, g.index)
    ax.set_xlim(0, 72)
    ax.set_xlabel("% of recorded sales at <= $100 (bars: 95% CI)")
    no_ygrid(ax)
    save(fig, "f02_transfer_share_by_borough")
    caption("f02_transfer_share_by_borough", "Nominal-transfer share by borough",
            f"Nominal transfers range from {100 * g.min():.1f}% of recorded sales in {g.idxmin()} to "
            f"{100 * g.max():.1f}% in {g.idxmax()} ({100 * (g.max() - g.min()):.1f} percentage points apart, "
            f"well beyond the 2-point threshold): motivates T4 (chi-square test of independence).")


def f03_missingness(ex):
    cols = {"apartment_number": "Apartment number", "gross_sqft": "Gross floor area",
            "land_sqft": "Land area", "commercial_units": "Commercial units",
            "residential_units": "Residential units", "total_units": "Total units",
            "year_built": "Year built", "latitude": "Coordinates", "zip_code": "ZIP code"}
    miss = (ex[list(cols)].isna().mean() * 100).rename(index=cols).sort_values()
    cat = ex.groupby("building_category", observed=True).agg(
        n=("gross_sqft", "size"), miss=("gross_sqft", lambda s: s.isna().mean() * 100))
    cat = cat.sort_values("n", ascending=False).head(10).sort_values("miss")
    fig, (a, b) = plt.subplots(2, 1, figsize=(COL_W, 3.6), height_ratios=[1, 1.1])
    a.barh(miss.index, miss.values, height=0.6, color=SERIES[0])
    for i, v in enumerate(miss.values):
        a.text(v + 1.2, i, f"{v:.1f}%", va="center", fontsize=6.5, color=INK_2)
    a.set_xlim(0, 100)
    a.set_xlabel("% missing after cleaning")
    no_ygrid(a)
    a.set_title("(a) Missing values, by column")
    labels = [short_cat(c) for c in cat.index.astype(str)]
    unit = [("CONDO" in c or "COOP" in c) for c in cat.index.astype(str)]
    b.barh(labels, cat["miss"], height=0.6, color=[SERIES[1] if u else SERIES[0] for u in unit])
    for i, v in enumerate(cat["miss"]):
        b.text(v + 1.2, i, f"{v:.0f}%", va="center", fontsize=6.5, color=INK_2)
    b.set_xlim(0, 112)
    b.set_xlabel("% with no floor area (10 largest types)")
    no_ygrid(b)
    b.set_title("(b) No floor area, by building type")
    b.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIES[1]), plt.Rectangle((0, 0), 1, 1, color=SERIES[0])],
             labels=["Condo / co-op unit", "Other"], loc="lower right")
    save(fig, "f03_missingness")
    is_unit = ex["building_category"].astype(str).str.contains("CONDO|COOP")
    caption("f03_missingness", "Missing values by column and by building type",
            f"Gross floor area is missing for {100 * ex.gross_sqft.isna().mean():.1f}% of sales, but that is "
            f"{100 * ex[is_unit].gross_sqft.isna().mean():.0f}% of condo/co-op unit sales vs "
            f"{100 * ex[~is_unit].gross_sqft.isna().mean():.0f}% of other sales: it is missing by design (the "
            f"area belongs to the building, not the unit), not at random. Per-sq-ft results therefore speak "
            f"for houses, rental and commercial buildings, not apartments; we do not impute it.")


def f04_year_built(ex):
    lots = ex.drop_duplicates("bbl_lot")  # one row per parcel so repeat sales don't double-count
    yb = lots["year_built"].dropna().astype(int)
    rng = yb[(yb >= 1880) & (yb <= 1980)]
    counts = rng.value_counts().reindex(range(1880, 1981), fill_value=0)
    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    colors = [SERIES[1] if y % 10 == 0 else (SERIES[3] if y % 5 == 0 else SERIES[0]) for y in counts.index]
    ax.bar(counts.index, counts.values, width=0.85, color=colors)
    ax.axvline(PREWAR_CUTOFF - 0.5, color=INK, lw=0.7)
    ax.text(PREWAR_CUTOFF + 1, counts.max() * 0.97, "pre-war\ncutoff", fontsize=6, color=INK, va="top")
    ax.set_ylabel("Parcels")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
    ax.grid(axis="x", visible=False)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=c) for c in (SERIES[1], SERIES[3], SERIES[0])],
              labels=["Year ends in 0", "Ends in 5", "Other years"], loc="upper left")
    save(fig, "f04_year_built_heaping")
    share0 = (yb % 10 == 0).mean()
    share05 = (yb % 5 == 0).mean()
    pre = yb[yb < 1940]
    caption("f04_year_built_heaping", "Heaping in year built",
            f"{100 * share05:.1f}% of parcels have a year built ending in 0 or 5 (20% expected without "
            f"rounding); {100 * share0:.1f}% end in 0. Among pre-1940 parcels it is "
            f"{100 * (pre % 5 == 0).mean():.1f}%. 1940 itself holds {int(counts.loc[1940]):,} parcels vs "
            f"{int(counts.loc[1939]):,} in 1939, so a building recorded as 1940 may really be pre-war: "
            f"T1 needs a sensitivity check with the cutoff moved (e.g. drop 1935-1945).")


def f05_trends(deals, pp):
    yearly = deals.groupby(["sale_year", "borough"], observed=True)["sale_price"].median().unstack()
    fig, (a, b) = plt.subplots(2, 1, figsize=(COL_W, 3.6))
    for bo in BOROUGH_ORDER:
        a.plot(yearly.index, yearly[bo] / 1e6, color=BOROUGH_COLORS[bo], label=bo, marker="o")
    a.set_ylabel("Median deal price ($M)")
    a.set_ylim(0, None)
    a.set_xticks(range(2016, 2026, 2))
    a.legend(ncol=3, loc="lower center")
    a.set_title("(a) Median market price by borough")

    res = pp[pp["building_category_code"].astype(str).isin(RES_CATS)]  # same type mix every year
    idx = res.groupby(["sale_year", "borough"], observed=True)["price_per_sqft"].median().unstack()
    n_ppsf = res.groupby(["sale_year", "borough"], observed=True).size().unstack()
    idx = 100 * idx / idx.loc[2019]
    b.axvspan(2019.5, 2021.5, color=GRID, alpha=0.7, lw=0)
    for bo in ["Manhattan", "Brooklyn", "Queens"]:
        b.plot(idx.index, idx[bo], color=BOROUGH_COLORS[bo], label=bo, marker="o")
    b.text(2020.5, 0.97, "COVID", transform=b.get_xaxis_transform(), ha="center", va="top",
           fontsize=6, color=MUTED)
    b.axhline(100, color=MUTED, lw=0.6)
    b.set_ylabel("Median $/sq ft (2019 = 100)")
    b.set_xticks(range(2016, 2026, 2))
    b.legend(loc="upper left")
    b.set_title("(b) Residential buildings, $/sq ft (P2)")
    save(fig, "f05_price_trends")
    growth = 100 * (yearly.loc[2025] / yearly.loc[2016] - 1)
    m = idx["Manhattan"]
    bq = idx[["Brooklyn", "Queens"]].mean(axis=1)
    caption("f05_price_trends", "Price trends by borough",
            f"Manhattan has the highest median deal price every year ({usd(yearly['Manhattan'].min())}-"
            f"{usd(yearly['Manhattan'].max())}), the obvious answer, but from 2016 to 2025 it rose "
            f"{growth['Manhattan']:.0f}% vs {growth.drop('Manhattan').min():.0f}-{growth.drop('Manhattan').max():.0f}% "
            f"in the other boroughs. Indexed to 2019, Manhattan's price per sq ft "
            f"was {m.loc[2021]:.0f} in 2021 vs {bq.loc[2021]:.0f} for the Brooklyn-Queens average and "
            f"{m.loc[2025]:.0f} vs {bq.loc[2025]:.0f} in 2025 (P2; 1-3 family and rental buildings only, so "
            f"the type mix is the same every year). Caveat: Manhattan has only "
            f"{int(n_ppsf['Manhattan'].min()):,}-{int(n_ppsf['Manhattan'].max()):,} such sales a year in this "
            f"set (its market is condos and co-ops, which carry no area), so T2 uses log price of like-for-like "
            f"apartment sales instead.")


def f06_prewar(pp):
    d = pp[pp["prewar"].notna() & pp["building_category_code"].astype(str).isin(RES_CATS)].copy()
    d["cat"] = d["building_category_code"].astype(str).map(RES_CATS)
    d["prewar"] = d["prewar"].astype(bool)
    med = d.groupby(["cat", "prewar"])["price_per_sqft"].median().unstack()
    med = med.reindex(list(RES_CATS.values()))
    pooled_gap = 100 * (np.exp(d[d.prewar].log_price_per_sqft.mean() - d[~d.prewar].log_price_per_sqft.mean()) - 1)

    # within neighbourhood x category cells with >= 10 sales in each group
    cell = d.groupby(["neighborhood", "cat", "prewar"], observed=True)["log_price_per_sqft"].agg(["median", "size"])
    cell = cell.unstack("prewar")
    cell = cell[(cell[("size", True)] >= 10) & (cell[("size", False)] >= 10)]
    diff = 100 * (np.exp(cell[("median", True)] - cell[("median", False)]) - 1)

    fig, (a, b) = plt.subplots(2, 1, figsize=(COL_W, 3.5), height_ratios=[1.1, 1])
    y = np.arange(len(med))[::-1]
    for yi, (_, r) in zip(y, med.iterrows()):
        a.plot([r[False], r[True]], [yi, yi], color=GRAY, lw=1.5, zorder=1)
    a.scatter(med[False], y, s=16, color=SERIES[0], label="1940 or later", zorder=2,
              edgecolor="white", linewidth=0.6)
    a.scatter(med[True], y, s=16, color=SERIES[1], label="Pre-war (< 1940)", zorder=2,
              edgecolor="white", linewidth=0.6)
    a.set_yticks(y, med.index)
    a.set_xlabel("Median price per sq ft ($)")
    a.legend(loc="upper left")
    no_ygrid(a)
    n_higher = int((med[True] > med[False]).sum())
    a.set_title(f"(a) Pooled: pre-war higher in {n_higher} of {len(med)} types")
    b.hist(diff, bins=np.arange(-80, 121, 5), color=SERIES[0])
    b.axvline(0, color=MUTED, lw=0.6)
    b.axvline(diff.median(), color=INK, lw=0.8)
    b.text(diff.median() + 4, b.get_ylim()[1] * 0.85, f"median {diff.median():+.1f}%", fontsize=6.5)
    b.set_xlabel("Pre-war premium within neighbourhood x type (%)")
    b.set_ylabel("Cells")
    b.set_title("(b) Within neighbourhood x type")
    save(fig, "f06_prewar_vs_newer")
    caption("f06_prewar_vs_newer", "Pre-war vs newer price per sq ft (P1)",
            f"Pooled over the city, pre-war residential buildings sell for {pooled_gap:+.1f}% per sq ft "
            f"(geometric mean) vs newer ones, but within the same neighbourhood and building type the median "
            f"pre-war premium is {diff.median():+.1f}% across {len(diff)} cells "
            f"({100 * (diff > 0).mean():.0f}% of cells positive, IQR {diff.quantile(0.25):+.0f}% to "
            f"{diff.quantile(0.75):+.0f}%). Holding location and type fixed moves the gap from "
            f"{pooled_gap:+.1f}% to {diff.median():+.1f}%, near the 5% 'matters' threshold, so the answer could "
            f"go either way: P1 is not obvious, and T1 must compare like with like.")
    return diff


def f07_size_price(pp):
    d = pp[pp["building_category_code"].astype(str).isin(["01", "02", "03"])]
    x, y = np.log10(d["gross_sqft"]), d["log10_price"]
    rho = x.rank().corr(y.rank())
    r_pp = np.log(d["gross_sqft"]).rank().corr(d["log_price_per_sqft"].rank())
    fig, ax = plt.subplots(figsize=(COL_W, 2.35))
    hb = ax.hexbin(x, y, gridsize=45, cmap=SEQ, mincnt=1, bins="log", linewidths=0)
    cb = fig.colorbar(hb, ax=ax, shrink=0.9, pad=0.02)
    cb.set_label("Sales per cell", color=INK_2)
    cb.outline.set_visible(False)
    # plain numbers: the default log labels are maths strings that parse_math=False prints raw
    cb.ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    cb.ax.yaxis.set_minor_formatter(NullFormatter())
    ax.set_xticks([3, np.log10(2000), np.log10(5000), 4], ["1,000", "2,000", "5,000", "10,000"])
    ax.set_xlim(np.log10(500), np.log10(15000))
    log_dollar_axis(ax, "y", ticks=(5, 6, 7))
    ax.set_xlabel("Gross floor area, sq ft (log)")
    ax.set_ylabel("Sale price (log)")
    ax.grid(False)
    save(fig, "f07_size_vs_price")
    caption("f07_size_vs_price", "Floor area vs price (1-3 family homes)",
            f"Spearman rho = {rho:.2f} between floor area and price for {len(d):,} 1-3 family sales: "
            f"bigger homes do cost more (the obvious question), but only moderately, since location varies "
            f"more than size. Price per sq ft falls with size (rho = {r_pp:.2f}), so per-sq-ft comparisons "
            f"must hold building type (and so size) fixed.")


def f08_volume(ex, deals):
    month = deals["sale_date"].dt.to_period("M")
    monthly = deals.groupby(month).size()
    nominal = ex[ex["price_class"] == "nominal"].groupby(ex["sale_date"].dt.to_period("M")).size()
    t = monthly.index.to_timestamp()
    fig, ax = plt.subplots(figsize=(COL_W, 1.85))
    ax.axvspan(pd.Timestamp("2020-03-01"), pd.Timestamp("2021-12-31"), color=GRID, alpha=0.7, lw=0)
    ax.plot(t, monthly.values, color=SERIES[0], label="Market deals", lw=1)
    ax.plot(t, nominal.reindex(monthly.index).values, color=SERIES[1], label="$0-$100 transfers", lw=1)
    ax.axvline(pd.Timestamp(TOLL_START), color=MUTED, lw=0.6)
    top = monthly.max() * 1.12
    ax.set_ylim(0, top)
    ax.text(pd.Timestamp("2020-04-01"), top * 0.97, "COVID", fontsize=6, color=MUTED, va="top")
    ax.text(pd.Timestamp("2024-11-15"), top * 0.97, "toll", fontsize=6, color=MUTED, ha="right", va="top")
    ax.set_xticks([pd.Timestamp(f"{yr}-01-01") for yr in range(2016, 2027, 2)], [str(yr) for yr in range(2016, 2027, 2)])
    ax.set_ylabel("Per month (70% set)")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v / 1000:.0f}K")
    ax.legend(loc="lower left", ncol=2)
    save(fig, "f08_sales_volume")
    q2_19 = monthly[(monthly.index >= "2019-04") & (monthly.index <= "2019-06")].sum()
    q2_20 = monthly[(monthly.index >= "2020-04") & (monthly.index <= "2020-06")].sum()
    peak = monthly.idxmax()
    caption("f08_sales_volume", "Monthly sales volume",
            f"Market deals in Apr-Jun 2020 were {100 * (q2_20 / q2_19 - 1):+.0f}% vs Apr-Jun 2019; the busiest month "
            f"was {peak} ({monthly.max():,} deals in this 70% set). The COVID period changes which properties "
            f"sell, a composition effect P2 must keep in mind; transfers track market deals month to month.")


def f09_neighbourhoods(pp):
    d = pp[pp["building_category_code"].astype(str).isin(RES_CATS)]
    g = d.groupby(["neighborhood"], observed=True).agg(
        med=("price_per_sqft", "median"), n=("price_per_sqft", "size"),
        borough=("borough", lambda s: s.mode().iloc[0]))
    g = g[g["n"] >= 100].sort_values("med", ascending=False).head(15).iloc[::-1]
    fig, ax = plt.subplots(figsize=(COL_W, 2.9))
    ax.barh(g.index.astype(str).str.title(), g["med"], height=0.65,
            color=[BOROUGH_COLORS[b] for b in g["borough"]])
    for i, (v, n) in enumerate(zip(g["med"], g["n"])):
        ax.text(v + 15, i, f"${v:,.0f} (n = {n:,})", va="center", fontsize=6, color=INK_2)
    ax.set_xlim(0, g["med"].max() * 1.45)
    ax.set_xlabel("Median $/sq ft, residential buildings")
    no_ygrid(ax)
    present = [b for b in BOROUGH_ORDER if b in set(g["borough"])]
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BOROUGH_COLORS[b]) for b in present],
               labels=present, loc="outside lower center", ncol=len(present))
    save(fig, "f09_top_neighbourhoods")
    top = g.iloc[::-1]
    caption("f09_top_neighbourhoods", "Most expensive neighbourhoods",
            f"Among neighbourhoods with >= 100 residential per-sq-ft sales, {top.index[0].title()} "
            f"({top['borough'].iloc[0]}) is priciest at ${top['med'].iloc[0]:,.0f}/sq ft; "
            f"{(top['borough'] == 'Manhattan').sum()} of the top 15 are in Manhattan and "
            f"{(top['borough'] == 'Brooklyn').sum()} in Brooklyn. Neighbourhood explains far more than borough, "
            f"so tests should condition on it.")


def f10_toll(ex):
    man_rows = ex[(ex["borough"] == "Manhattan") & ex["toll_zone"].notna() & ex["is_market"]].copy()
    man_rows["toll_zone"] = man_rows["toll_zone"].astype(bool)
    man = man_rows[man_rows["first_in_transaction"]]  # one row per deal
    fig, (a, b) = plt.subplots(1, 2, figsize=(COL_W, 2.45), width_ratios=[0.62, 1.5])
    for inside, col in [(False, SERIES[0]), (True, SERIES[1])]:
        s = man[man["toll_zone"] == inside]
        a.scatter(s["longitude"], s["latitude"], s=0.2, color=col, alpha=0.5, linewidths=0, rasterized=True)
    lon = np.linspace(-74.02, -73.93, 50)
    a.plot(lon, toll_line_lat(lon), color=INK, lw=0.7)
    a.set_xlim(-74.03, -73.90)
    a.set_ylim(40.70, 40.88)
    a.set_aspect(1 / np.cos(np.radians(40.78)))
    a.set_xticks([])
    a.set_yticks([])
    a.grid(False)
    a.set_title("(a) Zone", loc="left")

    d = man[man["sale_year"] >= 2023]
    q = d.groupby([d["sale_date"].dt.to_period("Q"), "toll_zone"])["sale_price"].median().unstack()
    n = d.groupby([d["sale_date"].dt.to_period("Q"), "toll_zone"]).size().unstack()
    t = q.index.to_timestamp() + pd.Timedelta(days=45)
    b.plot(t, q[True] / 1e6, color=SERIES[1], marker="o", label="Inside zone")
    b.plot(t, q[False] / 1e6, color=SERIES[0], marker="o", label="Outside zone")
    b.axvline(pd.Timestamp(TOLL_START), color=MUTED, lw=0.6)
    b.text(pd.Timestamp(TOLL_START) + pd.Timedelta(days=15), b.get_ylim()[0], "toll", fontsize=6,
           color=MUTED, va="bottom")
    b.set_ylabel("Median deal price ($M)")
    b.set_xticks([pd.Timestamp(f"{yr}-01-01") for yr in (2023, 2024, 2025, 2026)], ["2023", "2024", "2025", "2026"])
    fig.legend(*b.get_legend_handles_labels(), loc="outside lower center", ncol=2)
    b.set_title("(b) Manhattan, by quarter (P3)", loc="left")
    save(fig, "f10_toll_zone")

    def change(frame):
        yr = frame[frame.sale_year >= 2024].groupby(["sale_year", "toll_zone"])["sale_price"].median().unstack()
        return 100 * (yr.loc[2025] / yr.loc[2024] - 1), yr

    chg, yr = change(man)
    chg_rows, _ = change(man_rows)
    big = (man_rows[man_rows["multi_lot_sale"] & man_rows["toll_zone"] & (man_rows["sale_year"] == 2025)]
           .groupby("transaction_id").agg(lots=("row_id", "size"), price=("sale_price", "first"))
           .sort_values("lots"))
    biggest = (f"; the largest, one {usd(big['price'].iloc[-1])} deal repeated on {int(big['lots'].iloc[-1])} lots "
               f"in 2025, weighs as {int(big['lots'].iloc[-1])} sales") if len(big) else ""
    caption("f10_toll_zone", "Toll zone: map and quarterly prices",
            f"{100 * man['toll_zone'].mean():.0f}% of geocoded Manhattan market deals fall inside the zone. Counting "
            f"each deal once, the median price inside went {usd_m(yr.loc[2024, True])} -> "
            f"{usd_m(yr.loc[2025, True])} ({chg[True]:+.1f}%) from 2024 to 2025, outside "
            f"{usd_m(yr.loc[2024, False])} -> {usd_m(yr.loc[2025, False])} ({chg[False]:+.1f}%). "
            f"Counting every lot of multi-lot deals would instead "
            f"show {chg_rows[True]:+.1f}% inside vs {chg_rows[False]:+.1f}% outside{biggest}, so price "
            f"statistics use one row per deal. Quarterly medians are noisy ({int(n.min().min()):,}-"
            f"{int(n.max().max()):,} deals per cell), and the condo/co-op mix differs inside and outside, so T3 "
            f"compares like types.")


def f11_borough_box(deals):
    data = [deals.loc[deals["borough"] == b, "log10_price"].to_numpy() for b in BOROUGH_ORDER]
    fig, ax = plt.subplots(figsize=(COL_W, 1.75))
    bp = ax.boxplot(data, orientation="horizontal", showfliers=False, widths=0.5, patch_artist=True,
                    medianprops={"color": INK, "lw": 1}, whiskerprops={"color": MUTED, "lw": 0.6},
                    capprops={"color": MUTED, "lw": 0.6}, boxprops={"lw": 0})
    for patch in bp["boxes"]:
        patch.set_facecolor(SERIES[0])
        patch.set_alpha(0.85)
    ax.set_yticks(range(1, 6), BOROUGH_ORDER)
    ax.invert_yaxis()
    log_dollar_axis(ax, "x", ticks=(5, 6, 7))
    ax.set_xlabel("Price per market deal (log scale)")
    no_ygrid(ax)
    save(fig, "f11_price_by_borough")
    med = deals.groupby("borough", observed=True)["sale_price"].median().reindex(BOROUGH_ORDER)
    caption("f11_price_by_borough", "Market price by borough",
            "Median deal price: " + ", ".join(f"{b} {usd(v)}" for b, v in med.items())
            + ". The boxes overlap heavily, so borough alone is a weak summary of price.")


def f12_correlations(mk):
    single = mk[~mk["multi_lot_sale"]]  # a multi-lot row's price is not its own lot's price
    d = pd.DataFrame({
        "log price": single["log10_price"], "log $/sq ft": single["log_price_per_sqft"],
        "log floor area": np.log(single["gross_sqft"]), "log land area": np.log(single["land_sqft"]),
        "total units": single["total_units"], "year built": single["year_built"],
        "sale year": single["sale_year"], "latitude": single["latitude"],
        "longitude": single["longitude"]}).astype(float)
    c = d.rank().corr()
    fig, ax = plt.subplots(figsize=(COL_W, 2.95))
    im = ax.imshow(c.values, cmap=DIVERGING, vmin=-1, vmax=1)
    ax.set_xticks(range(len(c)), c.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(c)), c.columns)
    for i in range(len(c)):
        for j in range(len(c)):
            v = c.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=5.2,
                    color="white" if abs(v) > 0.6 else INK)
    ax.grid(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
    cb.outline.set_visible(False)
    cb.set_label("Spearman rho", color=INK_2)
    save(fig, "f12_correlations")
    caption("f12_correlations", "Correlation matrix",
            f"Log price rises with floor area (rho = {c.loc['log price', 'log floor area']:.2f}) and units "
            f"(rho = {c.loc['log price', 'total units']:.2f}); year built vs log $/sq ft is only "
            f"rho = {c.loc['year built', 'log $/sq ft']:.2f} citywide, and latitude/longitude vs log $/sq ft are "
            f"{c.loc['latitude', 'log $/sq ft']:.2f}/{c.loc['longitude', 'log $/sq ft']:.2f}: location matters "
            f"(f09) but not in a straight line north-south, so it must enter as neighbourhood, not coordinates. "
            f"Rank correlations (pairwise complete, multi-lot rows left out) because every variable is skewed; "
            f"associations, not causes.")


def main():
    setup_style()
    ex = pd.read_pickle(EXPLORE_PKL)
    assert (ex["split"] == "exploration").all()
    mk = ex[ex["is_market"]]
    deals = mk[mk["first_in_transaction"]]
    pp = ex[ex["price_per_sqft"].notna() & ~ex["ppsf_outlier"]]
    print(f"exploration rows {len(ex):,}; market rows {len(mk):,} = {len(deals):,} deals; "
          f"valid price per sq ft {len(pp):,}")

    f01_price_classes(ex, deals)
    f02_transfer_share(ex)
    f03_missingness(ex)
    f04_year_built(ex)
    f05_trends(deals, pp)
    f06_prewar(pp)
    f07_size_price(pp)
    f08_volume(ex, deals)
    f09_neighbourhoods(pp)
    f10_toll(ex)
    f11_borough_box(deals)
    f12_correlations(mk)

    lines = ["# EDA findings (exploration set, 70%, seed 42)", "",
             f"Rows: {len(ex):,} exploration rows; {len(mk):,} market-sale rows = {len(deals):,} market deals "
             f"(a multi-lot deal counted once); {len(pp):,} with a valid price per sq ft.", ""]
    for name, title, text in findings:
        lines += [f"## {title}", f"![{title}](../figures/{name}.png)", "", f"**Takeaway.** {text}", ""]
    (REPORTS / "eda_findings.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
