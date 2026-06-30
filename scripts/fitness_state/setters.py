from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from .csv_store import CSVStore
from .validators import validate_row


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _store(state_dir: str = "state") -> CSVStore:
    store = CSVStore(state_dir)
    store.initialize_all()
    return store


def _row_id(table: str, *, explicit: str | None = None, daily_date: str | None = None) -> str:
    if explicit:
        return explicit
    if daily_date:
        return f"{table}_{daily_date.replace('-', '')}"
    return f"{table}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def _prepare_row(table: str, payload: dict[str, Any], *, row_id: str | None = None, daily_date: str | None = None) -> dict[str, Any]:
    row = {
        "id": _row_id(table, explicit=row_id, daily_date=daily_date),
        "created_at": payload.get("created_at") or _now(),
        "updated_at": _now(),
        "source": payload.get("source") or "agent",
        "confidence": payload.get("confidence") or "unknown",
        "status": payload.get("status") or "",
        "llm_notes": payload.get("llm_notes") or "",
    }
    row.update(payload)
    return row


def _persist(table: str, payload: dict[str, Any], *, state_dir: str = "state", row_id: str | None = None, daily_date: str | None = None, daily: bool = False) -> dict[str, Any]:
    store = _store(state_dir)
    row = _prepare_row(table, payload, row_id=row_id, daily_date=daily_date)
    result = validate_row(table, row, strict=False)
    if not result.ok:
        return {"ok": False, "operation": table, "errors": result.errors, "warnings": result.warnings}
    saved = store.upsert_daily_row(table, result.normalized) if daily else store.append_row(table, result.normalized)
    return {
        "ok": True,
        "operation": table,
        "status": result.status,
        "id": saved["id"],
        "file": str(store.path_for(table)),
        "warnings": result.warnings,
    }


def set_user_profile(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    store = _store(state_dir)
    for row in store.read_rows("user_profile"):
        if row.get("status") == "active":
            row["status"] = "inactive"
    rows = store.read_rows("user_profile")
    for row in rows:
        if row.get("status") == "active":
            row["status"] = "inactive"
    if rows:
        store.write_rows("user_profile", rows)
    return _persist("user_profile", payload, state_dir=state_dir, row_id="user_profile")


def add_goal(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    return _persist("goals", payload, state_dir=state_dir)


def archive_goal(goal_id: str, *, state_dir: str = "state") -> dict[str, Any]:
    _store(state_dir).archive_row("goals", goal_id)
    return {"ok": True, "operation": "archive_goal", "id": goal_id}


def upsert_daily_body_stats(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("body_stats", payload, state_dir=state_dir, row_id=f"body_stats_{date.replace('-', '')}", daily_date=date, daily=True)


def add_target(*, state_dir: str = "state", archive_existing: bool = True, **payload: Any) -> dict[str, Any]:
    store = _store(state_dir)
    target_type = payload.get("target_type")
    if archive_existing and target_type:
        rows = store.read_rows("targets")
        changed = False
        for row in rows:
            if row.get("status") == "active" and row.get("target_type") == str(target_type):
                row["status"] = "inactive"
                changed = True
        if changed:
            store.write_rows("targets", rows)
    return _persist("targets", payload, state_dir=state_dir)


def archive_target(target_id: str, *, state_dir: str = "state") -> dict[str, Any]:
    _store(state_dir).archive_row("targets", target_id)
    return {"ok": True, "operation": "archive_target", "id": target_id}


def upsert_daily_diet_history(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("diet_history", payload, state_dir=state_dir, row_id=f"diet_history_{date.replace('-', '')}", daily_date=date, daily=True)


def upsert_daily_training_history(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("training_history", payload, state_dir=state_dir, row_id=f"training_history_{date.replace('-', '')}", daily_date=date, daily=True)


def upsert_daily_diet_plan(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("diet_plan", payload, state_dir=state_dir, row_id=f"diet_plan_{date.replace('-', '')}", daily_date=date, daily=True)


def upsert_daily_training_plan(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("training_plan", payload, state_dir=state_dir, row_id=f"training_plan_{date.replace('-', '')}", daily_date=date, daily=True)


def add_ingredient(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    return _persist("ingredients", payload, state_dir=state_dir)


def update_ingredient(ingredient_id: str, *, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    store = _store(state_dir)
    existing = next(row for row in store.read_rows("ingredients") if row.get("id") == ingredient_id)
    merged = {**existing, **payload, "id": ingredient_id, "updated_at": _now()}
    result = validate_row("ingredients", merged, strict=False)
    if not result.ok:
        return {"ok": False, "operation": "update_ingredient", "errors": result.errors, "warnings": result.warnings}
    store.update_row_by_id("ingredients", ingredient_id, result.normalized)
    return {"ok": True, "operation": "update_ingredient", "id": ingredient_id, "status": result.status, "warnings": result.warnings}


def add_recipe(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    return _persist("recipes", payload, state_dir=state_dir)


def update_recipe(recipe_id: str, *, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    store = _store(state_dir)
    existing = next(row for row in store.read_rows("recipes") if row.get("id") == recipe_id)
    merged = {**existing, **payload, "id": recipe_id, "updated_at": _now()}
    result = validate_row("recipes", merged, strict=False)
    if not result.ok:
        return {"ok": False, "operation": "update_recipe", "errors": result.errors, "warnings": result.warnings}
    store.update_row_by_id("recipes", recipe_id, result.normalized)
    return {"ok": True, "operation": "update_recipe", "id": recipe_id, "status": result.status, "warnings": result.warnings}


def add_recipe_ingredient_snapshot(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    return _persist("recipe_ingredients", payload, state_dir=state_dir)


def add_dietary_restriction(*, state_dir: str = "state", checked_on: str | None = None, **payload: Any) -> dict[str, Any]:
    payload["checked_on"] = checked_on or date.today().isoformat()
    return _persist("dietary_restrictions", payload, state_dir=state_dir)


def add_health_note(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("health_notes", payload, state_dir=state_dir)


def add_deviation(*, state_dir: str = "state", date: str, **payload: Any) -> dict[str, Any]:
    payload["date"] = date
    return _persist("deviations", payload, state_dir=state_dir)


def add_fridge_item(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    return _persist("fridge_items", payload, state_dir=state_dir)


def update_fridge_item(item_id: str, *, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    store = _store(state_dir)
    existing = next(row for row in store.read_rows("fridge_items") if row.get("id") == item_id)
    merged = {**existing, **payload, "id": item_id, "updated_at": _now()}
    result = validate_row("fridge_items", merged, strict=False)
    if not result.ok:
        return {"ok": False, "operation": "update_fridge_item", "errors": result.errors, "warnings": result.warnings}
    store.update_row_by_id("fridge_items", item_id, result.normalized)
    return {"ok": True, "operation": "update_fridge_item", "id": item_id, "status": result.status, "warnings": result.warnings}


def add_shopping_item(*, state_dir: str = "state", **payload: Any) -> dict[str, Any]:
    payload.setdefault("purchased", "no")
    return _persist("shopping_list", payload, state_dir=state_dir)


def mark_shopping_item_purchased(item_id: str, *, state_dir: str = "state") -> dict[str, Any]:
    store = _store(state_dir)
    store.update_row_by_id("shopping_list", item_id, {"purchased": "yes", "updated_at": _now()})
    return {"ok": True, "operation": "mark_shopping_item_purchased", "id": item_id}
