from collections.abc import Iterable
from typing import TYPE_CHECKING

from snap_buy.core.taxes import zero_taxed_money

if TYPE_CHECKING:
    from snap_buy.order.models import OrderLine


def get_subtotal(order_lines: Iterable["OrderLine"], fallback_currency: str):
    subtotal_iterator = (line.total_price for line in order_lines)
    return sum(subtotal_iterator, zero_taxed_money(currency=fallback_currency))
