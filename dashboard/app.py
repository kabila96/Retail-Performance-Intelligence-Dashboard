
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from scipy import stats

st.set_page_config(
    page_title="Retail Performance Intelligence Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "supermarket_sales.csv"
REPORT_PATH = Path(__file__).resolve().parents[1] / "outputs" / "Kabzozo_Supermarket_Analysis_Report.pdf"

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Sales"] = df["Unit price"] * df["Quantity"]
    df["Month"] = df["Date"].dt.month
    df["Month_Name"] = df["Date"].dt.strftime("%b")
    df["Weekday"] = df["Date"].dt.day_name()
    df["Quarter"] = "Q" + df["Date"].dt.quarter.astype(str)
    return df

def style():
    st.markdown("""
    <style>
    .stApp {background: linear-gradient(180deg, #f7f9fc 0%, #eef2f7 100%);}
    .block-container {padding-top: 1.2rem; padding-bottom: 1rem;}
    .hero-card {
        background: linear-gradient(135deg, #1f3c88 0%, #3b82f6 100%);
        padding: 1.2rem 1.4rem;
        border-radius: 20px;
        color: white;
        box-shadow: 0 8px 24px rgba(31,60,136,0.18);
        margin-bottom: 1rem;
    }
    .insight-box {
        background: white;
        padding: 1rem 1.1rem;
        border-radius: 18px;
        border: 1px solid #d8e0ea;
        box-shadow: 0 6px 18px rgba(0,0,0,0.05);
        margin-bottom: 0.8rem;
    }
    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #243b53;
        margin-top: 0.4rem;
        margin-bottom: 0.4rem;
    }
    .metric-caption {
        color: #627d98;
        font-size: 0.85rem;
    }
    </style>
    """, unsafe_allow_html=True)

def metric_delta(current, baseline):
    if baseline == 0 or pd.isna(baseline):
        return "n/a"
    delta = (current - baseline) / baseline * 100
    return f"{delta:+.1f}%"

def safe_mode(series):
    modes = series.mode()
    return modes.iloc[0] if not modes.empty else "n/a"

def human_money(v):
    return f"£{v:,.0f}"

def filtered_data(df):
    st.sidebar.markdown("## Filters")
    branch = st.sidebar.multiselect("Branch", sorted(df["Branch"].dropna().unique()), default=sorted(df["Branch"].dropna().unique()))
    customer_type = st.sidebar.multiselect("Customer Type", sorted(df["Customer type"].dropna().unique()), default=sorted(df["Customer type"].dropna().unique()))
    gender = st.sidebar.multiselect("Gender", sorted(df["Gender"].dropna().unique()), default=sorted(df["Gender"].dropna().unique()))
    product_line = st.sidebar.multiselect("Product Line", sorted(df["Product line"].dropna().unique()), default=sorted(df["Product line"].dropna().unique()))
    payment = st.sidebar.multiselect("Payment", sorted(df["Payment"].dropna().unique()), default=sorted(df["Payment"].dropna().unique()))
    date_min = df["Date"].min().date()
    date_max = df["Date"].max().date()
    date_range = st.sidebar.date_input("Date Range", value=(date_min, date_max), min_value=date_min, max_value=date_max)
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = date_min, date_max

    out = df[
        df["Branch"].isin(branch)
        & df["Customer type"].isin(customer_type)
        & df["Gender"].isin(gender)
        & df["Product line"].isin(product_line)
        & df["Payment"].isin(payment)
        & (df["Date"].dt.date >= start_date)
        & (df["Date"].dt.date <= end_date)
    ].copy()
    return out, (start_date, end_date)

def executive_summary(df):
    total_sales = df["Sales"].sum()
    avg_sales = df["Sales"].mean()
    total_txn = len(df)
    top_product = df.groupby("Product line")["Sales"].sum().sort_values(ascending=False)
    peak_month = df.groupby("Month_Name")["Sales"].sum().sort_values(ascending=False)
    top_branch = df.groupby("Branch")["Sales"].sum().sort_values(ascending=False)

    monthly = df.groupby(["Month", "Month_Name"], as_index=False)["Sales"].sum().sort_values("Month")
    prior_month = monthly["Sales"].iloc[-2] if len(monthly) > 1 else np.nan
    current_month = monthly["Sales"].iloc[-1] if len(monthly) else np.nan

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Revenue", human_money(total_sales))
    c2.metric("Avg Transaction", human_money(avg_sales))
    c3.metric("Transactions", f"{total_txn:,}")
    c4.metric("Top Product Line", top_product.index[0] if len(top_product) else "n/a")
    c5.metric("Latest Month vs Prior", metric_delta(current_month, prior_month))

    col1, col2 = st.columns((1.45, 1))
    with col1:
        product_sales = df.groupby("Product line", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
        fig = px.bar(product_sales, x="Product line", y="Sales", title="Revenue by Product Line", text_auto=".2s")
        fig.update_layout(height=420, xaxis_title="", yaxis_title="Provisional Revenue")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        monthly = monthly.copy()
        fig2 = px.line(monthly, x="Month_Name", y="Sales", markers=True, title="Monthly Sales Trend")
        fig2.update_layout(height=420, xaxis_title="", yaxis_title="Provisional Revenue")
        st.plotly_chart(fig2, use_container_width=True)

    if len(top_product) > 0 and len(top_branch) > 0 and len(peak_month) > 0:
        share = top_product.iloc[0] / total_sales * 100 if total_sales else np.nan
        st.markdown(
            f"""
            <div class="insight-box">
            <div class="section-title">Executive read-out</div>
            <div class="metric-caption">
            The filtered portfolio view contains <b>{total_txn:,}</b> transactions and <b>{human_money(total_sales)}</b> in provisional revenue.
            <b>{top_product.index[0]}</b> is the current revenue leader, contributing <b>{share:.1f}% </b>of total filtered revenue.
            The strongest branch by value is <b>{top_branch.index[0]}</b>, while <b>{peak_month.index[0]}</b> is the highest-revenue month in the current selection.
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def customer_intelligence(df):
    st.markdown("### Customer Intelligence")
    col1, col2 = st.columns(2)

    with col1:
        customer_summary = df.groupby("Customer type", as_index=False).agg(
            Transactions=("Sales", "size"),
            Total_Sales=("Sales", "sum"),
            Avg_Sales=("Sales", "mean"),
            Median_Sales=("Sales", "median")
        )
        fig = px.bar(customer_summary, x="Customer type", y="Avg_Sales", color="Customer type",
                     title="Average Transaction Value by Customer Type", text_auto=".2f")
        fig.update_layout(height=380, showlegend=False, xaxis_title="", yaxis_title="Average Transaction Value")
        st.plotly_chart(fig, use_container_width=True)

        groups = [g["Sales"].values for _, g in df.groupby("Customer type")]
        if len(groups) == 2 and all(len(g) > 0 for g in groups):
            stat, p = stats.mannwhitneyu(groups[0], groups[1], alternative="two-sided")
            st.caption(f"Mann-Whitney U p-value: {p:.4f}")

    with col2:
        pay_summary = df.groupby("Payment", as_index=False).agg(
            Transactions=("Sales", "size"),
            Avg_Sales=("Sales", "mean"),
            Total_Sales=("Sales", "sum")
        ).sort_values("Avg_Sales", ascending=False)
        fig = px.bar(pay_summary, x="Payment", y="Avg_Sales", color="Payment",
                     title="Average Transaction Value by Payment Method", text_auto=".2f")
        fig.update_layout(height=380, showlegend=False, xaxis_title="", yaxis_title="Average Transaction Value")
        st.plotly_chart(fig, use_container_width=True)

    mix = pd.pivot_table(df, index="Gender", columns="Product line", values="Sales", aggfunc="sum", fill_value=0)
    if not mix.empty:
        mix = mix.reset_index().melt(id_vars="Gender", var_name="Product line", value_name="Sales")
        fig3 = px.bar(mix, x="Gender", y="Sales", color="Product line", title="Sales Mix by Gender and Product Line")
        fig3.update_layout(height=420, xaxis_title="", yaxis_title="Provisional Revenue", legend_title="")
        st.plotly_chart(fig3, use_container_width=True)

    member_avg = df.loc[df["Customer type"] == "Member", "Sales"].mean()
    normal_avg = df.loc[df["Customer type"] == "Normal", "Sales"].mean()
    if pd.notna(member_avg) and pd.notna(normal_avg) and normal_avg != 0:
        lift = (member_avg - normal_avg) / normal_avg * 100
        top_payment = df.groupby("Payment")["Sales"].mean().sort_values(ascending=False).index[0]
        st.markdown(
            f"""
            <div class="insight-box">
            <div class="section-title">Customer insight panel</div>
            <div class="metric-caption">
            Members spend <b>{lift:.1f}%</b> more per transaction than non-members in the current filtered view.
            <b>{top_payment}</b> produces the highest average transaction value among payment methods.
            Gender differences appear more clearly in product mix than in overall revenue totals.
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def product_performance(df):
    st.markdown("### Product & Performance")
    col1, col2 = st.columns(2)

    with col1:
        summary = df.groupby("Product line", as_index=False).agg(
            Revenue=("Sales", "sum"),
            Avg_Rating=("Rating", "mean"),
            Transactions=("Sales", "size")
        ).sort_values("Revenue", ascending=False)
        fig = px.bar(summary, x="Product line", y="Revenue", color="Revenue",
                     title="Product Line Revenue Ranking", text_auto=".2s")
        fig.update_layout(height=380, xaxis_title="", yaxis_title="Provisional Revenue", coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        summary2 = summary.sort_values("Avg_Rating", ascending=False)
        fig2 = px.bar(summary2, x="Product line", y="Avg_Rating", color="Avg_Rating",
                      title="Average Rating by Product Line", text_auto=".2f")
        fig2.update_layout(height=380, xaxis_title="", yaxis_title="Average Rating", coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    heat = pd.pivot_table(df, index="Month_Name", columns="Product line", values="Sales", aggfunc="sum", fill_value=0)
    month_order = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    heat = heat.reindex([m for m in month_order if m in heat.index])
    if not heat.empty:
        fig3 = px.imshow(heat, text_auto=".0f", aspect="auto", title="Seasonality Heatmap: Revenue by Product Line and Month")
        fig3.update_layout(height=450, xaxis_title="", yaxis_title="")
        st.plotly_chart(fig3, use_container_width=True)

    if not summary.empty:
        top = summary.iloc[0]
        low = summary.iloc[-1]
        best_rating = summary.sort_values("Avg_Rating", ascending=False).iloc[0]
        st.markdown(
            f"""
            <div class="insight-box">
            <div class="section-title">Category strategy note</div>
            <div class="metric-caption">
            <b>{top['Product line']}</b> is the top revenue category, while <b>{best_rating['Product line']}</b> leads on customer rating.
            The lowest-revenue category in the current view is <b>{low['Product line']}</b>, which makes it a candidate for closer assortment and promotion review.
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

def deep_dive(df):
    st.markdown("### Deep Dive Analysis")
    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(df, x="Sales", nbins=30, title="Distribution of Transaction Size")
        fig.update_layout(height=360, xaxis_title="Provisional Revenue per Transaction", yaxis_title="Frequency")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if len(df) >= 3:
            slope, intercept = np.polyfit(df["Rating"], df["Sales"], 1)
            fig2 = px.scatter(df, x="Rating", y="Sales", opacity=0.35, title="Rating vs Spending")
            xvals = np.array([df["Rating"].min(), df["Rating"].max()])
            fig2.add_trace(go.Scatter(x=xvals, y=intercept + slope * xvals, mode="lines", name="Trend"))
            fig2.update_layout(height=360)
            st.plotly_chart(fig2, use_container_width=True)
            pearson_r, pearson_p = stats.pearsonr(df["Rating"], df["Sales"])
            spearman_r, spearman_p = stats.spearmanr(df["Rating"], df["Sales"])
            st.caption(f"Pearson r={pearson_r:.3f} (p={pearson_p:.4f}) | Spearman rho={spearman_r:.3f} (p={spearman_p:.4f})")

    branch = df.groupby("Branch", as_index=False).agg(
        Revenue=("Sales", "sum"),
        Avg_Transaction=("Sales", "mean"),
        Avg_Rating=("Rating", "mean"),
        Transactions=("Sales", "size")
    ).sort_values("Revenue", ascending=False)
    st.dataframe(branch, use_container_width=True)

    q = branch.copy()
    if not q.empty:
        q["Revenue_Flag"] = np.where(q["Revenue"] >= q["Revenue"].median(), "High Revenue", "Low Revenue")
        q["Rating_Flag"] = np.where(q["Avg_Rating"] >= q["Avg_Rating"].median(), "High Rating", "Low Rating")
        fig4 = px.scatter(
            q, x="Revenue", y="Avg_Rating", size="Transactions", color="Branch",
            text="Branch", title="Branch Positioning: Revenue vs Rating"
        )
        fig4.update_traces(textposition="top center")
        fig4.update_layout(height=420)
        st.plotly_chart(fig4, use_container_width=True)


def executive_report_download(df):
    st.markdown("### Executive Report")
    col1, col2 = st.columns((1.2, 1))
    with col1:
        st.markdown(
            """
            <div class="insight-box">
            <div class="section-title">Downloadable executive PDF</div>
            <div class="metric-caption">
            This report consolidates the analytical outputs, key visuals, interpretations, and strategic recommendations
            into a presentation-ready PDF for stakeholders, supervisors, or hiring managers.
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        summary = df.groupby("Product line", as_index=False)["Sales"].sum().sort_values("Sales", ascending=False)
        top_product = summary.iloc[0]["Product line"] if len(summary) else "n/a"
        total_sales = df["Sales"].sum()
        member_avg = df.loc[df["Customer type"] == "Member", "Sales"].mean()
        normal_avg = df.loc[df["Customer type"] == "Normal", "Sales"].mean()
        lift = ((member_avg - normal_avg) / normal_avg * 100) if pd.notna(member_avg) and pd.notna(normal_avg) and normal_avg != 0 else np.nan

        st.markdown(
            f"""
            <div class="insight-box">
            <div class="section-title">Recommendation snapshot</div>
            <div class="metric-caption">
            1. Prioritize inventory and promotions around <b>{top_product}</b>, currently the top revenue category.<br>
            2. Strengthen member-focused offers because members show higher transaction values where that segment is active.<br>
            3. Use seasonal planning and branch-level benchmarking to align staffing, stock, and promotions with demand patterns.
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        if REPORT_PATH.exists():
            with open(REPORT_PATH, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="Download Executive PDF Report",
                data=pdf_bytes,
                file_name="Kabzozo_Supermarket_Executive_Report.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            st.caption("Includes executive summary, analytical findings, visuals, and strategic recommendations.")
        else:
            st.warning("Executive PDF report file not found in outputs folder.")


def data_audit(df, date_range):
    st.markdown("### Data Audit & Download Center")
    q1, q3 = df["Sales"].quantile([0.25, 0.75])
    iqr = q3 - q1
    outliers = ((df["Sales"] < (q1 - 1.5 * iqr)) | (df["Sales"] > (q3 + 1.5 * iqr))).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows in Filtered View", f"{len(df):,}")
    c2.metric("Missing Values", int(df.isna().sum().sum()))
    c3.metric("Duplicate Rows", int(df.duplicated().sum()))
    c4.metric("IQR Sales Outliers", int(outliers))

    audit = pd.DataFrame({
        "Metric": ["Date start", "Date end", "Coverage days", "Mean sales", "Median sales", "Skewness"],
        "Value": [
            str(date_range[0]), str(date_range[1]),
            df["Date"].nunique(),
            round(df["Sales"].mean(), 2),
            round(df["Sales"].median(), 2),
            round(df["Sales"].skew(), 3)
        ]
    })
    st.dataframe(audit, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered dataset as CSV", data=csv, file_name="filtered_supermarket_sales.csv", mime="text/csv")

def main():
    style()
    df = load_data()

    st.markdown("""
    <div class="hero-card">
        <h2 style="margin:0;">Retail Performance Intelligence Dashboard</h2>
        <p style="margin:0.35rem 0 0 0;">
        A decision-focused retail intelligence dashboard designed to uncover revenue drivers, customer behavior patterns, and growth opportunities from real transaction data.
        The app combines data auditing, KPI monitoring, customer intelligence, category strategy, seasonality, and decision-focused interpretation.
        </p>
        <h4 style="margin:0;">Created by Powell A. Ndlovu</h4>
    </div>
    """, unsafe_allow_html=True)

    filtered_df, date_range = filtered_data(df)
    if filtered_df.empty:
        st.warning("The current filter selection returns no rows. Broaden the filters to continue.")
        st.stop()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Executive Overview", "Customer Intelligence", "Product & Performance",
        "Deep Dive Analysis", "Data Audit", "Executive Report"
    ])

    with tab1:
        executive_summary(filtered_df)
    with tab2:
        customer_intelligence(filtered_df)
    with tab3:
        product_performance(filtered_df)
    with tab4:
        deep_dive(filtered_df)
    with tab5:
        data_audit(filtered_df, date_range)
    with tab6:
        executive_report_download(filtered_df)

if __name__ == "__main__":
    main()
