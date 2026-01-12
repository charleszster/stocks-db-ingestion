from __future__ import annotations

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------
# Public dispatcher
# ---------------------------------------------------------------------

def validate_corporate_action(event: Dict[str, Any]) -> Optional[str]:
    """
    Validate a single corporate action event payload.

    Returns:
        None if valid
        str  describing why the event is invalid
    """

    action_type = event.get("action_type")

    if not action_type:
        return "missing action_type"

    if action_type == "split":
        return validate_split(event)

    if action_type == "dividend":
        return validate_dividend(event)

    return f"unsupported action_type: {action_type}"


# ---------------------------------------------------------------------
# Split validation
# ---------------------------------------------------------------------

def validate_split(event: Dict[str, Any]) -> Optional[str]:
    """
    Validate Massive split payload.
    """

    if not event.get("id"):
        return "missing id"

    if not event.get("execution_date"):
        return "missing execution_date"

    split_to = event.get("split_to")
    split_from = event.get("split_from")

    if split_to is None or split_from is None:
        return "missing split_to or split_from"

    if split_to <= 0 or split_from <= 0:
        return f"invalid split ratio: {split_to}:{split_from}"

    return None


# ---------------------------------------------------------------------
# Dividend validation
# ---------------------------------------------------------------------

def validate_dividend(event: Dict[str, Any]) -> Optional[str]:
    """
    Validate Massive dividend payload.
    """

    if not event.get("id"):
        return "missing id"

    if not event.get("ex_dividend_date"):
        return "missing ex_dividend_date"

    cash = event.get("cash_amount")
    if cash is None:
        return "missing cash_amount"

    if cash <= 0:
        return f"non-positive cash_amount: {cash}"

    if not event.get("currency"):
        return "missing currency"

    return None
