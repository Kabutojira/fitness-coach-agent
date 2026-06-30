import tempfile
import unittest
from datetime import date

from scripts.fitness_state.context import get_context, get_context_data
from scripts.fitness_state.setters import (
    add_dietary_restriction,
    add_goal,
    add_health_note,
    add_target,
    set_user_profile,
    upsert_daily_body_stats,
    upsert_daily_diet_history,
    upsert_daily_training_history,
)


class ContextTest(unittest.TestCase):
    def test_outputs_markdown_and_generates_missing_projections(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today().isoformat()
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180, llm_notes="activity_multiplier=1.55; training context present; training_level=intermediate; equipment=barbell; schedule=4 days per week")
            add_goal(state_dir=tmpdir, goal_type="fat_loss", goal_description="cut")
            add_target(state_dir=tmpdir, target_type="diet", effective_from=today, calories_kcal=2200, protein_g=160, carbs_g=240, fat_g=60)
            add_target(state_dir=tmpdir, target_type="training", effective_from=today, training_days_per_week=4)
            upsert_daily_body_stats(state_dir=tmpdir, date=today, weight_kg=80, waist_cm=85, body_fat_percent=18)
            upsert_daily_diet_history(state_dir=tmpdir, date=today, calories_kcal=2200, protein_g=160)
            upsert_daily_training_history(state_dir=tmpdir, date=today, trained="yes", training_type="strength")
            add_dietary_restriction(state_dir=tmpdir, restriction_type="preference", name="none")
            add_health_note(state_dir=tmpdir, date=today, note_type="injury", description="injury_status=none", impact_on_training="none")

            text = get_context(purpose="diet_plan", state_dir=tmpdir)
            self.assertIn("# Fitness Coach Context", text)
            self.assertIn("## 4. Next 7 Days Projected Targets", text)
            self.assertIn("status: ready", text)

    def test_blocks_diet_plan_when_weight_or_restrictions_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today().isoformat()
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180, llm_notes="activity_multiplier=1.55")
            add_goal(state_dir=tmpdir, goal_type="fat_loss", goal_description="cut")
            add_target(state_dir=tmpdir, target_type="diet", effective_from=today, calories_kcal=2200, protein_g=160, carbs_g=240, fat_g=60)
            data = get_context_data(purpose="diet_plan", state_dir=tmpdir)
            self.assertFalse(data["readiness"]["ok"])
            self.assertIn("latest weight_kg", data["readiness"]["missing"])
            self.assertIn("dietary restrictions checked", data["readiness"]["missing"])

    def test_blocks_training_plan_when_injury_status_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today().isoformat()
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180, llm_notes="activity_multiplier=1.55; training_level=intermediate; equipment=barbell; schedule=4 days per week")
            add_goal(state_dir=tmpdir, goal_type="strength", goal_description="get stronger")
            add_target(state_dir=tmpdir, target_type="training", effective_from=today, training_days_per_week=4)
            data = get_context_data(purpose="training_plan", state_dir=tmpdir)
            self.assertFalse(data["readiness"]["ok"])
            self.assertIn("injury/limitation status", data["readiness"]["missing"])

    def test_allows_diet_adjustment_when_required_fields_exist(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today().isoformat()
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180, llm_notes="activity_multiplier=1.55; training context present")
            add_goal(state_dir=tmpdir, goal_type="fat_loss", goal_description="cut")
            add_target(state_dir=tmpdir, target_type="diet", effective_from=today, calories_kcal=2200, protein_g=160, carbs_g=240, fat_g=60)
            upsert_daily_body_stats(state_dir=tmpdir, date=today, weight_kg=80, waist_cm=85, body_fat_percent=18)
            upsert_daily_diet_history(state_dir=tmpdir, date=today, calories_kcal=2200, protein_g=160)
            add_dietary_restriction(state_dir=tmpdir, restriction_type="preference", name="none")
            data = get_context_data(purpose="diet_adjustment", state_dir=tmpdir)
            self.assertTrue(data["readiness"]["ok"])
            self.assertEqual(len(data["diet_plan"]), 7)


if __name__ == "__main__":
    unittest.main()
