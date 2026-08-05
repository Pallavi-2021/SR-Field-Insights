import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    RED, GREEN,
    recommendations_header, action_card, kpi_with_download,
)

st.set_page_config(page_title="Transition Matrix", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Bad-Day Domino Effect", "A rough visit doesn't happen in isolation — this shows how one bad visit increases the chance the next one goes badly too.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p5")
fdf = apply_filters(df, filters)

if fdf.empty or "SRCode" not in fdf.columns:
    st.warning("No records match the current filters.")
    st.stop()


def dominant_state(row):
    if row["non_successful_visit"] == 1:
        return "Failed"
    if row["delayed_start"] == 1:
        return "Delayed Start"
    if row["rushed_visit"] == 1:
        return "Rushed"
    if row["off_route_visit_store"] == 1:
        return "Off-Route"
    return "Clean"


fdf = fdf.sort_values(["SRCode", "visit_start_dt"]) if "visit_start_dt" in fdf.columns else fdf.sort_values(["SRCode"])
fdf["state"] = fdf.apply(dominant_state, axis=1)
fdf["next_state"] = fdf.groupby("SRCode")["state"].shift(-1)

trans = fdf.dropna(subset=["next_state"])
states_order = ["Clean", "Delayed Start", "Rushed", "Off-Route", "Failed"]
ctab = pd.crosstab(trans["state"], trans["next_state"], normalize="index").reindex(
    index=states_order, columns=states_order, fill_value=0
)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("Sequential Visit Transition Heatmap", "Probability of moving from one visit state to the next.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        fig1 = px.imshow(
            ctab, text_auto=".0%", color_continuous_scale="Purples",
            labels=dict(x="Next Visit State", y="Current Visit State", color="Probability"),
        )
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig1, width='stretch')
        delayed_to_bad = ctab.loc["Delayed Start", ["Rushed", "Off-Route", "Failed"]].sum()
        insight_box(
            f"When a visit is flagged as a <b>Delayed Start</b>, there is a {delayed_to_bad:.0%} chance the very "
            "next visit is also Rushed, Off-Route, or Failed. Early-day delays cascade through the rest of the "
            "route — catching a late start immediately can prevent the day from unraveling."
        )

with c2:
    with st.container(border=True):
        card_header("Morning Start vs. Late-Day Outcome", "Impact of an on-time start on afternoon compliance.", icon="")
        fdf["day_part"] = np.where(fdf["visit_seq"] <= fdf.groupby("SRCode")["visit_seq"].transform("median"), "Early Route", "Late Route")
        fdf["had_morning_delay"] = fdf.groupby("SRCode")["delayed_start"].transform("first").map({1: "Delayed Morning Start", 0: "On-Time Morning Start"})

        late_outcomes = fdf[fdf["day_part"] == "Late Route"].groupby("had_morning_delay")["non_successful_visit"].mean().reset_index()
        late_outcomes.columns = ["Morning Start", "Late-Day Failure Rate"]
        fig2 = px.bar(late_outcomes, x="Morning Start", y="Late-Day Failure Rate", color="Morning Start",
                      color_discrete_map={"Delayed Morning Start": RED, "On-Time Morning Start": GREEN})
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig2)
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            "Reps who start their day late tend to carry that disruption into the afternoon, ending with a "
            "higher failure rate on later visits. Enforcing punctual first-call times is a high-leverage fix "
            "for end-of-day compliance."
        )

with st.container(border=True):
    card_header("Transition Probability Table", "Full state-to-state transition matrix.", icon="")
    st.dataframe((ctab * 100).round(1).rename(columns=lambda c: c + " (%)"), width='stretch')

with st.container(border=True):
    card_header("Drill-Down: Sequence Timelines", "Select a state transition to view the affected route timelines.", icon="")
    seq_options = [f"{a} → {b}" for a in states_order for b in states_order]
    sel_seq = st.selectbox("Select a state transition", seq_options,
                            index=seq_options.index("Delayed Start → Rushed") if "Delayed Start → Rushed" in seq_options else 0)
    a, b = sel_seq.split(" → ")
    detail = trans[(trans["state"] == a) & (trans["next_state"] == b)]
    cols = [c for c in ["SRCode", "StoreName", "Date", "visit_seq", "state", "next_state"] if c in detail.columns]
    st.dataframe(detail[cols].head(300), width='stretch')
    download_csv_button(ctab.reset_index(), " Download Transition Matrix (CSV)", "transition_matrix.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

# Riskiest trigger state: the current state with the highest combined probability
# of transitioning into Rushed, Off-Route, or Failed next — derived purely from the matrix.
bad_next = ["Rushed", "Off-Route", "Failed"]
trigger_risk = ctab[bad_next].sum(axis=1).drop("Failed", errors="ignore").sort_values(ascending=False)
top_trigger = trigger_risk.index[0]
top_trigger_prob = trigger_risk.iloc[0]

seq_counts = trans.groupby(["SRCode", "state", "next_state"]).size().reset_index(name="count")
worst_seq = seq_counts[(seq_counts["state"] == top_trigger) & (seq_counts["next_state"].isin(bad_next))]
worst_seq_reps = worst_seq.groupby("SRCode")["count"].sum().sort_values(ascending=False)

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Riskiest Trigger States", "Probability each state cascades into a bad outcome next.", icon="")
        tdf = trigger_risk.reset_index()
        tdf.columns = ["State", "Probability"]
        fig = px.bar(tdf, x="State", y="Probability", color_discrete_sequence=[RED])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with rc2:
    action_card(
        f"A visit in the <b>{top_trigger}</b> state has a {top_trigger_prob:.0%} chance the very next visit "
        "is Rushed, Off-Route, or Failed — this is the single most important trigger point to intervene on "
        "in real time.",
        priority="High",
    )
    if len(worst_seq_reps) > 0:
        action_card(
            f"<b>{worst_seq_reps.index[0]}</b> has triggered the {top_trigger} → bad-outcome sequence "
            f"{int(worst_seq_reps.iloc[0])} time(s) this period — the most of any rep — and is the best "
            "candidate for a same-day supervisor check-in when this pattern recurs.",
            priority="Medium",
        )
        worst_seq_df = worst_seq_reps.reset_index()
        worst_seq_df.columns = ["SRCode", "TimesTriggered"]
        kpi_with_download(
            len(worst_seq_df), "rep", "have triggered this bad-day pattern at least once",
            worst_seq_df, "bad_day_pattern_reps.csv",
        )
