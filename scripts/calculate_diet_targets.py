#!/usr/bin/env python3
"""Compute calorie and macro targets from explicit user stats.

The script is intentionally deterministic and refuses to guess missing inputs.
It prints JSON by default so an agent can consume the result directly.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Literal

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


def load_inputs() -> Inputs:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--age", required=True, type=int)
    parser.add_argument("--sex", required=True, choices=["male", "female"])
    parser.add_argument("--height-cm", required=True, type=positive_number)
    parser.add_argument("--weight-kg", required=True, type=positive_number)
    parser.add_argument("--activity-multiplier", required=True, type=positive_number)
    parser.add_argument(
        "--goal",
        required=True,
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
    args = parser.parse_args()

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


if __name__ == "__main__":
    print(json.dumps(compute(load_inputs()), indent=2, sort_keys=True))
