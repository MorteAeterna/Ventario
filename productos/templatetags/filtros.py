from django import template

register = template.Library()

@register.filter
def clp(value):
    try:
        return "{:,.0f}".format(int(value)).replace(",", ".")
    except:
        return value