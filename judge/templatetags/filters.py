from django import template

register = template.Library()


@register.filter
def percentage(value: float) -> str:
    return f"{value:.0%}"
