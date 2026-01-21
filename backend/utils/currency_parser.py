"""Brazilian Real (BRL) currency parsing utilities."""

import re
from typing import Optional


def parse_brl_currency(currency_string: str) -> Optional[float]:
    """
    Parse Brazilian Real (BRL) currency string to float.

    Brazilian format uses:
    - R$ as currency symbol
    - Dot (.) as thousands separator
    - Comma (,) as decimal separator

    Args:
        currency_string: Currency string in BRL format
                        (e.g., "R$ 119,90", "R$ 1.234,56", "-703,69")

    Returns:
        Float value or None if parsing fails

    Examples:
        >>> parse_brl_currency("R$ 119,90")
        119.9
        >>> parse_brl_currency("R$ 1.234,56")
        1234.56
        >>> parse_brl_currency("-703,69")
        -703.69
        >>> parse_brl_currency("R$ 10.000,00")
        10000.0
    """
    if not currency_string or not isinstance(currency_string, str):
        return None

    # Clean the string
    cleaned = currency_string.strip()

    # Check if value is negative
    is_negative = cleaned.startswith("-") or cleaned.startswith("(")

    # Remove currency symbol, parentheses, and spaces
    # Common patterns: "R$", "$", "R $", "(", ")"
    cleaned = re.sub(r"[R$\s()]", "", cleaned)

    # Remove any remaining letters or special chars except dots, commas, minus sign
    cleaned = re.sub(r"[^\d.,-]", "", cleaned)

    if not cleaned:
        return None

    # Handle negative sign
    cleaned = cleaned.lstrip("-")

    # Replace dots (thousands separator) with empty string
    # Replace comma (decimal separator) with dot
    # Brazilian format: 1.234,56 -> 1234.56
    cleaned = cleaned.replace(".", "")
    cleaned = cleaned.replace(",", ".")

    try:
        value = float(cleaned)
        return -value if is_negative else value
    except (ValueError, TypeError):
        return None


def format_brl_currency(value: float, include_symbol: bool = True) -> str:
    """
    Format a float value to Brazilian Real (BRL) currency string.

    Args:
        value: Numeric value to format
        include_symbol: Whether to include "R$ " prefix

    Returns:
        Formatted currency string

    Examples:
        >>> format_brl_currency(119.90)
        'R$ 119,90'
        >>> format_brl_currency(1234.56)
        'R$ 1.234,56'
        >>> format_brl_currency(-703.69)
        'R$ -703,69'
        >>> format_brl_currency(119.90, include_symbol=False)
        '119,90'
    """
    if value is None:
        return ""

    # Handle negative values
    is_negative = value < 0
    abs_value = abs(value)

    # Format with 2 decimal places
    formatted = f"{abs_value:,.2f}"

    # Replace comma (thousands) with temp marker
    # Replace dot (decimal) with comma
    # Replace temp marker with dot
    formatted = formatted.replace(",", "|")
    formatted = formatted.replace(".", ",")
    formatted = formatted.replace("|", ".")

    # Add negative sign if needed
    if is_negative:
        formatted = f"-{formatted}"

    # Add currency symbol if requested
    if include_symbol:
        formatted = f"R$ {formatted}"

    return formatted
