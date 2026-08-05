import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from utils import (
    inject_theme, sidebar_filters, apply_filters, require_data,
    insight_box, PLOTLY_TEMPLATE, style_axes, download_csv_button,
    render_top_header, card_header, date_range_label, PRIMARY, PRIMARY_SOFT,
    RED, RED_SOFT, ORANGE, GREEN,
    recommendations_header, action_card, READABLE, kpi_with_download, plain_takeaway,
)

st.set_page_config(page_title="Future Failure Prediction", page_icon="", layout="wide", initial_sidebar_state="expanded")
inject_theme()

df = require_data()
render_top_header("Future Failure Prediction", "Which reps are most likely to fail their next visit.",
                   icon="", date_range=date_range_label(df))

filters = sidebar_filters(df, "p3")
fdf = apply_filters(df, filters)

if fdf.empty or fdf["non_successful_visit"].nunique() < 2:
    st.warning("Not enough variation in outcomes within the current filter to build a prediction model.")
    st.stop()

feat_cols = ["CallDur", "gps_offset_m", "rushed_visit", "off_route_visit_store", "delayed_start", "non_instore_visit"]
model_df = fdf.dropna(subset=feat_cols + ["non_successful_visit"]).copy()

X = StandardScaler().fit_transform(model_df[feat_cols])
y = model_df["non_successful_visit"]

model = LogisticRegression(max_iter=500)
model.fit(X, y)
model_df["risk_prob"] = model.predict_proba(X)[:, 1]

sr_risk = model_df.groupby("SRCode").agg(
    avg_risk=("risk_prob", "mean"),
    visits=("risk_prob", "count"),
    sup=("Role_Senior Supervisor", "first") if "Role_Senior Supervisor" in model_df.columns else ("SRCode", "count"),
).reset_index().sort_values("avg_risk", ascending=False)

q_low, q_high = sr_risk["avg_risk"].quantile([0.33, 0.66])
def risk_cat(p):
    if p >= q_high:
        return "High"
    elif p >= q_low:
        return "Medium"
    return "Low"
sr_risk["Risk Category"] = sr_risk["avg_risk"].apply(risk_cat)

c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        card_header("Top 10 Highest-Risk Reps", "Predicted probability of failing the next visit.", icon="", bg=RED_SOFT, fg=RED)
        top10 = sr_risk.head(10)
        fig1 = px.bar(top10, x="SRCode", y="avg_risk", color="Risk Category",
                      color_discrete_map={"High": RED, "Medium": ORANGE, "Low": GREEN},
                      labels={"avg_risk": "Predicted Failure Probability"})
        fig1.update_layout(**PLOTLY_TEMPLATE["layout"])
        style_axes(fig1)
        st.plotly_chart(fig1, width='stretch')
        insight_box(
            f"The model estimates each rep's probability of a failed visit from call duration, GPS drift, and "
            f"prior behaviour flags. The top-risk rep, <b>{top10.iloc[0]['SRCode']}</b>, sits at "
            f"{top10.iloc[0]['avg_risk']:.0%} — proactively scheduling a supervisor ride-along can prevent "
            "failures before they happen."
        )

with c2:
    with st.container(border=True):
        card_header("Risk Category Distribution", "Share of the team likely to fail their NEXT visit (forward-looking prediction — see the Enterprise Risk Score page for each rep's overall risk profile).", icon="", bg=PRIMARY_SOFT, fg=PRIMARY)
        cat_counts = sr_risk["Risk Category"].value_counts().reindex(["High", "Medium", "Low"]).reset_index()
        cat_counts.columns = ["Risk Category", "Rep Count"]
        fig2 = px.pie(cat_counts, names="Risk Category", values="Rep Count", hole=0.6,
                      color="Risk Category", color_discrete_map={"High": RED, "Medium": ORANGE, "Low": GREEN})
        fig2.update_layout(**PLOTLY_TEMPLATE["layout"])
        st.plotly_chart(fig2, width='stretch')
        insight_box(
            "A large 'High Risk' slice signals a systemic issue (training, routing, or workload) rather than a "
            "few isolated reps — worth escalating to regional management if it exceeds roughly a quarter of the team."
        )

with st.container(border=True):
    card_header("Risk Leaderboard", "Full ranked list of reps by predicted risk.", icon="")
    st.dataframe(
        sr_risk.rename(columns={"avg_risk": "Predicted Risk", "visits": "Visits Analyzed"}),
        width='stretch',
    )

with st.container(border=True):
    card_header("Drill-Down: High-Risk Rep History", "Select High-Risk reps to inspect their visit history.", icon="", bg=RED_SOFT, fg=RED)
    high_risk_reps = st.multiselect(
        "Select High-Risk reps to inspect",
        sr_risk.loc[sr_risk["Risk Category"] == "High", "SRCode"].tolist(),
        default=sr_risk.loc[sr_risk["Risk Category"] == "High", "SRCode"].tolist()[:3],
    )
    if high_risk_reps:
        detail = fdf[fdf["SRCode"].isin(high_risk_reps)]
        cols = [c for c in ["SRCode", "Role_Senior Supervisor", "StoreName", "Date", "CallDur",
                             "gps_offset_m", "VisitStatus"] if c in detail.columns]
        st.dataframe(detail[cols].head(300), width='stretch')

    download_csv_button(sr_risk, " Download Risk Leaderboard (CSV)", "risk_leaderboard.csv")

# ---------------------------------------------------------------------------
# Recommended Actions
# ---------------------------------------------------------------------------
recommendations_header()

coef_df = pd.DataFrame({"Feature": feat_cols, "Coefficient": model.coef_[0]})
coef_df["AbsCoefficient"] = coef_df["Coefficient"].abs()
coef_df = coef_df.sort_values("AbsCoefficient", ascending=False)
coef_df["Feature"] = coef_df["Feature"].map(lambda c: READABLE.get(c, c))
top_lever = coef_df.iloc[0]
top_risk_rep = sr_risk.iloc[0]
n_high = int((sr_risk["Risk Category"] == "High").sum())

rc1, rc2 = st.columns(2, gap="medium")
with rc1:
    with st.container(border=True):
        card_header("Strongest Predictive Levers", "Which features most influence the model's risk score.", icon="")
        fig = px.bar(coef_df, x="Feature", y="Coefficient", color=coef_df["Coefficient"] > 0,
                     color_discrete_map={True: RED, False: GREEN},
                     labels={"Coefficient": "Standardized Coefficient"})
        fig.update_layout(**PLOTLY_TEMPLATE["layout"], showlegend=False)
        style_axes(fig)
        st.plotly_chart(fig, width='stretch')
        plain_takeaway(
            f"Bars pointing right (red) push risk up; bars pointing left (green) pull it down. "
            f"<b>{top_lever['Feature']}</b> has the biggest effect either way — it's the single most useful "
            "thing to change if you want to lower the team's overall predicted risk."
        )

with rc2:
    direction = "increases" if top_lever["Coefficient"] > 0 else "decreases"
    action_card(
        f"<b>{top_lever['Feature']}</b> is the strongest predictor of visit failure in the current model — "
        f"it {direction} predicted risk more than any other factor. This is the most controllable lever for "
        "reducing the team's overall predicted risk.",
        priority="High",
    )
    action_card(
        f"<b>{n_high}</b> reps fall in the High-Risk tier this period, led by <b>{top_risk_rep['SRCode']}</b> "
        f"at a {top_risk_rep['avg_risk']:.0%} predicted failure probability across {int(top_risk_rep['visits'])} "
        "visits analyzed — schedule this rep's ride-along first.",
        priority="High",
    )
    if n_high > 0:
        kpi_with_download(
            n_high, "rep", "predicted High-Risk for their next visit",
            sr_risk[sr_risk["Risk Category"] == "High"], "high_risk_predicted_reps.csv",
        )
    action_card(
        f"Reallocating supervisor time toward the {n_high} High-Risk reps (rather than spreading attention "
        "evenly across the team) targets the interventions where the model expects the largest reduction in "
        "failed visits per hour of coaching.",
        priority="Medium",
    )
