from pathlib import Path
import pandas as pd

data_folder = Path(__file__).resolve().parent / "data"

orders = pd.read_csv(data_folder / "orders.csv")
events = pd.read_csv(data_folder / "events.csv")

events["timestamp"] = pd.to_datetime(
    events["timestamp"], errors="coerce"
)

expected_steps = [
    "Order placed",
    "Payment confirmed",
    "Packing started",
    "Packing completed",
    "Order shipped",
    "Order delivered",
]

# Check identifiers, missing values, and repeated events.
assert not orders.isna().any().any(), "Missing order data"
assert not events.isna().any().any(), "Missing or invalid event data"
assert orders["order_id"].is_unique, "Duplicate order IDs"
assert not events.duplicated(
    ["order_id", "activity"]
).any(), "Repeated events"

assert set(events["order_id"]) == set(orders["order_id"]), (
    "Order IDs do not match between files"
)

assert set(events["activity"]) == set(expected_steps), (
    "Unexpected or missing activities"
)

# Turn the event log into one row per order.
timeline = events.pivot(
    index="order_id",
    columns="activity",
    values="timestamp",
)[expected_steps]

assert not timeline.isna().any().any(), "An order is missing a step"

# Confirm every step happens after the previous one.
for previous, current in zip(expected_steps, expected_steps[1:]):
    assert (timeline[current] >= timeline[previous]).all(), (
        f"Incorrect sequence: {previous} to {current}"
    )

print("All data quality checks passed.")
print(f"Validated {len(orders):,} orders and {len(events):,} events.")
print("\nFirst 5 order timelines:")
print(timeline.head().to_string())

# Calculate the time spent at each fulfillment stage.
timeline["packing_wait_hours"] = (
    timeline["Packing started"] - timeline["Payment confirmed"]
).dt.total_seconds() / 3600

timeline["packing_hours"] = (
    timeline["Packing completed"] - timeline["Packing started"]
).dt.total_seconds() / 3600

timeline["shipping_wait_hours"] = (
    timeline["Order shipped"] - timeline["Packing completed"]
).dt.total_seconds() / 3600

timeline["fulfillment_hours"] = (
    timeline["Order shipped"] - timeline["Payment confirmed"]
).dt.total_seconds() / 3600

# Exactly 48 hours counts as on time.
timeline["shipped_on_time"] = timeline["fulfillment_hours"] <= 48

# Combine order details with the calculated metrics.
analysis = orders.merge(
    timeline.reset_index(),
    on="order_id",
    how="left",
    validate="one_to_one",
)

total_orders = len(analysis)
on_time_rate = analysis["shipped_on_time"].mean() * 100
late_orders = (~analysis["shipped_on_time"]).sum()

print("\nFULFILLMENT KPIs")
print(f"Total orders: {total_orders:,}")
print(f"On time shipment rate: {on_time_rate:.1f}%")
print(f"Late shipments: {late_orders:,}")
print(
    f"Average fulfillment time: "
    f"{analysis['fulfillment_hours'].mean():.1f} hours"
)
print(
    f"Median fulfillment time: "
    f"{analysis['fulfillment_hours'].median():.1f} hours"
)

print("\nAVERAGE TIME BY STAGE")
stage_columns = [
    "packing_wait_hours",
    "packing_hours",
    "shipping_wait_hours",
]
print(analysis[stage_columns].mean().round(1))

# Keep full precision in the saved data.
analysis.to_csv(data_folder / "order_analysis.csv", index=False)
print("\nSaved order_analysis.csv")


# Compare performance across different groups.
for column in ["warehouse", "category", "stock_issue"]:
    summary = analysis.groupby(column).agg(
        orders=("order_id", "count"),
        avg_packing_wait_hours=("packing_wait_hours", "mean"),
        avg_fulfillment_hours=("fulfillment_hours", "mean"),
        on_time_rate=("shipped_on_time", "mean"),
    )

    summary["late_rate_pct"] = (1 - summary["on_time_rate"]) * 100
    summary = summary.drop(columns="on_time_rate")
    summary = summary.sort_values("late_rate_pct", ascending=False)

    print(f"\nPERFORMANCE BY {column.upper()}")
    print(summary.round(1).to_string())

    summary.to_csv(data_folder / f"summary_by_{column}.csv")

    # Compare warehouses within each stock condition.
warehouse_stock = analysis.groupby(
    ["warehouse", "stock_issue"]
).agg(
    orders=("order_id", "count"),
    avg_packing_wait_hours=("packing_wait_hours", "mean"),
    avg_fulfillment_hours=("fulfillment_hours", "mean"),
    on_time_rate=("shipped_on_time", "mean"),
)

warehouse_stock["late_rate_pct"] = (
    1 - warehouse_stock["on_time_rate"]
) * 100

warehouse_stock = warehouse_stock.drop(columns="on_time_rate")

print("\nWAREHOUSE PERFORMANCE BY STOCK CONDITION")
print(warehouse_stock.round(1).to_string())

# Count how many late orders had stock issues.
late_orders_df = analysis.loc[~analysis["shipped_on_time"]]
late_with_stock_issue = late_orders_df["stock_issue"].sum()
total_late = len(late_orders_df)

print("\nSTOCK ISSUES AMONG LATE ORDERS")
print(f"Total late orders: {total_late}")
print(f"Late orders with stock issues: {late_with_stock_issue}")

if total_late > 0:
    share = late_with_stock_issue / total_late * 100
    print(f"Share of late orders with stock issues: {share:.1f}%")

warehouse_stock.to_csv(
    data_folder / "warehouse_stock_comparison.csv"
)