from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Fulfillment Analytics",
    page_icon="📦",
    layout="wide",
)

DATA_PATH = Path(__file__).resolve().parent / "data" / "order_analysis.csv"

st.title("📦 Ecommerce Fulfillment Analytics")
st.caption(
    "Portfolio project • Simulated data • "
    "On time means shipped within 48 elapsed hours of payment."
)

if not DATA_PATH.exists():
    st.error("Run analyze_data.py first to create order_analysis.csv.")
    st.stop()

df = pd.read_csv(DATA_PATH)

# Convert CSV boolean values explicitly.
for column in ["stock_issue", "shipped_on_time"]:
    values = df[column].astype(str).str.lower()
    df[column] = values.map({"true": True, "false": False})

    if df[column].isna().any():
        st.error(f"Unexpected values in {column}. Check the source file.")
        st.stop()

# Sidebar filters.
st.sidebar.header("Filter orders")

warehouses = st.sidebar.multiselect(
    "Warehouse",
    options=sorted(df["warehouse"].unique()),
    default=sorted(df["warehouse"].unique()),
)

categories = st.sidebar.multiselect(
    "Product category",
    options=sorted(df["category"].unique()),
    default=sorted(df["category"].unique()),
)

stock_filter = st.sidebar.selectbox(
    "Stock status",
    ["All orders", "With stock issues", "Without stock issues"],
)

filtered = df[
    df["warehouse"].isin(warehouses)
    & df["category"].isin(categories)
].copy()

if stock_filter == "With stock issues":
    filtered = filtered[filtered["stock_issue"]]
elif stock_filter == "Without stock issues":
    filtered = filtered[~filtered["stock_issue"]]

if filtered.empty:
    st.info("No orders match these filters. Adjust your selections.")
    st.stop()

st.sidebar.caption(f"Showing {len(filtered):,} of {len(df):,} orders")

# Every metric uses the filtered data.
total_orders = len(filtered)
late_orders = int((~filtered["shipped_on_time"]).sum())
on_time_rate = filtered["shipped_on_time"].mean() * 100
average_hours = filtered["fulfillment_hours"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total orders", f"{total_orders:,}")
col2.metric("On time shipments", f"{on_time_rate:.1f}%")
col3.metric("Late shipments", f"{late_orders:,}")
col4.metric("Average fulfillment", f"{average_hours:.1f} hrs")

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Where orders spend time")

    stage_columns = {
        "packing_wait_hours": "Waiting for packing",
        "packing_hours": "Packing",
        "shipping_wait_hours": "Waiting for shipment",
    }

    stages = (
        filtered[list(stage_columns)]
        .mean()
        .rename(index=stage_columns)
        .rename_axis("Stage")
        .reset_index(name="Average hours")
    )

    fig = px.bar(
        stages,
        x="Average hours",
        y="Stage",
        orientation="h",
        text="Average hours",
        color_discrete_sequence=["#2563EB"],
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="auto")
    fig.update_layout(
        yaxis={"autorange": "reversed"},
        xaxis_title="Average elapsed hours",
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Late shipments by warehouse")

    warehouse_summary = (
        filtered.groupby("warehouse")
        .agg(
            orders=("order_id", "count"),
            on_time_rate=("shipped_on_time", "mean"),
        )
        .reset_index()
    )
    warehouse_summary["Late rate (%)"] = (
        1 - warehouse_summary["on_time_rate"]
    ) * 100

    fig = px.bar(
        warehouse_summary,
        x="warehouse",
        y="Late rate (%)",
        text="Late rate (%)",
        hover_data=["orders"],
        color_discrete_sequence=["#F97316"],
    )
    fig.update_traces(texttemplate="%{text:.1f}%")
    fig.update_layout(xaxis_title=None, yaxis_range=[0, 105])
    st.plotly_chart(fig, use_container_width=True)

st.subheader("How long does fulfillment take?")

fig = px.histogram(
    filtered,
    x="fulfillment_hours",
    nbins=35,
    color_discrete_sequence=["#14B8A6"],
    labels={"fulfillment_hours": "Fulfillment time (hours)"},
)
fig.add_vline(
    x=48,
    line_dash="dash",
    line_color="red",
    annotation_text="48 hour shipping deadline",
)
fig.update_layout(yaxis_title="Number of orders")
st.plotly_chart(fig, use_container_width=True)

st.subheader("Stock issues and late shipments")

stock_summary = (
    filtered.groupby("stock_issue")
    .agg(
        orders=("order_id", "count"),
        avg_fulfillment_hours=("fulfillment_hours", "mean"),
        on_time_rate=("shipped_on_time", "mean"),
    )
    .reset_index()
)

stock_summary["Stock status"] = stock_summary["stock_issue"].map(
    {True: "With stock issues", False: "Without stock issues"}
)
stock_summary["Late rate (%)"] = (
    1 - stock_summary["on_time_rate"]
) * 100

st.dataframe(
    stock_summary[
        ["Stock status", "orders", "avg_fulfillment_hours", "Late rate (%)"]
    ].rename(
        columns={
            "orders": "Orders",
            "avg_fulfillment_hours": "Average fulfillment hours",
        }
    ).round(1),
    hide_index=True,
    use_container_width=True,
)

late_with_stock = int(
    ((~filtered["shipped_on_time"]) & filtered["stock_issue"]).sum()
)

if late_orders:
    st.info(
        f"In this selection, {late_with_stock:,} of {late_orders:,} "
        f"late orders had stock issues "
        f"({late_with_stock / late_orders * 100:.1f}%). "
        "This describes an association in simulated data."
    )

with st.expander("Explore individual orders"):
    display_columns = [
        "order_id",
        "warehouse",
        "category",
        "stock_issue",
        "packing_wait_hours",
        "packing_hours",
        "shipping_wait_hours",
        "fulfillment_hours",
        "shipped_on_time",
    ]
    st.dataframe(
        filtered[display_columns].round(2),
        hide_index=True,
        use_container_width=True,
    )

st.download_button(
    "Download filtered order data",
    data=filtered.to_csv(index=False).encode("utf-8"),
    file_name="filtered_orders.csv",
    mime="text/csv",
)

st.caption(
    "Scope: 1,000 simulated completed orders. "
    "Inventory, warehouse, and category delay patterns were built "
    "into the generator. Findings are not real company results."
)