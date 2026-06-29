# Calculator Scripts

These helper scripts make the nutrition math deterministic.

## `calculate_diet_targets.py`

Computes:
- BMR
- TDEE
- calorie target
- protein, carbs, fat
- fiber
- hydration
- optional per-meal splits

Example:

```bash
python3 scripts/calculate_diet_targets.py \
  --age 35 \
  --sex male \
  --height-cm 180 \
  --weight-kg 80 \
  --activity-multiplier 1.55 \
  --goal fat_loss \
  --meals-per-day 4
```

Supported goals:
- `fat_loss`
- `recomposition`
- `maintenance`
- `muscle_gain`

Supported formulas:
- `mifflin_st_jeor` (default)
- `katch_mcardle` (requires `--body-fat-percent`)

## `calculate_recipe_nutrition.py`

Computes total and per-serving calories/macros from explicit ingredient inputs.

Example input JSON:

```json
{
  "recipe_name": "oats and yogurt",
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
    },
    {
      "name": "greek yogurt cup",
      "quantity": 2,
      "unit": "cup",
      "nutrition_basis": {
        "type": "per_unit",
        "calories_kcal": 120,
        "protein_g": 15,
        "carbs_g": 5,
        "fat_g": 0
      }
    }
  ]
}
```

Run it with:

```bash
python3 scripts/calculate_recipe_nutrition.py recipe.json
```

Supported nutrition basis types:
- `per_100g`
- `per_unit`
- `per_package`

## Regression test

```bash
python3 -m unittest tests/test_calculators.py
```
