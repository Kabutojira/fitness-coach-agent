import tempfile
import unittest
from datetime import date, timedelta

from scripts.fitness_state.getters import (
    get_active_goals,
    get_current_targets,
    get_diet_history,
    get_diet_plan,
    get_dietary_restrictions,
    get_fridge_items,
    get_health_notes,
    get_ingredients,
    get_latest_body_stats,
    get_recipes,
    get_shopping_list,
    get_training_history,
    get_training_plan,
    get_user_profile,
)
from scripts.fitness_state.setters import (
    add_dietary_restriction,
    add_fridge_item,
    add_goal,
    add_health_note,
    add_ingredient,
    add_recipe,
    add_shopping_item,
    add_target,
    set_user_profile,
    upsert_daily_body_stats,
    upsert_daily_diet_history,
    upsert_daily_diet_plan,
    upsert_daily_training_history,
    upsert_daily_training_plan,
)


class GettersTest(unittest.TestCase):
    def test_getters_return_expected_rows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180)
            add_goal(state_dir=tmpdir, goal_type="fat_loss", goal_description="cut")
            add_target(state_dir=tmpdir, target_type="diet", effective_from=today.isoformat(), calories_kcal=2200, protein_g=160)
            add_target(state_dir=tmpdir, target_type="training", effective_from=today.isoformat(), training_days_per_week=4)
            upsert_daily_body_stats(state_dir=tmpdir, date=today.isoformat(), weight_kg=80, waist_cm=85, body_fat_percent=18)
            upsert_daily_diet_history(state_dir=tmpdir, date=today.isoformat(), calories_kcal=2200, protein_g=160)
            upsert_daily_training_history(state_dir=tmpdir, date=today.isoformat(), trained="yes", training_type="strength")
            upsert_daily_diet_plan(state_dir=tmpdir, date=tomorrow.isoformat(), calories_kcal=2100, protein_g=160, carbs_g=200, fat_g=60)
            upsert_daily_training_plan(state_dir=tmpdir, date=tomorrow.isoformat(), planned_training="yes", training_type="strength")
            add_dietary_restriction(state_dir=tmpdir, restriction_type="preference", name="none")
            add_health_note(state_dir=tmpdir, date=today.isoformat(), note_type="recovery", description="fine")
            add_ingredient(state_dir=tmpdir, name="Greek yogurt", brand="Fage", basis_type="per_100g")
            add_recipe(state_dir=tmpdir, name="Overnight oats", servings=2)
            add_fridge_item(state_dir=tmpdir, item_name="Eggs", quantity=12, unit="unit")
            add_shopping_item(state_dir=tmpdir, item_name="Milk", quantity=1, unit="bottle")

            profile = get_user_profile(state_dir=tmpdir)
            latest_stats = get_latest_body_stats(state_dir=tmpdir)
            self.assertIsNotNone(profile)
            self.assertIsNotNone(latest_stats)
            if profile is None or latest_stats is None:
                raise AssertionError("expected seeded rows")
            self.assertEqual(profile["name"], "Alex")
            self.assertEqual(len(get_active_goals(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_current_targets(state_dir=tmpdir)), 2)
            self.assertEqual(latest_stats["weight_kg"], "80")
            self.assertEqual(len(get_diet_history(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_training_history(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_diet_plan(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_training_plan(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_dietary_restrictions(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_health_notes(state_dir=tmpdir)), 1)
            self.assertEqual(get_ingredients("yogurt", state_dir=tmpdir)[0]["brand"], "Fage")
            self.assertEqual(get_recipes("oats", state_dir=tmpdir)[0]["name"], "Overnight oats")
            self.assertEqual(len(get_fridge_items(state_dir=tmpdir)), 1)
            self.assertEqual(len(get_shopping_list(state_dir=tmpdir)), 1)


if __name__ == "__main__":
    unittest.main()
