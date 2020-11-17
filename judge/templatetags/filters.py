from typing import Optional

from django import template
from mistune import create_markdown

register = template.Library()


@register.filter
def percentage(value: Optional[float]) -> str:
    if value is None:
        return "0%"

    return f"{value:.0%}"


render_markdown = create_markdown()


@register.filter
def markdown(value: str) -> str:
    return render_markdown(value)
