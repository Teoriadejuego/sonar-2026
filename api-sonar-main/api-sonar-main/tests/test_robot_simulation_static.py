from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[3]
SIMULATION_ROOT = ROOT / "codigo" / "simulation_validation"


class RobotSimulationStaticTests(unittest.TestCase):
    def test_required_simulation_files_exist(self) -> None:
        required = [
            SIMULATION_ROOT / "README.md",
            SIMULATION_ROOT / "config" / "robot_simulation_config.json",
            SIMULATION_ROOT / "src" / "generate_robot_population.py",
            SIMULATION_ROOT / "src" / "run_direct_simulation.py",
            SIMULATION_ROOT / "src" / "run_backend_flow_simulation.py",
            SIMULATION_ROOT / "src" / "validate_simulation_outputs.py",
            SIMULATION_ROOT / "src" / "build_robot_analysis_tables.py",
            SIMULATION_ROOT / "src" / "figures_robot_validation.py",
            SIMULATION_ROOT / "src" / "utils.py",
        ]
        for path in required:
            self.assertTrue(path.exists(), f"Missing {path}")

    def test_simulation_config_is_well_formed(self) -> None:
        payload = json.loads(
            (SIMULATION_ROOT / "config" / "robot_simulation_config.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(payload["participants_valid_completed"], 6000)
        self.assertAlmostEqual(sum(payload["treatment_weights"].values()), 1.0)
        self.assertAlmostEqual(sum(payload["robot_mix"].values()), 1.0)
        self.assertAlmostEqual(sum(payload["language_weights"].values()), 1.0)
        self.assertIn("type_d_honest", payload["robot_mix"])


if __name__ == "__main__":
    unittest.main()
