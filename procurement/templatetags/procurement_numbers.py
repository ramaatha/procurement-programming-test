# filepath: procurement/templatetags/procurement_numbers.py
from django import template
from common.numbers import format_money,format_quantity_display

register=template.Library()


def _localized(value: str) -> str:
    whole,fraction=value.split('.')
    return f'{int(whole):,}'.replace(',','.')+','+fraction


@register.filter
def money_id(value: int) -> str:return _localized(format_money(value))


@register.filter
def quantity_id(value: int) -> str:return format_quantity_display(value)
