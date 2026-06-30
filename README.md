# Ultimate Fitness Coach Agent

A single-user, markdown-first fitness coach agent for Hermes or any compatible agent harness.

## Purpose

The agent acts as a stateful personal fitness coach with dietologist-level nutrition behavior, training planning, training progress tracking, fridge/shopping awareness, recipe support, photo-based food/fridge analysis, and adaptive weekly planning.

## Core behavior

- Ask user goals first.
- Collect enough personal, health, diet, lifestyle, and training data before creating the first plan.
- Before any later personalized diet, shopping, training, macro, calorie, or body-composition output, re-check the required stats from `state/` instead of assuming prior context is still sufficient.
- If required stats are missing, stale, or contradictory, do not generate the personalized plan anyway; tell the user what is missing and ask for the update.
- Maintain state in markdown files.
- Persist recurring ingredients/products and recurring recipes in markdown files so repeated meals can reuse known stats instead of being re-estimated each time.
- Generate diet and training plans.
- Update plans after real-life deviations.
- Use web/nutrition databases when precision matters.
- Search recipes and nutrition references online when useful.
- Track training progress.
- Keep fridge, shopping list, todo list, and reports current.
- Use medical-style triage when symptoms or injury questions appear.
- Escalate to professional care when the agent judges risk is material.

## Runtime targets

Primary: Hermes Agent  
Secondary: any harness able to read markdown context files, use skills, run scripts, and execute scheduled tasks.

## Source of truth

The source of truth is `state/`.

Do not treat chat history as sufficient when state files exist.

Personalized plans, meal plans, shopping lists, calorie/macro targets, and training prescriptions are stat-gated outputs: the agent must check the required user stats in state first and must ask for missing stats instead of guessing.

When the runtime can execute Python, use the deterministic helper scripts in `scripts/` for nutrition math instead of free-form LLM arithmetic:

- `scripts/calculate_diet_targets.py` computes BMR, TDEE, calorie targets, macros, fiber, hydration, and optional per-meal splits from explicit user stats.
- `scripts/calculate_recipe_nutrition.py` computes total and per-serving recipe nutrition from explicit ingredient quantities and nutrition bases.
- `tests/test_calculators.py` is the executable regression check for those scripts.

Recurring food memory should also live in `state/`, typically under:

- `state/ingredients/` for product/brand files
- `state/recipes/` for recurring meals and batch-cooked dishes
- optional `state/ingredients_index.md` and `state/recipes_index.md` catalogs

If the agent knows a meal is repeated, it should look for saved ingredient/recipe files before estimating from scratch. Brand-specific data should be saved with source and confidence notes.

## QA safeguard

The repository includes deterministic helper scripts for nutrition math and scheduled review artifact creation. Use them whenever the harness can run Python so state mutations are verifiable instead of being left to free-form model output.

- `scripts/calculate_diet_targets.py`
- `scripts/calculate_recipe_nutrition.py`
- `scripts/review_state.py`

The manual checklist at `qa/manual_stat_gating_checklist.md` is still useful for prompt/harness validation, but scheduled daily/weekly reviews should prefer `scripts/review_state.py` so the expected files are actually written and can be verified on disk.
