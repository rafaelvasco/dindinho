"""Brazilian date parsing utilities."""

from datetime import date, datetime
from typing import Optional
import re


def parse_brazilian_date(date_string: str) -> Optional[date]:
    """
    Parse Brazilian date format (DD/MM/YYYY) to Python date object.

    Args:
        date_string: Date string in Brazilian format (e.g., "03/01/2026", "3/1/2026")

    Returns:
        datetime.date object or None if parsing fails

    Examples:
        >>> parse_brazilian_date("03/01/2026")
        datetime.date(2026, 1, 3)
        >>> parse_brazilian_date("31/12/2025")
        datetime.date(2025, 12, 31)
    """
    if not date_string or not isinstance(date_string, str):
        return None

    # Clean the string - remove leading/trailing whitespace
    date_string = date_string.strip()

    # Try parsing DD/MM/YYYY format
    patterns = [
        r"^(\d{1,2})/(\d{1,2})/(\d{4})$",  # DD/MM/YYYY or D/M/YYYY
        r"^(\d{1,2})-(\d{1,2})-(\d{4})$",  # DD-MM-YYYY or D-M-YYYY
    ]

    for pattern in patterns:
        match = re.match(pattern, date_string)
        if match:
            try:
                day, month, year = match.groups()
                return date(int(year), int(month), int(day))
            except (ValueError, TypeError):
                continue

    # If no pattern matched, try datetime.strptime with common formats
    formats = [
        "%d/%m/%Y",  # 03/01/2026
        "%d-%m-%Y",  # 03-01-2026
        "%d/%m/%y",  # 03/01/26
        "%d-%m-%y",  # 03-01-26
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt).date()
        except (ValueError, TypeError):
            continue

    # If all parsing attempts fail, return None
    return None


def format_brazilian_date(dt: date) -> str:
    """
    Format a date object to Brazilian format (DD/MM/YYYY).

    Args:
        dt: Python date object

    Returns:
        Date string in DD/MM/YYYY format

    Example:
        >>> format_brazilian_date(date(2026, 1, 3))
        '03/01/2026'
    """
    if not dt:
        return ""

    return dt.strftime("%d/%m/%Y")
