from pathlib import Path
import sqlite3

import pandas as pd

data_folder = Path(__file__).resolve().parent / "data"

orders = pd.read_csv(data_folder / "orders.csv")
events = pd.read_csv(data_folder / "events.csv")

with sqlite3.connect(data_folder / "ecommerce.db") as connection:
    # Reload our source data so the script can be run again.
    orders.to_sql("orders", connection, if_exists="replace", index=False)
    events.to_sql("events", connection, if_exists="replace", index=False)

    # Calculate fulfillment time directly from the original events.
    query = """
    WITH order_times AS (
        SELECT
            order_id,
            MAX(CASE
                WHEN activity = 'Payment confirmed' THEN timestamp
            END) AS paid_at,
            MAX(CASE
                WHEN activity = 'Order shipped' THEN timestamp
            END) AS shipped_at
        FROM events
        GROUP BY order_id
    ),
    durations AS (
        SELECT
            order_id,
            (julianday(shipped_at) - julianday(paid_at)) * 24.0
                AS fulfillment_hours
        FROM order_times
    )
    SELECT
        COUNT(*) AS total_orders,
        SUM(CASE
            WHEN fulfillment_hours > 48 THEN 1 ELSE 0
        END) AS late_orders,
        ROUND(
            100.0 * AVG(CASE
                WHEN fulfillment_hours <= 48 THEN 1.0 ELSE 0.0
            END), 1
        ) AS on_time_rate_pct,
        ROUND(AVG(fulfillment_hours), 1) AS avg_fulfillment_hours
    FROM durations;
    """

    results = pd.read_sql_query(query, connection)

    print("SQL FULFILLMENT KPIs")
    print(results.to_string(index=False))

    results.to_csv(data_folder / "sql_kpis.csv", index=False)

print("\nSaved ecommerce.db and sql_kpis.csv")

# Read and execute our separate SQL file.
query_path = Path(__file__).resolve().parent / "warehouse_analysis.sql"
warehouse_query = query_path.read_text(encoding="utf-8")

with sqlite3.connect(data_folder / "ecommerce.db") as connection:
    warehouse_results = pd.read_sql_query(
        warehouse_query, connection
    )

print("\nSQL WAREHOUSE PERFORMANCE BY STOCK CONDITION")
print(warehouse_results.to_string(index=False))

warehouse_results.to_csv(
    data_folder / "sql_warehouse_stock.csv", index=False
)

# Compare every group with the Python summary.
python_results = pd.read_csv(
    data_folder / "warehouse_stock_comparison.csv"
)
python_results["stock_issue"] = (
    python_results["stock_issue"].astype(int)
)

sort_columns = ["warehouse", "stock_issue"]
compare_columns = [
    "warehouse",
    "stock_issue",
    "orders",
    "avg_packing_wait_hours",
    "avg_fulfillment_hours",
    "late_rate_pct",
]

expected = (
    python_results[compare_columns]
    .sort_values(sort_columns)
    .reset_index(drop=True)
    .round(1)
)

actual = (
    warehouse_results[compare_columns]
    .sort_values(sort_columns)
    .reset_index(drop=True)
)

pd.testing.assert_frame_equal(
    actual,
    expected,
    check_dtype=False,
    check_exact=False,
    atol=0.000001,
    rtol=0,
)

print("\nPASS: All six SQL groups match Python at displayed precision.")