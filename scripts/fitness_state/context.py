from __future__ import annotations

from typing import Any

from .getters import (
    get_active_goals,
    get_current_targets,
    get_deviations,
    get_diet_history,
    get_diet_plan,
    get_dietary_restrictions,
    get_health_notes,
    get_latest_body_stats,
    get_training_history,
    get_training_plan,
    get_user_profile,
)
from .projections import ensure_diet_plan_days, ensure_training_plan_days

PURPOSES = {
    "diet_plan",
    "diet_adjustment",
    "training_plan",
    "training_adjustment",
    "shopping_list",
    "weekly_review",
    "general",
}

DIET_PURPOSES = {"diet_plan", "diet_adjustment", "shopping_list"}
TRAINING_PURPOSES = {"training_plan", "training_adjustment"}


def _row_brief(row: dict[str, Any]) -> str:
    parts = []
    for key, value in row.items():
        if value in {"", None}:
            continue
        parts.append(f"{key}={value}")
    return ", ".join(parts) if parts else "(empty)"


def _section_lines(rows: list[dict[str, Any]], *, empty: str = "- none") -> list[str]:
    if not rows:
        return [empty]
    return [f"- {_row_brief(row)}" for row in rows]


def _has_value(row: dict[str, Any] | None, field: str) -> bool:
    return bool(row and row.get(field) not in {"", None})


def _notes_blob(*rows: dict[str, Any] | None) -> str:
    parts: list[str] = []
    for row in rows:
        if not row:
            continue
        for field in ("llm_notes", "goal_description", "calculation_method"):
            value = row.get(field)
            if value:
                parts.append(str(value).lower())
    return "\n".join(parts)


def _list_notes_blob(rows: list[dict[str, Any]]) -> str:
    return "\n".join(
        str(row.get(field, "")).lower()
        for row in rows
        for field in ("llm_notes", "description", "impact_on_training", "impact_on_diet", "summary")
        if row.get(field)
    )


def _has_keyword(text: str, *keywords: str) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _active_target(targets: list[dict[str, Any]], target_type: str) -> dict[str, Any] | None:
    matches = [row for row in targets if row.get("status") == "active" and row.get("target_type") in {target_type, "combined"}]
    if not matches:
        return None
    matches.sort(key=lambda row: row.get("effective_from", ""))
    return matches[-1]


def _profile_training_context(profile: dict[str, Any] | None, goals: list[dict[str, Any]], targets: list[dict[str, Any]]) -> str:
    text = _notes_blob(profile, *(goals or []), *(targets or []))
    return text


def _readiness(purpose: str, data: dict[str, Any]) -> dict[str, Any]:
    missing: list[str] = []
    profile = data["user_profile"]
    latest_stats = data["latest_body_stats"]
    goals = data["active_goals"]
    targets = data["targets"]
    diet_target = _active_target(targets, "diet")
    training_target = _active_target(targets, "training")
    restrictions = data["dietary_restrictions"]
    health_notes = data["health_notes"]
    notes_blob = _profile_training_context(profile, goals, targets)
    health_blob = _list_notes_blob(health_notes)

    if purpose in DIET_PURPOSES:
        if not goals:
            missing.append("active goal")
        if not _has_value(profile, "age"):
            missing.append("age")
        if not _has_value(profile, "sex"):
            missing.append("sex")
        if not _has_value(profile, "height_cm"):
            missing.append("height_cm")
        if not _has_value(latest_stats, "weight_kg"):
            missing.append("latest weight_kg")
        if not (_has_keyword(notes_blob, "activity", "training context", "activity_multiplier") or _has_value(diet_target, "steps") or _has_value(diet_target, "training_days_per_week")):
            missing.append("activity/training context")
        if not restrictions:
            missing.append("dietary restrictions checked")
        if not diet_target:
            missing.append("current diet targets")
        if not data["diet_plan"]:
            missing.append("next 7 days diet projection available")

    if purpose in TRAINING_PURPOSES:
        if not goals:
            missing.append("active goal")
        if not _has_keyword(notes_blob, "training_level", "training level"):
            missing.append("training level")
        if not (_has_keyword(notes_blob + "\n" + health_blob, "injury_status", "injury status", "no injury", "limitation", "pain", "recovery") or health_notes):
            missing.append("injury/limitation status")
        if not _has_keyword(notes_blob, "equipment", "gym", "dumbbell", "barbell", "home gym"):
            missing.append("available equipment")
        if not (_has_value(training_target, "training_days_per_week") or _has_keyword(notes_blob, "schedule", "days per week", "session duration")):
            missing.append("days per week or schedule constraints")
        if not training_target:
            missing.append("training target")
        if not data["training_plan"]:
            missing.append("next 7 days training projection available")

    return {
        "ok": not missing,
        "missing": missing,
        "checked": {
            "diet_history_rows": len(data["diet_history"]),
            "training_history_rows": len(data["training_history"]),
            "diet_plan_rows": len(data["diet_plan"]),
            "training_plan_rows": len(data["training_plan"]),
        },
    }


def get_context_data(*, purpose: str = "general", state_dir: str = "state") -> dict[str, Any]:
    if purpose not in PURPOSES:
        raise ValueError(f"Unsupported purpose: {purpose}")

    diet_plan = ensure_diet_plan_days(state_dir=state_dir) if purpose in DIET_PURPOSES | {"weekly_review", "general"} else get_diet_plan(state_dir=state_dir)
    training_plan = ensure_training_plan_days(state_dir=state_dir) if purpose in TRAINING_PURPOSES | {"weekly_review", "general"} else get_training_plan(state_dir=state_dir)

    data = {
        "purpose": purpose,
        "user_profile": get_user_profile(state_dir=state_dir),
        "active_goals": get_active_goals(state_dir=state_dir),
        "targets": get_current_targets(state_dir=state_dir),
        "latest_body_stats": get_latest_body_stats(state_dir=state_dir),
        "diet_history": get_diet_history(state_dir=state_dir),
        "training_history": get_training_history(state_dir=state_dir),
        "diet_plan": diet_plan,
        "training_plan": training_plan,
        "dietary_restrictions": get_dietary_restrictions(state_dir=state_dir),
        "health_notes": get_health_notes(state_dir=state_dir),
        "deviations": get_deviations(state_dir=state_dir),
    }
    data["readiness"] = _readiness(purpose, data)
    return data


def get_context(*, purpose: str = "general", state_dir: str = "state") -> str:
    data = get_context_data(purpose=purpose, state_dir=state_dir)
    profile = data["user_profile"]
    stats = data["latest_body_stats"]
    readiness = data["readiness"]

    lines = [
        "# Fitness Coach Context",
        "",
        "## Purpose",
        f"- {purpose}",
        "",
        "## 1. Targets",
    ]
    lines.extend(_section_lines(data["targets"], empty="- no active targets"))
    lines.extend([
        "",
        "## 2. Stats",
        f"- user_profile: {_row_brief(profile) if profile else 'missing'}",
        f"- latest_body_stats: {_row_brief(stats) if stats else 'missing'}",
    ])
    if data["active_goals"]:
        lines.append(f"- active_goals: {' | '.join(_row_brief(row) for row in data['active_goals'])}")
    else:
        lines.append("- active_goals: missing")

    lines.extend([
        "",
        "## 3. Past 7 Days History",
        "### Diet History",
    ])
    lines.extend(_section_lines(data["diet_history"]))
    lines.extend([
        "",
        "### Training History",
    ])
    lines.extend(_section_lines(data["training_history"]))
    lines.extend([
        "",
        "### Deviations",
    ])
    lines.extend(_section_lines(data["deviations"]))

    lines.extend([
        "",
        "## 4. Next 7 Days Projected Targets",
        "### Diet Plan",
    ])
    lines.extend(_section_lines(data["diet_plan"], empty="- no projected diet plan"))
    lines.extend([
        "",
        "### Training Plan",
    ])
    lines.extend(_section_lines(data["training_plan"], empty="- no projected training plan"))

    lines.extend([
        "",
        "## 5. Dietary Restrictions and Important Information",
        "### Dietary Restrictions",
    ])
    lines.extend(_section_lines(data["dietary_restrictions"], empty="- dietary restrictions not yet checked"))
    lines.extend([
        "",
        "### Health Notes",
    ])
    lines.extend(_section_lines(data["health_notes"]))

    lines.extend([
        "",
        "## Readiness Check",
        f"- status: {'ready' if readiness['ok'] else 'blocked'}",
        f"- checked: diet_history_rows={readiness['checked']['diet_history_rows']}, training_history_rows={readiness['checked']['training_history_rows']}, diet_plan_rows={readiness['checked']['diet_plan_rows']}, training_plan_rows={readiness['checked']['training_plan_rows']}",
    ])
    if readiness["missing"]:
        lines.append("- missing:")
        lines.extend([f"  - {item}" for item in readiness["missing"]])
    else:
        lines.append("- missing: none")

    return "\n".join(lines) + "\n"
