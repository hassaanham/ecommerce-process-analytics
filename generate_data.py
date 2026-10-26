from pathlib import Path
import random

import pandas as pd

# A fixed seed makes our results repeatable.
rng = random.Random(42)

# Save data beside this script.
data_folder = Path(__file__).resolve().parent / "data"
data_folder.mkdir(exist_ok=True)

orders = []
events = []

for number in range(1, 1001):
    order_id = f"ORD-{number:04d}"
    category = rng.choice(["Home Decor", "Lighting", "Accessories"])
    warehouse = rng.choice(["Chicago", "Dallas", "Atlanta"])

    placed_at = pd.Timestamp("2026-07-01") + pd.Timedelta(
        minutes=rng.randint(0, 90 * 24 * 60 - 1)
    )
    paid_at = placed_at + pd.Timedelta(minutes=rng.randint(1, 30))

    # Simulated inventory and workload conditions.
    stock_issue = rng.random() < 0.15
    queue_hours = rng.uniform(2, 24)

    if stock_issue:
        queue_hours += rng.uniform(24, 72)

    if warehouse == "Dallas":
        queue_hours += rng.uniform(5, 18)

    packing_started = paid_at + pd.Timedelta(hours=queue_hours)

    packing_hours = rng.uniform(1, 6)
    if category == "Lighting":
        packing_hours += rng.uniform(2, 8)

    packing_finished = packing_started + pd.Timedelta(hours=packing_hours)
    shipped_at = packing_finished + pd.Timedelta(hours=rng.uniform(2, 18))
    delivered_at = shipped_at + pd.Timedelta(hours=rng.uniform(24, 120))

    orders.append({
        "order_id": order_id,
        "category": category,
        "warehouse": warehouse,
        "order_value": round(rng.uniform(20, 250), 2),
        "stock_issue": stock_issue,
    })

    order_events = [
        ("Order placed", placed_at),
        ("Payment confirmed", paid_at),
        ("Packing started", packing_started),
        ("Packing completed", packing_finished),
        ("Order shipped", shipped_at),
        ("Order delivered", delivered_at),
    ]

    for activity, timestamp in order_events:
        events.append({
            "order_id": order_id,
            "activity": activity,
            "timestamp": timestamp,
        })

orders_df = pd.DataFrame(orders)
events_df = pd.DataFrame(events)

orders_df.to_csv(data_folder / "orders.csv", index=False)
events_df.to_csv(data_folder / "events.csv", index=False)

print(f"Created {len(orders_df):,} orders")
print(f"Created {len(events_df):,} events")
print(f"Saved to: {data_folder}")