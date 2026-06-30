from __future__ import annotations

from datetime import date, timedelta

from .getters import get_current_targets, get_diet_history, get_diet_plan, get_health_notes, get_training_history, get_training_plan
from .setters import upsert_daily_diet_plan, upsert_daily_training_plan


MIN_FAT_G = 30.0


def _float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    return float(value) if value not in {"", None} else default


def _future_dates(days: int) -> list[str]:
    start = date.today() + timedelta(days=1)
    return [(start + timedelta(days=index)).isoformat() for index in range(days)]


def _active_target_by_type(targets: list[dict[str, str]], target_type: str) -> dict[str, str] | None:
    matches = [row for row in targets if row.get("status") == "active" and row.get("target_type") in {target_type, "combined"}]
    if not matches:
        return None
    matches.sort(key=lambda row: row.get("effective_from", ""))
    return matches[-1]


def ensure_diet_plan_days(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    targets = get_current_targets(state_dir=state_dir)
    target = _active_target_by_type(targets, "diet")
    if not target:
        return get_diet_plan(days=days, state_dir=state_dir)

    existing = {row["date"]: row for row in get_diet_plan(days=days, state_dir=state_dir)}
    history = get_diet_history(days=7, state_dir=state_dir)
    recorded_days = len([row for row in history if row.get("calories_kcal")])
    compensation = 0.0
    remaining_uncompensated = 0.0
    compensation_reason = "No compensation needed"
    if recorded_days:
        target_calories = _float(target, "calories_kcal") * recorded_days
        actual_calories = sum(_float(row, "calories_kcal") for row in history)
        calorie_delta = actual_calories - target_calories
        raw_daily_compensation = calorie_delta / 7.0
        max_daily_compensation = _float(target, "calories_kcal") * 0.10
        if raw_daily_compensation > 0:
            compensation = min(raw_daily_compensation, max_daily_compensation)
            compensation_reason = "Reduce next-week calories to smooth past excess"
        elif raw_daily_compensation < 0:
            compensation = max(raw_daily_compensation, -max_daily_compensation)
            compensation_reason = "Increase next-week calories to smooth past undershoot"
        remaining_uncompensated = calorie_delta - (compensation * 7.0)
    else:
        compensation_reason = "No past 7-day diet history recorded; generated from active targets only"

    generated: list[dict[str, str]] = []
    for day in _future_dates(days):
        if day in existing:
            continue
        calories = _float(target, "calories_kcal") - compensation
        protein = _float(target, "protein_g")
        fat = max(_float(target, "fat_g"), MIN_FAT_G)
        carbs = _float(target, "carbs_g") - (compensation / 4.0)
        if carbs < 0:
            deficit = abs(carbs)
            carbs = 0.0
            fat = max(MIN_FAT_G, fat - (deficit * 4.0 / 9.0))
        notes = [
            f"recorded_history_days={recorded_days}",
            f"daily_compensation={round(compensation, 2)}",
        ]
        if remaining_uncompensated:
            notes.append(f"remaining_uncompensated_delta={round(remaining_uncompensated, 2)}")
        result = upsert_daily_diet_plan(
            state_dir=state_dir,
            date=day,
            calories_kcal=round(calories, 1),
            protein_g=round(protein, 1),
            carbs_g=round(max(carbs, 0.0), 1),
            fat_g=round(max(fat, MIN_FAT_G), 1),
            fiber_g=target.get("fiber_g", ""),
            water_l=target.get("water_l", ""),
            plan_summary="Auto-generated from active diet target",
            compensation_reason=compensation_reason,
            llm_notes="; ".join(notes),
            source="calculation",
            confidence="high",
        )
        generated.append({"date": day, "id": result.get("id", "")})
    return get_diet_plan(days=days, state_dir=state_dir)


def ensure_training_plan_days(days: int = 7, *, state_dir: str = "state") -> list[dict[str, str]]:
    targets = get_current_targets(state_dir=state_dir)
    target = _active_target_by_type(targets, "training")
    if not target:
        return get_training_plan(days=days, state_dir=state_dir)

    existing = {row["date"]: row for row in get_training_plan(days=days, state_dir=state_dir)}
    history = get_training_history(days=7, state_dir=state_dir)
    health_notes = get_health_notes(state_dir=state_dir)
    pain_present = any((row.get("impact_on_training") or row.get("description") or "").lower().find("pain") >= 0 for row in health_notes[-7:])
    target_days = int(float(target.get("training_days_per_week") or 0))
    completed_days = sum(1 for row in history if row.get("trained") in {"yes", "true", "1"})
    missed_days = max(target_days - completed_days, 0)

    generated = []
    remaining_makeup = missed_days if not pain_present else 0
    for index, day in enumerate(_future_dates(days)):
        if day in existing:
            continue
        planned_training = "yes" if target_days and index < target_days else "no"
        compensation_reason = "Base training target"
        if remaining_makeup > 0 and planned_training == "no":
            planned_training = "yes"
            remaining_makeup -= 1
            compensation_reason = "Rescheduled missed training without doubling hard sessions"
        if pain_present:
            compensation_reason = "Pain/recovery notes present; no catch-up load added"
        upsert_daily_training_plan(
            state_dir=state_dir,
            date=day,
            planned_training=planned_training,
            session_name="Planned session" if planned_training == "yes" else "Recovery / rest",
            training_type="strength" if planned_training == "yes" else "rest",
            duration_min=target.get("duration_min") or ("45" if planned_training == "yes" else "0"),
            intensity_target="moderate" if planned_training == "yes" else "recovery",
            progression_rule="keep progression smooth",
            plan_summary="Auto-generated from active training target",
            compensation_reason=compensation_reason,
            llm_notes=f"missed_days={missed_days}; remaining_makeup={remaining_makeup}; pain_present={str(pain_present).lower()}",
            source="calculation",
            confidence="medium",
        )
        generated.append(day)
    return get_training_plan(days=days, state_dir=state_dir)
