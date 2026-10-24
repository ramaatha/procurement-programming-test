# filepath: scripts/browser/observe.py
"""Read-only state evidence for an explicitly marked, isolated E2E database."""
import json
import sqlite3
import sys
from pathlib import Path

database = Path(sys.argv[1]).resolve()
if not (database.parent / ".e2e-isolated").is_file():
    raise SystemExit("Refusing database without .e2e-isolated marker")
key = sys.argv[2].replace("-", "")
connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA query_only = ON")

def rows(table, column, values):
    if not values:
        return []
    columns = {row["name"] for row in connection.execute(f'PRAGMA table_info("{table}")')}
    if column not in columns:
        raise RuntimeError(f"Unknown observer column: {table}.{column}")
    placeholders = ",".join("?" for _ in values)
    return [dict(row) for row in connection.execute(
        f'SELECT * FROM "{table}" WHERE "{column}" IN ({placeholders}) ORDER BY id', values
    )]

state = {"request": rows("procurement_purchaserequest", "id", [key])}
for table in ("requestitem", "requestrevision", "purchaseorder", "auditevent"):
    state[table] = rows("procurement_" + table, "request_id", [key])
revisions = [row["id"] for row in state["requestrevision"]]
orders = [row["id"] for row in state["purchaseorder"]]
state["quotation"] = rows("procurement_quotation", "revision_id", revisions)
quotations = [row["id"] for row in state["quotation"]]
state["revisionitem"] = rows("procurement_revisionitem", "revision_id", revisions)
state["approvaldecision"] = rows("procurement_approvaldecision", "revision_id", revisions)
state["quotationitem"] = rows("procurement_quotationitem", "quotation_id", quotations)
state["purchaseorderitem"] = rows("procurement_purchaseorderitem", "order_id", orders)
state["receipt"] = rows("procurement_receipt", "order_id", orders)
state["receiptitem"] = rows("procurement_receiptitem", "receipt_id", [r["id"] for r in state["receipt"]])
print(json.dumps(state, sort_keys=True))
connection.close()
