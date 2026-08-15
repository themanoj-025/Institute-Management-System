"""
Shared utility for reading typed configuration values from the ``SystemConfig`` table.

Provides a single source of truth for reading admin-configurable values
(risk thresholds, feature flags, etc.) across all modules.
"""

from typing import Any, Optional

from sqlalchemy.orm import Session


def get_config_value(
    session: Session,
    key: str,
    default: Any = None,
) -> Any:
    """Read a typed config value from ``SystemConfig``, falling back to *default*.

    The value's Python type is determined by the ``value_type`` column:
      - ``"int"`` → ``int``
      - ``"float"`` → ``float``
      - ``"bool"`` → ``bool`` (values ``"true"`` / ``"1"`` / ``"yes"`` are truthy)
      - ``"string"`` (or anything else) → ``str``

    Parameters
    ----------
    session : sqlalchemy.orm.Session
        Active database session.
    key : str
        Configuration key to look up.
    default : any
        Value returned if no entry exists for *key*.

    Returns
    -------
    any
        The typed configuration value, or *default* if not found.
    """
    from database.models import SystemConfig

    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not entry:
        return default

    raw = entry.value
    vtype = entry.value_type or "string"

    try:
        if vtype == "int":
            return int(raw)
        elif vtype == "float":
            return float(raw)
        elif vtype == "bool":
            return raw.lower() in ("true", "1", "yes")
        else:
            return raw
    except (ValueError, TypeError):
        return default


def get_config_float(
    session: Session,
    key: str,
    default: float = 0.0,
) -> float:
    """Read a float config value. Convenience wrapper around ``get_config_value``."""
    val = get_config_value(session, key, default)
    return float(val) if val is not None else default


def get_config_int(
    session: Session,
    key: str,
    default: int = 0,
) -> int:
    """Read an int config value. Convenience wrapper around ``get_config_value``."""
    val = get_config_value(session, key, default)
    return int(val) if val is not None else default


def set_config_value(
    session: Session,
    key: str,
    value: Any,
    description: str = "",
    user_id: Optional[int] = None,
):
    """Set a typed value in ``SystemConfig``, creating or updating as needed.

    Parameters
    ----------
    session : sqlalchemy.orm.Session
    key : str
    value : any
        The Python value to store. Its type determines the ``value_type`` column.
    description : str
        Human-readable description of what this config key controls.
    user_id : int, optional
        ID of the user making the change (for audit trail).
    """
    from database.models import SystemConfig

    # Determine value type and string representation
    if isinstance(value, bool):
        value_type = "bool"
        str_value = str(value).lower()
    elif isinstance(value, int):
        value_type = "int"
        str_value = str(value)
    elif isinstance(value, float):
        value_type = "float"
        str_value = str(value)
    else:
        value_type = "string"
        str_value = str(value)

    entry = session.query(SystemConfig).filter(SystemConfig.key == key).first()
    if entry:
        entry.value = str_value
        entry.value_type = value_type
        entry.updated_by = user_id
    else:
        from database.models import SystemConfig as SC

        entry = SC(
            key=key,
            value=str_value,
            value_type=value_type,
            description=description,
            updated_by=user_id,
        )
        session.add(entry)
    session.commit()
