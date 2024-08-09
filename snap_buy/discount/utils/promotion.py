from collections.abc import Iterable
from typing import TYPE_CHECKING

from prices import Money

from snap_buy.core.taxes import zero_money

if TYPE_CHECKING:
    from snap_buy.discount.models import PromotionRule


def calculate_discounted_price_for_rules(
    *,
    price: Money,
    rules: Iterable["PromotionRule"],
    currency: str,
):
    """Calculate the discounted price for provided rules.

    The discounts from rules summed up and applied to the price.
    """
    total_discount = zero_money(currency)
    for rule in rules:
        discount = rule.get_discount(currency)
        total_discount += price - discount(price)

    return max(price - total_discount, zero_money(currency))
