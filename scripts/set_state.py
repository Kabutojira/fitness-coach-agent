#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from fitness_state import setters


STATE_DEFAULT = str(Path(__file__).resolve().parents[1] / "state")


SetterFn = Callable[..., dict[str, Any]]


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-dir", default=STATE_DEFAULT)
    parser.add_argument("--source", default="agent")
    parser.add_argument("--confidence", default="unknown")
    parser.add_argument("--status")
    parser.add_argument("--llm-notes", default="")


def _payload(args: argparse.Namespace, fields: list[str]) -> dict[str, Any]:
    payload = {
        "source": args.source,
        "confidence": args.confidence,
        "llm_notes": args.llm_notes,
    }
    if args.status:
        payload["status"] = args.status
    for field in fields:
        value = getattr(args, field)
        if value is not None:
            payload[field] = value
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Write deterministic fitness CSV state")
    sub = parser.add_subparsers(dest="table", required=True)

    user_profile = sub.add_parser("user_profile")
    user_profile_sub = user_profile.add_subparsers(dest="command", required=True)
    user_profile_set = user_profile_sub.add_parser("set")
    _common(user_profile_set)
    for arg in ("name", "age", "sex", "height_cm", "country", "timezone"):
        user_profile_set.add_argument(f"--{arg.replace('_', '-')}")

    body_stats = sub.add_parser("body_stats")
    body_stats_sub = body_stats.add_subparsers(dest="command", required=True)
    body_stats_upsert = body_stats_sub.add_parser("upsert-daily")
    _common(body_stats_upsert)
    body_stats_upsert.add_argument("--date", required=True)
    for arg in ("weight_kg", "waist_cm", "body_fat_percent", "resting_hr", "sleep_hours", "steps", "measurement_notes"):
        body_stats_upsert.add_argument(f"--{arg.replace('_', '-')}")

    diet_history = sub.add_parser("diet_history")
    diet_history_sub = diet_history.add_subparsers(dest="command", required=True)
    diet_history_upsert = diet_history_sub.add_parser("upsert-daily")
    _common(diet_history_upsert)
    diet_history_upsert.add_argument("--date", required=True)
    for arg in ("calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g", "water_l", "alcohol_units", "adherence_score", "summary"):
        diet_history_upsert.add_argument(f"--{arg.replace('_', '-')}")

    training_history = sub.add_parser("training_history")
    training_history_sub = training_history.add_subparsers(dest="command", required=True)
    training_history_upsert = training_history_sub.add_parser("upsert-daily")
    _common(training_history_upsert)
    training_history_upsert.add_argument("--date", required=True)
    for arg in ("trained", "session_name", "training_type", "duration_min", "volume_summary", "intensity_summary", "steps", "cardio_min", "pain_notes", "performance_notes"):
        training_history_upsert.add_argument(f"--{arg.replace('_', '-')}")

    targets = sub.add_parser("targets")
    targets_sub = targets.add_subparsers(dest="command", required=True)
    targets_add = targets_sub.add_parser("add")
    _common(targets_add)
    for arg in ("effective_from", "effective_to", "target_type", "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "water_l", "steps", "training_days_per_week", "calculation_method"):
        targets_add.add_argument(f"--{arg.replace('_', '-')}")

    ingredient = sub.add_parser("ingredient")
    ingredient_sub = ingredient.add_subparsers(dest="command", required=True)
    ingredient_add = ingredient_sub.add_parser("add")
    _common(ingredient_add)
    for arg in ("name", "brand", "barcode", "basis_type", "basis_quantity", "basis_unit", "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g", "source_url", "last_verified"):
        ingredient_add.add_argument(f"--{arg.replace('_', '-')}")

    shopping = sub.add_parser("shopping_list")
    shopping_sub = shopping.add_subparsers(dest="command", required=True)
    shopping_add = shopping_sub.add_parser("add")
    _common(shopping_add)
    for arg in ("item_name", "ingredient_id", "quantity", "unit", "reason", "needed_by", "purchased"):
        shopping_add.add_argument(f"--{arg.replace('_', '-')}")
    shopping_mark = shopping_sub.add_parser("mark-purchased")
    shopping_mark.add_argument("--id", required=True)
    shopping_mark.add_argument("--state-dir", default=STATE_DEFAULT)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    dispatch: dict[tuple[str, str], tuple[SetterFn, list[str], str | None]] = {
        ("user_profile", "set"): (setters.set_user_profile, ["name", "age", "sex", "height_cm", "country", "timezone"], None),
        ("body_stats", "upsert-daily"): (setters.upsert_daily_body_stats, ["weight_kg", "waist_cm", "body_fat_percent", "resting_hr", "sleep_hours", "steps", "measurement_notes"], "date"),
        ("diet_history", "upsert-daily"): (setters.upsert_daily_diet_history, ["calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g", "water_l", "alcohol_units", "adherence_score", "summary"], "date"),
        ("training_history", "upsert-daily"): (setters.upsert_daily_training_history, ["trained", "session_name", "training_type", "duration_min", "volume_summary", "intensity_summary", "steps", "cardio_min", "pain_notes", "performance_notes"], "date"),
        ("targets", "add"): (setters.add_target, ["effective_from", "effective_to", "target_type", "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "water_l", "steps", "training_days_per_week", "calculation_method"], None),
        ("ingredient", "add"): (setters.add_ingredient, ["name", "brand", "barcode", "basis_type", "basis_quantity", "basis_unit", "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "salt_g", "source_url", "last_verified"], None),
        ("shopping_list", "add"): (setters.add_shopping_item, ["item_name", "ingredient_id", "quantity", "unit", "reason", "needed_by", "purchased"], None),
    }

    if (args.table, args.command) == ("shopping_list", "mark-purchased"):
        result = setters.mark_shopping_item_purchased(args.id, state_dir=args.state_dir)
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    fn, fields, date_field = dispatch[(args.table, args.command)]
    payload = _payload(args, fields)
    kwargs = {"state_dir": args.state_dir, **payload}
    if date_field:
        kwargs[date_field] = getattr(args, date_field)
    result = fn(**kwargs)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
