import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button, kpi_card, FLAG_COLS, READABLE,
    render_top_header, card_header, date_range_label, hero_risk_card,
    factor_risk_profile, assign_risk_tiers, recommendations_header, action_card, rank_table,
    zscore_outliers, compute_enterprise_risk, kpi_with_download, graph_explainer,
    compute_plan_compliance, plain_takeaway,
    PRIMARY, PRIMARY_SOFT, RED, RED_SOFT, ORANGE, ORANGE_SOFT, GREEN, GREEN_SOFT, BLUE, BLUE_SOFT,
)

st.set_page_config(page_title="Executive Dashboard", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("AI Insights for Field Execution", "AI-powered identification of key risks impacting sales effectiveness and compliance.",
                   icon="", date_range=date_range_label(df), filter_label="Filter")

filters = sidebar_filters(df, "p7")
fdf = apply_filters(df, filters)

if fdf.empty:
    st.warning("No records match the current filters.")
    st.stop()

total_reps = fdf["SRCode"].nunique()

# ---------------------------------------------------------------------------
# Fully data-driven risk profiles for the 4 headline behaviour patterns.
# See the "How these numbers are calculated" panel below for methodology.
# ---------------------------------------------------------------------------
hero_defs = [
    ("non_instore_visit", "Non-Instore Visits", "", PRIMARY_SOFT, PRIMARY,
     "record visits without entering the store, reducing meaningful customer engagement.",
     "pages/4_Correlation_Matrix.py"),
    ("rushed_visit", "Rushed Visits", "", RED_SOFT, RED,
     "consistently record shorter visit durations, indicating rushed store engagement.",
     "pages/2_Root_Cause_Analysis.py"),
    ("delayed_start", "Late Start Productivity Loss", "", ORANGE_SOFT, ORANGE,
     "consistently begin field activity later than their peers, reducing available selling time.",
     "pages/5_Transition_Matrix.py"),
    ("off_route_visit_store", "Chronic Route Non-Compliance", "", RED_SOFT, RED,
     "show GPS visit locations well outside their assigned store radius versus peers.",
     "pages/1_Behaviour_Clustering.py"),
]

profiles = {col: factor_risk_profile(fdf, col) for col, *_ in hero_defs}
tiers = assign_risk_tiers({col: p["composite_score"] for col, p in profiles.items()})

st.markdown("<br>", unsafe_allow_html=True)
cols = st.columns(2, gap="medium")
for i, (col, title, icon, icon_bg, icon_fg, desc, link) in enumerate(hero_defs):
    p = profiles[col]
    top_rep = p["affected_reps"].index[0] if p["affected_count"] > 0 else "—"
    top_rate = p["affected_reps"].iloc[0] if p["affected_count"] > 0 else 0
    impact_text = (
        f"Visits carrying this flag fail {p['impact_lift']:+.0%} more often than visits without it "
        f"(based on {len(fdf):,} visits in the current view)."
    )
    reco_text = (
        f"Coach the {p['affected_count']} rep(s) running >1 std. dev. above the {p['mu']:.0%} team average "
        f"(worst: {top_rep} at {top_rate:.0%})."
        if p["affected_count"] > 0 else
        "No rep is statistically elevated above the team average in this view — pattern is evenly distributed."
    )
    with cols[i % 2]:
        hero_risk_card(
            icon=icon, icon_bg=icon_bg, icon_fg=icon_fg,
            title=title,
            description=f"{p['affected_count']} SRs {desc}",
            risk_level=tiers[col], stat_value=str(p["affected_count"]), stat_label=f"{p['pct_affected']:.0%} of Total SRs",
            trend_delta=p["delta_pct"], impact=impact_text, recommendation=reco_text,
            affected=f"{p['affected_count']} SRs",
            trend_x=p["monthly"]["Month"], trend_y=p["monthly"][col] * 100,
            page_link=link, link_label="View Details",
        )
        if p["affected_count"] > 0:
            aff_df = p["affected_reps"].reset_index()
            aff_df.columns = ["SRCode", "Rate"]
            aff_df["Behaviour"] = title
            aff_df["Rate"] = (aff_df["Rate"] * 100).round(1)
            kpi_with_download(
                p['affected_count'], "rep", f"flagged for {title.lower()}",
                aff_df, f"{col}_affected_reps.csv",
            )

with st.expander(" How these risk numbers are calculated (methodology)"):
    st.markdown(
        f"""
**Per-rep incidence rate** — for each behaviour flag, we compute the mean flag value per `SRCode`
across all their visits in the current filtered view (e.g. a rep with 6 rushed visits out of 20 total
has a 30% Rushed Visit rate).

**"Affected" reps** — a rep is counted as affected when their incidence rate is more than **1 standard
deviation above the team's own mean** for that behaviour (a z-score threshold), *not* a fixed percentage.
This adapts automatically: a stricter or looser cut-off emerges naturally depending on how spread out the
team's behaviour actually is this period. Team mean (μ) and standard deviation (σ) for this view:

| Metric | Team Mean (μ) | Std. Dev (σ) | Affected Reps | % of Team |
|---|---|---|---|---|
{chr(10).join(f"| {title} | {profiles[c]['mu']:.1%} | {profiles[c]['sigma']:.1%} | {profiles[c]['affected_count']} | {profiles[c]['pct_affected']:.0%} |" for c, title, *_ in hero_defs)}

**Business impact (lift)** — the difference in overall visit-failure rate between visits *with* the flag
present and visits *without* it. This is the same lift calculation used on the Root Cause Analysis page,
so the two pages stay consistent.

**Composite risk score** = `% of team affected` × `business impact lift`. This blends *how widespread*
a pattern is with *how much it actually hurts outcomes* — a behaviour that's rare but severely damaging can
still outrank one that's common but low-impact.

**Risk tier (High / Medium / Low)** — the four composite scores above are ranked against each other;
the highest becomes High, the lowest becomes Low, and the middle two are Medium. Because this is a relative
ranking rather than a fixed cutoff, it recalibrates automatically whenever you change the filters.
        """
    )

total_affected = len(set().union(*[set(p["affected_reps"].index) for p in profiles.values()]))
title_lookup = {c: t for c, t, *_ in hero_defs}
top_pattern_col = max(profiles, key=lambda k: profiles[k]["composite_score"])
st.markdown(
    f"""
    <div class="summary-banner">
        <div style="display:flex;gap:14px;align-items:center;">
            <div class="summary-banner-icon"></div>
            <div class="summary-banner-text">
                <b>AI Summary:</b> A total of <b>{total_affected} SRs</b> are statistically elevated on at least
                one of the 4 key behavioural patterns above. The highest composite-risk pattern this period is
                <b>{title_lookup[top_pattern_col]}</b> — addressing it first offers the largest blended
                improvement in prevalence and outcome quality.
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# KPI Metrics
# ---------------------------------------------------------------------------
compliance_rate = 1 - fdf["non_successful_visit"].mean()
fdf["bad_habit_score"] = fdf[FLAG_COLS].mean(axis=1)
sr_bad = fdf.groupby("SRCode")["bad_habit_score"].mean()
bad_mask, bad_mu, bad_sigma = zscore_outliers(sr_bad)
high_risk_count = int(bad_mask.sum())

drivers = {"delayed_start": "Delayed Start", "rushed_visit": "Rushed Visit",
           "off_route_visit_store": "Off-Route Visit", "non_instore_visit": "Non-Instore Visit"}
impact = {}
for col, label in drivers.items():
    if (fdf[col] == 1).any() and (fdf[col] == 0).any():
        impact[label] = fdf.loc[fdf[col] == 1, "non_successful_visit"].mean() - fdf.loc[fdf[col] == 0, "non_successful_visit"].mean()
top_root_cause = max(impact, key=impact.get) if impact else "N/A"

monthly_p = fdf.groupby(["SRCode", "Month"])["bad_habit_score"].mean().reset_index()
sr_std = monthly_p.groupby("SRCode")["bad_habit_score"].std().fillna(0)
max_std = sr_std.max() if sr_std.max() > 0 else 1
consistency = 1 - (sr_std / max_std)
persistence = ((1 - sr_bad).clip(0, 1) * 60 + consistency.clip(0, 1) * 40).round(1)
avg_persistence = persistence.mean()

c1, c2, c3, c4 = st.columns(4)
with c1: kpi_card("Overall Compliance Rate", f"{compliance_rate:.0%}", icon="", bg=GREEN_SOFT, fg=GREEN)
with c2: kpi_card("High-Risk Rep Count", f"{high_risk_count}", icon="", bg=RED_SOFT, fg=RED,
                   sub=f">1σ above team avg bad-habit rate ({bad_mu:.0%})")
with c3: kpi_card("Top Root Cause", top_root_cause, icon="", bg=ORANGE_SOFT, fg=ORANGE)
with c4: kpi_card("Average Persistence Score", f"{avg_persistence:.0f} / 100", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)

if high_risk_count > 0:
    high_risk_df = sr_bad[bad_mask].reset_index()
    high_risk_df.columns = ["SRCode", "BadHabitRate"]
    high_risk_df["BadHabitRate"] = (high_risk_df["BadHabitRate"] * 100).round(1)
    kpi_with_download(
        high_risk_count, "rep", "are statistically high-risk this period",
        high_risk_df, "high_risk_reps.csv",
    )

st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    ec1, ec2 = st.columns([3, 1])
    with ec1:
        card_header("Enterprise Risk Score", "Weighted multi-factor model: 30% Frequency + 20% Statistical Association + 15% Persistence + 20% Opportunity Impact + 15% Interaction.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        try:
            value_per_planned = st.session_state.get("value_per_planned_visit", 0.0) or None
            ent_result, ent_meta = compute_enterprise_risk(fdf, value_per_planned_visit=value_per_planned)
            n_critical_high = int(ent_result["RiskCategory"].isin(["Critical", "High"]).sum())
            avg_score = ent_result["RiskScore"].mean()
            extra_clause = (
                f"**${ent_result['RI_dollar'].sum():,.0f}** total estimated revenue at risk this period."
                if ent_meta["has_dollar_est"] else
                f"**{ent_result['RI_raw'].sum():.0f}** total Opportunity Loss Index points (derived from VisitStatus, no revenue assumption)."
            )
            st.markdown(
                f"Team average Enterprise Risk Score: **{avg_score:.1f}/100** · "
                f"**{n_critical_high}** rep(s) in the Critical/High tier · "
                f"{extra_clause}"
            )
        except Exception:
            pass
    with ec2:
        st.markdown("<br>", unsafe_allow_html=True)
        try:
            st.page_link("pages/8_Enterprise_Risk_Score.py", label="Open Full Model  →")
        except Exception:
            st.markdown(f'<span style="color:{PRIMARY};font-weight:700;font-size:0.85rem;">Open Full Model →</span>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

colA, colB = st.columns(2, gap="medium")
with colA:
    with st.container(border=True):
        card_header("Failure Rate Trend by Month", "Overall visit-failure trajectory.", icon="", bg=RED_SOFT, fg=RED)
        trend = fdf.groupby("Month")["non_successful_visit"].mean().reset_index()
        fig = px.line(trend, x="Month", y="non_successful_visit", markers=True,
                      labels={"non_successful_visit": "Failure Rate"})
        fig.update_traces(line_color=PRIMARY, fill="tozeroy", fillcolor="rgba(108,92,231,0.08)")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with colB:
    with st.container(border=True):
        card_header("Root Cause Impact Ranking", "Which behaviour drives failure the most. (Full breakdown with drill-down on the Root Cause Analysis page.)", icon="", bg=ORANGE_SOFT, fg=ORANGE)
        impact_df = pd.DataFrame(list(impact.items()), columns=["Factor", "Impact"]).sort_values("Impact", ascending=False)
        fig = px.bar(impact_df, x="Factor", y="Impact", color="Factor")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

colC, colD = st.columns(2, gap="medium")
with colC:
    with st.container(border=True):
        card_header("Plan Compliance", "Are reps actually covering their full assigned route — not just doing well on the stores they visit?", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        plan_df = compute_plan_compliance(fdf)
        if not plan_df.empty and plan_df["PlannedStores"].sum() > 0:
            avg_compliance = plan_df["PlanCompliancePct"].mean()
            eval_month = plan_df["EvaluatedMonth"].iloc[0]
            fig = px.histogram(plan_df, x="PlanCompliancePct", nbins=15, color_discrete_sequence=[PRIMARY])
            fig.update_layout(**PLOTLY_TEMPLATE["layout"], xaxis_title="Plan Compliance %")
            style_axes(fig)
            st.plotly_chart(fig, width='stretch')
            low_compliance = plan_df[plan_df["PlanCompliancePct"] < plan_df["PlanCompliancePct"].median()]
            plain_takeaway(
                f"For <b>{eval_month}</b> (the most recent month in the current view), reps covered an average of "
                f"<b>{avg_compliance:.0f}%</b> of their territory. A rep can pass every quality check on the "
                "visits they make while still skipping most of their route — this chart catches that gap. "
                "See 'Plan Compliance — Full Breakdown' below for exactly how this is calculated, with a worked example."
            )
            kpi_with_download(
                len(low_compliance), "rep", "are below the team's median route coverage",
                low_compliance, "low_plan_compliance_reps.csv",
            )
        else:
            st.info("Not enough planned-visit history to calculate Plan Compliance for this view.")

with colD:
    with st.container(border=True):
        card_header("Team Consistency Trend", "Is the whole team's behaviour getting more or less consistent over time? (See the Consistency Tracker page for individual rep rankings.)", icon="", bg=GREEN_SOFT, fg=GREEN)
        team_monthly = monthly_p.groupby("Month")["bad_habit_score"].mean().reset_index()
        team_monthly["Team Consistency"] = (1 - team_monthly["bad_habit_score"]).clip(0, 1) * 100
        fig = px.line(team_monthly, x="Month", y="Team Consistency", markers=True)
        fig.update_traces(line_color=GREEN, fill="tozeroy", fillcolor="rgba(47,174,96,0.08)")
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    card_header("Executive Narrative", "Five key takeaways for leadership.", icon="")
    narrative_points = [
        f"Overall visit compliance stands at <b>{compliance_rate:.0%}</b>, with <b>{high_risk_count}</b> sales reps "
        f"statistically elevated (>1σ) above the team's average bad-habit rate of {bad_mu:.0%}.",
        f"<b>{top_root_cause}</b> is the leading operational driver of failed visits — addressing it first offers "
        f"the largest single improvement to visit success rates.",
        f"Average behaviour persistence across the team is <b>{avg_persistence:.0f}/100</b>, indicating "
        f"{'stable, largely compliant' if avg_persistence >= persistence.median() else 'inconsistent'} field execution "
        f"relative to the team's own median.",
        "Behaviour clustering shows distinct personas that warrant different, targeted coaching interventions "
        "rather than a one-size-fits-all policy — see Page 1 for the full breakdown.",
        "Sequential analysis confirms that early-day issues cascade into later failures — see Page 5 for the "
        "exact transition probabilities driving this.",
    ]
    for p in narrative_points:
        insight_box(p, icon="•")

# ---------------------------------------------------------------------------
# Recommended Actions — cross-page priority list, fully rank-derived
# ---------------------------------------------------------------------------
recommendations_header()

priority_df = pd.DataFrame([
    dict(Pattern=title, CompositeScore=profiles[col]["composite_score"],
         AffectedReps=profiles[col]["affected_count"], ImpactLift=profiles[col]["impact_lift"],
         Tier=tiers[col])
    for col, title, *_ in hero_defs
]).sort_values("CompositeScore", ascending=False)

rc1, rc2 = st.columns([1, 1], gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Priority Action Matrix", "Ranked by blended prevalence × business impact.", icon="")
        fig = px.bar(priority_df, x="CompositeScore", y="Pattern", orientation="h", color="Tier",
                     color_discrete_map={"High": RED, "Medium": ORANGE, "Low": GREEN},
                     labels={"CompositeScore": "Composite Risk Score"})
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with rc2:
    top_pattern = priority_df.iloc[0]
    second_pattern = priority_df.iloc[1] if len(priority_df) > 1 else None
    worst_rep_overall = sr_bad.sort_values(ascending=False).index[0]
    action_card(
        f"<b>{top_pattern['Pattern']}</b> carries the highest composite score this period "
        f"({top_pattern['CompositeScore']:.3f}), affecting {int(top_pattern['AffectedReps'])} reps with a "
        f"{top_pattern['ImpactLift']:+.0%} failure-rate impact. This is the single highest-leverage fix available "
        "right now.",
        priority="High",
    )
    if second_pattern is not None:
        action_card(
            f"<b>{second_pattern['Pattern']}</b> is the second priority (score {second_pattern['CompositeScore']:.3f}) "
            f"— consider pairing its fix with the top pattern above since both are ranked highest this period.",
            priority="Medium",
        )
    action_card(
        f"<b>{worst_rep_overall}</b> has the highest combined bad-habit rate of any rep in the current view "
        f"({sr_bad.loc[worst_rep_overall]:.0%}, vs a team average of {bad_mu:.0%}) — recommend this rep for "
        "immediate 1:1 review across all four patterns above.",
        priority="High",
    )

download_csv_button(priority_df, " Download Priority Action Matrix (CSV)", "priority_action_matrix.csv")

with st.container(border=True):
    plan_df_full = compute_plan_compliance(fdf)
    eval_month_full = plan_df_full["EvaluatedMonth"].iloc[0] if not plan_df_full.empty else None
    card_header(
        "Plan Compliance — Full Breakdown",
        f"Territory (planned stores across the filtered history) vs. stores actually visited in {eval_month_full}."
        if eval_month_full else "Planned stores vs. stores actually visited, per rep.",
        icon="", bg=PRIMARY_SOFT, fg=PRIMARY,
    )
    if not plan_df_full.empty and plan_df_full["PlannedStores"].sum() > 0:
        example_row = plan_df_full.iloc[len(plan_df_full) // 2]
        with st.expander("How is Plan Compliance calculated?"):
            st.markdown(
                f"""
**Step 1 — Find each rep's territory.** Every store where this rep has had a *planned* visit
(a VisitStatus of S or N), counted across all the months in your current filter.

**Step 2 — Pick one specific month to check.** The most recent month in your current filter —
right now that's **{eval_month_full}**.

**Step 3 — Compare them:**

&nbsp;&nbsp;&nbsp;&nbsp;Plan Compliance % = (Stores visited in {eval_month_full}) ÷ (Total territory stores) × 100

**Worked example from your own data:** rep **{example_row['SRCode']}** has **{int(example_row['PlannedStores'])}**
stores in their territory, but only visited **{int(example_row['VisitedPlannedStores'])}** of them in
{eval_month_full}. That's {int(example_row['VisitedPlannedStores'])} ÷ {int(example_row['PlannedStores'])} =
**{example_row['PlanCompliancePct']:.0f}%**. The other **{int(example_row['MissedPlannedStores'])}** stores show up
as "Missed Stores" in the table below, by name.

Since the uploaded data has no separate route-plan file, territory is inferred from visit history — this is the
closest substitute we can build from what's available. Narrow the sidebar's Month filter to check a different
specific period.
                """
            )
        pc1, pc2, pc3, pc4 = st.columns(4)
        with pc1: kpi_card("Total Planned Stores", f"{int(plan_df_full['PlannedStores'].sum()):,}", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        with pc2: kpi_card(f"Visited in {eval_month_full}", f"{int(plan_df_full['VisitedPlannedStores'].sum()):,}", icon="", bg=GREEN_SOFT, fg=GREEN)
        with pc3: kpi_card(f"Missed in {eval_month_full}", f"{int(plan_df_full['MissedPlannedStores'].sum()):,}", icon="", bg=RED_SOFT, fg=RED)
        with pc4: kpi_card("Avg Plan Compliance", f"{plan_df_full['PlanCompliancePct'].mean():.0f}%", icon="", bg=ORANGE_SOFT, fg=ORANGE)
        plain_takeaway(
            f"Every rep below the average is skipping a meaningful part of their route — check the 'Missed Store "
            f"Names' column to see exactly which stores they're not covering in {eval_month_full}."
        )
        st.dataframe(
            plan_df_full.rename(columns={
                "PlannedStores": "Planned Stores", "VisitedPlannedStores": "Visited",
                "MissedPlannedStores": "Missed", "PlanCompliancePct": "Compliance %",
                "MissedStores": "Missed Store Names", "EvaluatedMonth": "Evaluated Month",
            }),
            width='stretch',
        )
        download_csv_button(plan_df_full, " Download Plan Compliance (CSV)", "plan_compliance.csv")
    else:
        st.info("Not enough planned-visit history in the current filter to calculate Plan Compliance.")

with st.container(border=True):
    card_header("Master Drill-Down Table", "Search across every visit record in the current filter.", icon="")
    search = st.text_input("Search by SRCode, StoreName, or DistributorName", label_visibility="collapsed",
                            placeholder=" Search by SRCode, StoreName, or DistributorName")
    master = fdf.copy()
    if search:
        mask = pd.Series(False, index=master.index)
        for col in ["SRCode", "StoreName", "DistributorName"]:
            if col in master.columns:
                mask |= master[col].astype(str).str.contains(search, case=False, na=False)
        master = master[mask]
    display_cols = [c for c in ["SRCode", "DistributorName", "StoreName", "Date", "CallDur",
                                 "gps_offset_m", "VisitStatus"] + FLAG_COLS if c in master.columns]
    st.dataframe(master[display_cols].head(500).rename(columns=READABLE), width='stretch')

with st.container(border=True):
    card_header("Export Executive Findings", "Download filtered data or a summary report.", icon="")
    col1, col2 = st.columns(2)
    with col1:
        download_csv_button(master[display_cols], " Download Filtered Master Dataset (CSV)", "master_drilldown.csv")
    with col2:
        report_text = (
            "SR FIELD INSIGHTS — EXECUTIVE SUMMARY REPORT\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            + "\n".join(f"- {p.replace('<b>','').replace('</b>','')}" for p in narrative_points)
            + f"\n\nKPIs:\n- Overall Compliance Rate: {compliance_rate:.0%}"
            f"\n- High-Risk Rep Count: {high_risk_count}"
            f"\n- Top Root Cause: {top_root_cause}"
            f"\n- Average Persistence Score: {avg_persistence:.0f}/100\n"
            f"\nTop Priority Pattern: {top_pattern['Pattern']} (composite score {top_pattern['CompositeScore']:.3f})\n"
        )
        st.download_button(" Download Executive Summary Report (TXT)", report_text.encode("utf-8"),
                            file_name="executive_summary_report.txt", mime="text/plain")
