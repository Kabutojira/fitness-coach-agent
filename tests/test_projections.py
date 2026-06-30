import tempfile
import unittest
from datetime import date, timedelta

from scripts.fitness_state.projections import ensure_diet_plan_days, ensure_training_plan_days
from scripts.fitness_state.setters import add_health_note, add_target, upsert_daily_diet_history, upsert_daily_diet_plan, upsert_daily_training_history


class ProjectionsTest(unittest.TestCase):
    def test_diet_projection_compensates_within_bound_and_preserves_existing_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            add_target(
                state_dir=tmpdir,
                target_type="diet",
                effective_from=today.isoformat(),
                calories_kcal=2200,
                protein_g=160,
                carbs_g=240,
                fat_g=60,
                fiber_g=30,
                water_l=2.5,
            )
            for offset in range(7):
                upsert_daily_diet_history(
                    state_dir=tmpdir,
                    date=(today - timedelta(days=offset)).isoformat(),
                    calories_kcal=2700,
                    protein_g=160,
                )
            upsert_daily_diet_plan(
                state_dir=tmpdir,
                date=tomorrow.isoformat(),
                calories_kcal=2050,
                protein_g=160,
                carbs_g=210,
                fat_g=60,
                plan_summary="manual future",
            )

            rows = ensure_diet_plan_days(state_dir=tmpdir)
            first = next(row for row in rows if row["date"] == tomorrow.isoformat())
            second = next(row for row in rows if row["date"] == (tomorrow + timedelta(days=1)).isoformat())
            self.assertEqual(first["plan_summary"], "manual future")
            self.assertEqual(float(second["calories_kcal"]), 1980.0)
            self.assertEqual(float(second["protein_g"]), 160.0)
            self.assertGreaterEqual(float(second["fat_g"]), 30.0)
            self.assertGreaterEqual(float(second["carbs_g"]), 0.0)
            self.assertIn("remaining_uncompensated_delta", second["llm_notes"])

    def test_missing_history_does_not_overcompensate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            add_target(state_dir=tmpdir, target_type="diet", effective_from=today.isoformat(), calories_kcal=2200, protein_g=160, carbs_g=240, fat_g=60)
            rows = ensure_diet_plan_days(state_dir=tmpdir)
            first = next(row for row in rows if row["date"] == tomorrow.isoformat())
            self.assertEqual(float(first["calories_kcal"]), 2200.0)
            self.assertIn("recorded_history_days=0", first["llm_notes"])

    def test_training_projection_reschedules_missed_days_without_pain_spike(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today()
            add_target(state_dir=tmpdir, target_type="training", effective_from=today.isoformat(), training_days_per_week=3)
            upsert_daily_training_history(state_dir=tmpdir, date=today.isoformat(), trained="yes", training_type="strength")
            rows = ensure_training_plan_days(state_dir=tmpdir)
            planned_days = [row for row in rows if row["planned_training"] == "yes"]
            self.assertGreaterEqual(len(planned_days), 3)

            with_pain = tempfile.TemporaryDirectory()
            self.addCleanup(with_pain.cleanup)
            pain_dir = with_pain.name
            add_target(state_dir=pain_dir, target_type="training", effective_from=today.isoformat(), training_days_per_week=3)
            add_health_note(state_dir=pain_dir, date=today.isoformat(), note_type="pain", description="pain present", impact_on_training="pain")
            rows_with_pain = ensure_training_plan_days(state_dir=pain_dir)
            self.assertTrue(all("Pain/recovery notes present" in row["compensation_reason"] or row["compensation_reason"] == "Base training target" for row in rows_with_pain))


if __name__ == "__main__":
    unittest.main()
