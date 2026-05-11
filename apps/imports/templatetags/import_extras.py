from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def get_item(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key, "")
    return ""


@register.filter
def numfmt(value, decimals="auto"):
    if value is None or value == "":
        return ""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    sign = "-" if d < 0 else ""
    d = abs(d)

    if decimals is None or decimals == "":
        decimals = "auto"
    decimals = str(decimals).strip().lower()

    if decimals == "auto":
        q = d.quantize(Decimal("1")) if d == d.to_integral_value() else d.quantize(Decimal("0.01"))
        s = format(q, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
    else:
        try:
            dec_n = int(decimals)
        except ValueError:
            dec_n = 0
        if dec_n <= 0:
            s = format(d.quantize(Decimal("1")), "f")
        else:
            s = format(d.quantize(Decimal("1." + ("0" * dec_n))), "f")

    if "." in s:
        int_part, frac = s.split(".", 1)
    else:
        int_part, frac = s, ""

    try:
        int_part_fmt = f"{int(int_part):,}"
    except ValueError:
        int_part_fmt = int_part

    return f"{sign}{int_part_fmt}" + (f".{frac}" if frac else "")
