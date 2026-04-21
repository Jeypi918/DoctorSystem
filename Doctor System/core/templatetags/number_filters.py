from django import template

register = template.Library()

@register.filter
def abbreviate_number(value, default='0'):
    """
    Formats large numbers to abbreviated form:
    - < 1,000: full number (e.g., 999)
    - 1,000 - 999,999: xk (e.g., 21.6k for 21652)
    - 1,000,000+: xM (e.g., 1.2M)
    """
    try:
        num = float(value)
        if num < 1000:
            return f'{int(num):,}' if num.is_integer() else f'{num:,.1f}'
        elif num < 1000000:
            return f'{num/1000:.1f}k'
        else:
            return f'{num/1000000:.1f}M'
    except (ValueError, TypeError):
        return default

