import csv
import tempfile
import unittest
from pathlib import Path

from scripts.fitness_state.csv_store import CSVStore
from scripts.fitness_state.schemas import COMMON_FIELDS, SCHEMAS


class CSVStoreTest(unittest.TestCase):
    def test_initialize_creates_all_csv_files_with_headers(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)
            store.initialize_all()

            for table, schema in SCHEMAS.items():
                path = Path(tmpdir) / f"{table}.csv"
                self.assertTrue(path.exists(), table)
                with path.open("r", encoding="utf-8", newline="") as handle:
                    header = next(csv.reader(handle))
                self.assertEqual(header, schema)
                for field in COMMON_FIELDS:
                    self.assertIn(field, header)

    def test_append_and_update_preserve_stable_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = CSVStore(tmpdir)
            store.initialize_all()
            row = {
                "id": "ingredient_1",
                "created_at": "2026-06-30T00:00:00",
                "updated_at": "2026-06-30T00:00:00",
                "source": "agent",
                "confidence": "high",
                "status": "active",
                "llm_notes": "line1\nline2, \"quoted\"",
                "name": "Greek yogurt",
                "basis_type": "per_100g",
            }
            store.append_row("ingredients", row)
            saved = store.read_rows("ingredients")
            self.assertEqual(saved[0]["llm_notes"], row["llm_notes"])
            store.update_row_by_id("ingredients", "ingredient_1", {"brand": "Fage"})
            updated = store.read_rows("ingredients")
            self.assertEqual(updated[0]["brand"], "Fage")


if __name__ == "__main__":
    unittest.main()
