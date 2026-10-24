"""Shared paths, constants and plot style for the NYC Property Sales pipeline.

Every script imports from here so that a TA re-running the code gets the same
paths, seed and thresholds everywhere.
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "raw" / "NYC_Citywide_Annualized_Calendar_Sales_Update.csv"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
REPORTS = ROOT / "reports"
for _d in (PROCESSED, FIGURES, REPORTS):
    _d.mkdir(parents=True, exist_ok=True)

CLEAN_PKL = PROCESSED / "sales_clean.pkl"          # all rows after cleaning (with flags)
SPLIT_CSV = PROCESSED / "split_assignment.csv"     # row_id -> exploration / confirmation
EXPLORE_PKL = PROCESSED / "sales_exploration.pkl"  # 70 %: all EDA happens here
CONFIRM_PKL = PROCESSED / "sales_confirmation.pkl" # 30 %: held out for the hypothesis tests

SEED = 42
EXPLORATION_SHARE = 0.70

# Expected shape of the frozen download (checked by 01_audit_raw.py)
EXPECTED_RAW_ROWS = 845_607
EXPECTED_RAW_COLS = 29

BOROUGHS = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}
BOROUGH_ORDER = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]

# Price thresholds (fixed before looking at prices against anything; see README)
NOMINAL_MAX = 100          # <= $100: ownership transfer, not a market price
LOW_PRICE_MAX = 10_000     # $101 - $10,000: not a credible NYC market price for a property
MEGA_PRICE_MIN = 100_000_000

PREWAR_CUTOFF = 1940       # pre-war = year built < 1940
MIN_YEAR_BUILT = 1800      # earlier values are impossible for NYC's standing stock
TOLL_START = "2025-01-05"  # Manhattan congestion toll start date

# Manhattan's street grid is rotated ~29 degrees from true north, so "60th St and
# below" is a tilted line. Slope from two points on 60th St (5th Ave 40.7646,-73.9730;
# York Ave 40.7590,-73.9590) = -0.4; the line is then moved 0.0010 deg north so it runs
# between 60th and 61st St (the zone includes 60th St). Checked against parsed street
# addresses in 02_clean.py: every East/West 50th-70th St sale lands on the right side.
TOLL_LINE_LAT0, TOLL_LINE_LON0, TOLL_LINE_SLOPE = 40.7656, -73.9730, -0.4


def toll_line_lat(lon):
    """Latitude of the 60th Street line at a given longitude."""
    return TOLL_LINE_LAT0 + TOLL_LINE_SLOPE * (lon - TOLL_LINE_LON0)


# ---------------------------------------------------------------- plot style
# Categorical slots in fixed order (validated palette, light mode) - never cycled.
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BOROUGH_COLORS = dict(zip(BOROUGH_ORDER, SERIES))  # colour follows the borough everywhere
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, SURFACE = "#e1e0d9", "#c3c2b7", "#fcfcfb"
SEQ_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


# Figures are drawn at the exact size they print in the two-column LaTeX report
# (A4, 18 mm margins, 7 mm column gap), so 7 pt text in the figure is 7 pt on paper.
# Drawing them larger and letting LaTeX shrink them is what made labels unreadable.
COL_W = 3.29    # one column = 83.5 mm
FULL_W = 6.85   # both columns = 174 mm


def setup_style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
        # DejaVu Sans ships with matplotlib, so every machine draws identical figures
        "font.family": "DejaVu Sans", "font.size": 7,
        "text.color": INK, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "axes.titlesize": 7.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlepad": 4, "axes.labelsize": 7, "axes.labelpad": 2,
        "axes.edgecolor": AXIS, "axes.linewidth": 0.6,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.4, "grid.linestyle": "-",
        "axes.axisbelow": True, "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
        "xtick.major.size": 2, "ytick.major.size": 2, "xtick.major.width": 0.5, "ytick.major.width": 0.5,
        "xtick.major.pad": 1.5, "ytick.major.pad": 1.5,
        "lines.linewidth": 1.2, "lines.markersize": 2.5,
        "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "legend.frameon": False, "legend.fontsize": 6.5, "legend.handlelength": 1.4,
        "legend.borderaxespad": 0.3, "legend.labelspacing": 0.3,
        "patch.linewidth": 0,
        "text.parse_math": False,  # "$0-$100" is money, not maths
        "figure.dpi": 150, "figure.constrained_layout.use": True,
        "figure.constrained_layout.h_pad": 0.02, "figure.constrained_layout.w_pad": 0.02,
        "savefig.dpi": 300, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
        "pdf.fonttype": 42,  # embed TrueType so the text stays selectable in the PDF report
    })


def save(fig, name):
    """Write figures/<name>.pdf (vector, for the LaTeX report) and .png (for the README).
    Timestamps are left out so re-running gives byte-identical files."""
    pdf, png = FIGURES / f"{name}.pdf", FIGURES / f"{name}.png"
    fig.savefig(pdf, metadata={"CreationDate": None, "ModDate": None, "Producer": None})
    fig.savefig(png, metadata={"Software": None})
    plt.close(fig)
    return png
