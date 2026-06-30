#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from fitness_state.getters import get_table
from fitness_state.schemas import DAILY_DATE_FIELDS, SCHEMAS


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read deterministic fitness CSV state")
    parser.add_argument("table", choices=sorted(SCHEMAS))
    parser.add_argument("--format", choices=["json", "markdown", "csv"], default="json")
    parser.add_argument("--state-dir", default=str(Path(__file__).resolve().parents[1] / "state"))
    parser.add_argument("--active", action="store_true")
    parser.add_argument("--id")
    parser.add_argument("--date")
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--last", type=int)
    parser.add_argument("--next", dest="next_days", type=int)
    parser.add_argument("--search")
    return parser.parse_args()


def _date_field(table: str) -> str | None:
    if table in DAILY_DATE_FIELDS:
        return DAILY_DATE_FIELDS[table]
    for candidate in ("effective_from", "checked_on", "last_verified", "needed_by", "expires_on"):
        if candidate in SCHEMAS[table]:
            return candidate
    return None


def _filter_rows(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    if args.active:
        rows = [row for row in rows if row.get("status") == "active"]
    if args.id:
        rows = [row for row in rows if row.get("id") == args.id]

    date_field = _date_field(args.table)
    if args.date and date_field:
        rows = [row for row in rows if row.get(date_field) == args.date]
    if args.date_from and date_field:
        rows = [row for row in rows if row.get(date_field, "") >= args.date_from]
    if args.date_to and date_field:
        rows = [row for row in rows if row.get(date_field, "") <= args.date_to]

    if args.search:
        needle = args.search.lower()
        rows = [row for row in rows if any(needle in str(value).lower() for value in row.values())]

    if date_field:
        rows.sort(key=lambda row: row.get(date_field, ""))
    else:
        rows.sort(key=lambda row: (row.get("updated_at", ""), row.get("created_at", ""), row.get("id", "")))

    if args.last is not None:
        rows = rows[-args.last :]
    if args.next_days is not None:
        rows = rows[: args.next_days]
    return rows


def _as_json(rows: list[dict[str, str]]) -> str:
    return json.dumps(rows, indent=2, sort_keys=True)


def _as_markdown(table: str, rows: list[dict[str, str]]) -> str:
    lines = [f"# {table}", ""]
    if not rows:
        lines.append("- no rows")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"- id={row.get('id', '')}")
        for key, value in row.items():
            if key == "id" or value in {"", None}:
                continue
            lines.append(f"  - {key}: {value}")
    return "\n".join(lines)


def _as_csv(table: str, rows: list[dict[str, str]]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SCHEMAS[table], extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in SCHEMAS[table]})
    return buffer.getvalue().rstrip()


def main() -> None:
    args = _parse_args()
    rows = get_table(args.table, state_dir=args.state_dir)
    rows = _filter_rows(rows, args)

    if args.format == "json":
        print(_as_json(rows))
    elif args.format == "markdown":
        print(_as_markdown(args.table, rows))
    else:
        print(_as_csv(args.table, rows))


if __name__ == "__main__":
    main()
