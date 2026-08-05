import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button,
    render_top_header, card_header, date_range_label, kpi_card,
    PRIMARY, PRIMARY_SOFT, RED, RED_SOFT, ORANGE, ORANGE_SOFT, GREEN, GREEN_SOFT, BLUE, BLUE_SOFT,
    TEXT_MUTED, BORDER,
    compute_enterprise_risk, RISK_WEIGHTS, BEHAVIOR_LABELS,
    recommendations_header, action_card, plain_takeaway, kpi_with_download,
)

st.set_page_config(page_title="Enterprise Risk Score", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Enterprise Risk Score", "One overall risk score per rep, combining how often, how strong, how consistent, and how costly their behaviour patterns are.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p8")
fdf = apply_filters(df, filters)

if fdf.empty or fdf["SRCode"].nunique() < 2:
    st.warning("Not enough data in the current filter selection to compute the Enterprise Risk Score.")
    st.stop()

value_per_planned = st.session_state.get("value_per_planned_visit", 0.0) or None
result, meta = compute_enterprise_risk(fdf, value_per_planned_visit=value_per_planned)
has_dollar = meta["has_dollar_est"]
ri_meta = meta["ri_meta"]

# ---------------------------------------------------------------------------
# Pipeline visual
# ---------------------------------------------------------------------------
pipeline_steps = ["Sales Data", "Behaviour Detection", "Frequency (BF)", "Statistical\nAssociation (SA)",
                   "Persistence (P)", "Opportunity\nImpact (RI)", "Interaction\nScore (BIS)",
                   "Enterprise\nRisk Score", "Risk Category", "AI\nRecommendations"]
step_html = "".join(
    f'<div style="display:flex;align-items:center;">'
    f'<div style="background:{PRIMARY_SOFT};color:{PRIMARY};border-radius:12px;padding:10px 14px;'
    f'font-size:0.72rem;font-weight:700;text-align:center;white-space:pre-line;min-width:92px;">{s}</div>'
    + (f'<div style="color:{TEXT_MUTED};font-size:1rem;padding:0 6px;">→</div>' if i < len(pipeline_steps) - 1 else '')
    + '</div>'
    for i, s in enumerate(pipeline_steps)
)
with st.container(border=True):
    card_header("Enterprise AI Pipeline", "How raw visit data flows into a final coaching recommendation.", icon="")
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;padding:8px 4px;">{step_html}</div>', unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Methodology + weights
# ---------------------------------------------------------------------------
with st.expander(" Formula, weights, and how each component is calculated"):
    dollar_line = (
        f"An optional dollar overlay is active this period: **${value_per_planned:,.0f}** assumed per planned visit."
        if has_dollar else
        "No dollar figure is in use — the Opportunity Impact score below is entirely unitless and derived only "
        "from VisitStatus codes."
    )
    st.markdown(
        f"""
**Risk Score = 0.30×BF + 0.20×SA + 0.15×P + 0.20×RI + 0.15×BIS** (every component scaled 0-100 first)

| Component | Weight | What it measures | How it's calculated here |
|---|---|---|---|
| **BF** — Behaviour Frequency | 30% | How often undesirable behaviours occur | `Behaviour Count / Total Visits × 100`, averaged across Non-Instore, Rushed, Delayed Start, Off-Route |
| **SA** — Statistical Association | 20% | Strength of the link to failed visits | Chi-Square + Cramér's V (0-1) between each behaviour and visit failure, population-wide, scaled to 0-100, then frequency-weighted per rep |
| **P** — Behaviour Persistence | 15% | How sustained the behaviour is over time | `Days Behaviour Occurred / Window × 100`, averaged over rolling 30/60/90-day windows |
| **RI** — Opportunity Impact | 20% | Business cost of failed visits, from VisitStatus | See below — derived from E/S/N/X codes, no revenue assumption needed |
| **BIS** — Behaviour Interaction | 15% | Compounding effect of behaviour combinations | `Lift = P(A&B) / (P(A)×P(B))` for each rep's own strongest behaviour pair, scaled against the team's highest observed lift |

**Risk classification:** 0–20 Very Low · 21–40 Low · 41–60 Medium · 61–80 High · 81–100 Critical

**How Opportunity Impact (RI) is derived from VisitStatus:**

Your `VisitStatus` column codes each visit as **E** (Extra Successful/Unplanned), **S** (Successful/Planned),
**N** (Unsuccessful/Planned), or **X** (Extra Unsuccessful/Unplanned). A *planned* call represents a scheduled,
expected customer touchpoint, so losing one (N) is treated as costlier than losing an unplanned/bonus
attempt (X). The weight between the two isn't a business guess — it's this dataset's own mix:

- Share of all visits that are **planned** (S+N): **{ri_meta['w_planned']:.0%}** → weight applied to N
- Share of all visits that are **extra/unplanned** (E+X): **{ri_meta['w_extra']:.0%}** → weight applied to X

`Opportunity Loss Index = (Planned Failures × {ri_meta['w_planned']:.2f}) + (Extra Failures × {ri_meta['w_extra']:.2f})`,
then min-max scaled to 0-100 across reps in the current view. {dollar_line}

**Population-level Statistical Association (Chi-Square / Cramér's V) this period:**

| Behaviour | Cramér's V | SA Score (0-100) | p-value |
|---|---|---|---|
{chr(10).join(f"| {BEHAVIOR_LABELS[b]} | {meta['sa_df'].loc[b,'CramersV']:.3f} | {meta['sa_df'].loc[b,'SA_Score']:.1f} | {meta['sa_df'].loc[b,'PValue']:.2e} |" for b in meta['sa_df'].index)}

A p-value below 0.05 indicates the association between that behaviour and visit failure is statistically
significant (unlikely to be due to chance) in the current filtered dataset.

**Primary Failure Reason (AI Output) vs. the SA component above — these use different logic on purpose:**
the 20%-weighted **SA** component of the Risk Score reflects a rep's *overall* exposure to statistically-risky
behaviours (their overall behaviour frequency weighted by team-wide association strength). **Primary Failure
Reason**, shown in the AI Output card below, answers a narrower, rep-specific question: *"of the behaviours
this rep exhibits, which one is actually driving their failures — not just present regardless of outcome?"*

A behaviour only qualifies as a candidate if it is genuinely **more common on this rep's own failed visits
than on their own successful visits** (a positive excess rate). A behaviour that shows up just as often — or
more often — when the rep succeeds is excluded, even if its raw count among failures looks large, because it
isn't actually associated with *this rep's* failures. Among qualifying behaviours, the one with the strongest
rep-level Chi-Square/Cramér's V (computed from that rep's own full success + failure history) is selected as
Primary. This avoids a common pitfall: a behaviour a rep does constantly (in both good and bad visits) can
have a high raw failed-visit count without actually being what's causing the failures.
        """
    )

# ---------------------------------------------------------------------------
# Distribution + top risk reps
# ---------------------------------------------------------------------------
c1, c2 = st.columns(2, gap="medium")
tier_colors = {"Critical": RED, "High": ORANGE, "Medium": "#E8C34A", "Low": GREEN, "Very Low": BLUE}
with c1:
    with st.container(border=True):
        card_header("How Risky Is Each Rep?", "Every rep's overall risk score, from 0 (no concerns) to 100 (urgent).", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        fig = px.histogram(result, x="RiskScore", nbins=20, color="RiskCategory",
                            color_discrete_map=tier_colors)
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')
        n_crit_high = int(result["RiskCategory"].isin(["Critical", "High"]).sum())
        plain_takeaway(
            f"Most bars sitting toward the left means most of the team is low-risk. "
            f"<b>{n_crit_high} reps</b> currently fall in the Critical/High (red/orange) zone and need attention first."
        )

with c2:
    with st.container(border=True):
        card_header("Who Needs Attention First", "The 10 reps with the highest overall risk score.", icon="", bg=RED_SOFT, fg=RED)
        top10 = result.sort_values("RiskScore", ascending=False).head(10)
        fig = px.bar(top10, x="SRCode", y="RiskScore", color="RiskCategory",
                     color_discrete_map=tier_colors)
        fig.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')
        plain_takeaway(
            f"<b>{top10.iloc[0]['SRCode']}</b> has the highest overall risk score in the current view "
            f"({top10.iloc[0]['RiskScore']:.0f}/100) — start coaching conversations here."
        )

n_by_tier = result["RiskCategory"].value_counts()
kc = st.columns(5)
tier_order = ["Critical", "High", "Medium", "Low", "Very Low"]
tier_icons = {"Critical": "", "High": "", "Medium": "", "Low": "", "Very Low": ""}
for i, tier in enumerate(tier_order):
    with kc[i]:
        kpi_card(tier, str(int(n_by_tier.get(tier, 0))), icon=tier_icons[tier],
                  bg=f"{tier_colors[tier]}18", fg=tier_colors[tier])
        tier_reps = result[result["RiskCategory"] == tier]
        if len(tier_reps) > 0:
            st.download_button(
                "", tier_reps[["SRCode", "RiskScore", "PrimaryFailureReason"]].to_csv(index=False).encode("utf-8"),
                file_name=f"{tier.lower().replace(' ', '_')}_risk_reps.csv", mime="text/csv",
                key=f"dl_tier_{tier}", help=f"Download the {tier} risk rep list",
            )

with st.container(border=True):
    card_header("Full Component Table", "Every rep's BF / SA / P / RI / BIS and final score.", icon="")
    cols_to_show = ["SRCode", "BF", "SA", "P", "RI", "BIS", "RiskScore", "RiskCategory",
                     "PrimaryFailureReason", "PrimaryReasonRate", "PrimaryReasonDiff", "ConfidenceScore", "RI_raw"]
    rename_map = {"RI_raw": "Opportunity Loss Index", "PrimaryFailureReason": "Primary Failure Reason",
                  "PrimaryReasonRate": "Rate in Own Failed Visits", "PrimaryReasonDiff": "Excess Rate vs. Own Success Visits",
                  "ConfidenceScore": "Confidence (%)"}
    if has_dollar:
        cols_to_show.append("RI_dollar")
        rename_map["RI_dollar"] = "Est. Revenue at Risk ($)"
    display_df = result[cols_to_show].rename(columns=rename_map).sort_values("RiskScore", ascending=False)
    st.dataframe(display_df, width='stretch')
    download_csv_button(display_df, " Download Full Risk Score Table (CSV)", "enterprise_risk_scores.csv")

# ---------------------------------------------------------------------------
# AI Output — per-rep profile card
# ---------------------------------------------------------------------------
def confidence_tag(score):
    """Plain, action-oriented label instead of statistical jargon."""
    if score >= 60:
        return "Confirmed", GREEN, "Main issue", "safe to coach on directly"
    elif score >= 35:
        return "Likely", GREEN, "Main issue", "worth coaching on, but keep an eye on it"
    elif score >= 15:
        return "Possible", ORANGE, "Possible issue", "worth a quick check before assuming this is the main cause"
    else:
        return "Needs confirmation", RED, "Possible lead", "not yet statistically confirmed — worth a ride-along check first"


def fact_chip(label, value, color=TEXT_MUTED):
    return (
        f'<span style="display:inline-block;background:{color}14;color:{color};border-radius:999px;'
        f'padding:5px 12px;margin:3px 6px 3px 0;font-size:0.78rem;font-weight:600;">{label}: {value}</span>'
    )


with st.container(border=True):
    card_header("AI Output — Rep Risk Profile", "Select a rep for a plain-English risk summary.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
    sel_rep = st.selectbox("Select a Sales Rep", result.sort_values("RiskScore", ascending=False)["SRCode"])
    row = result[result["SRCode"] == sel_rep].iloc[0]
    tier_bg, tier_fg = f"{tier_colors[row['RiskCategory']]}18", tier_colors[row["RiskCategory"]]
    has_primary = pd.notna(row["PrimaryFailureReason"]) and row["PrimaryFailureReason"] != "None Identified"
    is_confirmed = bool(row.get("PrimaryReasonConfirmed", False))
    tag, tag_color, headline_word, tag_guidance = confidence_tag(row["ConfidenceScore"])
    rank_pct = max(100 - int(row["RI_Percentile"] * 100), 1)

    pc1, pc2 = st.columns([1, 2])
    with pc1:
        st.markdown(
            f"""
            <div style="background:{tier_bg};border-radius:16px;padding:18px;text-align:center;">
                <div style="font-size:2.2rem;font-weight:800;color:{tier_fg};">{row['RiskScore']:.1f}</div>
                <div class="badge" style="background-color:{tier_fg}25;color:{tier_fg};margin-top:6px;">{row['RiskCategory']} Risk</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pc2:
        if has_primary and is_confirmed:
            st.markdown(f"####  {headline_word}: {row['PrimaryFailureReason']}")
            st.markdown(f"This is {sel_rep}'s most common problem on failed calls.")
            chips = fact_chip("How sure", tag, tag_color)
            if row["SecondaryBehaviours"] != "None":
                chips += fact_chip("Also seen", row["SecondaryBehaviours"].split(",")[0].strip())
            chips += fact_chip("Missed opportunities", f"top {rank_pct}% of team", ORANGE)
            st.markdown(chips, unsafe_allow_html=True)
        elif has_primary and not is_confirmed:
            st.markdown("####  No single stand-out cause")
            st.markdown(
                f"Nothing clearly explains {sel_rep}'s failures on its own — closest lead is "
                f"**{row['PrimaryFailureReason']}**, but it's not a confirmed cause."
            )
            st.markdown(fact_chip("Missed opportunities", f"top {rank_pct}% of team", ORANGE), unsafe_allow_html=True)
        else:
            st.markdown("####  No behaviour pattern flagged")
            st.markdown(f"{sel_rep} doesn't show a meaningful failure pattern in the current data.")

    if has_primary and is_confirmed and tag in ("Confirmed", "Likely"):
        action_text = f" <b>What to do:</b> coach {sel_rep} on <b>{row['PrimaryFailureReason']}</b> — it's {tag_guidance}."
    elif has_primary and is_confirmed:
        action_text = f" <b>What to do:</b> before coaching {sel_rep}, verify <b>{row['PrimaryFailureReason']}</b> is really the cause — {tag_guidance}."
    elif has_primary and not is_confirmed:
        action_text = f" <b>What to do:</b> review {sel_rep}'s visit log directly, or look outside the tracked behaviours (store conditions, customer availability, etc.)."
    else:
        action_text = f" <b>What to do:</b> no action needed — {sel_rep} isn't showing a risk pattern right now."
    insight_box(action_text, icon="")


# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

critical_high = result[result["RiskCategory"].isin(["Critical", "High"])].sort_values("RiskScore", ascending=False)
top_reason = result["PrimaryFailureReason"].value_counts()

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Escalation List", "Reps requiring immediate management attention.", icon="", bg=RED_SOFT, fg=RED)
        if not critical_high.empty:
            esc_cols = ["SRCode", "RiskScore", "RiskCategory", "PrimaryFailureReason", "PrimaryReasonConfirmed", "RI_raw"]
            esc_rename = {"RiskScore": "Risk Score", "RiskCategory": "Risk Level",
                          "PrimaryFailureReason": "Main Problem", "PrimaryReasonConfirmed": "Confirmed?",
                          "RI_raw": "Missed Opportunity Score"}
            if has_dollar:
                esc_cols.append("RI_dollar")
                esc_rename["RI_dollar"] = "Revenue at Risk ($)"
            st.dataframe(critical_high[esc_cols].rename(columns=esc_rename), width='stretch')
        else:
            st.info("No reps currently fall in the Critical or High risk tiers for this filtered view.")

with rc2:
    if not critical_high.empty:
        worst = critical_high.iloc[0]
        action_card(
            f"<b>{worst['SRCode']}</b> is the highest Enterprise Risk Score in the current view "
            f"({worst['RiskScore']:.1f}/100, {worst['RiskCategory']}) — driven primarily by "
            f"<b>{worst['PrimaryFailureReason']}</b>. Recommend this rep for immediate 1:1 review.",
            priority="High",
        )
        impact_share = critical_high['RI_raw'].sum() / result['RI_raw'].sum() if result['RI_raw'].sum() > 0 else 0
        action_card(
            f"{len(critical_high)} rep(s) are in the Critical/High tier, collectively responsible for "
            f"{impact_share:.0%} of the team's total Opportunity Loss Index — prioritizing this group "
            "addresses the majority of recoverable lost visits.",
            priority="High",
        )
    else:
        action_card(
            "No reps are currently Critical or High risk — maintain current coaching cadence and monitor "
            "the Medium-tier group below for early drift.",
            priority="Low",
        )
    if len(top_reason) > 0:
        action_card(
            f"<b>{top_reason.index[0]}</b> is the most common Primary Failure Reason across "
            f"{int(top_reason.iloc[0])} rep(s) — a team-wide training module on this behaviour would have the "
            "broadest reach of any single intervention.",
            priority="Medium",
        )
