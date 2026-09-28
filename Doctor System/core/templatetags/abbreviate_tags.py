from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='abbrev')
def abbreviate(value):
    """
    Abbreviate large numbers: 1100 -> 1.1K, 65800 -> 65.8K, 1200000 -> 1.2M
    """
    try:
        n = float(value)
        if n < 1000:
            return f"{int(n):,}"
        elif n < 1000000:
            return f"{n/1000:.1f}K"
        else:
            return f"{n/1000000:.1f}M"
    except (ValueError, TypeError):
        return str(value)
