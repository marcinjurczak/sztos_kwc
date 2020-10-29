from typing import Optional

from django import template

register = template.Library()


@register.filter
def percentage(value: Optional[float]) -> str:
    if value is None:
        return "0%"

    return f"{value:.0%}"
