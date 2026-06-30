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

    def test_review_state_daily_bootstraps_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_root = Path(tmpdir) / "state"
            state_root.mkdir(parents=True, exist_ok=True)
            (state_root / "USER.md").write_text(
                "# User Profile\n\nStatus: not_initialized\n",
                encoding="utf-8",
            )

            data = self.run_script(
                "scripts/review_state.py",
                "--kind", "daily",
                "--date", "2026-06-30",
                "--state-root", str(state_root),
            )

            report_path = Path(data["report_path"])
            self.assertTrue(report_path.exists())
            self.assertTrue(data["report_exists"])
            self.assertIn("state/history/daily_reviews/2026-06-30.md", data["changed_files"])
            self.assertIn("state/todo_list.md", data["changed_files"])
            self.assertTrue(any("not_initialized" in item for item in data["blockers"]))
            todo_text = (state_root / "todo_list.md").read_text(encoding="utf-8")
            self.assertIn("Complete first-start intake.", todo_text)
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("Do not recalculate personalized diet/training/shopping targets", report_text)

    def test_review_state_weekly_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_root = Path(tmpdir) / "state"
            state_root.mkdir(parents=True, exist_ok=True)
            (state_root / "USER.md").write_text(
                "# User Profile\n\nStatus: ready\n",
                encoding="utf-8",
            )
            (state_root / "goals.md").write_text(
                "# Goals\n\n* Primary goal: fat loss\n",
                encoding="utf-8",
            )
            history = state_root / "history"
            history.mkdir(parents=True, exist_ok=True)
            (history / "body_stats.md").write_text(
                "# Body Stats\n\n* Weight: 80 kg on 2026-06-30\n* Waist: 90 cm\n",
                encoding="utf-8",
            )
            for name, content in {
                "food_log.md": "# Food Log\n\n* 2026-06-29: logged meals\n",
                "training_log.md": "# Training Log\n\n* 2026-06-29: squat 3x5 @ RPE 8\n",
                "deviations.md": "# Deviations\n\n* 2026-06-28: dinner out\n",
                "health_notes.md": "# Health Notes\n\n* No known intolerances\n",
            }.items():
                (history / name).write_text(content, encoding="utf-8")
            (state_root / "fridge_list.md").write_text("# Fridge List\n\n* Eggs\n", encoding="utf-8")
            (state_root / "todo_list.md").write_text("# Todo List\n\n## Active\n\n", encoding="utf-8")

            data = self.run_script(
                "scripts/review_state.py",
                "--kind", "weekly",
                "--date", "2026-06-30",
                "--state-root", str(state_root),
            )

            report_path = Path(data["report_path"])
            self.assertTrue(report_path.exists())
            self.assertEqual(report_path.name, "2026-06-30.md")
            self.assertIn("state/history/weekly_reports/2026-06-30.md", data["changed_files"])
            report_text = report_path.read_text(encoding="utf-8")
            self.assertIn("The scheduled review now writes a real report artifact", report_text)

    def test_review_state_honors_custom_state_root_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_root = Path(tmpdir) / "private_fitness_state"
            history = state_root / "history"
            history.mkdir(parents=True, exist_ok=True)
            (state_root / "USER.md").write_text("# User Profile\n\nStatus: ready\n", encoding="utf-8")
            (state_root / "goals.md").write_text("# Goals\n\n* Primary goal: maintenance\n", encoding="utf-8")
            (history / "body_stats.md").write_text(
                "# Body Stats\n\n* Weight: 75 kg on 2026-06-30\n* Waist: 84 cm\n",
                encoding="utf-8",
            )
            for name, content in {
                "food_log.md": "# Food Log\n\n* 2026-06-29: logged meals\n",
                "training_log.md": "# Training Log\n\n* 2026-06-29: bench 3x5\n",
                "deviations.md": "# Deviations\n\n* none\n",
                "health_notes.md": "# Health Notes\n\n* none\n",
            }.items():
                (history / name).write_text(content, encoding="utf-8")
            (state_root / "fridge_list.md").write_text("# Fridge List\n\n* Yogurt\n", encoding="utf-8")
            (state_root / "todo_list.md").write_text("# Todo List\n\n## Active\n\n", encoding="utf-8")

            data = self.run_script(
                "scripts/review_state.py",
                "--kind", "daily",
                "--date", "2026-06-30",
                "--state-root", str(state_root),
            )

            self.assertFalse(any("missing state/goals.md" in item for item in data["blockers"]))
            self.assertTrue(Path(data["report_path"]).exists())

    def test_review_state_is_idempotent_for_same_day(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_root = Path(tmpdir) / "state"
            first = self.run_script(
                "scripts/review_state.py",
                "--kind", "daily",
                "--date", "2026-06-30",
                "--state-root", str(state_root),
            )
            second = self.run_script(
                "scripts/review_state.py",
                "--kind", "daily",
                "--date", "2026-06-30",
                "--state-root", str(state_root),
            )

            self.assertTrue(first["changed_files"])
            self.assertEqual(second["changed_files"], [])
            self.assertTrue(Path(second["report_path"]).exists())


if __name__ == "__main__":
    unittest.main()
