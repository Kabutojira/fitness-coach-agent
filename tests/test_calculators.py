import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CalculatorScriptsTest(unittest.TestCase):
    def run_script(self, relative_path, *args):
        script = ROOT / relative_path
        result = subprocess.run(
            [sys.executable, str(script), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_calculate_diet_targets_mifflin(self):
        data = self.run_script(
            "scripts/calculate_diet_targets.py",
            "--age", "35",
            "--sex", "male",
            "--height-cm", "180",
            "--weight-kg", "80",
            "--activity-multiplier", "1.55",
            "--goal", "fat_loss",
            "--meals-per-day", "4",
        )
        self.assertEqual(data["targets"]["calories_kcal"], 2176)
        self.assertAlmostEqual(data["targets"]["protein_g"], 160.0)
        self.assertAlmostEqual(data["targets"]["fat_g"], 64.0)
        self.assertAlmostEqual(data["targets"]["carbs_g"], 240.1)
        self.assertEqual(data["mathematical_check"]["difference_vs_target_kcal"], 0.0)
        self.assertAlmostEqual(data["per_meal"]["protein_g"], 40.0)

    def test_calculate_diet_targets_katch_requires_body_fat(self):
        script = ROOT / "scripts/calculate_diet_targets.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--age", "35",
                "--sex", "male",
                "--height-cm", "180",
                "--weight-kg", "80",
                "--activity-multiplier", "1.55",
                "--goal", "fat_loss",
                "--formula", "katch_mcardle",
            ],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--body-fat-percent is required", result.stderr + result.stdout)

    def test_calculate_recipe_nutrition(self):
        recipe = {
            "recipe_name": "oats and yogurt",
            "servings": 2,
            "ingredients": [
                {
                    "name": "oats",
                    "quantity": 80,
                    "unit": "g",
                    "nutrition_basis": {
                        "type": "per_100g",
                        "calories_kcal": 389,
                        "protein_g": 16.9,
                        "carbs_g": 66.3,
                        "fat_g": 6.9,
                        "fiber_g": 10.6,
                    },
                },
                {
                    "name": "greek yogurt cup",
                    "quantity": 2,
                    "unit": "cup",
                    "nutrition_basis": {
                        "type": "per_unit",
                        "calories_kcal": 120,
                        "protein_g": 15,
                        "carbs_g": 5,
                        "fat_g": 0,
                        "fiber_g": 0,
                    },
                },
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "recipe.json"
            path.write_text(json.dumps(recipe), encoding="utf-8")
            data = self.run_script("scripts/calculate_recipe_nutrition.py", str(path))

        self.assertEqual(data["totals"]["calories_kcal"], 551.2)
        self.assertEqual(data["totals"]["protein_g"], 43.52)
        self.assertEqual(data["per_serving"]["protein_g"], 21.76)
        self.assertEqual(data["ingredients"][0]["basis_type"], "per_100g")


if __name__ == "__main__":
    unittest.main()
