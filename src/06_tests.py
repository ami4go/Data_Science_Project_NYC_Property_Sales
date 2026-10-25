"""Step 6 - the four hypothesis tests of reports/test_plan.md, on the 30 % CONFIRMATION set.

Only tests taught in CSE558 Lectures 5-8 are used. Each statistic is computed from the
lecture formula and cross-checked against scipy. Writes:
    reports/test_results.csv   one row per test (and per robustness / alternative run)
    reports/test_results.md    the numbers for report Section 5, test by test
    figures/f13_test_results   estimates with 95% CIs against the "matters" sizes
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from common import COL_W, CONFIRM_PKL, INK, INK_2, MUTED, REPORTS, SERIES, save, setup_style  # noqa: E402

ALPHA = 0.05
RES_CATS = ["01", "02", "03", "07", "08", "14"]  # 1-3 family homes and rental buildings
MATTERS_PCT = np.log(1.05)                       # 5% on the log scale
rows, md = [], []


def pct(x):
    return 100 * (np.exp(x) - 1)


def record(test, variant, estimate, lo, hi, stat_name, stat, df, p, unit, matters, decision, note=""):
    rows.append({"test": test, "variant": variant, "estimate": estimate, "ci_low": lo, "ci_high": hi,
                 "statistic": stat_name, "value": stat, "df": df, "p_value": p, "unit": unit,
                 "matters_threshold": matters, "decision": decision, "note": note})


def size_verdict(lo, hi, m, two_sided):
    """Compare the 95% CI with the smallest difference that matters (m > 0)."""
    if lo >= m or (two_sided and hi <= -m):
        return "matters: the whole interval is beyond the threshold"
    if -m < lo and hi < m:
        return "does not matter: the whole interval is inside +/- the threshold"
    return "unclear: the interval crosses the threshold"


def paired_t(d, side):
    """Paired t-test on cell differences d (Lecture 7): t = mean(d) / (s_d / sqrt(n))."""
    n, m, s = len(d), d.mean(), d.std(ddof=1)
    se = s / np.sqrt(n)
    t = m / se
    df = n - 1
    p = stats.t.sf(t, df) if side == "greater" else 2 * stats.t.sf(abs(t), df)
    half = stats.t.ppf(0.975, df) * se
    check = stats.ttest_1samp(d, 0, alternative=side)
    assert np.isclose(t, check.statistic) and np.isclose(p, check.pvalue)
    return dict(n=n, mean=m, sd=s, se=se, t=t, df=df, p=p, lo=m - half, hi=m + half)


def cells(frame, group, min_each):
    """Mean log $/sq ft per neighbourhood x category cell, for group True vs False."""
    g = frame.groupby(["neighborhood", "building_category_code", group], observed=True)["log_price_per_sqft"]
    c = g.agg(["mean", "size"]).unstack(group)
    c = c[(c[("size", True)] >= min_each) & (c[("size", False)] >= min_each)]
    return c[("mean", True)] - c[("mean", False)], int(c[("size", True)].sum() + c[("size", False)].sum())


def two_sample_alternatives(test, frame, group, side):
    """Unpaired runs on all sales (ignoring neighbourhood): F-test, pooled t, Welch t (Lectures 7-8)."""
    a = frame.loc[frame[group], "log_price_per_sqft"].to_numpy()
    b = frame.loc[~frame[group], "log_price_per_sqft"].to_numpy()
    va, vb = a.var(ddof=1), b.var(ddof=1)
    F = va / vb
    dfa, dfb = len(a) - 1, len(b) - 1
    pF = 2 * min(stats.f.sf(F, dfa, dfb), stats.f.cdf(F, dfa, dfb))
    record(test, "alt: F-test for two variances (all sales)", F, np.nan, np.nan, "F", F, f"({dfa}, {dfb})",
           pF, "ratio", np.nan, "reject equal variances" if pF < ALPHA else "do not reject equal variances")
    out = []
    for name, eq in [("pooled", True), ("Welch", False)]:
        r = stats.ttest_ind(a, b, equal_var=eq, alternative=side)
        diff = a.mean() - b.mean()
        if eq:
            sp2 = (dfa * va + dfb * vb) / (dfa + dfb)
            se, df = np.sqrt(sp2 * (1 / len(a) + 1 / len(b))), dfa + dfb
        else:
            se = np.sqrt(va / len(a) + vb / len(b))
            df = (va / len(a) + vb / len(b)) ** 2 / ((va / len(a)) ** 2 / dfa + (vb / len(b)) ** 2 / dfb)
        half = stats.t.ppf(0.975, df) * se
        record(test, f"alt: {name} two-sample t (all sales, ignores neighbourhood)", pct(diff), pct(diff - half),
               pct(diff + half), "t", r.statistic, round(df, 1), r.pvalue, "%", 5,
               "reject H0" if r.pvalue < ALPHA else "do not reject H0")
        out.append((name, diff, r, df))
    return F, pF, out, len(a), len(b)


# ============================================================================ T1
def t1(conf):
    pp = conf[conf["price_per_sqft"].notna() & ~conf["ppsf_outlier"]
              & conf["building_category_code"].astype(str).isin(RES_CATS) & conf["year_built"].notna()].copy()
    pp["prewar"] = pp["prewar"].astype(bool)
    d, n_sales = cells(pp, "prewar", 5)
    r = paired_t(d.to_numpy(), "greater")
    verdict = size_verdict(r["lo"], r["hi"], MATTERS_PCT, two_sided=False)
    record("T1", "main: paired t on neighbourhood x type cells", pct(r["mean"]), pct(r["lo"]), pct(r["hi"]),
           "t", r["t"], r["df"], r["p"], "%", 5, "reject H0" if r["p"] < ALPHA else "do not reject H0", verdict)

    rob = pp[~pp["year_built"].between(1935, 1945)]
    d2, _ = cells(rob, "prewar", 5)
    r2 = paired_t(d2.to_numpy(), "greater")
    record("T1", "robustness: without year built 1935-1945", pct(r2["mean"]), pct(r2["lo"]), pct(r2["hi"]),
           "t", r2["t"], r2["df"], r2["p"], "%", 5, "reject H0" if r2["p"] < ALPHA else "do not reject H0",
           size_verdict(r2["lo"], r2["hi"], MATTERS_PCT, False))
    F, pF, alts, na, nb = two_sample_alternatives("T1", pp, "prewar", "greater")

    md.extend([
        "## T1 (P1, primary): pre-war premium per sq ft, within neighbourhood x type",
        f"* Rows: {len(pp):,} confirmation sales with a valid price per sq ft and year built "
        f"(1-3 family and rental buildings); {r['n']} cells with >= 5 pre-war and >= 5 newer sales "
        f"({n_sales:,} sales).",
        f"* **Estimate:** mean within-cell premium {pct(r['mean']):+.2f}% "
        f"(95% CI {pct(r['lo']):+.2f}% to {pct(r['hi']):+.2f}%); mean d = {r['mean']:.4f} log points, "
        f"s_d = {r['sd']:.4f}.",
        f"* **Paired t-test (one-sided):** t = {r['t']:.3f}, d.f. = {r['df']}, p = {r['p']:.3g} -> "
        f"{'reject' if r['p'] < ALPHA else 'do not reject'} H0 at alpha = 0.05.",
        f"* **Does it matter (5%)?** {verdict}.",
        f"* Robustness, without year built 1935-1945: {pct(r2['mean']):+.2f}% "
        f"(95% CI {pct(r2['lo']):+.2f}% to {pct(r2['hi']):+.2f}%), t = {r2['t']:.3f}, d.f. = {r2['df']}, "
        f"p = {r2['p']:.3g} ({r2['n']} cells).",
        f"* Alternatives on all {na + nb:,} sales, ignoring neighbourhood: F = {F:.3f} (p = {pF:.3g}) for equal "
        f"variances; " + "; ".join(f"{n} t = {res.statistic:.2f}, d.f. = {df:.0f}, p = {res.pvalue:.3g}, "
                                     f"gap {pct(diff):+.2f}%" for n, diff, res, df in alts) + ".",
        "",
    ])
    return r, r2


# ============================================================================ T2
def window_test(deals, T, label):
    w = deals[(deals["sale_price"] >= 0.975 * T) & (deals["sale_price"] < 1.025 * T)]
    below = w["sale_price"] < T
    n1, x1 = int((~w["post"]).sum()), int((below & ~w["post"]).sum())  # pre
    n2, x2 = int(w["post"].sum()), int((below & w["post"]).sum())       # post
    p1, p2 = x1 / n1, x2 / n2
    pbar = (x1 + x2) / (n1 + n2)
    z = (p2 - p1) / np.sqrt(pbar * (1 - pbar) * (1 / n1 + 1 / n2))   # Lecture 7, pooled rate
    p = stats.norm.sf(z)                                               # one-sided, H1: p_post > p_pre
    se_u = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    lo, hi = p2 - p1 - 1.96 * se_u, p2 - p1 + 1.96 * se_u
    chi2, pchi, dfc, _ = stats.chi2_contingency([[x1, n1 - x1], [x2, n2 - x2]], correction=False)
    assert np.isclose(chi2, z ** 2)
    ok15 = min(x1, n1 - x1, x2, n2 - x2) >= 15                        # Lecture 5 rule of thumb
    return dict(T=T, label=label, n1=n1, x1=x1, n2=n2, x2=x2, p1=p1, p2=p2, z=z, p=p, lo=lo, hi=hi,
                chi2=chi2, pchi=pchi, ok15=ok15)


def t2(conf):
    deals = conf[conf["is_market"] & conf["first_in_transaction"]
                 & conf["tax_class_at_sale"].isin([1, 2]) & (conf["sale_year"] != 2019)].copy()
    deals["post"] = deals["sale_year"] >= 2020
    out = {}
    for T, label in [(2.0e6, "main: $2M (tax step)"), (3.0e6, "second window: $3M (tax step)"),
                     (1.5e6, "placebo: $1.5M (no step)"), (2.5e6, "placebo: $2.5M (no step)")]:
        r = window_test(deals, T, label)
        out[T] = r
        verdict = size_verdict(r["lo"], r["hi"], 0.10, two_sided=False)
        record("T2", label, 100 * (r["p2"] - r["p1"]), 100 * r["lo"], 100 * r["hi"], "z", r["z"], "-", r["p"],
               "pp", 10, "reject H0" if r["p"] < ALPHA else "do not reject H0",
               verdict + ("" if r["ok15"] else "; fewer than 15 in a cell"))
    m = out[2.0e6]
    record("T2", "alt: chi-square independence 2x2 at $2M (two-sided)", m["chi2"], np.nan, np.nan, "chi2",
           m["chi2"], 1, m["pchi"], "-", np.nan, "reject H0" if m["pchi"] < ALPHA else "do not reject H0",
           "chi-square = z squared")
    md.append("## T2 (N1): bunching just below $2M after the July 2019 mansion-tax step")
    md.append(f"* Rows: residential market deals (tax class 1-2, one row per deal), 2016-18 vs 2020-25, "
              f"2019 dropped; window = price within 2.5% of the threshold.")
    for T, r in out.items():
        md.append(f"* **{r['label']}:** below-line share {100 * r['p1']:.1f}% ({r['x1']}/{r['n1']}) -> "
                  f"{100 * r['p2']:.1f}% ({r['x2']}/{r['n2']}); difference {100 * (r['p2'] - r['p1']):+.1f} pp "
                  f"(95% CI {100 * r['lo']:+.1f} to {100 * r['hi']:+.1f}); z = {r['z']:.2f}, one-sided "
                  f"p = {r['p']:.3g}.")
    md.append(f"* Does it matter (10 pp) at $2M? {size_verdict(m['lo'], m['hi'], 0.10, False)}.")
    md.append(f"* Check: chi-square 2x2 at $2M = {m['chi2']:.2f} (= z^2), d.f. = 1, two-sided p = {m['pchi']:.3g}.")
    md.append("")
    return out


# ============================================================================ T3
def t3(conf):
    d = conf[conf["price_class"].isin(["nominal", "low", "market"])].copy()
    d["transfer"] = d["price_class"] == "nominal"
    rate = d.groupby("building_category", observed=True)["transfer"].mean()           # citywide r_c
    n_bc = d.groupby(["borough", "building_category"], observed=True).size().unstack(fill_value=0)
    E = (n_bc * rate.reindex(n_bc.columns)).sum(axis=1)                                  # expected transfers
    O = d.groupby("borough", observed=True)["transfer"].sum().reindex(E.index)
    n_b = d.groupby("borough", observed=True).size().reindex(E.index)
    chi2 = float(((O - E) ** 2 / E).sum())
    df = len(O) - 1
    p = stats.chi2.sf(chi2, df)
    check = stats.chisquare(O.to_numpy(), E.to_numpy())
    assert np.isclose(chi2, check.statistic)
    obs_share, exp_share = O / n_b, E / n_b
    gap = 100 * (obs_share - exp_share)
    se = np.sqrt(obs_share * (1 - obs_share) / n_b)
    lo, hi = gap - 196 * se, gap + 196 * se
    for b in gap.index:
        record("T3", f"borough gap vs building-mix expectation: {b}", gap[b], lo[b], hi[b], "-", np.nan, "-",
               np.nan, "pp", 2, "-", size_verdict(lo[b] / 100, hi[b] / 100, 0.02, True))
    big = int((gap.abs() >= 2).sum())
    record("T3", "main: chi-square goodness of fit (borough counts vs building-mix expectation)", chi2, np.nan,
           np.nan, "chi2", chi2, df, p, "-", 2, "reject H0" if p < ALPHA else "do not reject H0",
           f"{big} of {len(gap)} boroughs differ from expectation by >= 2 pp")
    raw = pd.crosstab(d["borough"], d["transfer"])
    chi_raw, p_raw, df_raw, _ = stats.chi2_contingency(raw, correction=False)
    raw_share = 100 * raw[True] / raw.sum(axis=1)
    record("T3", "alt: chi-square independence borough x transfer (raw, mixes building type)", chi_raw, np.nan,
           np.nan, "chi2", chi_raw, df_raw, p_raw, "-", np.nan,
           "reject H0" if p_raw < ALPHA else "do not reject H0",
           f"raw spread {raw_share.max() - raw_share.min():.1f} pp")
    md.append("## T3 (P4 upgraded): $0-$100 transfers by borough, holding building type fixed")
    md.append(f"* Rows: {len(d):,} confirmation deeds; citywide transfer rate per building category "
              f"(47 categories) gives each borough's expected transfers.")
    md.append(f"* **Chi-square goodness of fit:** chi2 = {chi2:,.1f}, d.f. = {df}, p = {p:.3g} -> "
              f"{'reject' if p < ALPHA else 'do not reject'} H0. Smallest expected count {E.min():,.0f} (>= 5).")
    for b in gap.index:
        md.append(f"  * {b}: observed {100 * obs_share[b]:.1f}% vs expected {100 * exp_share[b]:.1f}% "
                  f"-> {gap[b]:+.1f} pp (95% CI {lo[b]:+.1f} to {hi[b]:+.1f}); O/E = {O[b] / E[b]:.3f}.")
    md.append(f"* Does it matter (2 pp)? {big} of {len(gap)} boroughs are 2 pp or more from their expected share.")
    md.append(f"* Alternative, raw chi-square of independence (ignores building type): chi2 = {chi_raw:,.1f}, "
              f"d.f. = {df_raw}, p = {p_raw:.3g}; raw shares "
              + ", ".join(f"{b} {v:.1f}%" for b, v in raw_share.items())
              + f" (spread {raw_share.max() - raw_share.min():.1f} pp).")
    md.append("* Caveat: expected counts use rates estimated from the same data, so d.f. = 4 is approximate.")
    md.append("")
    return gap, lo, hi


# ============================================================================ T4
def t4(conf):
    pp = conf[conf["price_per_sqft"].notna() & ~conf["ppsf_outlier"]
              & conf["building_category_code"].astype(str).isin(RES_CATS)
              & conf["commercial_units"].notna()].copy()
    pp["mixed"] = pp["commercial_units"] > 0
    d, n_sales = cells(pp, "mixed", 3)
    r = paired_t(d.to_numpy(), "two-sided")
    verdict = size_verdict(r["lo"], r["hi"], MATTERS_PCT, two_sided=True)
    record("T4", "main: paired t on neighbourhood x type cells", pct(r["mean"]), pct(r["lo"]), pct(r["hi"]),
           "t", r["t"], r["df"], r["p"], "%", 5, "reject H0" if r["p"] < ALPHA else "do not reject H0", verdict)
    F, pF, alts, na, nb = two_sample_alternatives("T4", pp, "mixed", "two-sided")
    md.extend([
        "## T4 (N2): buildings with shops vs purely residential, within neighbourhood x type",
        f"* Rows: {len(pp):,} confirmation sales ({int(pp['mixed'].sum()):,} mixed-use); {r['n']} cells with "
        f">= 3 of each ({n_sales:,} sales).",
        f"* **Estimate:** mean within-cell gap {pct(r['mean']):+.2f}% (95% CI {pct(r['lo']):+.2f}% to "
        f"{pct(r['hi']):+.2f}%).",
        f"* **Paired t-test (two-sided):** t = {r['t']:.3f}, d.f. = {r['df']}, p = {r['p']:.3g} -> "
        f"{'reject' if r['p'] < ALPHA else 'do not reject'} H0.",
        f"* **Does it matter (5%)?** {verdict}.",
        f"* Alternatives on all {na + nb:,} sales: F = {F:.3f} (p = {pF:.3g}); "
        + "; ".join(f"{n} t = {res.statistic:.2f}, d.f. = {df:.0f}, p = {res.pvalue:.3g}, gap {pct(diff):+.2f}%"
                    for n, diff, res, df in alts) + ".",
        "",
    ])
    return r


# ============================================================================ figure
def figure(r1, r1b, out2, gap, lo, hi, r4):
    fig, (a, b, c) = plt.subplots(3, 1, figsize=(COL_W, 3.9), height_ratios=[1, 1.1, 1.3])

    def ci_rows(ax, items, thr, unit, two_sided):
        y = np.arange(len(items))[::-1]
        ax.axvspan(-thr if two_sided else -1e9, thr, color="#eef1f4", lw=0, zorder=0)
        for yi, (name, est, l, h) in zip(y, items):
            ax.plot([l, h], [yi, yi], color=SERIES[0], lw=1.4)
            ax.plot(est, yi, "o", color=SERIES[0], ms=3.5)
        ax.axvline(0, color=MUTED, lw=0.6)
        ax.axvline(thr, color=INK, lw=0.6, ls="--")
        if two_sided:
            ax.axvline(-thr, color=INK, lw=0.6, ls="--")
        ax.set_yticks(y, [f"{i[0]}  {i[1]:+.1f}{unit}" for i in items])
        ax.set_ylim(-0.6, len(items) - 0.4)
        ax.grid(axis="y", visible=False)

    items = [("T1 pre-war", pct(r1["mean"]), pct(r1["lo"]), pct(r1["hi"])),
             ("T1 no 1935-45", pct(r1b["mean"]), pct(r1b["lo"]), pct(r1b["hi"])),
             ("T4 shops", pct(r4["mean"]), pct(r4["lo"]), pct(r4["hi"]))]
    ci_rows(a, items, 5, "%", True)
    lim = max(abs(v) for it in items for v in it[1:]) * 1.35
    a.set_xlim(-lim, lim)
    a.set_xlabel("Within-cell $/sq ft gap (%)")
    a.set_title("(a) T1, T4: paired t (5%)")

    items = [(f"{lab.split(':')[1].strip().split(' (')[0]}", 100 * (r["p2"] - r["p1"]), 100 * r["lo"],
              100 * r["hi"]) for r in out2.values() for lab in [r["label"]]]
    ci_rows(b, items, 10, " pp", False)
    b.set_xlim(min(-6, min(i[2] for i in items) - 3), max(i[3] for i in items) * 1.3)
    b.set_xlabel("Change in share below the line (pp)")
    b.set_title("(b) T2: two-proportion z (10 pp)")

    items = [(f"{bo}", gap[bo], lo[bo], hi[bo]) for bo in gap.index]
    ci_rows(c, items, 2, " pp", True)
    lim = max(abs(v) for it in items for v in it[1:]) * 1.4
    c.set_xlim(-lim, lim)
    c.set_xlabel("Transfer share minus expected (pp)")
    c.set_title("(c) T3: chi-square GOF (2 pp)")
    save(fig, "f13_test_results")


def main():
    setup_style()
    conf = pd.read_pickle(CONFIRM_PKL)
    assert (conf["split"] == "confirmation").all()
    md.extend(["# Hypothesis test results (confirmation set, 30%, seed 42)", "",
               f"Plan fixed in advance: `reports/test_plan.md`. Rows: {len(conf):,}. alpha = 0.05.", ""])
    r1, r1b = t1(conf)
    out2 = t2(conf)
    gap, lo, hi = t3(conf)
    r4 = t4(conf)
    figure(r1, r1b, out2, gap, lo, hi, r4)
    res = pd.DataFrame(rows)
    res.to_csv(REPORTS / "test_results.csv", index=False, float_format="%.6g")
    (REPORTS / "test_results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
