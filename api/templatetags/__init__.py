from django import template
from django.utils.safestring import mark_safe
from api.models.abstract.soft_delete_model import SoftDeleteModel

register = template.Library()

@register.filter
def selected_soft_delete_list(to_delete: SoftDeleteModel):
    html = """
        <ul>
    """
    for item in to_delete[0]:
        if type(item) is list:
            continue
        html += f'<li>{item}</li>'
    html += """
        </ul>
    """
    return mark_safe(html)
