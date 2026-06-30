# Manual CSV State Checklist

## First start

- Agent asks for missing required stats.
- Agent writes partial answers through setters.
- Incomplete rows are marked as incomplete.
- Agent does not generate a diet plan until get_context allows it.
- Agent does not generate a training plan until get_context allows it.

## State writes

- New body stats are written through setter.
- New diet history is written through setter.
- New training history is written through setter.
- New ingredient is written through setter.
- New recipe is written through setter.
- New deviation is written through setter.
- New plan rows are written through setter.

## Context

- Agent runs get_context before diet plan.
- Agent runs get_context before diet adjustment.
- Agent runs get_context before training plan.
- Agent runs get_context before training adjustment.
- Agent runs get_context before shopping list.
- Agent follows readiness check.

## Projection

- Missing next 7 days diet plan is generated.
- Missing next 7 days training plan is generated.
- Past week calorie excess is compensated next week.
- Compensation is bounded and realistic.
- Protein is preserved.
- Notes explain compensation.

## Determinism

- Same CSV state produces same context.
- Same calculator inputs produce same targets.
- Repeated recipes reuse saved CSV snapshots.
