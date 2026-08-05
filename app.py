import streamlit as st
import pandas as pd
from utils import (
    inject_theme, process_dataframe, sample_dataframe, READABLE, FLAG_COLS,
    render_top_header, card_header, kpi_card, insight_box, date_range_label,
    PRIMARY, PRIMARY_SOFT, GREEN, GREEN_SOFT, ORANGE, ORANGE_SOFT, BLUE, BLUE_SOFT, RED, RED_SOFT,
)

st.set_page_config(page_title="SR Field Insights", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

render_top_header(
    "SR Field Insights",
    "AI-powered visibility into field-visit quality, compliance, and rep behaviour.",
    icon="",
)

with st.container(border=True):
    card_header("Data Setup", "Upload your visit-level CSV, or explore instantly with sample data.", icon="")
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader("Upload CSV dataset", type=["csv"], label_visibility="collapsed")
    with col2:
        load_sample = st.button(" Load Sample Data Instead", width='stretch')

if uploaded is not None:
    try:
        raw_df = pd.read_csv(uploaded)
        processed = process_dataframe(raw_df)
        st.session_state["df"] = processed
        st.session_state["data_source"] = uploaded.name
        st.session_state["raw_visit_status"] = raw_df["VisitStatus"] if "VisitStatus" in raw_df.columns else None
        st.success(f" Loaded and processed **{len(processed):,}** visit records from `{uploaded.name}`.")
    except Exception as e:
        st.error(f"Could not process this file: {e}")

if load_sample:
    sample_raw = sample_dataframe()
    processed = process_dataframe(sample_raw)
    st.session_state["df"] = processed
    st.session_state["data_source"] = "Sample Dataset (synthetic)"
    st.session_state["raw_visit_status"] = sample_raw["VisitStatus"]
    st.success(f" Sample dataset loaded — **{len(processed):,}** synthetic visit records.")

if "df" in st.session_state and st.session_state["df"] is not None:
    df = st.session_state["df"]
    st.markdown(f"<p style='color:#767893;font-size:0.85rem;'>Current data source: <b>{st.session_state.get('data_source','—')}</b></p>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1: kpi_card("Total Visit Records", f"{len(df):,}", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
    with c2: kpi_card("Unique SRs", f"{df['SRCode'].nunique() if 'SRCode' in df else 0:,}", icon="", bg=BLUE_SOFT, fg=BLUE)
    with c3: kpi_card("Unique Stores", f"{df['StoreName'].nunique() if 'StoreName' in df else 0:,}", icon="", bg=ORANGE_SOFT, fg=ORANGE)
    with c4: kpi_card("Date Range", date_range_label(df), icon="", bg=GREEN_SOFT, fg=GREEN)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        card_header("Automated Feature Engineering Preview", "GPS offsets, visit timestamps, and behaviour flags — auto-computed.", icon="")
        preview_cols = [c for c in [
            "SRCode", "StoreName", "Date", "TimeIn", "TimeOut", "CallDur", "gps_offset_m", "VisitStatus"
        ] + FLAG_COLS if c in df.columns]
        st.dataframe(df[preview_cols].rename(columns=READABLE).head(200), width='stretch')

    insight_box(
        "Navigate using the sidebar (or the pages menu) to explore <b>Behaviour Clustering</b>, "
        "<b>Root Cause Analysis</b>, <b>Failure Prediction</b>, and more. Every page reacts to its own "
        "drill-down filters in the sidebar.",
        icon="",
    )

    with st.container(border=True):
        card_header("Enterprise Risk Score — Opportunity Impact", "Derived automatically from VisitStatus (E/S/N/X) — no assumption required.", icon="", bg=GREEN_SOFT, fg=GREEN)
        if "VisitStatusCode" in df.columns:
            vc = df["VisitStatusCode"].value_counts().reindex(["E", "S", "N", "X"], fill_value=0)
            vcols = st.columns(4)
            vlabels = {"E": "Extra Successful", "S": "Successful (Planned)", "N": "Unsuccessful (Planned)", "X": "Extra Unsuccessful"}
            vcolors = [(GREEN_SOFT, GREEN), (GREEN_SOFT, GREEN), (RED_SOFT, RED), (RED_SOFT, RED)]
            for i, code in enumerate(["E", "S", "N", "X"]):
                with vcols[i]:
                    bg, fg = vcolors[i]
                    kpi_card(f"{code} — {vlabels[code]}", f"{int(vc[code]):,}", icon="", bg=bg, fg=fg)
            st.caption(
                "Revenue Impact (RI) is computed from these codes: a lost **planned** call (N) is weighted more "
                "heavily than a lost **extra/unplanned** call (X), using the dataset's own planned-vs-extra mix "
                "as the weight — no revenue figure is required. See the Enterprise Risk Score page for the full "
                "calculation."
            )
            with st.expander(" Verify: raw vs. parsed VisitStatus values"):
                raw_vs = st.session_state.get("raw_visit_status")
                if raw_vs is not None:
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        st.markdown("**Raw values found in your file** (top 10)")
                        st.dataframe(raw_vs.astype(str).value_counts().head(10).rename("Count"), width='stretch')
                    with rc2:
                        st.markdown("**Parsed into E / S / N / X**")
                        st.dataframe(df["VisitStatusCode"].value_counts().rename("Count"), width='stretch')
                    st.caption(
                        "If a raw value on the left isn't mapping the way you expect on the right, it's likely "
                        "using wording or punctuation the parser doesn't yet recognize — share an example and it "
                        "can be added."
                    )
                else:
                    st.caption("Raw values aren't available for this session — reload the file to see this comparison.")
        else:
            st.caption("Upload a dataset with a `VisitStatus` column to enable the Opportunity Impact calculation.")

        with st.expander(" Optional: also show a dollar estimate"):
            st.caption(
                "If you know your average revenue per planned visit, entering it here will additionally show a "
                "$ Revenue-at-Risk figure alongside the primary (unitless) Opportunity Impact score. Leave at 0 "
                "to skip — this is entirely optional and off by default."
            )
            st.session_state["value_per_planned_visit"] = st.number_input(
                "Average Revenue per Planned Visit ($) — optional",
                min_value=0.0, value=float(st.session_state.get("value_per_planned_visit", 0.0)), step=50.0,
            )
else:
    st.info("No dataset loaded yet. Upload a CSV above or click **Load Sample Data** to explore the app.")
