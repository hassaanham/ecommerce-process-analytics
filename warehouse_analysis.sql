WITH order_times AS (
    SELECT
        order_id,
        MAX(CASE
            WHEN activity = 'Payment confirmed' THEN timestamp
        END) AS paid_at,
        MAX(CASE
            WHEN activity = 'Packing started' THEN timestamp
        END) AS packing_started_at,
        MAX(CASE
            WHEN activity = 'Order shipped' THEN timestamp
        END) AS shipped_at
    FROM events
    GROUP BY order_id
),
order_metrics AS (
    SELECT
        o.order_id,
        o.warehouse,
        o.stock_issue,
        (julianday(t.packing_started_at) - julianday(t.paid_at))
            * 24.0 AS packing_wait_hours,
        (julianday(t.shipped_at) - julianday(t.paid_at))
            * 24.0 AS fulfillment_hours
    FROM orders AS o
    JOIN order_times AS t
        ON o.order_id = t.order_id
)
SELECT
    warehouse,
    stock_issue,
    COUNT(*) AS orders,
    ROUND(AVG(packing_wait_hours), 1) AS avg_packing_wait_hours,
    ROUND(AVG(fulfillment_hours), 1) AS avg_fulfillment_hours,
    ROUND(
        100.0 * AVG(CASE
            WHEN fulfillment_hours > 48 THEN 1.0 ELSE 0.0
        END), 1
    ) AS late_rate_pct
FROM order_metrics
GROUP BY warehouse, stock_issue
ORDER BY warehouse, stock_issue;

