import json
from decimal import ROUND_DOWN, Decimal
from typing import Any

from crypto_exchange.lib.constants import MAX_DIGITS_AFTER_DOT


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Decimal):
            return str(obj)
        return super(DecimalEncoder, self).default(obj)


def format_decimal(
    value: Decimal,
    max_digits: int = MAX_DIGITS_AFTER_DOT,
) -> str:
    quantized_value = value.quantize(
        Decimal("1." + "0" * max_digits),
        rounding=ROUND_DOWN,
    )
    return format(quantized_value, "f")
