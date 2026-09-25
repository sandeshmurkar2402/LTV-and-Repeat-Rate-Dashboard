"""Transforms raw Google Sheet values into the pivoted tables the dashboard needs."""
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

BLUE_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "brand_blue_heat", ["#f7fbff", "#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#0d366b"]
)
GREEN_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "brand_green_heat", ["#f4fbf8", "#c9f0e0", "#8fddbf", "#43c491", "#1baf7a", "#0d5c3f"]
)
VIOLET_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "brand_violet_heat", ["#f8f6fd", "#dcd3f7", "#b7a4ec", "#8874d6", "#4a3aa7", "#2a1f66"]
)
TEAL_HEATMAP_CMAP = LinearSegmentedColormap.from_list(
    "brand_teal_heat", ["#f2fbfa", "#c3ede8", "#7fd4c9", "#33ada0", "#0f7d72", "#0a4f48"]
)

COHORT_ORDER = [
    "enrolled_users", "M0", "M01", "M02", "M03", "M04", "M05", "M06",
    "M07", "M08", "M09", "M10", "M11", "M12", "M12plus",
]
COHORT_LABELS = {
    "enrolled_users": "New",
    "M0": "M0", "M01": "M1", "M02": "M2", "M03": "M3", "M04": "M4",
    "M05": "M5", "M06": "M6", "M07": "M7", "M08": "M8", "M09": "M9",
    "M10": "M10", "M11": "M11", "M12": "M12", "M12plus": "M12+",
}
NEW_ACQ_LABEL = COHORT_LABELS["enrolled_users"]  # short table-column header for enrolled_users
DIMENSION_COLS = ["acq_business_line", "acq_platform", "cm_business_line", "platform", "fo_val_buc"]
# acq_platform ordered before cm_business_line, and platform ("CM Platform")
# after it, here (not alphabetical/schema order) specifically so Cross Sales
# (Platform x Acq BL)'s row outline expands Acq BL -> Acq Platform -> CM
# Business Line -> CM Platform, per request — this is the only current metric
# with all 4 of these active at once (Cross_Sell only ever has
# acq_business_line + cm_business_line active, so it's unaffected by this
# ordering). The raw sheet's own "platform" column — distinct from
# "acq_platform" — was populated with real per-row values alongside
# cm_business_line; it's the platform the CM/repeat-side transaction happened
# on, the same way cm_business_line is the repeat-side business line.
DIMENSION_LABELS = {
    "acq_business_line": "Acquisition Business Line",
    "cm_business_line": "CM Business Line",
    "acq_platform": "Acquisition Platform",
    "platform": "CM Platform",
    "fo_val_buc": "FO Value Bucket",
}
METRIC_LABELS = {
    "Overall_Repeat_Rate": "Overall",
    "Businessline_Repeat_Rate": "By Business Line",
    "Platforwise_Repeat_Rate": "By Platform",
    "Repeat_Rate_FO_Value": "By FO Value Bucket",
    "Cross_Sell": "Cross Sales",
    # New sheet metric (added alongside Cross Sales, not replacing it). Originally
    # cm_business_line was a constant 'All' placeholder for every row of this
    # metric; the sheet has since been populated with real per-type values, so it
    # now varies alongside acq_business_line and acq_platform — 3 active
    # dimensions (see get_active_dimension_filters/DIMENSION_COLS order:
    # acq_business_line, cm_business_line, acq_platform), giving this view a
    # 3-level row outline (Acq BL -> CM BL -> Acq Platform). Labeled distinctly
    # from "Cross Sales" (acq_business_line x cm_business_line only) and "By
    # Platform" (no business-line breakdown at all).
    "Platforwise_Acq_BL_Repeat_Rate": "Cross Sales (Platform x Acq BL)",
}
# Only these use the M0-M12+ acquisition-cohort pivot the Revenue/Users/Purchases/AOV
# tabs are built around. Recency and the Session/Purchase Month metrics have their own
# dedicated tabs (different bucket scheme / no cohort structure at all) — excluding them
# here keeps them out of the "View" dropdown on those cohort tabs, where they'd otherwise
# produce a nonsense table.
MAIN_DASHBOARD_METRICS = list(METRIC_LABELS.keys())

RECENCY_ORDER = [
    "NA", "0", "1", "2", "3", "4", "5", "6", "7",
    "8-14days", "15-30days", "31-45days", "46+_days",
]
RECENCY_LABELS = {
    "NA": "N/A", "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7",
    "8-14days": "8-14 Days", "15-30days": "15-30 Days", "31-45days": "31-45 Days", "46+_days": "46+ Days",
}
PERIOD_METRIC_SOURCE_COLS = {
    "Revenue": ("rev", "new_users_revenue", "repeat_users_revenue"),
    "Users": ("users", "new_users", "repeat_users"),
    "Purchases": ("purchases", "new_users_purchases", "repeat_users_purchases"),
}
BUSINESS_LINE_PRIORITY_ORDER = [
    "Group Online", "Group Offline", "One On One", "One On One Extension",
    "Digital Goods", "Platform Fees", "Energy Exchange", "Uncategorised",
    "DAILYSESSION", "INCOMPLETE_DATA_WHILE_PAYMENT_RECONCILIATION",
]
DIMENSION_PRIORITY = {
    "acq_business_line": BUSINESS_LINE_PRIORITY_ORDER,
    "cm_business_line": BUSINESS_LINE_PRIORITY_ORDER,
}
DIMENSION_DEFAULT = {
    "acq_business_line": "Group Online",
    "cm_business_line": "Group Online",
}


def order_with_priority(options: list, priority: list) -> list:
    """Priority items first (in the given order), then the rest alphabetically."""
    pri = [o for o in priority if o in options]
    rest = sorted(o for o in options if o not in priority)
    return pri + rest


def _to_num(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.replace(",", "", regex=False).str.strip()
    cleaned = cleaned.replace({"[NULL]": np.nan, "": np.nan, "nan": np.nan})
    return pd.to_numeric(cleaned, errors="coerce")


NUMERIC_COLS = [
    "rev", "users", "purchases",
    "new_users_revenue", "new_users", "repeat_users_revenue", "repeat_users",
    "new_users_purchases", "repeat_users_purchases",
]


def build_repeat_df(raw_values) -> pd.DataFrame:
    header, *rows = raw_values
    df = pd.DataFrame(rows, columns=header)
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = _to_num(df[c])
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df["acq_platform"] = df["acq_platform"].replace({"[NULL]": "Unknown"})
    if "platform" in df.columns:
        # Same treatment as acq_platform above — without this, platform's
        # (CM Platform's) "[NULL]" rows would just be silently dropped by
        # unique_options() instead of surfacing as a real, filterable
        # "Unknown" category the way Acquisition Platform's already do.
        df["platform"] = df["platform"].replace({"[NULL]": "Unknown"})
    df = df.dropna(subset=["period"])
    return df


def build_ltv_df(raw_values) -> pd.DataFrame:
    header, *rows = raw_values
    df = pd.DataFrame(rows, columns=header)
    df = df.loc[:, [c for c in df.columns if c.strip() != ""]]
    df["Month"] = pd.to_datetime(df["Month"], format="%d-%b-%y", errors="coerce")
    df = df.dropna(subset=["Month"])
    for c in df.columns:
        if c != "Month":
            df[c] = _to_num(df[c])
    return df.sort_values("Month").reset_index(drop=True)


def unique_options(series: pd.Series) -> list:
    """Distinct non-empty values, excluding the sheet's raw '[NULL]' placeholder
    (which otherwise shows up as a bogus, literal dropdown option)."""
    return sorted(u for u in series.dropna().unique() if u and u != "[NULL]")


def get_metric_options(df: pd.DataFrame):
    available = set(df["metric"].unique())
    return [m for m in MAIN_DASHBOARD_METRICS if m in available]


def get_active_dimension_filters(df: pd.DataFrame, metric: str):
    """Returns (dict of column -> sorted option list, sub-dataframe for this metric).

    Only dimensions that actually vary for the chosen metric are returned, so the
    UI never offers a combination that yields zero rows.
    """
    sub = df[df["metric"] == metric]
    active = {}
    for d in DIMENSION_COLS:
        uniques = unique_options(sub[d])
        if len(uniques) > 1:
            active[d] = uniques
    return active, sub


def filter_df(sub: pd.DataFrame, selections: dict) -> pd.DataFrame:
    """Each selection value may be a scalar (single-select) or a list (multi-select —
    matching rows are combined via isin, and pivot_cohort's sum aggregation then adds
    their New/Rev/Users/Purchases together automatically)."""
    out = sub
    for col, val in selections.items():
        if isinstance(val, (list, tuple, set)):
            out = out[out[col].isin(val)]
        else:
            out = out[out[col] == val]
    return out


CROSS_SELL_METRICS = {"Cross_Sell", "Platforwise_Acq_BL_Repeat_Rate"}
# Platforwise_Acq_BL_Repeat_Rate's cm_business_line column was a constant "All"
# placeholder when this metric was first added (see METRIC_LABELS) — the sheet
# has since been populated with real per-type cm_business_line values, and its
# enrolled_users rows now self-match cm_business_line == acq_business_line,
# the exact same pattern Cross_Sell already had this fix for. Added here so its
# New-users denominator no longer double-counts across cm_business_line types.


PLATFORM_SELF_MATCH_METRICS = {"Platforwise_Acq_BL_Repeat_Rate"}
# Platforwise_Acq_BL_Repeat_Rate's enrolled_users rows ALSO self-match
# platform == acq_platform (the same "self" pattern as cm_business_line ==
# acq_business_line, just on the platform pair instead of the business-line
# pair — verified directly against the sheet: for a given acq_business_line/
# period, the correctly cm_business_line-self-matched enrolled_users rows
# still had one row per acq_platform, each with platform == that same
# acq_platform). Without also self-matching on this pair, drilling into one
# specific Acquisition Platform (or CM Platform) still summed the New/
# enrolled_users total across every platform, showing the exact same
# (too-large) "New" value on every Acq Platform / CM Platform sub-row instead
# of that platform's own count. Cross_Sell has no platform breakdown at all,
# so it's unaffected by this — scoped to this one metric.


def with_acq_line_enrolled(df: pd.DataFrame, filtered: pd.DataFrame, metric: str, acq_business_line, acq_platform=None) -> pd.DataFrame:
    """Cross_Sell's 'enrolled_users' row is tagged per cm_business_line ('type'), so
    filtering to one specific type (as the M0-M12+ numerator does) leaves most months
    with no enrolled_users row at all. The denominator should instead be that same
    acq_business_line's OWN enrolled_users row — i.e. the row where cm_business_line
    equals acq_business_line — not summed across every cm_business_line/type breakdown
    for that acq line (that double-counts: e.g. Group Offline, Jun-2026 was giving 310
    = 307 (Group Offline) + 3 (Group Online) + 0 (Platform Fees) instead of the correct
    307). acq_business_line may be a single value or a list — with multiple acq lines
    selected, each contributes its own self-matched row, summed together.

    acq_platform (only meaningful for PLATFORM_SELF_MATCH_METRICS) narrows the same
    way — a single value when a specific Acquisition Platform (or, since they're
    always fixed together, CM Platform) sub-row is being drilled into, or the
    currently-checked list from the filter picker otherwise; omitted (None) sums
    across every platform, matching the un-narrowed aggregate/total row."""
    if metric not in CROSS_SELL_METRICS or not acq_business_line:
        return filtered
    acq_lines = acq_business_line if isinstance(acq_business_line, (list, tuple, set)) else [acq_business_line]
    if not acq_lines:
        return filtered
    mask = (
        (df["metric"] == metric)
        & (df["acq_business_line"].isin(acq_lines))
        & (df["cm_business_line"] == df["acq_business_line"])
        & (df["months_since_acq_buc"] == "enrolled_users")
    )
    if metric in PLATFORM_SELF_MATCH_METRICS:
        mask = mask & (df["platform"] == df["acq_platform"])
        if acq_platform:
            acq_platforms = acq_platform if isinstance(acq_platform, (list, tuple, set)) else [acq_platform]
            if acq_platforms:
                mask = mask & df["acq_platform"].isin(acq_platforms)
    enrolled_rows = df[mask]
    if enrolled_rows.empty:
        return filtered
    summed = enrolled_rows.groupby("period", as_index=False)[NUMERIC_COLS].sum()
    summed["months_since_acq_buc"] = "enrolled_users"
    without_enrolled = filtered[filtered["months_since_acq_buc"] != "enrolled_users"]
    return pd.concat([without_enrolled, summed], ignore_index=True)


def pivot_cohort(df_filtered: pd.DataFrame, value_col: str) -> pd.DataFrame:
    pv = df_filtered.pivot_table(
        index="period", columns="months_since_acq_buc", values=value_col, aggfunc="sum"
    )
    pv = pv.reindex(columns=COHORT_ORDER)
    return pv.sort_index()


def to_repeat_rate_pct(pv: pd.DataFrame) -> pd.DataFrame:
    denom = pv["enrolled_users"].replace(0, np.nan)
    pct = pv.drop(columns=["enrolled_users"]).div(denom, axis=0) * 100
    pct.insert(0, "enrolled_users", pv["enrolled_users"])
    return pct


def compute_aov(rev_pv: pd.DataFrame, purchases_pv: pd.DataFrame) -> pd.DataFrame:
    purch_safe = purchases_pv.replace(0, np.nan)
    return rev_pv / purch_safe


def safe_divide_series(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Elementwise numerator / denominator, treating a 0 denominator as missing
    (NaN) rather than raising or dividing by zero — used for the AOV/ARPU 'Total'
    row, which needs the true blended ratio (sum of revenue / sum of the
    denominator) rather than an average of already-computed per-bucket ratios."""
    return numerator / denominator.replace(0, np.nan)


def relabel(pv: pd.DataFrame, labels: dict | None = None) -> pd.DataFrame:
    labels = labels if labels is not None else COHORT_LABELS
    disp = pv.copy()
    disp.columns = [labels.get(c, c) for c in disp.columns]
    disp.index = disp.index.strftime("%b-%Y")
    disp.index.name = "Month"
    return disp


# ------------------------------------------------------------- Recency tab ---
# Recency measures how activity in a given month breaks down by how long ago the
# user's last engagement was (buckets 0-7, then day ranges for longer gaps) — a
# composition-of-current-activity view, not an acquisition cohort. "Total" here is a
# real row sum (every bucket together = 100%), unlike the repeat-rate tabs where "New"
# is an independent acquisition count that the cohort values are compared against.

def pivot_recency(df_filtered: pd.DataFrame, value_col: str) -> pd.DataFrame:
    pv = df_filtered.pivot_table(
        index="period", columns="months_since_acq_buc", values=value_col, aggfunc="sum"
    )
    pv = pv.reindex(columns=RECENCY_ORDER)
    return pv.sort_index()


def with_total_column(pv: pd.DataFrame, bucket_cols: list) -> pd.DataFrame:
    out = pv.copy()
    out.insert(0, "Total", out[bucket_cols].sum(axis=1, skipna=True))
    return out


def to_contribution_pct(pv_with_total: pd.DataFrame, bucket_cols: list) -> pd.DataFrame:
    total = pv_with_total["Total"].replace(0, np.nan)
    pct = pv_with_total[bucket_cols].div(total, axis=0) * 100
    pct.insert(0, "Total", pv_with_total["Total"])
    return pct


# --------------------------------------------------- Session/Purchase Month tabs ---
# These carry no cohort breakdown at all (months_since_acq_buc is always "ALL") — just
# a Total/New/Repeat split per period, already computed at source. "Total" (rev/users/
# purchases) is the authoritative figure here, not a sum of New+Repeat we compute
# ourselves — the two don't always reconcile exactly (New+Repeat can double-count a
# user), so each column is shown exactly as the sheet provides it.

def pivot_period_metric(df_filtered: pd.DataFrame, value_type: str) -> pd.DataFrame:
    total_col, new_col, repeat_col = PERIOD_METRIC_SOURCE_COLS[value_type]
    grouped = df_filtered.groupby("period")[[total_col, new_col, repeat_col]].sum()
    grouped.columns = ["Total", "New", "Repeat"]
    return grouped.sort_index()


def with_new_repeat_pct(pv: pd.DataFrame) -> pd.DataFrame:
    """Adds 'New %' and 'Repeat %' — each share of that period's Total."""
    out = pv.copy()
    total_safe = out["Total"].replace(0, np.nan)
    out["New %"] = out["New"] / total_safe * 100
    out["Repeat %"] = out["Repeat"] / total_safe * 100
    return out


# --------------------------------------- Business Line / Platform contribution ---
# "How much does each business line contribute to platform X's total?" (and the
# mirror, "how much does each platform contribute to business line Y's total?") —
# an open-ended-dimension version of pivot_recency: same period-indexed pivot, but
# the bucket dimension is business line or platform (no fixed order) rather than a
# fixed recency/cohort enum, so it's reindexed by whatever's actually present instead
# of a constant list. with_total_column / to_contribution_pct above are already
# dimension-agnostic and are reused as-is.

def pivot_by_dimension(df_filtered: pd.DataFrame, dim_col: str, value_col: str) -> pd.DataFrame:
    """Like unique_options(), rows where dim_col is the sheet's raw '[NULL]'
    placeholder (or empty) are dropped first — otherwise '[NULL]' shows up as a
    bogus, literal breakdown column alongside the real business lines/platforms."""
    clean = df_filtered[df_filtered[dim_col].apply(lambda v: bool(v) and v != "[NULL]")]
    pv = clean.pivot_table(index="period", columns=dim_col, values=value_col, aggfunc="sum")
    return pv.sort_index()


def true_period_total(df_filtered: pd.DataFrame, value_col: str) -> pd.Series:
    """Sum of value_col by period across EVERY row — deliberately NOT filtered by
    whether the breakdown dimension (business line / platform) is tagged. Used as
    the contribution-% denominator instead of summing pivot_by_dimension's named
    bucket columns: some revenue's business line is always tagged but its platform
    sometimes isn't (or vice versa), so summing only the valid buckets would silently
    undercount the true total whenever that happens (e.g. it under-reported Apr-2026
    Purchase Month revenue by ~₹350k when broken down by platform specifically,
    versus the same period's true, business-line-agnostic total)."""
    return df_filtered.groupby("period")[value_col].sum().sort_index()


def exclude_platform_fees(df: pd.DataFrame) -> pd.DataFrame:
    """Platform Fees isn't a real business line — it's an extra charge tacked onto a
    purchase that already belongs to some other (real) business line. A user counted
    there would be counted AGAIN if Platform Fees' own rows were included when
    summing Users across multiple business lines into a combined total, so this
    scope must be excluded before that kind of sum. Revenue/Purchases/AOV are
    unaffected and must never be passed through this.
    If df is ENTIRELY Platform Fees rows (e.g. a scope already isolated to just that
    one line item), excluding would leave nothing — return df unchanged so that
    line item's own real value still displays instead of a false zero."""
    if "cm_business_line" not in df.columns:
        return df
    filtered = df[df["cm_business_line"] != "Platform Fees"]
    return filtered if not filtered.empty else df


def format_table(disp: pd.DataFrame, pct_cols: set | None = None, currency_cols: set | None = None) -> pd.DataFrame:
    """Renders a numeric table to display strings, showing '–' for missing cohorts.
    Uses an en dash rather than a plain hyphen: st.dataframe otherwise prints the
    literal word 'None' for NaN cells, and st.table renders a bare '-' as an empty
    markdown bullet list ('-' is CommonMark list syntax) instead of the character."""
    pct_cols = pct_cols or set()
    currency_cols = currency_cols or set()
    out = pd.DataFrame(index=disp.index)
    for c in disp.columns:
        if c in pct_cols:
            out[c] = disp[c].map(lambda v: f"{v:,.1f}%" if pd.notna(v) else "–")
        else:
            prefix = "₹" if c in currency_cols else ""
            out[c] = disp[c].map(lambda v: f"{prefix}{v:,.0f}" if pd.notna(v) else "–")
    return out


def table_height(n_rows: int, row_px: int = 35, header_px: int = 38, padding_px: int = 12) -> int:
    """Full pixel height needed to show every row with no internal scrollbar —
    grows automatically with the number of months in the selected date range."""
    return header_px + row_px * max(n_rows, 1) + padding_px


def _relative_luminance(rgba) -> float:
    """WCAG relative luminance — same formula pandas' own background_gradient uses
    internally to decide when a cell is 'dark enough' to need a lighter text color."""
    def _channel(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (_channel(c) for c in rgba[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


HEADER_BG = "#4a0404"
HEADER_TEXT = "#ffffff"


def _with_header_style(styler):
    """Dark maroon / white header row — only works via st.table, not st.dataframe
    (st.dataframe's header is canvas-rendered by the grid widget and ignores Styler
    table_styles entirely; 'thead th' scopes this to the header row only, leaving
    the Month row-index cells, which pandas also renders as <th>, untouched)."""
    return styler.set_table_styles(
        [{"selector": "thead th", "props": [("background-color", HEADER_BG), ("color", HEADER_TEXT)]}],
        overwrite=False,
    )


def styled_cohort_table(str_df: pd.DataFrame, numeric_df: pd.DataFrame, gradient_cols: list, cmap=None,
                         dark_text_color: str | None = None, text_color_threshold: float = 0.5):
    """Colors the cohort cells like a heatmap directly in the table (gmap drives the
    color scale off the real numbers while str_df supplies the already-formatted,
    NaN-safe display text — st.dataframe otherwise mishandles NaN text via na_rep).

    Missing cohort cells (not yet elapsed) are filled with the range minimum rather
    than left as NaN: matplotlib's cmap(nan) renders solid black, which pandas'
    background_gradient passes straight through as an opaque cell background.

    dark_text_color: on dark cells, use this color instead of pandas' default white
    (white reads poorly against a light-hued ramp like yellow/amber)."""
    cmap = cmap or BLUE_HEATMAP_CMAP
    block = numeric_df[gradient_cols].astype(float)
    fill_value = block.min().min()
    if pd.isna(fill_value):
        fill_value = 0.0
    filled = block.fillna(fill_value)
    gmap = filled.to_numpy()

    if dark_text_color is None:
        styler = str_df.style.background_gradient(
            cmap=cmap, subset=gradient_cols, gmap=gmap, axis=None,
            text_color_threshold=text_color_threshold,
        )
        return _with_header_style(styler)

    vmin, vmax = np.nanmin(gmap), np.nanmax(gmap)
    span = vmax - vmin if vmax > vmin else 1.0
    norm = (filled - vmin) / span

    def _text_color(col):
        return [
            f"color: {dark_text_color}" if _relative_luminance(cmap(v)) < text_color_threshold else ""
            for v in norm[col.name]
        ]

    styler = str_df.style.background_gradient(
        cmap=cmap, subset=gradient_cols, gmap=gmap, axis=None, text_color_threshold=0,
    )
    styler = styler.apply(_text_color, subset=gradient_cols, axis=0)
    return _with_header_style(styler)


# ------------------------------------------------- Period-over-period diff tables ---
# Every rendered table gets a companion table directly below it showing each
# period's value vs. the immediately preceding period (in chronological order,
# within whatever month range is currently selected). Absolute-value columns
# (Revenue/Users/Purchases/AOV/ARPU/absolute contribution amounts) can toggle
# between an Absolute Diff (current - previous) and a % Diff / growth-drop
# ((current - previous) / previous * 100); percentage columns (Repeat Rate %,
# %Contribution, New %/Repeat %) always show a percentage-point difference —
# same arithmetic as Absolute Diff, just labeled "pp" instead of a currency/plain
# number, since subtracting two percentages already IS the percentage-point
# change, not something that itself needs "growth-rate-of-a-growth-rate" treatment.
DIFF_GROWTH_COLOR = "#0d5c3f"
DIFF_GROWTH_BG = "#e6f7ef"
DIFF_DROP_COLOR = "#8a1f1f"
DIFF_DROP_BG = "#fdeaea"


def compute_period_diff(pv: pd.DataFrame, pct_cols: set | None = None, diff_mode: str = "% Diff") -> tuple:
    """Row-over-row difference (row[t] - row[t-1]); the first row has no
    predecessor and is dropped, so the result has one fewer row than pv.

    Returns (diff_df, kinds) where kinds maps each column to how it should be
    labeled/formatted downstream: 'pp' (percentage-point diff — pct_cols always
    get this), 'pct' (a growth/drop % diff — non-pct columns when diff_mode is
    '% Diff'), or 'abs' (a plain absolute diff — non-pct columns when diff_mode
    is 'Absolute Diff')."""
    pct_cols = pct_cols or set()
    prev = pv.shift(1)
    abs_diff = pv - prev
    out = pd.DataFrame(index=pv.index, columns=pv.columns, dtype=float)
    kinds = {}
    for c in pv.columns:
        if c in pct_cols:
            out[c] = abs_diff[c]
            kinds[c] = "pp"
        elif diff_mode == "% Diff":
            out[c] = safe_divide_series(abs_diff[c], prev[c]) * 100
            kinds[c] = "pct"
        else:
            out[c] = abs_diff[c]
            kinds[c] = "abs"
    return out.iloc[1:], kinds


BASELINE_GRAY = "#c3c2b7"


def diff_bar_colors(values) -> list:
    """Per-bar green/red (growth/drop) marker colors for a Plotly bar trace —
    values may include NaN (neutral gray) for the always-empty first period."""
    out = []
    for v in values:
        if pd.isna(v):
            out.append(BASELINE_GRAY)
        elif v >= 0:
            out.append(DIFF_GROWTH_COLOR)
        else:
            out.append(DIFF_DROP_COLOR)
    return out


def styled_multi_group_table(str_df: pd.DataFrame, numeric_df: pd.DataFrame, groups: list):
    """Like styled_cohort_table, but each group of columns gets its own independent
    color scale (and its own cmap) — e.g. absolute counts, percentages, and AOV don't
    belong on the same gradient, so grouping them separately keeps each one meaningful
    while still visually distinguishing the sections (blue/green/violet) at a glance.

    groups: list of (col_list, cmap) tuples."""
    styler = str_df.style
    for cols, cmap in groups:
        cols = [c for c in cols if c in numeric_df.columns]
        if not cols:
            continue
        block = numeric_df[cols].astype(float)
        fill_value = block.min().min()
        if pd.isna(fill_value):
            fill_value = 0.0
        gmap = block.fillna(fill_value).to_numpy()
        styler = styler.background_gradient(cmap=cmap, subset=cols, gmap=gmap, axis=None)
    return _with_header_style(styler)
