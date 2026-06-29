# INSTALL.md

## Clone

```bash
git clone <repo-url> fitness-coach-agent
cd fitness-coach-agent
```

## What this repository contains

- `AGENTS.md`: primary operating instructions
- `SOUL.md`: high-level behavioral/personality constraints
- `templates/`: reusable markdown templates for user state, plans, reviews, ingredients, and recipes
- `state/`: live private user state at runtime
- `qa/`: manual regression safeguards

## Recommended runtime model

This repository is markdown-first. The agent should read and update files under `state/` on every real interaction.

Keep `state/` private.

## Bootstrap a fresh private state directory

Create the directories:

```bash
mkdir -p state/history state/ingredients state/recipes state/web_research
```

Copy the templates you want to initialize:

```bash
cp templates/diet_targets_template.md state/diet_targets.md
cp templates/next_7_days_diet_template.md state/next_7_days_diet.md
cp templates/next_7_days_training_template.md state/next_7_days_training.md
cp templates/fridge_list_template.md state/fridge_list.md
cp templates/to_buy_list_template.md state/to_buy_list.md
cp templates/todo_list_template.md state/todo_list.md
cp templates/ingredients_index_template.md state/ingredients_index.md
cp templates/recipes_index_template.md state/recipes_index.md
```

Then create the user-specific files that are not scaffolded yet, such as:

- `state/USER.md`
- `state/goals.md`
- `state/training_targets.md`
- `state/history/body_stats.md`
- `state/history/food_log.md`
- `state/history/training_log.md`
- `state/history/deviations.md`
- `state/history/health_notes.md`

Use `templates/ingredient_template.md` and `templates/recipe_template.md` whenever a recurring product, brand, or meal should be saved for reuse.

## Hermes usage

Recommended mapping:

- `AGENTS.md` as the main instruction file
- `SOUL.md` as the personality / behavior file if supported
- `state/` as private persistent user state
- `qa/` as manual validation guidance

## Generic harness requirements

Any compatible harness should be able to:

- read markdown files
- edit markdown files
- preserve state across sessions
- run daily/weekly review jobs if desired
- use web or nutrition lookup tools when precision matters

## Validation

After setup, manually verify the stat-gating behavior with:

- `qa/manual_stat_gating_checklist.md`

The repository does not currently include an executable test harness.
