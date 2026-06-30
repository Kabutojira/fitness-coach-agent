from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from .schemas import DATE_FIELDS, ENUM_FIELDS, NON_NEGATIVE_NUMERIC_FIELDS, NUMERIC_FIELDS, POSITIVE_NUMERIC_FIELDS, REQUIRED_FIELDS, SCHEMAS, TIMESTAMP_FIELDS


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    status: str
    normalized: dict[str, str]


def _parse_date(value: str, field: str) -> None:
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid date format for {field}: {value}") from exc


def _parse_timestamp(value: str, field: str) -> None:
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid timestamp for {field}: {value}") from exc


def _parse_number(value: str, field: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"invalid numeric type for {field}: {value}") from exc


def validate_row(table: str, row: dict[str, Any], *, strict: bool = False) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    normalized: dict[str, str] = {}

    schema = set(SCHEMAS[table])
    unknown = sorted(set(row) - schema)
    if unknown:
        errors.extend(f"invalid CSV column: {name}" for name in unknown)

    for column in SCHEMAS[table]:
        value = row.get(column, "")
        normalized[column] = "" if value is None else str(value)

    for field, value in normalized.items():
        if value == "":
            continue
        try:
            if field in DATE_FIELDS:
                _parse_date(value, field)
            elif field in TIMESTAMP_FIELDS:
                _parse_timestamp(value, field)
            elif field in ENUM_FIELDS and value not in ENUM_FIELDS[field]:
                raise ValueError(f"invalid enum for {field}: {value}")
            elif field in NUMERIC_FIELDS:
                parsed = _parse_number(value, field)
                if field in NON_NEGATIVE_NUMERIC_FIELDS and parsed < 0:
                    if field == "weight_kg":
                        raise ValueError("negative weight")
                    if field == "calories_kcal":
                        raise ValueError("negative calories")
                    if field in {"protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g"}:
                        raise ValueError(f"negative macros: {field}")
                    raise ValueError(f"invalid {field}: must be >= 0")
                if field in POSITIVE_NUMERIC_FIELDS and parsed <= 0:
                    raise ValueError(f"invalid {field}: must be > 0")
        except ValueError as exc:
            errors.append(str(exc))

    missing_required = sorted(field for field in REQUIRED_FIELDS.get(table, set()) if not normalized.get(field))
    if strict:
        errors.extend(f"missing required field: {field}" for field in missing_required)
        status = normalized.get("status") or "active"
    else:
        warnings.extend(f"{field} missing" for field in missing_required)
        status = normalized.get("status") or ("incomplete" if missing_required else "active")

    if table == "recipes" and normalized.get("servings"):
        try:
            if float(normalized["servings"]) <= 0:
                errors.append("invalid recipe serving count")
        except ValueError:
            errors.append("invalid recipe serving count")

    if errors:
        status = normalized.get("status") or "incomplete"

    normalized["status"] = status
    return ValidationResult(ok=not errors, errors=errors, warnings=warnings, status=status, normalized=normalized)
