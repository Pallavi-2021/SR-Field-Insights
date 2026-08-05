import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    ORANGE, ORANGE_SOFT, RED, RED_SOFT, GREEN,
    quantile_bins, recommendations_header, action_card, compute_store_risk, kpi_with_download, plain_takeaway,
)

st.set_page_config(page_title="Root Cause Analysis", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Root Cause Analysis", "Understanding why visits fail — and what to fix first.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p2")
fdf = apply_filters(df, filters)

if fdf.empty:
    st.warning("No records match the current filters.")
    st.stop()

drivers = {
    "delayed_start": "Delayed Start",
    "rushed_visit": "Rushed Visit",
    "off_route_visit_store": "Off-Route Visit",
    "non_instore_visit": "Non-Instore Visit",
}

failure_rate_overall = fdf["non_successful_visit"].mean()
rows = []
for col, label in drivers.items():
    with_flag = fdf.loc[fdf[col] == 1, "non_successful_visit"].mean() if (fdf[col] == 1).any() else np.nan
    without_flag = fdf.loc[fdf[col] == 0, "non_successful_visit"].mean() if (fdf[col] == 0).any() else np.nan
    lift = (with_flag - without_flag) if pd.notna(with_flag) and pd.notna(without_flag) else np.nan
    rows.append(dict(Factor=label, col=col, FailureRateWithFactor=with_flag,
                      FailureRateWithoutFactor=without_flag, ImpactLift=lift,
                      AffectedVisits=int((fdf[col] == 1).sum())))
impact_df = pd.DataFrame(rows).sort_values("ImpactLift", ascending=False)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("Top Drivers of Failed Visits", "Increase in failure rate when each factor is present.", icon="", bg=RED_SOFT, fg=RED)
        fig1 = px.bar(
            impact_df, x="Factor", y="ImpactLift", color="Factor",
            labels={"ImpactLift": "Increase in Failure Rate vs. Baseline"},
            text=impact_df["ImpactLift"].map(lambda v: f"{v:+.0%}" if pd.notna(v) else "n/a"),
        )
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig1)
        st.plotly_chart(fig1, width='stretch')
        top_driver = impact_df.iloc[0]
        insight_box(
            f"<b>{top_driver['Factor']}</b> is the single strongest driver of visit failure — visits with this "
            f"issue fail {top_driver['ImpactLift']:+.0%} more often than the baseline ({failure_rate_overall:.0%}). "
            "Fixing this first will likely produce the biggest overall improvement."
        )

with c2:
    with st.container(border=True):
        card_header("Failure Rate by Threshold", "Where visits start tipping into failure (quantile-based bins).", icon="", bg=ORANGE_SOFT, fg=ORANGE)
        bin_choice = st.radio("Bin by:", ["Call Duration (min)", "GPS Distance Offset (m)"], horizontal=True)
        if bin_choice.startswith("Call"):
            fdf["_bin"] = quantile_bins(fdf["CallDur"], q=6)
        else:
            fdf["_bin"] = quantile_bins(fdf["gps_offset_m"], q=6)
        bin_rate = fdf.groupby("_bin", observed=True)["non_successful_visit"].mean().reset_index()
        fig2 = px.line(bin_rate, x="_bin", y="non_successful_visit", markers=True,
                       labels={"_bin": bin_choice, "non_successful_visit": "Failure Rate"})
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"])
        fig2.update_traces(line_color=RED, fill="tozeroy", fillcolor="rgba(229,72,77,0.08)")
        style_axes(fig2)
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            "Bins are built from the data's own quantiles (equal-sized groups), so the ranges shown always "
            "reflect this dataset's actual spread rather than a fixed assumption. The steepest step up in "
            "failure rate marks the operational tipping point worth targeting."
        )

with st.container(border=True):
    card_header("Root Cause Ranking", "Failure rate with vs. without each factor present.", icon="")
    st.dataframe(
        impact_df[["Factor", "FailureRateWithFactor", "FailureRateWithoutFactor", "ImpactLift", "AffectedVisits"]]
        .rename(columns={"FailureRateWithFactor": "Failure Rate (Factor Present)",
                          "FailureRateWithoutFactor": "Failure Rate (Factor Absent)",
                          "ImpactLift": "Impact (Lift)", "AffectedVisits": "Affected Visits"}),
        width='stretch',
    )

with st.container(border=True):
    card_header("Drill-Down: Reps/Stores Behind a Root Cause", "Select a primary failure driver to inspect.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
    sel_driver = st.selectbox("Select a primary failure driver", impact_df["Factor"])
    sel_col = impact_df.loc[impact_df["Factor"] == sel_driver, "col"].iloc[0]
    detail = fdf[(fdf[sel_col] == 1) & (fdf["non_successful_visit"] == 1)]
    st.dataframe(
        detail[["SRCode", "StoreName", "Date", "CallDur", "gps_offset_m", "VisitStatus"]].head(300),
        width='stretch',
    )
    download_csv_button(impact_df, " Download Root Cause Ranking (CSV)", "root_cause_ranking.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

sr_driver = fdf.groupby("SRCode")[sel_col].mean().sort_values(ascending=False)
worst_bin = bin_rate.sort_values("non_successful_visit", ascending=False).iloc[0]
best_bin = bin_rate.sort_values("non_successful_visit", ascending=True).iloc[0]
spread = worst_bin["non_successful_visit"] - best_bin["non_successful_visit"]

rec_col1, rec_col2 = st.columns(2, gap="medium")
with rec_col1:
    with st.container(border=True):
        card_header("Reps Most Exposed to the Top Driver", f"Ranked by {sel_driver} rate.", icon="")
        top_exposed = sr_driver.head(8).reset_index()
        top_exposed.columns = ["SRCode", "Rate"]
        fig = px.bar(top_exposed, x="SRCode", y="Rate", color_discrete_sequence=[RED])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with rec_col2:
    action_card(
        f"<b>{top_driver['Factor']}</b> has the largest measured effect on failure "
        f"({top_driver['ImpactLift']:+.0%}), affecting {int(top_driver['AffectedVisits']):,} visits this period. "
        f"Start remediation with <b>{sr_driver.index[0]}</b>, whose {sel_driver} rate ({sr_driver.iloc[0]:.0%}) "
        "is the highest of any rep in the current view.",
        priority="High",
    )
    action_card(
        f"The gap between the best- and worst-performing {bin_choice.split(' (')[0].lower()} band is "
        f"{spread:.0%} failure rate ('{best_bin['_bin']}' vs '{worst_bin['_bin']}'). Visits landing in the "
        f"'{worst_bin['_bin']}' band should trigger a supervisor review before being logged.",
        priority="Medium",
    )
    if len(impact_df) > 1:
        second = impact_df.iloc[1]
        action_card(
            f"<b>{second['Factor']}</b> is the second-largest driver ({second['ImpactLift']:+.0%}) — "
            "bundling a fix for both top drivers into a single coaching session will address the majority "
            "of controllable failure causes at once.",
            priority="Medium",
        )

with st.container(border=True):
    card_header("Stores Needing Attention", "Stores with a statistically higher failure rate than the team average.", icon="", bg=RED_SOFT, fg=RED)
    store_risk = compute_store_risk(fdf)
    if not store_risk.empty:
        n_high_risk_stores = int(store_risk["IsHighRisk"].sum())
        high_risk_stores = store_risk[store_risk["IsHighRisk"]]
        if n_high_risk_stores > 0:
            fig = px.bar(high_risk_stores.head(10), x="StoreName", y="FailureRate", color_discrete_sequence=[RED])
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False, yaxis_title="Failure Rate")
            style_axes(fig)
            st.plotly_chart(fig, width='stretch')
            plain_takeaway(
                f"These stores fail visits noticeably more than the team average of "
                f"{store_risk['TeamAvgFailureRate'].iloc[0]:.0%} — worth checking whether the issue is the "
                "rep, the store itself (access, stock, contact availability), or the route assignment."
            )
            kpi_with_download(
                n_high_risk_stores, "store", "have a statistically high failure rate",
                store_risk[["StoreName", "TotalVisits", "FailedVisits", "FailureRate"]][store_risk["IsHighRisk"]],
                "high_risk_stores.csv",
            )
        else:
            st.info("No stores are statistically elevated above the team average failure rate in this view.")

