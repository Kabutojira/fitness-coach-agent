# Ultimate Fitness Coach Agent

A single-user fitness coach agent with deterministic CSV state.

## Source of truth

`state/*.csv` is the only source of truth.

Rules:
- Do not treat chat history or legacy markdown files as authoritative when CSV state exists.
- Do not edit CSV files manually.
- All reads must go through getters or `scripts/get_state.py`.
- All writes must go through setters or `scripts/set_state.py`.
- Before any personalized diet plan, training plan, shopping list, target calculation, or adjustment, run `scripts/get_context.py` with the matching `--purpose`.
- If `get_context` reports blocked readiness, ask only for the missing fields and stop.

Legacy markdown files may still be present in `state/`, but they are obsolete and non-authoritative.

## State layout

The CSV files live directly under `state/`:

- `user_profile.csv`
- `goals.csv`
- `targets.csv`
- `body_stats.csv`
- `diet_history.csv`
- `training_history.csv`
- `diet_plan.csv`
- `training_plan.csv`
- `ingredients.csv`
- `recipes.csv`
- `recipe_ingredients.csv`
- `dietary_restrictions.csv`
- `health_notes.csv`
- `deviations.csv`
- `fridge_items.csv`
- `shopping_list.csv`
- `web_research.csv`

Every CSV includes deterministic metadata columns:

`id,created_at,updated_at,source,confidence,status,llm_notes`

## Deterministic helpers

- `scripts/get_state.py` reads CSV state in json, markdown, or csv format.
- `scripts/set_state.py` writes validated rows and daily upserts.
- `scripts/get_context.py` renders markdown context and readiness checks.
- `scripts/calculate_diet_targets.py` supports explicit CLI inputs and `--from-state` / `--write-state`.
- `scripts/calculate_recipe_nutrition.py` supports explicit JSON input and `--from-state` / `--write-state`.

## Projection behavior

`get_context` ensures the next 7 days of diet and training projection exist.

Diet projection:
- fills only missing future rows
- preserves existing future plan rows
- smooths past calorie over/undershoot across the next week
- caps daily compensation at 10% of daily calories
- preserves protein and avoids negative carbs/fats

Training projection:
- fills only missing future rows
- reschedules missed sessions conservatively
- avoids catch-up load spikes when pain or recovery concerns exist

## Testing

Run:

```bash
python3 -m pytest -q
```

Manual QA checklist:

- `qa/manual_csv_state_checklist.md`
