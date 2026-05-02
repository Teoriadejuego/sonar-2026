from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[3] / "ops" / "qa_reporting.py"
SPEC = importlib.util.spec_from_file_location("qa_reporting", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load qa_reporting module from {MODULE_PATH}")
qa_reporting = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = qa_reporting
SPEC.loader.exec_module(qa_reporting)


class QAReportingTests(unittest.TestCase):
    def test_log_and_load_results_accumulate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            report_path = Path(tmp_dir) / "results.jsonl"
            csv_path = Path(tmp_dir) / "results.csv"

            first = qa_reporting.log_test_result(
                test_id="PERF-001",
                scenario="Landing carga inicial",
                input_data={"network": "slow-4g"},
                expected_result="La pantalla principal responde sin bloqueo visible.",
                actual_result="La pantalla cargó en 1.8 s.",
                status="OK",
                impact="MEDIUM",
                notes="Primera prueba",
                report_path=report_path,
            )
            second = qa_reporting.log_test_result(
                test_id="FLOW-002",
                scenario="Claim con pérdida de red",
                input_data={"network": "offline-then-online"},
                expected_result="La sesión se conserva y el claim se reintenta.",
                actual_result="El claim se reintentó al volver online.",
                status="WARNING",
                impact="HIGH",
                notes="Reintento en background",
                report_path=report_path,
            )

            rows = qa_reporting.load_test_results(report_path)

            self.assertEqual(2, len(rows))
            self.assertEqual(first["test_id"], rows[0]["test_id"])
            self.assertEqual(second["test_id"], rows[1]["test_id"])

            exported = qa_reporting.export_results_csv(report_path, csv_path)
            csv_content = exported.read_text(encoding="utf-8")
            self.assertTrue(exported.exists())
            self.assertIn("PERF-001", csv_content)
            self.assertIn("FLOW-002", csv_content)

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            qa_reporting.build_test_result(
                test_id="BAD-001",
                scenario="Estado no válido",
                input_data={},
                expected_result="Debe fallar la validación.",
                actual_result="Se probó un estado inválido.",
                status="BROKEN",
                impact="LOW",
            )

    def test_invalid_impact_raises(self):
        with self.assertRaises(ValueError):
            qa_reporting.build_test_result(
                test_id="BAD-002",
                scenario="Impacto no válido",
                input_data={},
                expected_result="Debe fallar la validación.",
                actual_result="Se probó un impacto inválido.",
                status="FAIL",
                impact="SEVERE",
            )


if __name__ == "__main__":
    unittest.main()
