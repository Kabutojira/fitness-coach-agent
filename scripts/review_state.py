#!/usr/bin/env python3
"""Write deterministic daily/weekly review artifacts for the fitness workspace.

The goal is to make scheduled reviews verifiable: the script creates the expected
state scaffold, writes the review file, optionally updates todo_list.md, and
prints machine-readable JSON describing exactly what changed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
import shutil
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"

DEFAULT_USER_MD = """# User Profile

Status: not_initialized

The agent must run first-start intake before creating the first full diet or training plan.
"""

DEFAULT_GOALS_MD = """# Goals

* Primary goal:
* Target outcome:
* Target date:
"""

DEFAULT_HISTORY_FILES = {
    "body_stats.md": "# Body Stats\n\n*\n",
    "food_log.md": "# Food Log\n\n*\n",
    "training_log.md": "# Training Log\n\n*\n",
    "deviations.md": "# Deviations\n\n*\n",
    "health_notes.md": "# Health Notes\n\n*\n",
}

TEMPLATE_COPIES = {
    "diet_targets_template.md": "diet_targets.md",
    "training_targets_template.md": "training_targets.md",
    "next_7_days_diet_template.md": "next_7_days_diet.md",
    "next_7_days_training_template.md": "next_7_days_training.md",
    "fridge_list_template.md": "fridge_list.md",
    "to_buy_list_template.md": "to_buy_list.md",
    "todo_list_template.md": "todo_list.md",
    "ingredients_index_template.md": "ingredients_index.md",
    "recipes_index_template.md": "recipes_index.md",
}

REQUIRED_STATS = {
    "USER.md": "first-start intake status and basic profile",
    "goals.md": "defined goal and target outcome",
    "history/body_stats.md": "current weight with date and body stats history",
    "history/food_log.md": "recent food logging",
    "history/training_log.md": "recent training logging",
    "history/deviations.md": "diet deviation history",
    "history/health_notes.md": "diet-relevant health constraints",
}


@dataclass
class ReviewResult:
    kind: str
    review_date: date
    report_path: Path
    changed_files: list[str]
    blockers: list[str]
    todo_updates: list[str]
    scaffolded_files: list[str]


class StateWorkspace:
    def __init__(self, state_root: Path):
        self.state_root = state_root
        self.changed_files: list[str] = []
        self.scaffolded_files: list[str] = []

    def rel(self, path: Path) -> str:
        return str(path.relative_to(self.state_root.parent))

    def mkdir(self, path: Path) -> None:
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            self.changed_files.append(self.rel(path))

    def write_if_missing(self, path: Path, content: str) -> None:
        if path.exists():
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        relative = self.rel(path)
        self.changed_files.append(relative)
        self.scaffolded_files.append(relative)

    def copy_template_if_missing(self, template_name: str, destination_name: str) -> None:
        destination = self.state_root / destination_name
        if destination.exists():
            return
        template = TEMPLATES / template_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, destination)
        relative = self.rel(destination)
        self.changed_files.append(relative)
        self.scaffolded_files.append(relative)

    def overwrite(self, path: Path, content: str) -> None:
        existing = path.read_text(encoding="utf-8") if path.exists() else None
        if existing == content:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.changed_files.append(self.rel(path))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", required=True, choices=["daily", "weekly"])
    parser.add_argument("--date", dest="review_date", help="ISO date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument(
        "--state-root",
        type=Path,
        default=ROOT / "state",
        help="Path to the workspace state directory. Defaults to ./state under the repo root.",
    )
    return parser.parse_args()


def parse_iso_date(raw: str | None) -> date:
    if raw is None:
        return date.today()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def ensure_state_layout(workspace: StateWorkspace) -> None:
    workspace.mkdir(workspace.state_root)
    for subdir in [
        workspace.state_root / "history",
        workspace.state_root / "history" / "daily_reviews",
        workspace.state_root / "history" / "weekly_reports",
        workspace.state_root / "ingredients",
        workspace.state_root / "recipes",
        workspace.state_root / "web_research",
    ]:
        workspace.mkdir(subdir)

    workspace.write_if_missing(workspace.state_root / "USER.md", DEFAULT_USER_MD)
    workspace.write_if_missing(workspace.state_root / "goals.md", DEFAULT_GOALS_MD)

    for filename, content in DEFAULT_HISTORY_FILES.items():
        workspace.write_if_missing(workspace.state_root / "history" / filename, content)

    for template_name, destination_name in TEMPLATE_COPIES.items():
        workspace.copy_template_if_missing(template_name, destination_name)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def has_meaningful_content(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    placeholder_lines = {
        "*",
        "* [ ] Complete first-start intake.",
        "* [ ] Update current weight.",
        "* [ ] Update fridge list.",
        "* [ ] Define primary goal.",
        "* Primary goal:",
        "* Target outcome:",
        "* Target date:",
    }
    real_lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    return any(
        line not in placeholder_lines
        and not line.startswith("#")
        and line != "##"
        and not line.endswith(":")
        for line in real_lines
    )


def detect_blockers(state_root: Path) -> list[str]:
    blockers: list[str] = []
    user_text = read_text(state_root / "USER.md")
    if "Status: not_initialized" in user_text:
        blockers.append("state/USER.md still says Status: not_initialized")

    for relative_path, description in REQUIRED_STATS.items():
        path = state_root / relative_path
        display_path = f"state/{relative_path}"
        if not path.exists():
            blockers.append(f"missing {display_path} ({description})")
            continue
        if relative_path != "USER.md" and not has_meaningful_content(read_text(path)):
            blockers.append(f"placeholder-only {display_path} ({description})")

    fridge_text = read_text(state_root / "fridge_list.md")
    if not has_meaningful_content(fridge_text):
        blockers.append("fridge inventory is still empty or placeholder-only")

    body_stats = read_text(state_root / "history" / "body_stats.md").lower()
    if "waist" not in body_stats:
        blockers.append("waist measurement not recorded in state/history/body_stats.md")

    return blockers


def derive_todo_updates(blockers: Iterable[str]) -> list[str]:
    updates: list[str] = []
    blocker_text = "\n".join(blockers)
    if "Status: not_initialized" in blocker_text:
        updates.append("Complete first-start intake.")
    if "body_stats.md" in blocker_text:
        updates.append("Record current weight with date in state/history/body_stats.md.")
    if "waist measurement" in blocker_text:
        updates.append("Add a waist measurement to state/history/body_stats.md.")
    if "food_log.md" in blocker_text:
        updates.append("Log at least 3 detailed intake days, including alcohol/eat-out days.")
    if "training_log.md" in blocker_text:
        updates.append("Log at least 3 training sessions with exercises, loads, reps, and RPE/RIR.")
    if "fridge inventory" in blocker_text:
        updates.append("Update state/fridge_list.md with the current fridge inventory.")
    if "goals.md" in blocker_text:
        updates.append("Define the primary goal and target outcome in state/goals.md.")
    return updates


def merge_todo_updates(existing_text: str, updates: list[str]) -> str:
    if not updates:
        return existing_text

    lines = existing_text.splitlines()
    active_heading = next((i for i, line in enumerate(lines) if line.strip() == "## Active"), None)
    if active_heading is None:
        lines = ["# Todo List", "", "## Active", ""] + lines
        active_heading = 2

    insert_at = active_heading + 1
    while insert_at < len(lines) and (not lines[insert_at].startswith("## ")):
        insert_at += 1

    existing_items = {line.strip() for line in lines}
    new_lines = []
    for update in updates:
        bullet = f"* [ ] {update}"
        if bullet not in existing_items:
            new_lines.append(bullet)
    if not new_lines:
        return existing_text

    if insert_at > active_heading + 1 and lines[insert_at - 1] != "":
        new_lines.insert(0, "")
    if insert_at < len(lines) and new_lines and lines[insert_at - 1] != "":
        new_lines.append("")

    merged = lines[:insert_at] + new_lines + lines[insert_at:]
    return "\n".join(merged).rstrip() + "\n"


def render_daily(review_date: date, blockers: list[str], todo_updates: list[str]) -> str:
    blocker_lines = [f"* {item}" for item in blockers] if blockers else ["* No blocking stat gaps detected."]
    todo_lines = [f"* Added/confirmed todo: {item}" for item in todo_updates] if todo_updates else ["* No todo changes needed."]
    guidance = (
        "* Do not recalculate personalized diet/training/shopping targets until the blockers above are cleared."
        if blockers
        else "* Personalized recalculation can proceed because the required state files are present."
    )
    return f"""# Daily Review

## Date

* {review_date.isoformat()}

## Today Diet

* No deterministic diet adjustment was made by the script. Review `state/history/food_log.md` manually if new intake was logged.

## Today Training

* No deterministic training adjustment was made by the script. Review `state/history/training_log.md` manually if new training was logged.

## Fridge Status

* Checked whether `state/fridge_list.md` exists and contains more than placeholder scaffolding.

## Shopping Status

* Checked whether `state/to_buy_list.md` exists so scheduled reviews have a writable shopping artifact.

## Ingredient And Recipe Memory Updates

* No ingredient or recipe files were modified by this script.
* If recurring foods were discussed in chat, save them separately under `state/ingredients/` or `state/recipes/`.
* Estimates still need explicit brand/label confirmation when precision matters.

## Deviations To Recover

* No deviation recovery was auto-applied. Use `state/history/deviations.md` for actual logged deviations.

## Required Stat Check

{chr(10).join(blocker_lines)}

## Todo Updates

{chr(10).join(todo_lines)}

## Message To User

{guidance}
"""


def render_weekly(review_date: date, blockers: list[str], todo_updates: list[str]) -> str:
    start = review_date - timedelta(days=6)
    blocker_bullets = [f"* {item}" for item in blockers] if blockers else ["* No blocking stat gaps detected."]
    action_bullets = [f"* {item}" for item in todo_updates] if todo_updates else ["* No new actions added."]
    summary = (
        "* Personalized weekly recalculation is deferred because the required state is missing, placeholder-only, or stale."
        if blockers
        else "* Required state files are present; personalized weekly recalculation can be reviewed manually."
    )
    return f"""# Weekly Report

## Period

* From: {start.isoformat()}
* To: {review_date.isoformat()}

## Executive Summary

{summary}

## Goal Progress

* No deterministic goal-progress calculation is attempted here without explicit up-to-date measurements.

## Body Stats

{chr(10).join(blocker_bullets)}

## Diet Adherence

* Review `state/history/food_log.md` manually once enough dated entries exist.

## Macro Quality

* No macro-quality score is generated by this script; it only verifies that the required artifacts exist.

## Micronutrient Quality

* No micronutrient-quality score is generated by this script; it only verifies that the required artifacts exist.

## Alcohol

* Alcohol review is deferred to actual dated food/deviation logs.

## Training Progress

* Review `state/history/training_log.md` manually once enough detailed sessions exist.

## Recovery

* Recovery review is deferred until consistent health/training notes exist.

## What Worked

* The scheduled review now writes a real report artifact and can bootstrap missing state scaffolding.

## What Failed

* The previous free-form review flow could report changes without leaving verifiable files on disk.

## Plan Changes

* No personalized targets were changed by this deterministic script.

## Next Week Actions

{chr(10).join(action_bullets)}
"""


def unique_preserving_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def run_review(kind: str, review_date: date, state_root: Path) -> ReviewResult:
    workspace = StateWorkspace(state_root.resolve())
    ensure_state_layout(workspace)

    blockers = detect_blockers(workspace.state_root)
    todo_updates = derive_todo_updates(blockers)

    todo_path = workspace.state_root / "todo_list.md"
    merged_todo = merge_todo_updates(read_text(todo_path), todo_updates)
    workspace.overwrite(todo_path, merged_todo)

    if kind == "daily":
        report_path = workspace.state_root / "history" / "daily_reviews" / f"{review_date.isoformat()}.md"
        report = render_daily(review_date, blockers, todo_updates)
    else:
        report_path = workspace.state_root / "history" / "weekly_reports" / f"{review_date.isoformat()}.md"
        report = render_weekly(review_date, blockers, todo_updates)

    workspace.overwrite(report_path, report)
    workspace.changed_files = unique_preserving_order(workspace.changed_files)
    workspace.scaffolded_files = unique_preserving_order(workspace.scaffolded_files)

    return ReviewResult(
        kind=kind,
        review_date=review_date,
        report_path=report_path,
        changed_files=workspace.changed_files,
        blockers=blockers,
        todo_updates=todo_updates,
        scaffolded_files=workspace.scaffolded_files,
    )


def main() -> None:
    args = parse_args()
    result = run_review(args.kind, parse_iso_date(args.review_date), args.state_root)
    print(
        json.dumps(
            {
                "kind": result.kind,
                "review_date": result.review_date.isoformat(),
                "report_path": str(result.report_path),
                "report_exists": result.report_path.exists(),
                "changed_files": result.changed_files,
                "scaffolded_files": result.scaffolded_files,
                "blockers": result.blockers,
                "todo_updates": result.todo_updates,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
