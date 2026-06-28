# INSTALL.md

## Install

```bash
git clone <repo-url> fitness-coach-agent
cd fitness-coach-agent
bash scripts/bootstrap_user_state.sh
````

## Hermes usage

Use this repository as a Hermes profile/project folder.

Recommended mapping:

* `AGENTS.md` as main instruction file
* `SOUL.md` as personality file if supported
* `.agents/skills/` as skill folder
* `cron/` as scheduled task folder
* `state/` as private persistent user state

Keep `state/` private.

## Generic harness usage

Any harness can use this project if it can:

* read markdown files
* edit markdown files
* run scripts
* use skill instructions
* run daily/weekly jobs

## Optional integrations

This scaffold is markdown-first.

Optional future integrations:

* Alexa list read skill
* nutrition database search
* recipe search
* doctor search
* smartwatch import
* scale import
  EOF

cat > templates/USER_template.md <<'EOF'

# User Profile

Status: not_initialized

## Basic Data

* Name:
* Age:
* Sex:
* Height_cm:
* Current_weight_kg:
* Current_weight_date:
* Waist_cm:
* Waist_date:
* Current_city:
* Travel_context:

## Lifestyle

* Job_activity_level:
* Steps_per_day:
* Sleep_quality:
* Stress_level:
* Smoking:
* Alcohol_pattern:
* Eating_out_frequency:
* Cooking_time_available:
* Budget:
* Usual_supermarkets:
* Food_country_context:

## Health Context

* Diagnosed_conditions:
* Medications:
* Allergies:
* Intolerances:
* Injuries:
* Digestive_issues:
* Bloodwork_notes:
* Doctor_constraints:
* Dietitian_constraints:

## Diet Preferences

* Liked_foods:
* Disliked_foods:
* Preferred_cuisines:
* Meals_per_day:
* Breakfast_preference:
* Batch_cooking:
* Exact_grams_or_rounded:
* Hunger_pattern:
* Trigger_foods:
* Cheat_foods:

## Training Context

* Training_level:
* Current_training:
* Available_equipment:
* Days_per_week:
* Session_duration:
* Preferred_training:
* Current_lifts:
* Cardio_level:
* Injury_limitations:
* Sports:

## Data Freshness

* Last_weight_check:
* Last_waist_check:
* Last_progress_photo:
* Last_training_update:
* Last_diet_review:
* Last_bloodwork:
  EOF

cat > templates/goals_template.md <<'EOF'

# Goals

## Primary Goal

*

## Secondary Goals

*

## Target Outcome

* Target weight:
* Target waist:
* Target performance:
* Target date:
* Realistic milestone:
* Aggressive milestone:
* Conservative milestone:

## Behavior Goals

* Alcohol:
* Steps:
* Sleep:
* Training:
* Meal prep:
* Eating out:

## Current Assessment

*

## Constraints

*

## Success Metrics

*

