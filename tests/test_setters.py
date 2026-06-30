import csv
import tempfile
import unittest
from pathlib import Path

from scripts.fitness_state.setters import (
    add_goal,
    add_target,
    set_user_profile,
    upsert_daily_body_stats,
    upsert_daily_diet_history,
    upsert_daily_training_history,
)


class SettersTest(unittest.TestCase):
    def test_allows_incomplete_rows_and_marks_incomplete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            profile = set_user_profile(state_dir=tmpdir, name="Alex", sex="male")
            body = upsert_daily_body_stats(state_dir=tmpdir, date="2026-06-30", weight_kg=80)
            self.assertTrue(profile["ok"])
            self.assertEqual(profile["status"], "incomplete")
            self.assertTrue(body["ok"])
            self.assertEqual(body["status"], "incomplete")

    def test_rejects_invalid_structural_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            invalid_date = upsert_daily_body_stats(state_dir=tmpdir, date="2026-99-30", weight_kg=80)
            self.assertFalse(invalid_date["ok"])
            self.assertIn("invalid date format", " ".join(invalid_date["errors"]))

            invalid_enum = add_goal(state_dir=tmpdir, goal_type="bad_goal", goal_description="x")
            self.assertFalse(invalid_enum["ok"])
            self.assertIn("invalid enum", " ".join(invalid_enum["errors"]))

            negative_weight = upsert_daily_body_stats(state_dir=tmpdir, date="2026-06-30", weight_kg=-1)
            self.assertFalse(negative_weight["ok"])
            self.assertIn("negative weight", " ".join(negative_weight["errors"]))

            negative_calories = add_target(state_dir=tmpdir, target_type="diet", effective_from="2026-06-30", calories_kcal=-1)
            self.assertFalse(negative_calories["ok"])
            self.assertIn("negative calories", " ".join(negative_calories["errors"]))

    def test_upserts_daily_rows_and_preserves_notes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            note = 'line1\nline2, "quoted"'
            first = upsert_daily_diet_history(state_dir=tmpdir, date="2026-06-30", calories_kcal=2000, protein_g=150, llm_notes=note)
            second = upsert_daily_diet_history(state_dir=tmpdir, date="2026-06-30", calories_kcal=2200, protein_g=155, llm_notes=note)
            self.assertEqual(first["id"], second["id"])

            training = upsert_daily_training_history(state_dir=tmpdir, date="2026-06-30", trained="yes", training_type="strength")
            self.assertTrue(training["ok"])

            history_path = Path(tmpdir) / "diet_history.csv"
            with history_path.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["calories_kcal"], "2200")
            self.assertEqual(rows[0]["llm_notes"], note)


if __name__ == "__main__":
    unittest.main()
