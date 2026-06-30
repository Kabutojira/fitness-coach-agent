from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path

from .schemas import DAILY_DATE_FIELDS, SCHEMAS, TABLE_FILES


class CSVStore:
    def __init__(self, state_dir: str | Path = "state") -> None:
        self.state_dir = Path(state_dir)

    def path_for(self, table: str) -> Path:
        return self.state_dir / TABLE_FILES[table]

    def initialize_all(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        for table in SCHEMAS:
            self.ensure_file(table)

    def ensure_file(self, table: str) -> Path:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        path = self.path_for(table)
        if not path.exists():
            self._atomic_write(table, [])
        return path

    def read_rows(self, table: str) -> list[dict[str, str]]:
        path = self.ensure_file(table)
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))

    def write_rows(self, table: str, rows: list[dict[str, str]]) -> None:
        self.ensure_file(table)
        self._atomic_write(table, rows)

    def append_row(self, table: str, row: dict[str, str]) -> dict[str, str]:
        normalized = self._normalize_row(table, row)
        rows = self.read_rows(table)
        rows.append(normalized)
        self.write_rows(table, rows)
        return normalized

    def update_row_by_id(self, table: str, row_id: str, updates: dict[str, str]) -> dict[str, str]:
        rows = self.read_rows(table)
        normalized_updates = self._normalize_partial(table, updates)
        for row in rows:
            if row.get("id") == row_id:
                row.update(normalized_updates)
                self.write_rows(table, rows)
                return row
        raise KeyError(f"{table} row not found: {row_id}")

    def upsert_daily_row(self, table: str, row: dict[str, str]) -> dict[str, str]:
        date_field = DAILY_DATE_FIELDS.get(table)
        if not date_field:
            raise ValueError(f"{table} is not a daily table")
        normalized = self._normalize_row(table, row)
        match = normalized.get(date_field, "")
        rows = self.read_rows(table)
        for existing in rows:
            if existing.get(date_field) == match:
                created_at = existing.get("created_at")
                existing.update(normalized)
                if created_at:
                    existing["created_at"] = created_at
                self.write_rows(table, rows)
                return existing
        rows.append(normalized)
        self.write_rows(table, rows)
        return normalized

    def archive_row(self, table: str, row_id: str) -> dict[str, str]:
        return self.update_row_by_id(table, row_id, {"status": "archived"})

    def active_rows(self, table: str) -> list[dict[str, str]]:
        return [row for row in self.read_rows(table) if row.get("status") not in {"inactive", "archived"}]

    def filter_date_range(
        self,
        table: str,
        start: str | None = None,
        end: str | None = None,
        date_field: str | None = None,
    ) -> list[dict[str, str]]:
        field = date_field or DAILY_DATE_FIELDS.get(table, "date")
        rows = []
        for row in self.read_rows(table):
            value = row.get(field, "")
            if not value:
                continue
            if start and value < start:
                continue
            if end and value > end:
                continue
            rows.append(row)
        return rows

    def _normalize_row(self, table: str, row: dict[str, str | int | float | None]) -> dict[str, str]:
        ordered: dict[str, str] = {}
        for column in SCHEMAS[table]:
            value = row.get(column, "")
            ordered[column] = "" if value is None else str(value)
        return ordered

    def _normalize_partial(self, table: str, row: dict[str, str | int | float | None]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for column, value in row.items():
            if column not in SCHEMAS[table]:
                continue
            normalized[column] = "" if value is None else str(value)
        return normalized

    def _atomic_write(self, table: str, rows: list[dict[str, str]]) -> None:
        path = self.path_for(table)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=path.name, dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=SCHEMAS[table], extrasaction="ignore")
                writer.writeheader()
                for row in rows:
                    writer.writerow(self._normalize_row(table, row))
            os.replace(tmp_name, path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
