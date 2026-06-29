#!/usr/bin/env python3
"""Compute total and per-serving recipe nutrition from explicit ingredient data.

Input is a JSON document with this shape:
{
  "recipe_name": "overnight oats",
  "servings": 2,
  "ingredients": [
    {
      "name": "oats",
      "quantity": 80,
      "unit": "g",
      "nutrition_basis": {
        "type": "per_100g",
        "calories_kcal": 389,
        "protein_g": 16.9,
        "carbs_g": 66.3,
        "fat_g": 6.9,
        "fiber_g": 10.6
      }
    }
  ]
}

Supported basis types:
- per_100g    quantity unit must be g
- per_unit    quantity is a count of units
- per_package quantity is a count of packages
"""

from __future__ import annotations

import argparse
import json
from typing import Any

MACRO_KEYS = ("calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g")


def load_payload() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path to the recipe JSON file")
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_number(mapping: dict[str, Any], key: str) -> float:
    value = mapping.get(key, 0)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SystemExit(f"Invalid numeric value for {key}: {value!r}") from exc


def scale_ingredient(ingredient: dict[str, Any]) -> dict[str, Any]:
    name = ingredient.get("name") or "unnamed ingredient"
    quantity = get_number(ingredient, "quantity")
    if quantity < 0:
        raise SystemExit(f"Ingredient {name!r} has a negative quantity")

    basis = ingredient.get("nutrition_basis")
    if not isinstance(basis, dict):
        raise SystemExit(f"Ingredient {name!r} is missing nutrition_basis")

    basis_type = basis.get("type")
    unit = ingredient.get("unit")
    if basis_type == "per_100g":
        if unit != "g":
            raise SystemExit(f"Ingredient {name!r} uses per_100g basis but unit is {unit!r}, expected 'g'")
        multiplier = quantity / 100.0
    elif basis_type in {"per_unit", "per_package"}:
        multiplier = quantity
    else:
        raise SystemExit(
            f"Ingredient {name!r} has unsupported nutrition_basis.type {basis_type!r}. "
            "Use per_100g, per_unit, or per_package."
        )

    scaled = {key: round(get_number(basis, key) * multiplier, 2) for key in MACRO_KEYS}
    scaled["quantity"] = quantity
    scaled["unit"] = unit
    scaled["basis_type"] = basis_type
    scaled["name"] = name
    return scaled


def compute(payload: dict[str, Any]) -> dict[str, Any]:
    ingredients = payload.get("ingredients")
    if not isinstance(ingredients, list) or not ingredients:
        raise SystemExit("ingredients must be a non-empty array")

    servings = get_number(payload, "servings") if payload.get("servings") is not None else 1.0
    if servings <= 0:
        raise SystemExit("servings must be > 0")

    scaled_ingredients = [scale_ingredient(item) for item in ingredients]
    totals = {key: round(sum(item[key] for item in scaled_ingredients), 2) for key in MACRO_KEYS}
    per_serving = {key: round(value / servings, 2) for key, value in totals.items()}
    math_check = round((totals["protein_g"] * 4) + (totals["carbs_g"] * 4) + (totals["fat_g"] * 9), 2)

    return {
        "recipe_name": payload.get("recipe_name"),
        "servings": servings,
        "ingredients": scaled_ingredients,
        "totals": totals,
        "per_serving": per_serving,
        "mathematical_check": {
            "macro_kcal_from_protein_carbs_fat": math_check,
            "difference_vs_total_calories_kcal": round(math_check - totals["calories_kcal"], 2),
        },
    }


if __name__ == "__main__":
    print(json.dumps(compute(load_payload()), indent=2, sort_keys=True))
