import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button, FLAG_COLS,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    GREEN, RED,
    recommendations_header, action_card, kpi_with_download,
)

st.set_page_config(page_title="Persistence Score", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Consistency Tracker", "Tells apart a rep having one bad week from a rep who's stuck in a bad pattern every month.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p6")
fdf = apply_filters(df, filters)

if fdf.empty or "Month" not in fdf.columns:
    st.warning("No records match the current filters.")
    st.stop()

fdf["bad_habit_score"] = fdf[FLAG_COLS].mean(axis=1)

monthly = fdf.groupby(["SRCode", "Month"])["bad_habit_score"].mean().reset_index()
sr_stats = monthly.groupby("SRCode")["bad_habit_score"].agg(["mean", "std", "count"]).fillna(0).reset_index()
sr_stats["std"] = sr_stats["std"].fillna(0)

max_std = sr_stats["std"].max() if sr_stats["std"].max() > 0 else 1
sr_stats["consistency"] = 1 - (sr_stats["std"] / max_std)

sr_stats["Persistence Score"] = (
    (1 - sr_stats["mean"]).clip(0, 1) * 60 + sr_stats["consistency"].clip(0, 1) * 40
).round(1)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("Persistence Score Distribution", "0-100 consistency index across all reps.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        fig1 = px.histogram(sr_stats, x="Persistence Score", nbins=20, color_discrete_sequence=[PRIMARY])
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig1)
        st.plotly_chart(fig1, width='stretch')
        insight_box(
            "Higher scores mean a rep reliably keeps their bad-habit rate low, month after month. Scores "
            "clustered low on the left indicate reps whose compliance is either consistently poor or "
            "unpredictably swinging between good and bad months — both are coaching priorities."
        )

with c2:
    with st.container(border=True):
        card_header("Top vs. Bottom Reps", "Most consistent performers vs. persistent habitual offenders.", icon="")
        top5 = sr_stats.sort_values("Persistence Score", ascending=False).head(5).copy()
        top5["Group"] = "Top 5 Most Consistent"
        bottom5 = sr_stats.sort_values("Persistence Score", ascending=True).head(5).copy()
        bottom5["Group"] = "Bottom 5 Habitual Offenders"
        leader = pd.concat([top5, bottom5])
        fig2 = px.bar(leader.sort_values("Persistence Score"), x="Persistence Score", y="SRCode", color="Group",
                      orientation="h",
                      color_discrete_map={"Top 5 Most Consistent": GREEN, "Bottom 5 Habitual Offenders": RED})
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig2)
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            f"<b>{top5.iloc[0]['SRCode']}</b> is the most consistently compliant rep in the current view, while "
            f"<b>{bottom5.iloc[0]['SRCode']}</b> shows the most persistent bad-habit pattern. Pairing the two in "
            "a mentorship or shadow-visit program is a low-cost way to transfer good habits."
        )

with st.container(border=True):
    card_header("Persistence Summary Table", "Every rep's score, consistency, and months tracked.", icon="")
    st.dataframe(
        sr_stats[["SRCode", "mean", "consistency", "Persistence Score", "count"]]
        .rename(columns={"mean": "Avg Bad-Habit Rate", "consistency": "Month-to-Month Consistency", "count": "Months Tracked"})
        .sort_values("Persistence Score", ascending=False),
        width='stretch',
    )

with st.container(border=True):
    card_header("Drill-Down: Individual Rep Trend", "Select a rep to view their month-over-month habit trend.", icon="")
    sel_sr = st.selectbox("Select a Sales Rep", sorted(sr_stats["SRCode"].unique()))
    trend = monthly[monthly["SRCode"] == sel_sr].sort_values("Month")
    fig3 = px.line(trend, x="Month", y="bad_habit_score", markers=True,
                   labels={"bad_habit_score": "Monthly Bad-Habit Rate"})
    fig3.update_traces(line_color=PRIMARY, fill="tozeroy", fillcolor="rgba(108,92,231,0.08)")
    fig3.update_layout(**PLOTLY_TEMPLATE["layout"])
    style_axes(fig3)
    st.plotly_chart(fig3, width='stretch')
    log_cols = [c for c in ["StoreName", "Date", "CallDur", "gps_offset_m", "VisitStatus"] + FLAG_COLS if c in fdf.columns]
    st.dataframe(fdf[fdf["SRCode"] == sel_sr][log_cols].head(300), width='stretch')

    download_csv_button(sr_stats, " Download Persistence Leaderboard (CSV)", "persistence_leaderboard.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

# Priority = low persistence combined with high visit volume (more visits = more at-risk
# customer touchpoints per low-consistency rep). Both axes and the median split-lines are
# derived entirely from this dataset's own distribution.
sr_stats["Priority Score"] = (100 - sr_stats["Persistence Score"]) * sr_stats["count"].rank(pct=True)
priority_reps = sr_stats.sort_values("Priority Score", ascending=False).head(8)
med_persistence = sr_stats["Persistence Score"].median()
med_count = sr_stats["count"].median()

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Coaching Priority Matrix", "Persistence score vs. visit volume — top-right needs attention.", icon="")
        fig = px.scatter(sr_stats, x="Persistence Score", y="count", size="count", color="Persistence Score",
                          color_continuous_scale=["#E5484D", "#E68A2E", "#2FAE60"],
                          labels={"count": "Months Tracked × Visit Volume", "Persistence Score": "Persistence Score"},
                          hover_data=["SRCode"])
        fig.add_vline(x=med_persistence, line_dash="dash", line_color="#A0A1B8")
        fig.add_hline(y=med_count, line_dash="dash", line_color="#A0A1B8")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')
        insight_box(
            "Dashed lines mark the team's own median on each axis. Reps in the lower-right — high visit volume "
            "but below-median persistence — represent the largest coaching opportunity, since they touch the "
            "most customers while being the least consistent."
        )

with rc2:
    top_priority = priority_reps.iloc[0]
    action_card(
        f"<b>{top_priority['SRCode']}</b> is the top coaching priority — a below-average persistence score of "
        f"{top_priority['Persistence Score']:.0f}/100 combined with high visit volume means inconsistency here "
        "affects the most customer touchpoints.",
        priority="High",
    )
    if len(priority_reps) > 1:
        action_card(
            f"<b>{priority_reps.iloc[1]['SRCode']}</b> and <b>{priority_reps.iloc[2]['SRCode']}</b> round out "
            "the top-3 priority list — consider grouping all three into the same coaching cohort this cycle.",
            priority="Medium",
        )
    kpi_with_download(
        len(priority_reps), "rep", "are top coaching priorities (low consistency + high visit volume)",
        priority_reps[["SRCode", "Persistence Score", "Priority Score", "count"]].rename(columns={"count": "Months Tracked"}),
        "coaching_priority_reps.csv",
    )
    top5_names = ", ".join(sr_stats.sort_values('Persistence Score', ascending=False)['SRCode'].head(3).tolist())
    action_card(
        f"Pair each priority rep above with one of the team's most consistent performers "
        f"({top5_names}) for a shadow-visit — transferring proven habits tends to move the persistence "
        "score faster than generic training.",
        priority="Medium",
    )
