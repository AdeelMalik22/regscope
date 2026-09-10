"""Small SQLite-backed API for manually exercising RegScope.

Run with:

    python main.py

Then open http://127.0.0.1:8000/report. The tracked report function writes
profiles and baselines to ``.regscope-demo``.
"""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from time import perf_counter
from typing import Any

from regscope import track


DATABASE = ":memory:"
HOST = "127.0.0.1"
PORT = 8000


def create_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        PRAGMA journal_mode = MEMORY;
        PRAGMA synchronous = OFF;
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            region TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX orders_customer_id_idx ON orders(customer_id);
        CREATE INDEX orders_status_idx ON orders(status);
        """
    )

    customers = [
        (customer_id, f"Customer {customer_id}", f"region-{customer_id % 8}")
        for customer_id in range(1, 501)
    ]
    connection.executemany(
        "INSERT INTO customers (id, name, region) VALUES (?, ?, ?)", customers
    )

    orders = []
    for order_id in range(1, 50_001):
        customer_id = ((order_id - 1) % 500) + 1
        amount = ((order_id * 37) % 1_000_00) / 100
        status = ("paid", "pending", "cancelled")[order_id % 3]
        created_at = f"2026-{(order_id % 12) + 1:02d}-{(order_id % 28) + 1:02d}"
        orders.append((order_id, customer_id, amount, status, created_at))

    connection.executemany(
        """
        INSERT INTO orders (id, customer_id, amount, status, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        orders,
    )
    connection.commit()
    return connection


@track(baseline_dir=".regscope-demo", warmup_runs=1)
def heavy_customer_report(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Run an aggregate query with joins, filtering, ranking, and recursion."""
    query = """
        WITH RECURSIVE months(month_number) AS (
            SELECT 1
            UNION ALL
            SELECT month_number + 1 FROM months WHERE month_number < 12
        ), monthly_orders AS (
            SELECT
                customer_id,
                CAST(substr(created_at, 6, 2) AS INTEGER) AS month_number,
                COUNT(*) AS order_count,
                ROUND(SUM(amount), 2) AS revenue
            FROM orders
            WHERE status = 'paid'
            GROUP BY customer_id, month_number
        ), ranked_customers AS (
            SELECT
                customers.region,
                customers.id,
                customers.name,
                SUM(monthly_orders.order_count) AS order_count,
                ROUND(SUM(monthly_orders.revenue), 2) AS revenue,
                RANK() OVER (
                    PARTITION BY customers.region
                    ORDER BY SUM(monthly_orders.revenue) DESC
                ) AS regional_rank
            FROM customers
            JOIN monthly_orders ON monthly_orders.customer_id = customers.id
            JOIN months ON months.month_number = monthly_orders.month_number
            GROUP BY customers.region, customers.id, customers.name
        )
        SELECT region, id, name, order_count, revenue, regional_rank
        FROM ranked_customers
        WHERE regional_rank <= 5
        ORDER BY revenue DESC, id
    """
    return [dict(row) for row in connection.execute(query)]


class DemoHandler(BaseHTTPRequestHandler):
    connection: sqlite3.Connection

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        started = perf_counter()
        if self.path == "/health":
            self.send_json({"status": "ok"})
            return
        if self.path == "/report":
            rows = heavy_customer_report(self.connection)
            profile = heavy_customer_report.get_current_profile()
            self.send_json(
                {
                    "rows": rows,
                    "row_count": len(rows),
                    "request_seconds": round(perf_counter() - started, 6),
                    "regscope": {
                        "duration_ns": profile.duration_ns if profile else None,
                        "exceptions": profile.exceptions if profile else None,
                        "call_graph": profile.call_graph if profile else {},
                    },
                }
            )
            return
        self.send_json({"error": "try /health or /report"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{self.log_date_time_string}] {format % args}")


def main() -> None:
    connection = create_database()

    class BoundDemoHandler(DemoHandler):
        pass

    BoundDemoHandler.connection = connection
    server = ThreadingHTTPServer((HOST, PORT), BoundDemoHandler)
    print(f"RegScope SQLite demo listening at http://{HOST}:{PORT}")
    print("Try /health and /report; press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping demo server.")
    finally:
        server.server_close()
        connection.close()


if __name__ == "__main__":
    main()
