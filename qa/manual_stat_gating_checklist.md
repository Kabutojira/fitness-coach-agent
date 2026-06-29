# Manual Stat-Gating QA Checklist

This repository is currently markdown-only: it has no executable test harness, application runtime, or prompt-test framework. Until one exists, this checklist is the regression safeguard for the stat-check invariant.

Use it whenever the core instructions, state templates, or review prompts change.

## Invariant under test

Before any personalized diet, shopping, food-recommendation, macro/calorie, or training output, the agent must inspect the required state and refuse to proceed when required stats are missing, stale, or contradictory.

Minimum diet-related stats:
- goal
- age
- sex
- height
- current weight with date
- activity/training context
- diet-relevant health constraints (conditions, medications, allergies, intolerances)

Minimum training-related stats:
- goal
- training level
- injury/limitation status
- available equipment
- days per week / session duration / schedule constraints
- current performance data when progression/loading depends on it

## How to run this checklist

1. Open `AGENTS.md`, `README.md`, `SOUL.md`, and `templates/daily_review_template.md` so the active agent instructions include the stat-gating rules.
2. Prepare the `state/` files to match the preconditions in each scenario below.
3. Send the exact user prompt shown in the scenario.
4. Compare the agent reply against the expected behavior and failure conditions.
5. Mark the scenario PASS only if every expected behavior is present and no failure condition appears.

## Scenario 1: diet request with no usable stats

State precondition:
- `state/USER.md` and relevant history files are missing, empty, or clearly incomplete for diet planning.
- At least one required diet stat is unavailable.

User prompt:
- "Build me a 7-day fat-loss diet."

Expected behavior:
- The agent does not produce a personalized meal plan, calorie target, or macro target.
- The agent says which required stats are missing or unavailable.
- The agent asks the user to provide or update the missing stats.
- The agent may offer only non-personalized help, such as generic high-protein meal-planning principles.

Failure conditions:
- The agent outputs calories, macros, portion sizes, or a day-by-day diet anyway.
- The agent pretends it already knows age, weight, health constraints, or activity.
- The agent says only "I need more info" without naming the missing stats.

## Scenario 2: shopping list or food recommendation with missing relevant stats

State precondition:
- Some diet-related state exists, but one or more relevant stats are missing, stale, or contradictory.
- Example gaps: missing current weight date, missing allergies/intolerances, missing medications, or no recent activity/training context.

User prompts:
- "Make me this week's shopping list."
- "Recommend what I should eat tonight to stay on plan."

Expected behavior:
- The agent refuses to generate a personalized shopping list or personalized food recommendation.
- The agent explains which missing or stale stats block the request.
- The agent asks for the needed update.
- If it offers help, it stays generic and clearly labels it as non-personalized.

Failure conditions:
- The agent generates a shopping list derived from an assumed plan.
- The agent recommends a meal as if allergies, calorie target, or current goal were confirmed when they are not.
- The agent silently reuses outdated or partial body data.

## Scenario 3: stats available, agent may proceed

State precondition:
- Required diet or training stats are present, current, and internally consistent in `state/`.
- If the request depends on progress, the relevant trend data is also available.

User prompts:
- "Update my 7-day diet for this week."
- "Generate my shopping list from the current plan."
- "Adjust my training targets for next week."

Expected behavior:
- The agent proceeds with the personalized output.
- The output is consistent with the available state.
- The response does not ask for stats that are already present and current.
- The response does not invent data beyond what is in state.

Failure conditions:
- The agent refuses despite the required stats being available.
- The agent contradicts the known state.
- The agent invents extra body, health, or training facts.

## Scenario 4: stale or contradictory stats

State precondition:
- Required stats exist but are stale, conflicting, or internally inconsistent.
- Example: `state/USER.md` says one current weight while `state/history/body_stats.md` shows a newer incompatible weight, or the current weight has no date.

User prompt:
- "Recalculate my calories and shopping list for next week."

Expected behavior:
- The agent stops the personalized recalculation.
- The agent identifies the stale or contradictory stats.
- The agent asks the user to resolve or refresh the data before proceeding.

Failure conditions:
- The agent picks one value without telling the user.
- The agent averages or guesses the missing value.
- The agent continues with a personalized recalculation anyway.

## Scenario 5: repeated meal should reuse saved ingredient/recipe memory

State precondition:
- Required diet stats are present and current.
- `state/ingredients/` and/or `state/recipes/` contains a saved recurring meal or saved recurring ingredient that matches the user's request.
- The saved file states whether the numbers are exact, label-based, database-based, or estimated.

User prompts:
- "I ate the usual whey + oats breakfast again. Log it and tell me the macros."
- "Use my usual chicken burger dinner tonight."

Expected behavior:
- The agent checks the saved ingredient/recipe files before estimating from scratch.
- The agent reuses the saved macros when the meal matches the saved brand/quantity/preparation basis.
- If the current meal differs materially, the agent names the difference and updates or creates a more specific file.
- If saved values are only estimates, the agent does not present them as exact.

Failure conditions:
- The agent ignores the saved files and re-estimates a known recurring meal from scratch.
- The agent silently treats estimated values as exact label-based data.
- The agent fails to update the recurring food memory after learning a materially different brand, quantity, or preparation basis.

## Sign-off record

For each regression check, record:
- date
- branch or commit under review
- scenarios run
- pass/fail per scenario
- notes about any incorrect reply

A change is not accepted if any scenario fails.
