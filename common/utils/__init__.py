from calendar import monthrange
from datetime import date, timedelta

from django.core.cache import cache
from django.utils import timezone


def resolve_period(request, *, default="14d"):
    today = timezone.localdate()
    period = (request.GET.get("period") or default).strip().lower()
    year = request.GET.get("year")
    month = request.GET.get("month")
    start = request.GET.get("start")
    end = request.GET.get("end")

    if period == "today":
        start_date, end_date = today, today
        label = "اليوم"
    elif period == "7d":
        start_date, end_date = today - timedelta(days=6), today
        label = "آخر 7 أيام"
    elif period == "14d":
        start_date, end_date = today - timedelta(days=13), today
        label = "آخر 14 يوم"
    elif period == "month":
        try:
            y = int(year) if year else today.year
            m = int(month) if month else today.month
            last_day = monthrange(y, m)[1]
            start_date, end_date = date(y, m, 1), date(y, m, last_day)
            label = "هذا الشهر"
        except Exception:
            start_date, end_date = today - timedelta(days=29), today
            period = "30d"
            label = "آخر 30 يوم"
    elif period == "year":
        try:
            y = int(year) if year else today.year
            start_date, end_date = date(y, 1, 1), date(y, 12, 31)
            label = "هذه السنة"
        except Exception:
            start_date, end_date = date(today.year, 1, 1), today
            label = "هذه السنة"
    elif period == "custom":
        try:
            start_date = date.fromisoformat(str(start))
            end_date = date.fromisoformat(str(end))
            if end_date < start_date:
                start_date, end_date = end_date, start_date
            label = "فترة مخصصة"
        except Exception:
            start_date, end_date = today - timedelta(days=13), today
            period = "14d"
            label = "آخر 14 يوم"
    else:
        start_date, end_date = today - timedelta(days=13), today
        period = "14d"
        label = "آخر 14 يوم"

    period_len_days = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_len_days - 1)

    return {
        "period": period,
        "label": label,
        "start": start_date,
        "end": end_date,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "year": int(year) if str(year).isdigit() else start_date.year,
        "month": int(month) if str(month).isdigit() else start_date.month,
    }


def _cache_incr(key: str, *, default=1) -> int:
    try:
        return cache.incr(key)
    except Exception:
        cache.set(key, default, None)
        return default


def bump_project_version(project_id):
    _cache_incr(f"ver:project:{project_id}")
    _cache_incr("ver:global_admin")


def bump_user_version(user_id):
    _cache_incr(f"ver:user:{user_id}")


def get_user_version(user):
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return cache.get("ver:global_admin", 0) or 0
    return cache.get(f"ver:user:{user.pk}", 0) or 0


def get_project_version(project_id):
    return cache.get(f"ver:project:{project_id}", 0) or 0
