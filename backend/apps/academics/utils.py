from django.utils import timezone


def get_current_academic_year_label(start_month=9):
    """
    Return the current academic year label as YYYY/YYYY+1.
    Example in April 2026 -> 2025/2026 when start_month is September.
    """
    today = timezone.localdate()
    if today.month >= start_month:
        start_year = today.year
        end_year = today.year + 1
    else:
        start_year = today.year - 1
        end_year = today.year
    return f"{start_year}/{end_year}"

