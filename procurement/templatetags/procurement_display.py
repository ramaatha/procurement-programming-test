# filepath: procurement/templatetags/procurement_display.py
from django import template

from procurement.selectors import operational_stage
from procurement.stages import audit_label, stage_label

register = template.Library()
register.filter('stage_label',stage_label)
register.filter('audit_label',audit_label)


@register.filter
def request_stage(target):
    return stage_label(operational_stage(target))
