from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def ph_money(value):
    """
    Format number as Philippine money: ₱ 1,234,567.89
    Handles None/empty as '—'
    """
    if value is None or value == '' or value == 0:
        return mark_safe('—')
    
    try:
        num = float(value)
        formatted = f"{num:,.2f}"
        return mark_safe(f'₱ {formatted}')
    except (ValueError, TypeError):
        return mark_safe('—')
