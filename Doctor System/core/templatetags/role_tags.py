from django import template
from core.decorators import get_user_role

register = template.Library()

@register.filter
def user_role(user):
    return get_user_role(user)
