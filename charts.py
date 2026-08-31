"""Plotly figure builders, styled per the dataviz palette (references/palette.md)."""
import numpy as np
import plotly.graph_objects as go
from matplotlib import colormaps
from matplotlib.colors import to_hex

CATEGORICAL = ["#2a78d6", "#1baf7a", "#eda100", "#008300", "#4a3aa7", "#e34948", "#e87ba4", "#eb6834"]
MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

TITLE_FONT = dict(color="#52514e", size=14)

BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=MUTED, size=12),
    legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=10, r=10, t=40, b=10),
    hovermode="x unified",
)


def _title(text):
    return dict(text=text, font=TITLE_FONT)


def _style_axes(fig):
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, ticks="outside", tickcolor=BASELINE)
    fig.update_yaxes(showgrid=True, gridcolor=GRIDLINE, zeroline=False)
    return fig


def multi_line(df, x, y_cols, labels, title, y_title="", emphasize_first=False):
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Scatter(
            x=df[x], y=df[col], mode="lines+markers", name=labels.get(col, col),
            line=dict(width=3 if (emphasize_first and i == 0) else 2, color=CATEGORICAL[i % len(CATEGORICAL)],
                      shape="spline", smoothing=0.35),
            marker=dict(size=5),
        ))
    fig.update_layout(title=_title(title), yaxis_title=y_title, **BASE_LAYOUT)
    return _style_axes(fig)


def grouped_bar(df, x, y_cols, labels, title, y_title=""):
    fig = go.Figure()
    for i, col in enumerate(y_cols):
        fig.add_trace(go.Bar(x=df[x], y=df[col], name=labels.get(col, col), marker_color=CATEGORICAL[i % len(CATEGORICAL)]))
    fig.update_layout(title=_title(title), yaxis_title=y_title, barmode="group", **BASE_LAYOUT)
    return _style_axes(fig)


def single_bar(x, y, title, y_title="", color=None):
    fig = go.Figure(go.Bar(x=list(x), y=list(y), marker_color=color or CATEGORICAL[0]))
    fig.update_layout(title=_title(title), yaxis_title=y_title, showlegend=False, **BASE_LAYOUT)
    return _style_axes(fig)


def combo_bar_line(x, bar_y, line_y, bar_label, line_label, title, bar_y_title="", line_y_title="",
                    bar_color=None, line_color=None):
    """Bar (left axis) + smooth line (right axis) — the one case where two y-axes
    are appropriate, since acquisitions (count) and LTV (currency) are different
    units. Each axis is color-coded to its series so the pairing stays unambiguous."""
    bar_color = bar_color or CATEGORICAL[0]
    line_color = line_color or CATEGORICAL[4]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(x), y=list(bar_y), name=bar_label, marker_color=bar_color, yaxis="y1"))
    fig.add_trace(go.Scatter(
        x=list(x), y=list(line_y), name=line_label, mode="lines+markers",
        line=dict(width=3, color=line_color, shape="spline", smoothing=0.35),
        marker=dict(size=6, color=line_color), yaxis="y2",
    ))
    fig.update_layout(
        title=_title(title),
        yaxis=dict(title=dict(text=bar_y_title, font=dict(color=bar_color)), tickfont=dict(color=bar_color),
                    showgrid=True, gridcolor=GRIDLINE, zeroline=False),
        yaxis2=dict(title=dict(text=line_y_title, font=dict(color=line_color)), tickfont=dict(color=line_color),
                     overlaying="y", side="right", showgrid=False, zeroline=False),
        **BASE_LAYOUT,
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, ticks="outside", tickcolor=BASELINE)
    return fig


def new_repeat_bar(x, new_y, repeat_y, title, y_title="", height=420):
    """New (bottom) + Repeat (top) stacked to Total, with fixed colors so 'New' and
    'Repeat' always read the same way across every chart that uses this split."""
    fig = go.Figure()
    fig.add_trace(go.Bar(x=list(x), y=list(new_y), name="New", marker_color=CATEGORICAL[0]))
    fig.add_trace(go.Bar(x=list(x), y=list(repeat_y), name="Repeat", marker_color=CATEGORICAL[1]))
    fig.update_layout(title=_title(title), barmode="stack", height=height, yaxis_title=y_title, **BASE_LAYOUT)
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, ticks="outside", tickcolor=BASELINE, tickangle=-45)
    fig.update_yaxes(showgrid=True, gridcolor=GRIDLINE, zeroline=False)
    return fig


def _ordinal_ramp(n):
    """n perceptually well-spread colors along an ordered ramp (turbo, clipped away
    from its near-black ends) — cohorts M0..M12+ are ordinal, not nominal, so a
    smoothly ordered ramp reads correctly and scales to any cohort count."""
    cmap = colormaps["turbo"]
    return [to_hex(cmap(t)) for t in np.linspace(0.08, 0.92, max(n, 1))]


def stacked_cohort_bar(pivot_df, cohort_cols, col_labels, title, is_pct=False, height=580, pct_axis_title="Repeat Rate %", colors=None):
    """Month on x, one stacked bar segment per column (cohort, or any other ordered
    breakdown — recency buckets, New/Repeat, etc.) on y.

    colors: explicit per-segment colors, for nominal breakdowns (business line,
    platform) where a smoothly-ordered ramp would wrongly imply sequence — defaults
    to the ordinal turbo ramp for genuinely ordered breakdowns (cohorts, recency)."""
    x_labels = [d.strftime("%b-%Y") for d in pivot_df.index]
    colors = colors or _ordinal_ramp(len(cohort_cols))
    value_fmt = ".1f" if is_pct else ",.0f"
    fig = go.Figure()
    for i, col in enumerate(cohort_cols):
        label = col_labels.get(col, col)
        fig.add_trace(go.Bar(
            x=x_labels, y=pivot_df[col].fillna(0), name=label, marker_color=colors[i],
            hovertemplate=label + ": %{y:" + value_fmt + "}" + ("%" if is_pct else "") + "<extra></extra>",
        ))
    fig.update_layout(
        title=_title(title), barmode="stack", height=height,
        yaxis_title=pct_axis_title if is_pct else "",
        **BASE_LAYOUT,
    )
    fig.update_xaxes(showgrid=False, linecolor=BASELINE, ticks="outside", tickcolor=BASELINE, tickangle=-45)
    fig.update_yaxes(showgrid=True, gridcolor=GRIDLINE, zeroline=False)
    return fig
