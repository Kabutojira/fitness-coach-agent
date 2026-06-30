#!/usr/bin/env python3
"""Compute calorie and macro targets from explicit user stats or CSV state.

The script is intentionally deterministic and refuses to guess missing inputs.
It prints JSON by default so an agent can consume the result directly.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from fitness_state.getters import get_active_goals, get_latest_body_stats, get_user_profile
from fitness_state.setters import add_target

Sex = Literal["male", "female"]
Goal = Literal["fat_loss", "recomposition", "maintenance", "muscle_gain"]
Formula = Literal["mifflin_st_jeor", "katch_mcardle"]

GOAL_DEFAULTS = {
    "fat_loss": {"calorie_adjustment_percent": -20.0, "protein_g_per_kg": 2.0, "fat_g_per_kg": 0.8},
    "recomposition": {"calorie_adjustment_percent": -10.0, "protein_g_per_kg": 2.0, "fat_g_per_kg": 0.8},
    "maintenance": {"calorie_adjustment_percent": 0.0, "protein_g_per_kg": 1.8, "fat_g_per_kg": 0.8},
    "muscle_gain": {"calorie_adjustment_percent": 10.0, "protein_g_per_kg": 1.8, "fat_g_per_kg": 0.8},
}


@dataclass(frozen=True)
class Inputs:
    age: int
    sex: Sex
    height_cm: float
    weight_kg: float
    activity_multiplier: float
    goal: Goal
    formula: Formula
    body_fat_percent: float | None
    calorie_adjustment_percent: float
    protein_g_per_kg: float
    fat_g_per_kg: float
    fiber_g_per_1000_kcal: float
    water_ml_per_kg: float
    meals_per_day: int | None


def positive_number(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be > 0")
    return parsed


def bounded_percent(value: str) -> float:
    parsed = float(value)
    if parsed <= 0 or parsed >= 100:
        raise argparse.ArgumentTypeError("percent must be between 0 and 100")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--age", type=int)
    parser.add_argument("--sex", choices=["male", "female"])
    parser.add_argument("--height-cm", type=positive_number)
    parser.add_argument("--weight-kg", type=positive_number)
    parser.add_argument("--activity-multiplier", type=positive_number)
    parser.add_argument(
        "--goal",
        choices=list(GOAL_DEFAULTS),
        help="fat_loss, recomposition, maintenance, muscle_gain",
    )
    parser.add_argument(
        "--formula",
        choices=["mifflin_st_jeor", "katch_mcardle"],
        default="mifflin_st_jeor",
    )
    parser.add_argument("--body-fat-percent", type=bounded_percent)
    parser.add_argument("--calorie-adjustment-percent", type=float)
    parser.add_argument("--protein-g-per-kg", type=positive_number)
    parser.add_argument("--fat-g-per-kg", type=positive_number)
    parser.add_argument("--fiber-g-per-1000-kcal", type=positive_number, default=14.0)
    parser.add_argument("--water-ml-per-kg", type=positive_number, default=35.0)
    parser.add_argument("--meals-per-day", type=int)
    parser.add_argument("--from-state", action="store_true")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    return parser


def _require(value, message: str):
    if value in {None, ""}:
        raise SystemExit(message)
    return value


def _extract_note_number(text: str | None, key: str) -> float | None:
    if not text:
        return None
    match = re.search(rf"{re.escape(key)}\s*=\s*([0-9]+(?:\.[0-9]+)?)", text)
    return float(match.group(1)) if match else None


def _goal_from_state(state_dir: str) -> Goal:
    active_goals = get_active_goals(state_dir=state_dir)
    if not active_goals:
        raise SystemExit("missing required state input: active goal")
    goal_type = active_goals[-1].get("goal_type") or ""
    if goal_type not in GOAL_DEFAULTS:
        raise SystemExit(f"unsupported goal_type for calculator: {goal_type}")
    return goal_type  # type: ignore[return-value]


def inputs_from_state(args: argparse.Namespace) -> Inputs:
    profile = get_user_profile(state_dir=args.state_dir)
    stats = get_latest_body_stats(state_dir=args.state_dir)
    if not profile:
        raise SystemExit("missing required state input: user_profile")
    if not stats:
        raise SystemExit("missing required state input: latest body_stats")

    notes = str(profile.get("llm_notes", ""))
    activity_multiplier = _extract_note_number(notes, "activity_multiplier")
    meals_per_day = _extract_note_number(notes, "meals_per_day")
    body_fat_percent = stats.get("body_fat_percent") or args.body_fat_percent

    age_value = _require(profile.get("age"), "missing required state input: age")
    sex_value = _require(profile.get("sex"), "missing required state input: sex")
    height_value = _require(profile.get("height_cm"), "missing required state input: height_cm")
    weight_value = _require(stats.get("weight_kg"), "missing required state input: weight_kg")

    age = int(float(str(age_value)))
    sex_text = str(sex_value)
    if sex_text == "male":
        sex: Sex = "male"
    elif sex_text == "female":
        sex = "female"
    else:
        raise SystemExit(f"unsupported sex in state: {sex_text}")
    height_cm = float(str(height_value))
    weight_kg = float(str(weight_value))
    goal = _goal_from_state(args.state_dir)
    if activity_multiplier is None:
        raise SystemExit("missing required state input: activity_multiplier in user_profile.llm_notes")

    defaults = GOAL_DEFAULTS[goal]
    return Inputs(
        age=age,
        sex=sex,
        height_cm=height_cm,
        weight_kg=weight_kg,
        activity_multiplier=activity_multiplier,
        goal=goal,
        formula=args.formula,
        body_fat_percent=float(body_fat_percent) if body_fat_percent not in {None, ""} else None,
        calorie_adjustment_percent=(
            args.calorie_adjustment_percent
            if args.calorie_adjustment_percent is not None
            else defaults["calorie_adjustment_percent"]
        ),
        protein_g_per_kg=args.protein_g_per_kg or defaults["protein_g_per_kg"],
        fat_g_per_kg=args.fat_g_per_kg or defaults["fat_g_per_kg"],
        fiber_g_per_1000_kcal=args.fiber_g_per_1000_kcal,
        water_ml_per_kg=args.water_ml_per_kg,
        meals_per_day=int(meals_per_day) if meals_per_day is not None else None,
    )


def load_inputs(args: argparse.Namespace) -> Inputs:
    if args.from_state:
        return inputs_from_state(args)

    required = ["age", "sex", "height_cm", "weight_kg", "activity_multiplier", "goal"]
    missing = [name for name in required if getattr(args, name) in {None, ""}]
    if missing:
        raise SystemExit(f"missing required arguments: {', '.join('--' + name.replace('_', '-') for name in missing)}")
    if args.age <= 0:
        raise SystemExit("--age must be > 0")
    if args.meals_per_day is not None and args.meals_per_day <= 0:
        raise SystemExit("--meals-per-day must be > 0 when provided")
    if args.formula == "katch_mcardle" and args.body_fat_percent is None:
        raise SystemExit("--body-fat-percent is required when --formula=katch_mcardle")

    defaults = GOAL_DEFAULTS[args.goal]
    return Inputs(
        age=args.age,
        sex=args.sex,
        height_cm=args.height_cm,
        weight_kg=args.weight_kg,
        activity_multiplier=args.activity_multiplier,
        goal=args.goal,
        formula=args.formula,
        body_fat_percent=args.body_fat_percent,
        calorie_adjustment_percent=(
            args.calorie_adjustment_percent
            if args.calorie_adjustment_percent is not None
            else defaults["calorie_adjustment_percent"]
        ),
        protein_g_per_kg=args.protein_g_per_kg or defaults["protein_g_per_kg"],
        fat_g_per_kg=args.fat_g_per_kg or defaults["fat_g_per_kg"],
        fiber_g_per_1000_kcal=args.fiber_g_per_1000_kcal,
        water_ml_per_kg=args.water_ml_per_kg,
        meals_per_day=args.meals_per_day,
    )


def mifflin_st_jeor(inputs: Inputs) -> float:
    base = 10 * inputs.weight_kg + 6.25 * inputs.height_cm - 5 * inputs.age
    return base + (5 if inputs.sex == "male" else -161)


def katch_mcardle(inputs: Inputs) -> float:
    assert inputs.body_fat_percent is not None
    lean_mass_kg = inputs.weight_kg * (1 - inputs.body_fat_percent / 100)
    return 370 + (21.6 * lean_mass_kg)


def round1(value: float) -> float:
    return round(value, 1)


def round_int(value: float) -> int:
    return int(round(value))


def compute(inputs: Inputs) -> dict:
    if inputs.formula == "mifflin_st_jeor":
        bmr = mifflin_st_jeor(inputs)
    else:
        bmr = katch_mcardle(inputs)

    tdee = bmr * inputs.activity_multiplier
    target_kcal = tdee * (1 + inputs.calorie_adjustment_percent / 100)

    protein_g = inputs.weight_kg * inputs.protein_g_per_kg
    fat_g = inputs.weight_kg * inputs.fat_g_per_kg
    protein_kcal = protein_g * 4
    fat_kcal = fat_g * 9
    remaining_kcal = target_kcal - protein_kcal - fat_kcal
    carbs_g = remaining_kcal / 4
    if carbs_g < 0:
        raise SystemExit(
            "Calculated carbs are negative. Lower the protein/fat targets or raise calories."
        )
    carbs_kcal = carbs_g * 4
    total_macro_kcal = protein_kcal + carbs_kcal + fat_kcal
    fiber_g = (target_kcal / 1000) * inputs.fiber_g_per_1000_kcal
    water_l = (inputs.weight_kg * inputs.water_ml_per_kg) / 1000

    per_meal = None
    if inputs.meals_per_day:
        per_meal = {
            "calories_kcal": round1(target_kcal / inputs.meals_per_day),
            "protein_g": round1(protein_g / inputs.meals_per_day),
            "carbs_g": round1(carbs_g / inputs.meals_per_day),
            "fat_g": round1(fat_g / inputs.meals_per_day),
            "fiber_g": round1(fiber_g / inputs.meals_per_day),
        }

    return {
        "inputs": {
            "age": inputs.age,
            "sex": inputs.sex,
            "height_cm": inputs.height_cm,
            "weight_kg": inputs.weight_kg,
            "activity_multiplier": inputs.activity_multiplier,
            "goal": inputs.goal,
            "formula": inputs.formula,
            "body_fat_percent": inputs.body_fat_percent,
            "protein_g_per_kg": inputs.protein_g_per_kg,
            "fat_g_per_kg": inputs.fat_g_per_kg,
            "calorie_adjustment_percent": inputs.calorie_adjustment_percent,
            "fiber_g_per_1000_kcal": inputs.fiber_g_per_1000_kcal,
            "water_ml_per_kg": inputs.water_ml_per_kg,
            "meals_per_day": inputs.meals_per_day,
        },
        "targets": {
            "calories_kcal": round_int(target_kcal),
            "protein_g": round1(protein_g),
            "carbs_g": round1(carbs_g),
            "fat_g": round1(fat_g),
            "fiber_g": round1(fiber_g),
            "water_l": round1(water_l),
            "meals_per_day": inputs.meals_per_day,
        },
        "calculation_notes": {
            "formula": inputs.formula,
            "bmr_estimate": round1(bmr),
            "tdee_estimate": round1(tdee),
            "deficit_or_surplus_percent": inputs.calorie_adjustment_percent,
            "protein_basis_g_per_kg": inputs.protein_g_per_kg,
            "fat_basis_g_per_kg": inputs.fat_g_per_kg,
            "carb_basis": "remaining calories after protein and fat",
        },
        "mathematical_check": {
            "protein_kcal": round1(protein_kcal),
            "carbs_kcal": round1(carbs_kcal),
            "fat_kcal": round1(fat_kcal),
            "total_macro_kcal": round1(total_macro_kcal),
            "difference_vs_target_kcal": round1(total_macro_kcal - target_kcal),
        },
        "per_meal": per_meal,
    }


def maybe_write_state(result: dict, *, state_dir: str) -> dict[str, str] | None:
    return add_target(
        state_dir=state_dir,
        source="calculation",
        confidence="high",
        target_type="diet",
        effective_from=date.today().isoformat(),
        calories_kcal=result["targets"]["calories_kcal"],
        protein_g=result["targets"]["protein_g"],
        carbs_g=result["targets"]["carbs_g"],
        fat_g=result["targets"]["fat_g"],
        fiber_g=result["targets"]["fiber_g"],
        water_l=result["targets"]["water_l"],
        calculation_method=f"calculate_diet_targets:{result['calculation_notes']['formula']}",
        llm_notes="Generated by calculate_diet_targets.py --write-state",
    )


def main() -> None:
    args = build_parser().parse_args()
    inputs = load_inputs(args)
    result = compute(inputs)
    if args.write_state:
        result["state_write"] = maybe_write_state(result, state_dir=args.state_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
