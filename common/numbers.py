# filepath: common/numbers.py
import re
from collections.abc import Iterable
from decimal import Decimal, ROUND_HALF_UP, localcontext

from django.core.exceptions import ValidationError

MAX_INT64 = 9223372036854775807


def _scaled(value: str, places: int, *, allow_zero: bool) -> int:
    if not isinstance(value, str) or len(value) > 24 or re.fullmatch(r'[0-9]+(?:\.[0-9]{1,' + str(places) + r'})?', value) is None:
        raise ValidationError('Gunakan angka biasa dengan titik desimal dan presisi yang sesuai.')
    whole, _, fraction = value.partition('.')
    result = int(whole) * 10**places + int(fraction.ljust(places, '0'))
    _integer(result, allow_zero=allow_zero)
    return result


def _integer(value: int, *, allow_zero: bool = True) -> None:
    if type(value) is not int or not (0 if allow_zero else 1) <= value <= MAX_INT64:
        raise ValidationError('Nilai tidak valid atau melebihi batas penyimpanan.')


def parse_quantity(value: str, *, allow_zero: bool = False) -> int:
    return _scaled(value, 3, allow_zero=allow_zero)


def parse_money(value: str) -> int:
    return _scaled(value, 2, allow_zero=False)


def line_total(qty_milli: int, unit_price_minor: int) -> int:
    _integer(qty_milli, allow_zero=False)
    _integer(unit_price_minor, allow_zero=False)
    with localcontext() as context:
        context.prec = 64
        result = int((Decimal(qty_milli) * Decimal(unit_price_minor) / 1000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    _integer(result)
    return result


def document_total(lines: Iterable[int]) -> int:
    total = 0
    for value in lines:
        _integer(value)
        total += value
        _integer(total)
    return total


def format_quantity(value: int) -> str:
    _integer(value)
    return f'{value // 1000}.{value % 1000:03d}'


def format_money(value: int) -> str:
    _integer(value)
    return f'{value // 100}.{value % 100:02d}'
