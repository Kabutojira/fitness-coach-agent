import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.fitness_state.setters import add_goal, add_recipe, add_recipe_ingredient_snapshot, set_user_profile, upsert_daily_body_stats

ROOT = Path(__file__).resolve().parents[1]


class StateCalculatorIntegrationTest(unittest.TestCase):
    def run_script(self, relative_path, *args):
        result = subprocess.run(
            [sys.executable, str(ROOT / relative_path), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_calculate_diet_targets_from_state_matches_explicit_and_writes_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            today = date.today().isoformat()
            set_user_profile(state_dir=tmpdir, name="Alex", age=35, sex="male", height_cm=180, llm_notes="activity_multiplier=1.55; meals_per_day=4")
            add_goal(state_dir=tmpdir, goal_type="fat_loss", goal_description="cut")
            upsert_daily_body_stats(state_dir=tmpdir, date=today, weight_kg=80, waist_cm=85, body_fat_percent=18)

            explicit = self.run_script(
                "scripts/calculate_diet_targets.py",
                "--age", "35",
                "--sex", "male",
                "--height-cm", "180",
                "--weight-kg", "80",
                "--activity-multiplier", "1.55",
                "--goal", "fat_loss",
                "--meals-per-day", "4",
            )
            from_state = self.run_script(
                "scripts/calculate_diet_targets.py",
                "--from-state",
                "--write-state",
                "--state-dir", tmpdir,
            )

            self.assertEqual(explicit["targets"], from_state["targets"])
            self.assertTrue(from_state["state_write"]["ok"])
            with (Path(tmpdir) / "targets.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["target_type"], "diet")

    def test_calculate_recipe_nutrition_from_state_and_write_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recipe = add_recipe(state_dir=tmpdir, name="Overnight oats", servings=2)
            recipe_id = recipe["id"]
            add_recipe_ingredient_snapshot(
                state_dir=tmpdir,
                recipe_id=recipe_id,
                ingredient_name="Oats",
                quantity=80,
                unit="g",
                basis_type="per_100g",
                basis_quantity=100,
                basis_unit="g",
                calories_kcal=389,
                protein_g=16.9,
                carbs_g=66.3,
                fat_g=6.9,
                fiber_g=10.6,
                salt_g=0,
            )
            add_recipe_ingredient_snapshot(
                state_dir=tmpdir,
                recipe_id=recipe_id,
                ingredient_name="Greek yogurt cup",
                quantity=2,
                unit="cup",
                basis_type="per_unit",
                basis_quantity=1,
                basis_unit="cup",
                calories_kcal=120,
                protein_g=15,
                carbs_g=5,
                fat_g=0,
                fiber_g=0,
                salt_g=0,
            )

            data = self.run_script(
                "scripts/calculate_recipe_nutrition.py",
                "--from-state",
                "--recipe-id", recipe_id,
                "--write-state",
                "--state-dir", tmpdir,
            )
            self.assertEqual(data["totals"]["calories_kcal"], 551.2)
            self.assertEqual(data["per_serving"]["protein_g"], 21.76)
            self.assertTrue(data["state_write"]["ok"])

            with (Path(tmpdir) / "recipes.csv").open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["total_calories_kcal"], "551.2")


if __name__ == "__main__":
    unittest.main()
