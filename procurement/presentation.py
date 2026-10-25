# filepath: procurement/presentation.py
from common.numbers import format_quantity_display
from procurement.models import PurchaseOrder
from procurement.selectors import order_balances


def balance_rows(order: PurchaseOrder) -> list[dict]:
    balances = order_balances(order)
    rows = []
    for item in order.items.all():
        balance = balances[item.pk]
        rejected = balance['rejected_milli']
        # A historical total can exceed the int64 bound of a single stored line.
        rows.append(dict(item=item,ordered=format_quantity_display(balance['ordered_milli']),
                         accepted=format_quantity_display(balance['accepted_milli']),remaining=format_quantity_display(balance['remaining_milli']),
                         rejected=format_quantity_display(rejected)))
    return rows
