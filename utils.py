"""
Shared utilities & design system for the SR Field Insights Streamlit application.

Visual language matches the reference "AI Insights" card design:
- soft lavender canvas, white rounded cards, colored icon roundels
- red/orange/green risk pills, trend arrows ("+8% vs Last Month")
- sparkline trend charts, footer meta rows, "View Details" links
- clean Inter typography, generous spacing, subtle shadows
"""

import numpy as np
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# DESIGN TOKENS
# ---------------------------------------------------------------------------
BG = "#F3F3FB"
CARD_BG = "#FFFFFF"
BORDER = "#EEEDF9"
TEXT_DARK = "#1D1E2C"
TEXT_MUTED = "#767893"
TEXT_FAINT = "#A0A1B8"

PRIMARY = "#6C5CE7"
PRIMARY_DARK = "#5847D6"
PRIMARY_SOFT = "#EFEBFE"
PRIMARY_SOFT_TEXT = "#6C5CE7"

RED = "#E5484D"
RED_SOFT = "#FDEAEA"
ORANGE = "#E68A2E"
ORANGE_SOFT = "#FFF1DE"
GREEN = "#2FAE60"
GREEN_SOFT = "#E9F9EF"
BLUE = "#3B82F6"
BLUE_SOFT = "#E8F1FE"

RISK_STYLES = {
    "High": (RED_SOFT, RED),
    "Medium": (ORANGE_SOFT, ORANGE),
    "Low": (GREEN_SOFT, GREEN),
}

FLAG_COLS = [
    "non_successful_visit",
    "non_instore_visit",
    "rushed_visit",
    "off_route_visit_store",
    "delayed_start",
]

READABLE = {
    "non_successful_visit": "Failed Visit Flag",
    "non_instore_visit": "Non-Instore Visit Flag",
    "rushed_visit": "Rushed Visit Flag",
    "off_route_visit_store": "Off-Route Visit Flag",
    "delayed_start": "Delayed Start Flag",
    "CallDur": "Call Duration (min)",
    "gps_offset_m": "GPS Distance Offset (m)",
    "TotalCalls": "Total Calls",
}

FLAG_ICON_STYLE = {
    "non_successful_visit": ("", RED_SOFT, RED),
    "non_instore_visit": ("", PRIMARY_SOFT, PRIMARY),
    "rushed_visit": ("⏱", RED_SOFT, RED),
    "off_route_visit_store": ("", ORANGE_SOFT, ORANGE),
    "delayed_start": ("", ORANGE_SOFT, ORANGE),
}

VISIT_STATUS_MAP = {
    "E": "Extra Successful Call (Unplanned)",
    "S": "Successful Call (Planned)",
    "N": "Unsuccessful Call (Planned)",
    "X": "Extra Unsuccessful Call (Unplanned)",
}


# ---------------------------------------------------------------------------
# THEME / CSS
# ---------------------------------------------------------------------------
def inject_theme():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stApp {{
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}
        .stApp {{ background-color: {BG}; }}

        #MainMenu, footer {{ visibility: hidden; }}
        div[data-testid="stDecoration"] {{ display: none; }}
        div[data-testid="stToolbar"] {{ right: 1rem; }}

        section[data-testid="stSidebar"] {{
            background-color: {CARD_BG};
            border-right: 1px solid {BORDER};
        }}
        section[data-testid="stSidebar"] .stMultiSelect, section[data-testid="stSidebar"] label {{
            font-size: 0.85rem;
        }}

        h1, h2, h3, h4, h5 {{ color: {TEXT_DARK}; font-weight: 700; letter-spacing: -0.01em; }}
        p, span, label, div {{ color: {TEXT_DARK}; }}
        .block-container {{ padding-top: 4.5rem; padding-bottom: 3rem; max-width: 1300px; }}

        header[data-testid="stHeader"] {{
            background-color: {BG};
            height: 3rem;
        }}

        /* ---- Bordered containers become premium cards everywhere ---- */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {CARD_BG};
            border-radius: 20px !important;
            border: 1px solid {BORDER} !important;
            box-shadow: 0 6px 22px rgba(108, 92, 231, 0.07);
            padding: 4px 6px;
            transition: box-shadow 0.2s ease;
            margin-bottom: 18px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
            box-shadow: 0 10px 30px rgba(108, 92, 231, 0.12);
        }}

        /* ---- Top page header ---- */
        .top-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 14px;
            margin: 4px 0 22px 0;
        }}
        .top-header-left {{ display: flex; align-items: center; gap: 14px; }}
        .top-header-icon {{
            width: 46px; height: 46px; min-width: 46px;
            border-radius: 14px;
            background: linear-gradient(135deg, {PRIMARY} 0%, #8B7CF6 100%);
            display: flex; align-items: center; justify-content: center;
            font-size: 1.35rem;
            box-shadow: 0 6px 16px rgba(108, 92, 231, 0.35);
        }}
        .top-header-title {{ font-size: 1.5rem; font-weight: 800; color: {TEXT_DARK}; line-height: 1.4; margin: 0; padding: 0; }}
        .top-header-subtitle {{ font-size: 0.9rem; color: {TEXT_MUTED}; margin-top: 2px; line-height: 1.4; }}
        .top-header-right {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .chip {{
            background-color: {CARD_BG};
            border: 1px solid {BORDER};
            padding: 8px 16px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            color: {TEXT_MUTED};
            box-shadow: 0 2px 8px rgba(108,92,231,0.06);
        }}

        /* ---- Card section header (icon + title inside a card) ---- */
        .card-header {{ display: flex; align-items: center; gap: 12px; margin: 10px 4px 4px 4px; }}
        .card-icon {{
            width: 38px; height: 38px; min-width: 38px;
            border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 1.05rem;
        }}
        .card-title {{ font-size: 1.05rem; font-weight: 700; color: {TEXT_DARK}; }}
        .card-subtitle {{ font-size: 0.8rem; color: {TEXT_MUTED}; margin-top: -2px; }}

        /* ---- Badges / pills ---- */
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.03em;
            text-transform: uppercase;
        }}
        .badge-high {{ background-color: {RED_SOFT}; color: {RED}; }}
        .badge-med  {{ background-color: {ORANGE_SOFT}; color: {ORANGE}; }}
        .badge-low  {{ background-color: {GREEN_SOFT}; color: {GREEN}; }}
        .badge-info {{ background-color: {PRIMARY_SOFT}; color: {PRIMARY}; }}

        .trend-up-bad {{ color: {RED}; font-weight: 700; font-size: 0.82rem; }}
        .trend-up-good {{ color: {GREEN}; font-weight: 700; font-size: 0.82rem; }}
        .trend-down-bad {{ color: {RED}; font-weight: 700; font-size: 0.82rem; }}
        .trend-down-good {{ color: {GREEN}; font-weight: 700; font-size: 0.82rem; }}
        .trend-muted {{ color: {TEXT_FAINT}; font-size: 0.78rem; }}

        /* ---- Insight / narrative boxes ---- */
        .insight-card {{
            background: linear-gradient(135deg, {PRIMARY_SOFT} 0%, #F7F5FF 100%);
            border-radius: 16px;
            padding: 16px 20px;
            border: 1px solid #E7E2FD;
            margin: 10px 4px 14px 4px;
            display: flex;
            gap: 12px;
            align-items: flex-start;
        }}
        .insight-card-icon {{
            width: 30px; height: 30px; min-width: 30px;
            border-radius: 10px;
            background-color: {PRIMARY};
            color: white;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.85rem;
        }}
        .insight-text {{ color: {TEXT_MUTED} !important; font-size: 0.92rem; line-height: 1.55; }}
        .insight-text * {{ color: {TEXT_MUTED} !important; }}

        /* ---- KPI cards ---- */
        .kpi-card {{
            background-color: {CARD_BG};
            border-radius: 18px;
            padding: 18px 20px;
            border: 1px solid {BORDER};
            box-shadow: 0 6px 20px rgba(108, 92, 231, 0.07);
            display: flex; flex-direction: column; gap: 6px;
        }}
        .kpi-top {{ display: flex; justify-content: space-between; align-items: center; }}
        .kpi-icon {{
            width: 34px; height: 34px; border-radius: 10px;
            display: flex; align-items: center; justify-content: center; font-size: 0.95rem;
        }}
        .kpi-label {{ color: {TEXT_MUTED}; font-size: 0.8rem; font-weight: 600; }}
        .kpi-value {{ color: {TEXT_DARK}; font-size: 1.9rem; font-weight: 800; letter-spacing: -0.02em; }}
        .kpi-sub {{ color: {TEXT_FAINT}; font-size: 0.76rem; }}

        /* ---- Hero risk cards (Executive Dashboard, matches reference) ---- */
        .hero-card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin: 6px 6px 0 6px; }}
        .hero-icon {{
            width: 42px; height: 42px; border-radius: 13px;
            display: flex; align-items: center; justify-content: center; font-size: 1.15rem;
        }}
        .hero-trend {{ text-align: right; font-size: 0.78rem; color: {TEXT_MUTED}; }}
        .hero-title {{ font-size: 1.08rem; font-weight: 800; margin: 12px 6px 2px 6px; color: {TEXT_DARK}; }}
        .hero-desc {{ font-size: 0.85rem; color: {TEXT_MUTED}; margin: 0 6px 12px 6px; line-height: 1.5; }}
        .hero-stat-box {{
            border-radius: 14px; padding: 10px 16px; text-align: center; min-width: 92px;
        }}
        .hero-stat-value {{ font-size: 1.5rem; font-weight: 800; }}
        .hero-footer {{
            display: flex; gap: 18px; margin: 14px 6px 6px 6px; padding-top: 12px;
            border-top: 1px solid {BORDER}; flex-wrap: wrap;
        }}
        .hero-footer-item {{ display: flex; gap: 8px; align-items: flex-start; max-width: 220px; }}
        .hero-footer-icon {{
            width: 24px; height: 24px; min-width: 24px; border-radius: 8px;
            display: flex; align-items: center; justify-content: center; font-size: 0.75rem;
            background-color: {PRIMARY_SOFT}; color: {PRIMARY};
        }}
        .hero-footer-label {{ font-size: 0.7rem; color: {TEXT_FAINT}; font-weight: 700; text-transform: uppercase; }}
        .hero-footer-value {{ font-size: 0.78rem; color: {TEXT_DARK}; font-weight: 500; line-height: 1.3; }}
        .hero-meta {{ display: flex; justify-content: space-between; align-items: center; margin: 8px 6px 2px 6px; }}
        .hero-updated {{ font-size: 0.72rem; color: {TEXT_FAINT}; }}

        .summary-banner {{
            background: linear-gradient(135deg, {PRIMARY} 0%, #8B7CF6 100%);
            border-radius: 20px;
            padding: 20px 26px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
            box-shadow: 0 10px 30px rgba(108,92,231,0.28);
            margin: 6px 0 24px 0;
        }}
        .summary-banner-text {{ color: white; font-size: 0.92rem; max-width: 640px; line-height: 1.5; }}
        .summary-banner-text b {{ color: white; }}
        .summary-banner-icon {{
            width: 42px; height: 42px; border-radius: 13px; background: rgba(255,255,255,0.18);
            display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
        }}

        /* ---- Buttons ---- */
        .stButton>button, .stDownloadButton>button {{
            background-color: {PRIMARY};
            color: white !important;
            border-radius: 10px;
            border: none;
            font-weight: 600;
            padding: 0.45rem 1rem;
            white-space: nowrap;
            box-shadow: 0 4px 14px rgba(108, 92, 231, 0.25);
        }}
        .stButton>button:hover, .stDownloadButton>button:hover {{ background-color: {PRIMARY_DARK}; color: white; }}

        div[data-testid="stMetric"] {{
            background-color: {CARD_BG};
            border-radius: 16px;
            padding: 14px 18px;
            box-shadow: 0 6px 20px rgba(108, 92, 231, 0.07);
            border: 1px solid {BORDER};
        }}

        div[data-testid="stExpander"] {{
            border-radius: 16px !important;
            border: 1px solid {BORDER} !important;
            background-color: {CARD_BG};
        }}

        hr {{ border-color: {BORDER}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


PLOTLY_TEMPLATE = dict(
    layout=dict(
        font=dict(family="Inter, Segoe UI, sans-serif", color=TEXT_DARK, size=13),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=[PRIMARY, "#A29BFE", ORANGE, RED, GREEN, BLUE],
        margin=dict(t=36, l=10, r=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11)),
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
    )
)


def style_axes(fig):
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False)
    fig.update_yaxes(showgrid=True, gridcolor=BORDER, zeroline=False, showline=False)
    return fig


# ---------------------------------------------------------------------------
# UI COMPONENTS
# ---------------------------------------------------------------------------
def render_top_header(title, subtitle, icon="", date_range=None, filter_label=None):
    right = ""
    if date_range:
        right += f'<div class="chip">&nbsp; {date_range}</div>'
    if filter_label:
        right += f'<div class="chip">▽&nbsp; {filter_label}</div>'
    st.markdown(
        f"""
        <div class="top-header">
            <div class="top-header-left">
                <div class="top-header-icon">{icon}</div>
                <div>
                    <div class="top-header-title">{title}</div>
                    <div class="top-header-subtitle">{subtitle}</div>
                </div>
            </div>
            <div class="top-header-right">{right}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def card_header(title, subtitle=None, icon="", bg=PRIMARY_SOFT, fg=PRIMARY):
    st.markdown(
        f"""
        <div class="card-header">
            <div class="card-icon" style="background-color:{bg};color:{fg};">{icon}</div>
            <div>
                <div class="card-title">{title}</div>
                {f'<div class="card-subtitle">{subtitle}</div>' if subtitle else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_box(text, icon=""):
    st.markdown(
        f"""
        <div class="insight-card">
            <div class="insight-card-icon">{icon}</div>
            <div class="insight-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(label, value, icon="", bg=PRIMARY_SOFT, fg=PRIMARY, sub=None):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-top">
                <div class="kpi-label">{label}</div>
                <div class="kpi-icon" style="background-color:{bg};color:{fg};">{icon}</div>
            </div>
            <div class="kpi-value">{value}</div>
            {f'<div class="kpi-sub">{sub}</div>' if sub else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def trend_html(delta_pct, bad_when_up=True):
    """Render a small colored trend arrow like '↑ +8% vs Last Month'."""
    if delta_pct is None or (isinstance(delta_pct, float) and np.isnan(delta_pct)):
        return '<span class="trend-muted">No prior period</span>'
    up = delta_pct >= 0
    arrow = "↑" if up else "↓"
    is_bad = up if bad_when_up else (not up)
    cls = "trend-up-bad" if is_bad else "trend-up-good"
    return f'<span class="{cls}">{arrow} {delta_pct:+.0%}</span> <span class="trend-muted">vs Last Month</span>'


def risk_badge(level):
    cls = {"High": "badge-high", "Medium": "badge-med", "Low": "badge-low"}.get(level, "badge-med")
    return f'<span class="badge {cls}">{level} Risk</span>'


def sparkline(x, y, color=PRIMARY, fill=True, height=90):
    import plotly.graph_objects as go
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers",
        line=dict(color=color, width=2.5, shape="spline"),
        marker=dict(size=5, color=color),
        fill="tozeroy" if fill else None,
        fillcolor=color.replace(")", ", 0.12)").replace("rgb", "rgba") if color.startswith("rgb") else None,
    ))
    fig.update_layout(
        height=height, margin=dict(t=4, l=0, r=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, showticklabels=True, tickfont=dict(size=9, color=TEXT_FAINT), showline=False),
        yaxis=dict(showgrid=False, showticklabels=False, showline=False),
    )
    return fig


def hero_risk_card(icon, icon_bg, icon_fg, title, description, risk_level, stat_value, stat_label,
                    trend_delta, impact, recommendation, affected, trend_x=None, trend_y=None,
                    page_link=None, link_label="View Details"):
    """Renders a card matching the reference 'AI Insights' risk-card design."""
    risk_bg, risk_fg = RISK_STYLES.get(risk_level, RISK_STYLES["Medium"])
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="hero-card-header">
                <div class="hero-icon" style="background-color:{icon_bg};color:{icon_fg};">{icon}</div>
                <div class="hero-trend">{trend_html(trend_delta)}</div>
            </div>
            <div class="hero-title">{title}</div>
            <div class="hero-desc">{description}</div>
            """,
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([2, 1])
        with c1:
            if trend_x is not None and trend_y is not None and len(trend_x) > 1:
                fig = sparkline(trend_x, trend_y, color=risk_fg)
                st.plotly_chart(fig, width='stretch', config={"displayModeBar": False}, key=f"spark_{title}")
            else:
                st.markdown("<div style='height:70px;'></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(
                f"""
                <div class="hero-stat-box" style="background-color:{risk_bg};">
                    <div class="hero-stat-value" style="color:{risk_fg};">{stat_value}</div>
                    <div style="margin-top:4px;">{risk_badge(risk_level)}</div>
                    <div style="font-size:0.68rem;color:{TEXT_MUTED};margin-top:6px;">{stat_label}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="hero-footer">
                <div class="hero-footer-item">
                    <div class="hero-footer-icon"></div>
                    <div><div class="hero-footer-label">Impact</div><div class="hero-footer-value">{impact}</div></div>
                </div>
                <div class="hero-footer-item">
                    <div class="hero-footer-icon"></div>
                    <div><div class="hero-footer-label">Recommendation</div><div class="hero-footer-value">{recommendation}</div></div>
                </div>
                <div class="hero-footer-item">
                    <div class="hero-footer-icon"></div>
                    <div><div class="hero-footer-label">Affected</div><div class="hero-footer-value">{affected}</div></div>
                </div>
            </div>
            <div class="hero-meta"><div class="hero-updated"> Updated: Today</div></div>
            """,
            unsafe_allow_html=True,
        )
        if page_link:
            try:
                st.page_link(page_link, label=f"{link_label}  →")
            except Exception:
                st.markdown(
                    f'<div style="text-align:right;"><span style="color:{PRIMARY};font-weight:700;font-size:0.85rem;">{link_label} →</span></div>',
                    unsafe_allow_html=True,
                )


def download_csv_button(df, label, filename):
    st.download_button(label, df.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv")


# ---------------------------------------------------------------------------
# DATA: haversine + feature engineering
# ---------------------------------------------------------------------------
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def process_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for col in ["VisitLatitude", "VisitLongitude", "StoreLatitude", "StoreLongitude", "CallDur", "TotalCalls"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if {"VisitLatitude", "VisitLongitude", "StoreLatitude", "StoreLongitude"}.issubset(df.columns):
        df["gps_offset_m"] = haversine_m(
            df["VisitLatitude"], df["VisitLongitude"], df["StoreLatitude"], df["StoreLongitude"]
        )
    else:
        df["gps_offset_m"] = np.nan

    if "Date" in df.columns:
        df["Date_parsed"] = pd.to_datetime(df["Date"], errors="coerce")
        if df["Date_parsed"].isna().mean() > 0.3:
            df["Date_parsed"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    else:
        df["Date_parsed"] = pd.NaT

    def _combine(datecol, timecol):
        if timecol not in df.columns:
            return pd.Series(pd.NaT, index=df.index)
        t = pd.to_datetime(df[timecol].astype(str), errors="coerce", format="mixed")
        return pd.to_datetime(
            df["Date_parsed"].dt.strftime("%Y-%m-%d").fillna("") + " " + t.dt.strftime("%H:%M:%S").fillna("00:00:00"),
            errors="coerce",
        )

    df["visit_start_dt"] = _combine("Date", "TimeIn")
    df["visit_end_dt"] = _combine("Date", "TimeOut")

    if df["Date_parsed"].notna().any():
        df["Month"] = df["Date_parsed"].dt.strftime("%Y-%m")
    elif "Month" not in df.columns:
        df["Month"] = np.nan

    # ---- VisitStatus code parsing (E/S/N/X) ----------------------------------
    # E = Extra successful (unplanned), S = Successful (planned),
    # N = Unsuccessful (planned), X = Extra unsuccessful (unplanned)
    #
    # Real-world values may appear as a bare letter ("E"), a letter with a
    # description ("E - Extra successful call (unplanned)"), or just the
    # description with no leading letter at all. We try three progressively
    # looser passes so we don't silently mis-classify real data:
    if "VisitStatus" in df.columns:
        raw = df["VisitStatus"].astype(str).str.strip()
        upper = raw.str.upper()

        # Pass 1: the whole cell is exactly one of E/S/N/X
        code = upper.where(upper.isin(["E", "S", "N", "X"]))

        # Pass 2: cell starts with the code letter followed by a separator
        # (e.g. "E - Extra successful call (unplanned)", "E: ...", "E_...")
        leading = upper.str.extract(r"^([ESNX])(?:[\s\-_:).]|$)")[0]
        code = code.fillna(leading)

        # Pass 3: no leading letter — classify from the description keywords
        still_missing = code.isna() & raw.ne("") & raw.str.lower().ne("nan")
        if still_missing.any():
            lower_desc = raw.str.lower()
            is_extra = lower_desc.str.contains("extra|unplanned", regex=True, na=False)
            is_unsuccessful = lower_desc.str.contains("unsuccessful|fail|declined|no sale", regex=True, na=False)
            kw_code = np.select(
                [is_extra & is_unsuccessful, is_extra & ~is_unsuccessful,
                 ~is_extra & is_unsuccessful, ~is_extra & ~is_unsuccessful],
                ["X", "E", "N", "S"], default=None,
            )
            code = code.mask(still_missing, pd.Series(kw_code, index=df.index).where(still_missing))

        is_coded = code.notna()

        if is_coded.mean() > 0.5:
            code = code.fillna("S")  # residual unmapped rows default to the most common/neutral case
            df["VisitStatusCode"] = code
            df["VisitStatusLabel"] = code.map(VISIT_STATUS_MAP).fillna(df["VisitStatus"])
            df["is_planned_visit"] = code.isin(["S", "N"]).astype(int)
            df["is_extra_visit"] = code.isin(["E", "X"]).astype(int)
            df["is_successful_status"] = code.isin(["E", "S"]).astype(int)
            # VisitStatus is the ground truth when coded — reconcile the outcome flag to match
            df["non_successful_visit"] = (1 - df["is_successful_status"]).astype(int)
        else:
            unsuccessful_text = raw.str.contains("unsuccessful|fail", case=False, na=False)
            df["VisitStatusCode"] = np.where(unsuccessful_text, "N", "S")
            df["VisitStatusLabel"] = df["VisitStatus"]
            df["is_planned_visit"] = 1
            df["is_extra_visit"] = 0
            if "non_successful_visit" not in df.columns:
                df["non_successful_visit"] = unsuccessful_text.astype(int)
            df["is_successful_status"] = (df["non_successful_visit"] == 0).astype(int)
    else:
        df["VisitStatusCode"] = "S"
        df["VisitStatusLabel"] = "Unknown"
        df["is_planned_visit"] = 1
        df["is_extra_visit"] = 0
        df["is_successful_status"] = (df.get("non_successful_visit", 0) == 0).astype(int)

    for c in FLAG_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
        else:
            df[c] = 0

    sort_cols = [c for c in ["SRCode", "visit_start_dt"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    if "SRCode" in df.columns:
        df["visit_seq"] = df.groupby("SRCode").cumcount() + 1

    return df


def sample_dataframe(n_reps=25, months=6, seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    roles_sup = [f"Senior Supervisor {i}" for i in range(1, 5)]
    distributors = [f"Distributor {c}" for c in "ABCDEFGH"]
    stores = [f"Store {i:03d}" for i in range(1, 61)]
    base_date = datetime(2025, 1, 1)

    rows = []
    for r in range(n_reps):
        sr_code = f"SR{1000+r}"
        persona_bias = rng.choice(["clean", "rushed", "offroute", "delayed", "mixed"], p=[0.25, 0.25, 0.2, 0.15, 0.15])
        dist = rng.choice(distributors)
        sup = rng.choice(roles_sup)
        n_visits = months * rng.integers(18, 30)
        total_days = months * 30
        base_offsets = np.linspace(0, total_days - 1, n_visits) if n_visits > 1 else np.array([0])
        jitter = rng.integers(-1, 2, size=n_visits)
        offsets = np.clip(base_offsets + jitter, 0, total_days - 1).astype(int)
        offsets.sort()
        for v in range(n_visits):
            cur_date = base_date + timedelta(days=int(offsets[v]))
            store = rng.choice(stores)
            store_lat, store_lon = 19.07 + rng.normal(0, 0.05), 72.87 + rng.normal(0, 0.05)

            delayed = rng.random() < (0.45 if persona_bias in ("delayed", "mixed") else 0.12)
            rushed = rng.random() < (0.5 if persona_bias in ("rushed", "mixed") else 0.1) or (delayed and rng.random() < 0.3)
            offroute = rng.random() < (0.4 if persona_bias in ("offroute", "mixed") else 0.08)

            offset = abs(rng.normal(400 if offroute else 40, 250 if offroute else 30))
            call_dur = max(1, rng.normal(6 if rushed else 18, 3))
            hour_in = 11 if delayed else rng.integers(8, 10)
            min_in = rng.integers(0, 59)
            time_in = f"{hour_in:02d}:{min_in:02d}:00"
            time_out_dt = cur_date.replace(hour=hour_in, minute=min_in) + timedelta(minutes=call_dur)
            time_out = time_out_dt.strftime("%H:%M:%S")

            fail_prob = 0.05 + 0.35 * rushed + 0.3 * offroute + 0.15 * delayed + (0.2 if call_dur < 5 else 0)
            failed = rng.random() < min(fail_prob, 0.9)
            non_instore = 1 if offset > 300 and rng.random() < 0.6 else 0
            is_extra = rng.random() < 0.15  # ~15% of visits are unplanned/extra calls
            if failed:
                visit_status = "X" if is_extra else "N"
            else:
                visit_status = "E" if is_extra else "S"

            rows.append(dict(
                **{"Role_Assistant Sales Manager": "Yes" if rng.random() < 0.2 else "No"},
                **{"Role_Senior Supervisor": sup},
                **{"Role_Supervisor": f"Supervisor {rng.integers(1, 12)}"},
                DistributorCode=f"D{distributors.index(dist)+1:03d}",
                DistributorName=dist,
                SRCode=sr_code,
                Date=cur_date.strftime("%Y-%m-%d"),
                TimeIn=time_in,
                TimeOut=time_out,
                CallDur=round(call_dur, 1),
                StoreIDREF=stores.index(store) + 1,
                StoreID=stores.index(store) + 1,
                StoreName=store,
                VisitStatus=visit_status,
                TotalCalls=rng.integers(1, 4),
                VisitLatitude=store_lat + rng.normal(0, offset / 111000),
                VisitLongitude=store_lon + rng.normal(0, offset / 111000),
                StoreLatitude=store_lat,
                StoreLongitude=store_lon,
                STOREGPSUPDATED="Yes",
                Month=cur_date.strftime("%Y-%m"),
                non_successful_visit=int(failed),
                non_instore_visit=int(non_instore),
                rushed_visit=int(rushed),
                off_route_visit_store=int(offroute),
                delayed_start=int(delayed),
            ))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# FILTERS
# ---------------------------------------------------------------------------
def sidebar_filters(df: pd.DataFrame, key_prefix="global"):
    st.sidebar.markdown("###  Drill-Down Filters")

    months = sorted(df["Month"].dropna().unique().tolist()) if "Month" in df.columns else []
    sel_months = st.sidebar.multiselect("Month", months, default=months, key=f"{key_prefix}_month")

    sup_col = "Role_Senior Supervisor" if "Role_Senior Supervisor" in df.columns else None
    sel_sup = []
    if sup_col:
        sups = sorted(df[sup_col].dropna().unique().tolist())
        sel_sup = st.sidebar.multiselect("Senior Supervisor", sups, default=sups, key=f"{key_prefix}_sup")

    dists = sorted(df["DistributorName"].dropna().unique().tolist()) if "DistributorName" in df.columns else []
    sel_dist = st.sidebar.multiselect("Distributor", dists, default=dists, key=f"{key_prefix}_dist")

    sr_codes = sorted(df["SRCode"].dropna().unique().tolist()) if "SRCode" in df.columns else []
    sel_sr = st.sidebar.multiselect("SR Code (optional)", sr_codes, default=[], key=f"{key_prefix}_sr")

    stores = sorted(df["StoreName"].dropna().unique().tolist()) if "StoreName" in df.columns else []
    sel_store = st.sidebar.multiselect("Store (optional)", stores, default=[], key=f"{key_prefix}_store")

    return dict(months=sel_months, sup=sel_sup, dist=sel_dist, sr=sel_sr, store=sel_store, sup_col=sup_col)


def apply_filters(df: pd.DataFrame, filters: dict) -> pd.DataFrame:
    out = df.copy()
    if filters.get("months"):
        out = out[out["Month"].isin(filters["months"])]
    if filters.get("sup_col") and filters.get("sup"):
        out = out[out[filters["sup_col"]].isin(filters["sup"])]
    if filters.get("dist"):
        out = out[out["DistributorName"].isin(filters["dist"])]
    if filters.get("sr"):
        out = out[out["SRCode"].isin(filters["sr"])]
    if filters.get("store"):
        out = out[out["StoreName"].isin(filters["store"])]
    return out


def date_range_label(df: pd.DataFrame) -> str:
    if "Date_parsed" in df.columns and df["Date_parsed"].notna().any():
        lo, hi = df["Date_parsed"].min(), df["Date_parsed"].max()
        return f"{lo.strftime('%d %b %Y')} – {hi.strftime('%d %b %Y')}"
    return "All Dates"


def require_data():
    if "df" not in st.session_state or st.session_state["df"] is None:
        st.warning(" No dataset loaded yet. Please go to the **Data Setup** page to upload a CSV or load sample data.")
        st.stop()
    return st.session_state["df"]


# ---------------------------------------------------------------------------
# DATA-DRIVEN RISK & RECOMMENDATION ENGINE
# ---------------------------------------------------------------------------
# Every function below derives its cutoffs from the shape of the current
# dataset itself (z-scores, quantiles, ranks) rather than fixed business
# constants — so results automatically recalibrate as the data/filters change.

def zscore_outliers(rate: pd.Series, z_thresh: float = 1.0):
    """
    Flag entries statistically elevated relative to their own peer group:
    more than `z_thresh` standard deviations above the group's mean.
    Falls back to 'above the median' if the group has zero variance.
    Returns (mask: bool Series, mu: float, sigma: float).
    """
    mu = rate.mean()
    sigma = rate.std(ddof=0)
    if sigma == 0 or pd.isna(sigma):
        mask = rate > rate.median()
    else:
        mask = (rate - mu) / sigma > z_thresh
    return mask, mu, sigma


def factor_risk_profile(fdf: pd.DataFrame, flag_col: str, outcome_col: str = "non_successful_visit"):
    """
    Build a full, purely data-derived risk profile for one behaviour flag:
      - per-rep incidence rate
      - statistically elevated ("affected") reps -> z-score > 1 vs team mean
      - business impact -> lift in outcome failure rate when flag is present vs absent
      - composite risk score -> (% of team affected) x (impact lift)
      - month-over-month trend of the team-wide incidence rate
    No fixed percentage cutoffs are used anywhere in this function.
    """
    sr_rate = fdf.groupby("SRCode")[flag_col].mean().sort_values(ascending=False)
    total_reps = sr_rate.shape[0]

    mask, mu, sigma = zscore_outliers(sr_rate)
    affected_reps = sr_rate[mask]
    affected_count = int(mask.sum())
    pct_affected = affected_count / total_reps if total_reps else 0.0

    if (fdf[flag_col] == 1).any() and (fdf[flag_col] == 0).any():
        impact_lift = fdf.loc[fdf[flag_col] == 1, outcome_col].mean() - fdf.loc[fdf[flag_col] == 0, outcome_col].mean()
    else:
        impact_lift = 0.0

    composite_score = pct_affected * max(impact_lift, 0)

    monthly = fdf.groupby("Month")[flag_col].mean().reset_index().sort_values("Month")
    monthly_recent = monthly.tail(6)
    delta_pct = None
    if len(monthly_recent) >= 2:
        prev, cur = monthly_recent[flag_col].iloc[-2], monthly_recent[flag_col].iloc[-1]
        if prev > 0:
            delta_pct = (cur - prev) / prev

    return dict(
        sr_rate=sr_rate, total_reps=total_reps, mu=mu, sigma=sigma,
        affected_reps=affected_reps, affected_count=affected_count, pct_affected=pct_affected,
        impact_lift=impact_lift, composite_score=composite_score,
        monthly=monthly_recent, delta_pct=delta_pct,
    )


def assign_risk_tiers(score_map: dict):
    """
    Rank-based High/Medium/Low tiering: the metric(s) with the highest composite
    score are 'High', lowest are 'Low', the remainder 'Medium'. Because this is a
    relative ranking (not an absolute cutoff), it self-calibrates to whatever the
    current filtered dataset contains.
    """
    n = len(score_map)
    ordered = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)
    edge = max(1, round(n / 3))
    tiers = {}
    for i, (k, _) in enumerate(ordered):
        if i < edge:
            tiers[k] = "High"
        elif i >= n - edge:
            tiers[k] = "Low"
        else:
            tiers[k] = "Medium"
    return tiers


def quantile_bins(series: pd.Series, q: int = 5):
    """
    Data-driven binning: splits a numeric series into quantile-based buckets
    (equal population, not equal width), with human-readable range labels.
    Replaces fixed/hardcoded bin edges.
    """
    clean = series.dropna()
    try:
        binned, edges = pd.qcut(clean, q=q, retbins=True, duplicates="drop")
    except ValueError:
        binned, edges = pd.cut(clean, bins=min(q, clean.nunique()), retbins=True)
    labels = [f"{edges[i]:.0f}–{edges[i+1]:.0f}" for i in range(len(edges) - 1)]
    cat = pd.cut(series, bins=edges, labels=labels, include_lowest=True)
    return cat


def rank_table(df: pd.DataFrame, sort_col: str, n: int = 5, ascending: bool = False) -> pd.DataFrame:
    return df.sort_values(sort_col, ascending=ascending).head(n)


# ---------------------------------------------------------------------------
# RECOMMENDATION UI COMPONENTS
# ---------------------------------------------------------------------------
def recommendations_header():
    st.markdown("<br>", unsafe_allow_html=True)
    card_header("Recommended Actions", "Data-driven next steps generated from the current filtered view.",
                icon="", bg=GREEN_SOFT, fg=GREEN)


def action_card(text, priority="Medium", icon=""):
    bg, fg = RISK_STYLES.get(priority, RISK_STYLES["Medium"])
    st.markdown(
        f"""
        <div class="insight-card" style="background:linear-gradient(135deg,{bg} 0%, #FFFFFF 100%); border-color:{fg}22;">
            <div class="insight-card-icon" style="background-color:{fg};">{icon}</div>
            <div class="insight-text">
                <span class="badge" style="background-color:{fg}20;color:{fg};margin-right:8px;">{priority} Priority</span>
                {text}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ENTERPRISE RISK SCORE ENGINE
# Risk Score = 0.30*BF + 0.20*SA + 0.15*P + 0.20*RI + 0.15*BIS
# ---------------------------------------------------------------------------
from scipy.stats import chi2_contingency
from itertools import combinations

BEHAVIOR_FLAGS = ["non_instore_visit", "rushed_visit", "delayed_start", "off_route_visit_store"]
BEHAVIOR_LABELS = {c: READABLE.get(c, c) for c in BEHAVIOR_FLAGS}

RISK_WEIGHTS = dict(BF=0.30, SA=0.20, P=0.15, RI=0.20, BIS=0.15)

RISK_BANDS = [(0, 20, "Very Low"), (20, 40, "Low"), (40, 60, "Medium"), (60, 80, "High"), (80, 100.001, "Critical")]


def classify_risk(score: float) -> str:
    for lo, hi, label in RISK_BANDS:
        if lo <= score < hi:
            return label
    return "Critical"


def behaviour_frequency(fdf: pd.DataFrame, flag_cols=BEHAVIOR_FLAGS) -> pd.DataFrame:
    """BF = Behaviour Count / Total Visits x 100, per rep, per behaviour."""
    bf = fdf.groupby("SRCode")[flag_cols].mean() * 100
    bf["BF"] = bf[flag_cols].mean(axis=1)
    return bf


def cramers_v(table: pd.DataFrame):
    """Chi-Square + Cramér's V for a 2x2 contingency table. Returns (v, chi2, p)."""
    if table.shape[0] < 2 or table.shape[1] < 2:
        return 0.0, 0.0, 1.0
    chi2, p, dof, expected = chi2_contingency(table, correction=False)
    n = table.values.sum()
    if n == 0:
        return 0.0, 0.0, 1.0
    r, k = table.shape
    v = np.sqrt((chi2 / n) / min(k - 1, r - 1))
    return float(v), float(chi2), float(p)


def statistical_association(fdf: pd.DataFrame, flag_cols=BEHAVIOR_FLAGS, outcome_col="non_successful_visit") -> pd.DataFrame:
    """
    Population-level Chi-Square + Cramér's V between each behaviour flag and the
    failed-visit outcome. Cramér's V (0-1) is scaled to a 0-100 SA score.
    """
    rows = []
    for col in flag_cols:
        table = pd.crosstab(fdf[col], fdf[outcome_col])
        v, chi2, p = cramers_v(table)
        rows.append(dict(Behaviour=col, CramersV=v, Chi2=chi2, PValue=p, SA_Score=v * 100))
    return pd.DataFrame(rows).set_index("Behaviour")


def behaviour_persistence(fdf: pd.DataFrame, flag_cols=BEHAVIOR_FLAGS, windows=(30, 60, 90)) -> pd.Series:
    """
    P = (Days Behaviour Occurred / Observation Window) x 100, averaged across
    rolling 30/60/90-day windows ending on the last observed date in the data,
    then averaged across all tracked behaviours.
    """
    if "Date_parsed" not in fdf.columns or fdf["Date_parsed"].isna().all():
        return pd.Series(0.0, index=fdf["SRCode"].unique())

    ref_date = fdf["Date_parsed"].max()
    scores = {}
    for rep, rep_df in fdf.groupby("SRCode"):
        window_scores = []
        for w in windows:
            window_start = ref_date - pd.Timedelta(days=w - 1)
            wdf = rep_df[rep_df["Date_parsed"] >= window_start]
            if wdf.empty:
                continue
            per_behavior = []
            for col in flag_cols:
                days_occurred = wdf.loc[wdf[col] == 1, "Date_parsed"].dt.normalize().nunique()
                per_behavior.append(min(days_occurred / w * 100, 100))
            window_scores.append(np.mean(per_behavior))
        scores[rep] = np.mean(window_scores) if window_scores else 0.0
    return pd.Series(scores)


def opportunity_impact(fdf: pd.DataFrame, value_per_planned_visit: float = None, outcome_col="non_successful_visit"):
    """
    RI — Revenue/Opportunity Impact, derived from VisitStatus (E/S/N/X) rather
    than an assumed dollar figure:

      N = Unsuccessful Call (Planned)   -> a *committed* visit slot was lost
      X = Extra Unsuccessful (Unplanned) -> a *bonus* attempt was wasted

    A planned call represents a scheduled, expected customer touchpoint, so a
    planned failure (N) is treated as a costlier loss than an unplanned/extra
    failure (X). The relative weight between the two is not an arbitrary
    business guess — it's the dataset's own mix of planned vs. extra visits
    (`w_planned` = share of all visits that are planned). If a dataset has no
    VisitStatus codes at all, every visit defaults to "planned" and this
    collapses to a simple failed-visit count.

    Returns:
      raw_index   — unitless weighted opportunity-loss index per rep
      norm        — raw_index min-max scaled to 0-100 across reps in view
      dollar_est  — optional $ estimate (raw_index x value_per_planned_visit)
                    if the user supplied a conversion value, else None
      meta        — dict of the weights/columns used, for transparency
    """
    has_status = "is_planned_visit" in fdf.columns and "is_extra_visit" in fdf.columns
    if not has_status:
        fdf = fdf.copy()
        fdf["is_planned_visit"] = 1
        fdf["is_extra_visit"] = 0

    w_planned = fdf["is_planned_visit"].mean()
    w_extra = 1 - w_planned
    if w_planned == 0 and w_extra == 0:
        w_planned, w_extra = 1.0, 0.0

    planned_fail = ((fdf["is_planned_visit"] == 1) & (fdf[outcome_col] == 1)).groupby(fdf["SRCode"]).sum()
    extra_fail = ((fdf["is_extra_visit"] == 1) & (fdf[outcome_col] == 1)).groupby(fdf["SRCode"]).sum()

    all_reps = fdf["SRCode"].unique()
    planned_fail = planned_fail.reindex(all_reps, fill_value=0)
    extra_fail = extra_fail.reindex(all_reps, fill_value=0)

    raw_index = planned_fail * w_planned + extra_fail * w_extra

    lo, hi = raw_index.min(), raw_index.max()
    norm = (raw_index - lo) / (hi - lo) * 100 if hi > lo else raw_index * 0

    dollar_est = raw_index * value_per_planned_visit if value_per_planned_visit else None

    meta = dict(w_planned=w_planned, w_extra=w_extra, planned_fail=planned_fail, extra_fail=extra_fail,
                has_status_codes=has_status)
    return raw_index, norm, dollar_est, meta


def behaviour_interaction_score(fdf: pd.DataFrame, flag_cols=BEHAVIOR_FLAGS, min_support: int = 2):
    """
    BIS: pairwise Lift = P(A&B) / (P(A) x P(B)).

    Two views are computed:
      - pair_lift_pop: population-level lift per pair (for reporting "which
        combination is strongest across the whole team").
      - bis_series: each rep's OWN strongest pairwise lift, computed from that
        rep's individual visit history (not just whether they ever exhibited
        both behaviours once) so reps are actually differentiated. Pairs with
        fewer than `min_support` occurrences of either behaviour for that rep
        are skipped to avoid unstable ratios from tiny sample sizes.

    The population's own maximum per-rep lift is normalised to 100, and every
    rep's score is scaled proportionally to it (data-driven, no fixed lift cap).
    """
    pair_lift_pop = {}
    for a, b in combinations(flag_cols, 2):
        pa, pb = fdf[a].mean(), fdf[b].mean()
        pab = ((fdf[a] == 1) & (fdf[b] == 1)).mean()
        if pa > 0 and pb > 0:
            pair_lift_pop[(a, b)] = pab / (pa * pb)

    rep_best_lift = {}
    for rep, rdf in fdf.groupby("SRCode"):
        best = 0.0
        for a, b in combinations(flag_cols, 2):
            count_a, count_b = int(rdf[a].sum()), int(rdf[b].sum())
            if count_a < min_support or count_b < min_support:
                continue
            pa, pb = rdf[a].mean(), rdf[b].mean()
            pab = ((rdf[a] == 1) & (rdf[b] == 1)).mean()
            lift = pab / (pa * pb) if pa > 0 and pb > 0 else 0.0
            best = max(best, lift)
        rep_best_lift[rep] = best

    rep_lift_series = pd.Series(rep_best_lift)
    max_lift = rep_lift_series.max()
    bis_series = (rep_lift_series / max_lift * 100) if max_lift > 0 else rep_lift_series * 0

    return pair_lift_pop, bis_series


def compute_enterprise_risk(fdf: pd.DataFrame, value_per_planned_visit: float = None,
                             flag_cols=BEHAVIOR_FLAGS, outcome_col="non_successful_visit"):
    """
    Assembles the full Enterprise Risk Score pipeline and returns a per-rep
    DataFrame with every component, the composite score, risk category, and
    the fields needed for the AI Output (primary reason, secondary behaviours,
    confidence, opportunity impact, coaching recommendation).
    """
    bf_df = behaviour_frequency(fdf, flag_cols)
    sa_df = statistical_association(fdf, flag_cols, outcome_col)
    p_series = behaviour_persistence(fdf, flag_cols)
    raw_ri, ri_norm, dollar_est, ri_meta = opportunity_impact(fdf, value_per_planned_visit, outcome_col)
    pair_lift, bis_series = behaviour_interaction_score(fdf, flag_cols)

    reps = bf_df.index
    sa_rep = {}
    primary_reason = {}
    secondary = {}
    confidence = {}
    primary_rate = {}
    primary_diff = {}
    confirmed = {}
    for rep in reps:
        weights = bf_df.loc[rep, flag_cols] / 100
        wsum = weights.sum()
        sa_rep[rep] = float((weights * sa_df["SA_Score"]).sum() / wsum) if wsum > 0 else 0.0

        # Primary Failure Reason: a behaviour only qualifies if it's genuinely
        # MORE common on this rep's failed visits than on their own successful
        # visits (diff > 0) — a behaviour that's just as common (or more common)
        # when the rep succeeds is not a failure driver, no matter how often it
        # shows up in raw failed-visit counts. Among qualifying behaviours, rank
        # by this rep's own Chi-Square/Cramér's V (computed from their full
        # success+failure history), not by raw counts.
        rep_df = fdf[fdf["SRCode"] == rep]
        rep_failed = rep_df[rep_df[outcome_col] == 1]
        rep_success = rep_df[rep_df[outcome_col] == 0]

        rate_failed = rep_failed[flag_cols].mean() if len(rep_failed) > 0 else pd.Series(0.0, index=flag_cols)
        rate_success = rep_success[flag_cols].mean() if len(rep_success) > 0 else pd.Series(0.0, index=flag_cols)
        diff = rate_failed - rate_success

        rep_v = {}
        for col in flag_cols:
            table = pd.crosstab(rep_df[col], rep_df[outcome_col])
            v, _, _ = cramers_v(table)
            rep_v[col] = v
        rep_v = pd.Series(rep_v)

        qualifying = diff[diff > 0]
        if len(qualifying) > 0:
            ranked = rep_v.loc[qualifying.index].sort_values(ascending=False)
            primary_reason[rep] = ranked.index[0]
            secondary[rep] = [c for c in ranked.index[1:]]
            confidence[rep] = float(sa_df.loc[ranked.index[0], "SA_Score"])
            primary_rate[rep] = float(rate_failed[ranked.index[0]])
            primary_diff[rep] = float(diff[ranked.index[0]])
            confirmed[rep] = True
        elif diff.abs().sum() > 0 or rate_failed.sum() > 0:
            # No behaviour is genuinely MORE common in failure than success for this rep —
            # so there's no confirmed single cause. Rather than a dead-end "None Identified",
            # surface the behaviour closest to being a driver (least-negative / most frequent
            # in failures) as a tentative note, clearly flagged as unconfirmed.
            ranked = diff.sort_values(ascending=False)
            primary_reason[rep] = ranked.index[0]
            secondary[rep] = [c for c in ranked.index[1:]]
            confidence[rep] = float(sa_df.loc[ranked.index[0], "SA_Score"])
            primary_rate[rep] = float(rate_failed[ranked.index[0]])
            primary_diff[rep] = float(diff[ranked.index[0]])
            confirmed[rep] = False
        else:
            primary_reason[rep] = None
            secondary[rep] = []
            confidence[rep] = 0.0
            primary_rate[rep] = 0.0
            primary_diff[rep] = 0.0
            confirmed[rep] = False

    out = pd.DataFrame(index=reps)
    out["BF"] = bf_df["BF"]
    out["SA"] = pd.Series(sa_rep)
    out["P"] = p_series.reindex(reps).fillna(0.0)
    out["RI_raw"] = raw_ri.reindex(reps).fillna(0.0)
    out["RI"] = ri_norm.reindex(reps).fillna(0.0)
    out["RI_dollar"] = dollar_est.reindex(reps).fillna(0.0) if dollar_est is not None else None
    out["BIS"] = bis_series.reindex(reps).fillna(0.0)

    out["RiskScore"] = (
        RISK_WEIGHTS["BF"] * out["BF"] + RISK_WEIGHTS["SA"] * out["SA"] + RISK_WEIGHTS["P"] * out["P"]
        + RISK_WEIGHTS["RI"] * out["RI"] + RISK_WEIGHTS["BIS"] * out["BIS"]
    ).round(1)
    out["RiskCategory"] = out["RiskScore"].apply(classify_risk)
    out["PrimaryFailureReason"] = pd.Series(primary_reason).map(lambda c: BEHAVIOR_LABELS.get(c, "None Identified"))
    out["PrimaryReasonRate"] = pd.Series(primary_rate).round(3)
    out["PrimaryReasonDiff"] = pd.Series(primary_diff).round(3)
    out["PrimaryReasonConfirmed"] = pd.Series(confirmed)
    out["RI_Percentile"] = out["RI_raw"].rank(pct=True).round(2)
    out["SecondaryBehaviours"] = pd.Series(secondary).map(lambda cs: ", ".join(BEHAVIOR_LABELS.get(c, c) for c in cs) if cs else "None")
    out["ConfidenceScore"] = pd.Series(confidence).round(1)

    meta = dict(sa_df=sa_df, pair_lift=pair_lift, ri_meta=ri_meta, has_dollar_est=dollar_est is not None)
    return out.reset_index().rename(columns={"index": "SRCode"}), meta


# ---------------------------------------------------------------------------
# BUSINESS-FRIENDLY UI COMPONENTS (KPI + download, graph explainer)
# ---------------------------------------------------------------------------
def kpi_with_download(count, noun, description, entity_df, filename, color=PRIMARY):
    """
    Renders a plain-English sentence naming an entity count (e.g. '23 reps have
    high rushed-visit rates') with a download button beside it, so the person
    can act on the insight immediately instead of hunting for the list
    elsewhere. Use anywhere the dashboard says 'X reps/stores are ...'.

    count: number of entities (int)
    noun: singular noun, e.g. "rep" or "store" — pluralized automatically
    description: rest of the sentence after the bolded count, e.g.
                 "are in the highest-risk persona (Rushed Operators)"
    """
    plural_noun = noun if count == 1 else f"{noun}s"
    sentence_html = f"<b>{count} {plural_noun}</b> {description}"
    c1, c2 = st.columns([5, 2])
    with c1:
        st.markdown(
            f'<div style="padding:8px 0;font-size:0.92rem;line-height:1.4;">{sentence_html}</div>',
            unsafe_allow_html=True,
        )
    with c2:
        if entity_df is not None and len(entity_df) > 0:
            st.download_button("Download", entity_df.to_csv(index=False).encode("utf-8"),
                                file_name=filename, mime="text/csv",
                                key=f"dl_{filename}_{id(entity_df)}", width='stretch')


def graph_explainer(title, what_it_shows, takeaway, icon=""):
    """
    Standard header block for every graph: a plain title, one sentence on what
    it shows, and a plain-English takeaway — so a non-technical reader never
    has to interpret a chart cold.
    """
    st.markdown(
        f"""
        <div style="margin:4px 4px 10px 4px;">
            <div style="font-size:1.02rem;font-weight:700;color:{TEXT_DARK};">{icon} {title}</div>
            <div style="font-size:0.85rem;color:{TEXT_MUTED};margin-top:2px;">{what_it_shows}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def plain_takeaway(text, icon=""):
    """A lighter-weight version of insight_box, styled the same, used directly under a graph as its 'so what'."""
    insight_box(text, icon=icon)


# ---------------------------------------------------------------------------
# PLAN COMPLIANCE
# ---------------------------------------------------------------------------
def compute_plan_compliance(fdf: pd.DataFrame) -> pd.DataFrame:
    """
    Plan Compliance answers: "Did the rep actually cover their assigned route,
    not just perform well on the stores they happened to visit?"

    The uploaded dataset has no separate planned-route file, so a rep's
    "Planned Stores" (their territory) is inferred as every store that has
    received a planned visit (VisitStatus S or N) from that rep across the
    CURRENTLY FILTERED view. "Visited Planned Stores" is measured for a
    single, specific evaluation period — the most recent calendar month
    present in that same filtered view — not the whole filtered range.

    This is deliberate: if "visited" used the same date range as "territory,"
    the two would be measuring the same rows and could trivially show 100%
    (e.g. when no month filter narrows anything, "the whole dataset" would be
    compared against itself). Comparing one recent month against the broader
    multi-month territory avoids that structurally, regardless of whether the
    person applied extra filters. Narrow the Month filter to a single earlier
    month to evaluate compliance for that specific period instead.

    If your data has an explicit planned-route file, that would replace this
    inferred-territory approach with an exact one — this is a transparent,
    fully data-driven proxy in the meantime.
    """
    if "StoreID" not in fdf.columns or "SRCode" not in fdf.columns or "Month" not in fdf.columns:
        return pd.DataFrame()
    if fdf["Month"].dropna().empty:
        return pd.DataFrame()

    store_name_map = fdf.drop_duplicates("StoreID").set_index("StoreID")["StoreName"] if "StoreName" in fdf.columns else None

    latest_month = fdf["Month"].max()
    recent_period = fdf[fdf["Month"] == latest_month]

    planned_col = "is_planned_visit" if "is_planned_visit" in fdf.columns else None
    planned_mask = (fdf[planned_col] == 1) if planned_col else pd.Series(True, index=fdf.index)
    territory = fdf[planned_mask].groupby("SRCode")["StoreID"].apply(lambda s: set(s.dropna().unique()))
    visited_period = recent_period.groupby("SRCode")["StoreID"].apply(lambda s: set(s.dropna().unique()))

    reps = sorted(set(territory.index) | set(visited_period.index))
    rows = []
    for rep in reps:
        planned_stores = territory.get(rep, set())
        visited_stores = visited_period.get(rep, set())
        covered = planned_stores & visited_stores
        missed = planned_stores - visited_stores
        planned_n = len(planned_stores)
        pct = (len(covered) / planned_n * 100) if planned_n > 0 else np.nan
        missed_names = [str(store_name_map.get(s, s)) for s in missed] if store_name_map is not None else [str(s) for s in missed]
        rows.append(dict(
            SRCode=rep, EvaluatedMonth=latest_month, PlannedStores=planned_n, VisitedPlannedStores=len(covered),
            MissedPlannedStores=len(missed), PlanCompliancePct=round(pct, 1) if pd.notna(pct) else np.nan,
            MissedStores=", ".join(sorted(missed_names)[:15]) + (" ..." if len(missed_names) > 15 else ""),
        ))
    return pd.DataFrame(rows).sort_values("PlanCompliancePct", na_position="last")


# ---------------------------------------------------------------------------
# STORE-LEVEL RISK
# ---------------------------------------------------------------------------
def compute_store_risk(fdf: pd.DataFrame, outcome_col: str = "non_successful_visit") -> pd.DataFrame:
    """
    Flags stores with a statistically elevated failure rate — the store-level
    counterpart to rep-level risk. Uses the same z-score approach (more than
    1 standard deviation above the average store's failure rate) so a store
    is only flagged when it's a genuine outlier, not just unlucky.
    """
    if "StoreName" not in fdf.columns:
        return pd.DataFrame()

    store_stats = fdf.groupby("StoreName").agg(
        TotalVisits=(outcome_col, "count"),
        FailedVisits=(outcome_col, "sum"),
    )
    store_stats["FailureRate"] = store_stats["FailedVisits"] / store_stats["TotalVisits"]
    mask, mu, sigma = zscore_outliers(store_stats["FailureRate"])
    store_stats["IsHighRisk"] = mask
    store_stats["TeamAvgFailureRate"] = mu
    return store_stats.reset_index().sort_values("FailureRate", ascending=False)
