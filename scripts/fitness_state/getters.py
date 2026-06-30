from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .csv_store import CSVStore


def _store(state_dir: str = "state") -> CSVStore:
    store = CSVStore(state_dir)
    store.initialize_all()
    return store


def _active_latest(rows: list[dict[str, str]], date_field: str | None = None) -> dict[str, str] | None:
    filtered = [row for row in rows if row.get("status") not in {"inactive", "archived"}]
    if not filtered:
        return None
    if date_field:
        filtered.sort(key=lambda row: row.get(date_field, ""))
    else:
        filtered.sort(key=lambda row: (row.get("updated_at", ""), row.get("created_at", ""), row.get("id", "")))
    return filtered[-1]


def _range_days(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _future_days(days: int) -> tuple[str, str]:
    start = date.today() + timedelta(days=1)
    end = start + timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def get_rows(table: str, *, state_dir: str = "state") -> list[dict[str, str]]:
    return _store(state_dir).read_rows(table)


def get_user_profile(*, state_dir: str = "state") -> dict[str, str] | None:
    return _active_latest(_store(state_dir).read_rows("user_profile"))


def get_active_goals(*, state_dir: str = "state") -> list[dict[str, str]]:
    return [row for row in _store(state_dir).read_rows("goals") if row.get("status") == "active"]


def get_current_targets(*, state_dir: str = "state") -> list[dict[str, str]]:
    return [row for row in _store(state_dir).read_rows("targets") if row.get("status") == "active"]


def get_latest_body_stats(*, state_dir: str = "state") -> dict[str, str] | None:
    return _active_latest(_store(state_dir).read_rows("body_stats"), "date")


def get_body_stats_history(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _range_days(days)
    return _store(state_dir).filter_date_range("body_stats", start, end)


def get_diet_history(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _range_days(days)
    return _store(state_dir).filter_date_range("diet_history", start, end)


def get_training_history(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _range_days(days)
    return _store(state_dir).filter_date_range("training_history", start, end)


def get_diet_plan(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _future_days(days)
    return _store(state_dir).filter_date_range("diet_plan", start, end)


def get_training_plan(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _future_days(days)
    return _store(state_dir).filter_date_range("training_plan", start, end)


def get_dietary_restrictions(*, state_dir: str = "state") -> list[dict[str, str]]:
    return [row for row in _store(state_dir).read_rows("dietary_restrictions") if row.get("status") != "archived"]


def get_health_notes(*, state_dir: str = "state") -> list[dict[str, str]]:
    rows = [row for row in _store(state_dir).read_rows("health_notes") if row.get("status") != "archived"]
    rows.sort(key=lambda row: row.get("date", ""))
    return rows


def get_deviations(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    start, end = _range_days(days)
    return _store(state_dir).filter_date_range("deviations", start, end)


def get_ingredients(search: str | None = None, *, state_dir: str = "state") -> list[dict[str, str]]:
    rows = [row for row in _store(state_dir).read_rows("ingredients") if row.get("status") != "archived"]
    if search:
        needle = search.lower()
        rows = [row for row in rows if needle in row.get("name", "").lower() or needle in row.get("brand", "").lower()]
    return rows


def get_recipes(search: str | None = None, *, state_dir: str = "state") -> list[dict[str, str]]:
    rows = [row for row in _store(state_dir).read_rows("recipes") if row.get("status") != "archived"]
    if search:
        needle = search.lower()
        rows = [row for row in rows if needle in row.get("name", "").lower()]
    return rows


def get_fridge_items(*, state_dir: str = "state") -> list[dict[str, str]]:
    return [row for row in _store(state_dir).read_rows("fridge_items") if row.get("status") != "archived"]


def get_shopping_list(*, state_dir: str = "state") -> list[dict[str, str]]:
    return [row for row in _store(state_dir).read_rows("shopping_list") if row.get("status") != "archived"]


def get_table(table: str, *, state_dir: str = "state") -> list[dict[str, str]]:
    return _store(state_dir).read_rows(table)


def summarize_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    return [{key: value for key, value in row.items() if value != ""} for row in rows]
