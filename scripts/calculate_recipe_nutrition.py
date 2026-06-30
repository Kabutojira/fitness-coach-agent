#!/usr/bin/env python3
"""Compute total and per-serving recipe nutrition from explicit ingredient data or CSV state.

Explicit input JSON shape:
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
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from fitness_state.getters import get_rows
from fitness_state.setters import update_recipe

MACRO_KEYS = ("calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", help="Path to the recipe JSON file")
    parser.add_argument("--recipe-id")
    parser.add_argument("--from-state", action="store_true")
    parser.add_argument("--write-state", action="store_true")
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    return parser


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_state:
        if not args.recipe_id:
            raise SystemExit("--recipe-id is required with --from-state")
        recipes = {row.get("id"): row for row in get_rows("recipes", state_dir=args.state_dir)}
        recipe = recipes.get(args.recipe_id)
        if not recipe:
            raise SystemExit(f"recipe not found: {args.recipe_id}")
        ingredients = [row for row in get_rows("recipe_ingredients", state_dir=args.state_dir) if row.get("recipe_id") == args.recipe_id]
        if not ingredients:
            raise SystemExit(f"recipe has no recipe_ingredients snapshots: {args.recipe_id}")
        payload_ingredients = []
        for row in ingredients:
            payload_ingredients.append(
                {
                    "name": row.get("ingredient_name") or row.get("name") or "ingredient",
                    "quantity": row.get("quantity") or 0,
                    "unit": row.get("unit"),
                    "nutrition_basis": {
                        "type": row.get("basis_type"),
                        "quantity": row.get("basis_quantity") or 1,
                        "unit": row.get("basis_unit"),
                        "calories_kcal": row.get("calories_kcal") or 0,
                        "protein_g": row.get("protein_g") or 0,
                        "carbs_g": row.get("carbs_g") or 0,
                        "fat_g": row.get("fat_g") or 0,
                        "fiber_g": row.get("fiber_g") or 0,
                        "salt_g": row.get("salt_g") or 0,
                    },
                }
            )
        return {
            "recipe_id": args.recipe_id,
            "recipe_name": recipe.get("name"),
            "servings": recipe.get("servings") or 1,
            "ingredients": payload_ingredients,
        }

    if not args.input:
        raise SystemExit("input path is required unless --from-state is used")
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
    default_basis_quantity = 100.0 if basis_type == "per_100g" else 1.0
    basis_quantity = get_number(basis, "quantity") if basis.get("quantity") not in {None, ""} else default_basis_quantity
    unit = ingredient.get("unit")
    if basis_type == "per_100g":
        if unit != "g":
            raise SystemExit(f"Ingredient {name!r} uses per_100g basis but unit is {unit!r}, expected 'g'")
        multiplier = quantity / basis_quantity
    elif basis_type in {"per_unit", "per_package"}:
        multiplier = quantity / basis_quantity
    else:
        raise SystemExit(
            f"Ingredient {name!r} has unsupported nutrition_basis.type {basis_type!r}. "
            "Use per_100g, per_unit, or per_package."
        )

    scaled: dict[str, Any] = {key: round(get_number(basis, key) * multiplier, 2) for key in MACRO_KEYS}
    scaled["quantity"] = quantity
    scaled["unit"] = unit
    scaled["basis_type"] = basis_type
    scaled["basis_quantity"] = basis_quantity
    scaled["basis_unit"] = basis.get("unit")
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
        "recipe_id": payload.get("recipe_id"),
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


def maybe_write_state(result: dict[str, Any], *, state_dir: str) -> dict[str, Any] | None:
    recipe_id = result.get("recipe_id")
    if not recipe_id:
        return None
    return update_recipe(
        recipe_id,
        state_dir=state_dir,
        total_calories_kcal=result["totals"]["calories_kcal"],
        total_protein_g=result["totals"]["protein_g"],
        total_carbs_g=result["totals"]["carbs_g"],
        total_fat_g=result["totals"]["fat_g"],
        total_fiber_g=result["totals"]["fiber_g"],
        total_salt_g=result["totals"]["salt_g"],
        per_serving_calories_kcal=result["per_serving"]["calories_kcal"],
        per_serving_protein_g=result["per_serving"]["protein_g"],
        per_serving_carbs_g=result["per_serving"]["carbs_g"],
        per_serving_fat_g=result["per_serving"]["fat_g"],
        per_serving_fiber_g=result["per_serving"]["fiber_g"],
        per_serving_salt_g=result["per_serving"]["salt_g"],
        last_verified=date.today().isoformat(),
        llm_notes="Updated by calculate_recipe_nutrition.py --write-state",
    )


def main() -> None:
    args = build_parser().parse_args()
    result = compute(load_payload(args))
    if args.write_state:
        result["state_write"] = maybe_write_state(result, state_dir=args.state_dir)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
