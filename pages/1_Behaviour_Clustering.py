import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button, FLAG_COLS,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    ORANGE, ORANGE_SOFT, RED, RED_SOFT,
    recommendations_header, action_card, kpi_with_download, plain_takeaway,
)

st.set_page_config(page_title="Behaviour Clustering", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Behaviour Clustering", "Reps naturally fall into a few behaviour types — this groups them so similar reps can be coached together.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p1")
fdf = apply_filters(df, filters)

if fdf.empty or fdf["SRCode"].nunique() < 3:
    st.warning("Not enough data in the current filter selection to build clusters (need at least 3 SRs).")
    st.stop()

agg = fdf.groupby("SRCode").agg(
    avg_call_dur=("CallDur", "mean"),
    avg_gps_offset=("gps_offset_m", "mean"),
    failure_rate=("non_successful_visit", "mean"),
    rushed_rate=("rushed_visit", "mean"),
    offroute_rate=("off_route_visit_store", "mean"),
    delayed_rate=("delayed_start", "mean"),
    visits=("SRCode", "count"),
).fillna(0).reset_index()

features = ["avg_call_dur", "avg_gps_offset", "failure_rate", "rushed_rate", "offroute_rate", "delayed_rate"]
X = StandardScaler().fit_transform(agg[features])

n_clusters = min(4, max(2, agg.shape[0] // 3))
km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
agg["cluster"] = km.fit_predict(X)

agg["risk_score"] = agg["failure_rate"] * 0.4 + agg["rushed_rate"] * 0.25 + agg["offroute_rate"] * 0.2 + agg["delayed_rate"] * 0.15
cluster_risk = agg.groupby("cluster")["risk_score"].mean().sort_values()

persona_pool = ["Top Compliant", "Steady Performers", "Delayed Starters", "Rushed Operators", "Off-Route Reps"]
persona_pool = persona_pool[:n_clusters] if n_clusters <= len(persona_pool) else persona_pool + [f"Cluster {i}" for i in range(n_clusters - len(persona_pool))]
persona_map = {cl: persona_pool[i] for i, cl in enumerate(cluster_risk.index)}
agg["Persona"] = agg["cluster"].map(persona_map)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("Reps Grouped by Persona", "Call duration vs. GPS distance offset, sized by visit volume.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        fig1 = px.scatter(
            agg, x="avg_call_dur", y="avg_gps_offset", color="Persona", size="visits",
            hover_data={"SRCode": True, "failure_rate": ":.0%"},
            labels={"avg_call_dur": "Average Call Duration (min)", "avg_gps_offset": "Average GPS Offset (m)"},
        )
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig1)
        st.plotly_chart(fig1, width='stretch')
        insight_box(
            "Each dot is one sales rep. Reps clustered toward short call durations and large GPS offsets are "
            "most likely logging rushed or off-route visits — good candidates for a ride-along or coaching check-in."
        )

with c2:
    with st.container(border=True):
        card_header("Persona Profile Comparison", "Average behaviour metrics across each persona.", icon="", bg=ORANGE_SOFT, fg=ORANGE)
        profile = agg.groupby("Persona").agg(
            avg_call_dur=("avg_call_dur", "mean"), failure_rate=("failure_rate", "mean"),
            rushed_rate=("rushed_rate", "mean"), offroute_rate=("offroute_rate", "mean"),
        ).reset_index()
        profile_melt = profile.melt(id_vars="Persona", var_name="Metric", value_name="Value")
        metric_labels = {"avg_call_dur": "Avg Call Duration (min)", "failure_rate": "Failure Rate",
                          "rushed_rate": "Rushed Visit Rate", "offroute_rate": "Off-Route Rate"}
        profile_melt["Metric"] = profile_melt["Metric"].map(metric_labels)
        fig2 = px.bar(profile_melt, x="Persona", y="Value", color="Metric", barmode="group")
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig2)
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            "Personas with visibly higher failure and anomaly rates (rushed / off-route) are dragging down "
            "overall visit quality and should receive targeted retraining or route audits first."
        )

with st.container(border=True):
    card_header("Cluster Summary Table", "Sortable rep-level averages for every persona.", icon="")
    st.dataframe(
        agg[["SRCode", "Persona", "avg_call_dur", "avg_gps_offset", "failure_rate", "visits"]]
        .rename(columns={"avg_call_dur": "Avg Call Duration", "avg_gps_offset": "Avg GPS Offset (m)",
                          "failure_rate": "Failure Rate", "visits": "Total Visits"})
        .sort_values("Failure Rate", ascending=False),
        width='stretch',
    )

with st.container(border=True):
    card_header("Drill-Down: Persona Visit Log", "Select a cluster persona to inspect underlying visits.", icon="", bg=RED_SOFT, fg=RED)
    sel_persona = st.selectbox("Select a Cluster Persona", sorted(agg["Persona"].unique()))
    sel_srs = agg.loc[agg["Persona"] == sel_persona, "SRCode"]
    detail = fdf[fdf["SRCode"].isin(sel_srs)]
    st.dataframe(
        detail[["SRCode", "StoreName", "Date", "CallDur", "gps_offset_m", "VisitStatus"] + FLAG_COLS].head(300),
        width='stretch',
    )
    download_csv_button(agg, " Download Cluster Assignments (CSV)", "cluster_assignments.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

persona_risk = agg.groupby("Persona")["risk_score"].mean().sort_values(ascending=False)
worst_persona = persona_risk.index[0]
worst_persona_reps = agg.loc[agg["Persona"] == worst_persona, "SRCode"].nunique()
priority_reps = agg.sort_values("risk_score", ascending=False).head(8)

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Priority Coaching List", "Reps ranked by composite risk score across all behaviours.", icon="")
        fig = px.bar(priority_reps, x="SRCode", y="risk_score", color="Persona",
                     labels={"risk_score": "Composite Risk Score"})
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with rc2:
    action_card(
        f"The <b>{worst_persona}</b> persona has the highest average risk score of any group "
        f"({persona_risk.iloc[0]:.2f}), spanning {worst_persona_reps} rep(s). This group should receive the "
        "next coaching cycle's primary focus.",
        priority="High",
    )
    worst_persona_df = agg[agg["Persona"] == worst_persona][["SRCode", "Persona", "failure_rate", "risk_score"]]
    kpi_with_download(
        worst_persona_reps, "rep", f"are in the highest-risk persona ({worst_persona})",
        worst_persona_df, "worst_persona_reps.csv",
    )
    action_card(
        f"<b>{priority_reps.iloc[0]['SRCode']}</b> ranks highest overall for combined risk "
        f"(failure rate {priority_reps.iloc[0]['failure_rate']:.0%}, {priority_reps.iloc[0]['visits']} visits "
        f"analyzed) — recommend a 1:1 review as the single highest-leverage individual action available.",
        priority="High",
    )
    if len(persona_risk) > 1:
        second_persona = persona_risk.index[1]
        action_card(
            f"<b>{second_persona}</b> is the next-highest-risk persona (score {persona_risk.iloc[1]:.2f}). "
            "Consider a shared training module since both top personas likely share overlapping root causes.",
            priority="Medium",
        )
