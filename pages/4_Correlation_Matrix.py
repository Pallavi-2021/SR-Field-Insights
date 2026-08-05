import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button, READABLE, FLAG_COLS,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    ORANGE, ORANGE_SOFT,
    recommendations_header, action_card, kpi_with_download,
)

st.set_page_config(page_title="Correlation Matrix", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Habit Combinations", "Some bad habits travel together — this page finds which ones, so fixing one can improve the other automatically.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p4")
fdf = apply_filters(df, filters)

if fdf.empty:
    st.warning("No records match the current filters.")
    st.stop()

corr_cols = FLAG_COLS
corr = fdf[corr_cols].corr()
labels = [READABLE.get(c, c) for c in corr_cols]
corr.index = labels
corr.columns = labels

pairs = []
for i in range(len(corr_cols)):
    for j in range(i + 1, len(corr_cols)):
        pairs.append((labels[i], labels[j], corr.iloc[i, j]))
pairs_df = pd.DataFrame(pairs, columns=["Habit A", "Habit B", "Correlation"]).sort_values("Correlation", ascending=False)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("How Habits Connect", "Darker squares = two habits happen together more often. Look for the darkest square off the diagonal.", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        fig1 = px.imshow(corr, text_auto=".2f", color_continuous_scale="Purples", zmin=-1, zmax=1, aspect="auto")
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig1, width='stretch')
        top_pair = pairs_df.iloc[0]
        insight_box(
            f"Habits that appear together tend to cause a domino effect. <b>{top_pair['Habit A']}</b> and "
            f"<b>{top_pair['Habit B']}</b> show the strongest connection (correlation {top_pair['Correlation']:.2f}) "
            "— coaching one usually improves the other, so pair them in the same training session."
        )

with c2:
    with st.container(border=True):
        card_header("Top 3 Strongest Habit Pairs", "The behavioural chains worth breaking first.", icon="", bg=ORANGE_SOFT, fg=ORANGE)
        top3 = pairs_df.head(3).copy()
        top3["Pair"] = top3["Habit A"] + " + " + top3["Habit B"]
        fig2 = px.bar(top3, x="Pair", y="Correlation", color="Pair", text=top3["Correlation"].map(lambda v: f"{v:.2f}"))
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig2)
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            "These three pairs are the strongest behavioural chains in the data. Addressing the root habit in "
            "each pair (usually the earlier one in a rep's day) tends to reduce both issues at once."
        )

with st.container(border=True):
    card_header("Correlation Highlights", "All habit pairs ranked by strength of connection.", icon="")
    st.dataframe(pairs_df, width='stretch')

with st.container(border=True):
    card_header("Drill-Down: SRs Exhibiting a Habit Pair", "Select a pair to see who exhibits both concurrently.", icon="")
    pair_options = (pairs_df["Habit A"] + " + " + pairs_df["Habit B"]).tolist()
    sel_pair = st.selectbox("Select a habit pair", pair_options)
    a_label, b_label = sel_pair.split(" + ")
    inv_readable = {v: k for k, v in READABLE.items()}
    col_a, col_b = inv_readable.get(a_label, a_label), inv_readable.get(b_label, b_label)
    detail = fdf[(fdf[col_a] == 1) & (fdf[col_b] == 1)]
    cols = [c for c in ["SRCode", "StoreName", "Date", "CallDur", "gps_offset_m", "VisitStatus"] if c in detail.columns]
    st.dataframe(detail[cols].head(300), width='stretch')
    download_csv_button(pairs_df, " Download Correlation Highlights (CSV)", "correlation_highlights.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

# "Centrality" = sum of a habit's correlation with every other habit — the habit most
# entangled with the rest of the behaviour network, purely derived from the correlation matrix itself.
centrality = corr.abs().sum().sort_values(ascending=False) - 1  # subtract self-correlation (1.0)
hub_habit = centrality.index[0]
prevalence = fdf[[c for c in FLAG_COLS if READABLE.get(c, c) == hub_habit]].mean().iloc[0] if any(READABLE.get(c, c) == hub_habit for c in FLAG_COLS) else np.nan

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Which Habit to Fix First", "Habits ranked by how connected they are to all the other bad habits — fixing the top one has the widest ripple effect.", icon="")
        cent_df = centrality.reset_index()
        cent_df.columns = ["Habit", "Total Correlation"]
        fig = px.bar(cent_df, x="Habit", y="Total Correlation", color_discrete_sequence=[PRIMARY])
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')

with rc2:
    action_card(
        f"<b>{hub_habit}</b> is the most 'connected' habit in the network — it correlates most strongly with "
        "the rest of the behaviour set. Fixing this one habit is likely to produce ripple improvements across "
        "the others, making it the highest-leverage single intervention.",
        priority="High",
    )
    action_card(
        f"<b>{top_pair['Habit A']}</b> and <b>{top_pair['Habit B']}</b> co-occur more than any other pair "
        f"(correlation {top_pair['Correlation']:.2f}) — bundle these two into the same coaching module rather "
        "than treating them as separate issues.",
        priority="Medium",
    )
    top_pair_col_a = inv_readable.get(top_pair["Habit A"], top_pair["Habit A"])
    top_pair_col_b = inv_readable.get(top_pair["Habit B"], top_pair["Habit B"])
    pair_reps = fdf[(fdf[top_pair_col_a] == 1) & (fdf[top_pair_col_b] == 1)]["SRCode"].drop_duplicates().to_frame()
    if len(pair_reps) > 0:
        kpi_with_download(
            len(pair_reps), "rep", f"show both {top_pair['Habit A']} and {top_pair['Habit B']}",
            pair_reps, "top_habit_pair_reps.csv",
        )
