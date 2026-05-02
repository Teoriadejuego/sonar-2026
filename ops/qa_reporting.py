from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

QAStatus = Literal["OK", "FAIL", "WARNING"]
QAImpact = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

STATUS_VALUES: tuple[QAStatus, ...] = ("OK", "FAIL", "WARNING")
IMPACT_VALUES: tuple[QAImpact, ...] = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
SCHEMA_VERSION = "qa-test-report-v1"

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = REPO_ROOT / "outputs" / "qa_reports"
DEFAULT_JSONL_PATH = DEFAULT_REPORT_DIR / "test_results.jsonl"
DEFAULT_CSV_PATH = DEFAULT_REPORT_DIR / "test_results.csv"


@dataclass(slots=True)
class QATestResult:
    schema_version: str
    test_id: str
    timestamp: str
    scenario: str
    input: Any
    expected_result: str
    actual_result: str
    status: QAStatus
    impact: QAImpact
    notes: str


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_report_path(report_path: str | Path | None = None) -> Path:
    return Path(report_path) if report_path is not None else DEFAULT_JSONL_PATH


def _validate_status(status: str) -> QAStatus:
    if status not in STATUS_VALUES:
        raise ValueError(
            f"Invalid QA status {status!r}. Expected one of: {', '.join(STATUS_VALUES)}",
        )
    return status


def _validate_impact(impact: str) -> QAImpact:
    if impact not in IMPACT_VALUES:
        raise ValueError(
            f"Invalid QA impact {impact!r}. Expected one of: {', '.join(IMPACT_VALUES)}",
        )
    return impact


def build_test_result(
    *,
    test_id: str,
    scenario: str,
    input_data: Any,
    expected_result: str,
    actual_result: str,
    status: str,
    impact: str,
    notes: str = "",
    timestamp: str | None = None,
) -> dict[str, Any]:
    if not test_id.strip():
        raise ValueError("test_id is required")
    if not scenario.strip():
        raise ValueError("scenario is required")
    if not expected_result.strip():
        raise ValueError("expected_result is required")
    if not actual_result.strip():
        raise ValueError("actual_result is required")

    result = QATestResult(
        schema_version=SCHEMA_VERSION,
        test_id=test_id.strip(),
        timestamp=timestamp or utc_now_iso(),
        scenario=scenario.strip(),
        input=input_data,
        expected_result=expected_result.strip(),
        actual_result=actual_result.strip(),
        status=_validate_status(status),
        impact=_validate_impact(impact),
        notes=notes.strip(),
    )
    return asdict(result)


def append_test_result(
    result: dict[str, Any],
    report_path: str | Path | None = None,
) -> Path:
    destination = normalize_report_path(report_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(result, ensure_ascii=False))
        handle.write("\n")
    return destination


def log_test_result(
    *,
    test_id: str,
    scenario: str,
    input_data: Any,
    expected_result: str,
    actual_result: str,
    status: str,
    impact: str,
    notes: str = "",
    timestamp: str | None = None,
    report_path: str | Path | None = None,
) -> dict[str, Any]:
    result = build_test_result(
        test_id=test_id,
        scenario=scenario,
        input_data=input_data,
        expected_result=expected_result,
        actual_result=actual_result,
        status=status,
        impact=impact,
        notes=notes,
        timestamp=timestamp,
    )
    append_test_result(result, report_path=report_path)
    return result


def load_test_results(report_path: str | Path | None = None) -> list[dict[str, Any]]:
    source = normalize_report_path(report_path)
    if not source.exists():
        return []

    rows: list[dict[str, Any]] = []
    with source.open("r", encoding="utf-8-sig") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def export_results_csv(
    report_path: str | Path | None = None,
    csv_path: str | Path | None = None,
) -> Path:
    rows = load_test_results(report_path)
    destination = Path(csv_path) if csv_path is not None else DEFAULT_CSV_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "schema_version",
        "test_id",
        "timestamp",
        "scenario",
        "input",
        "expected_result",
        "actual_result",
        "status",
        "impact",
        "notes",
    ]

    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = dict(row)
            normalized["input"] = json.dumps(
                normalized.get("input"),
                ensure_ascii=False,
            )
            writer.writerow(normalized)

    return destination


__all__ = [
    "DEFAULT_CSV_PATH",
    "DEFAULT_JSONL_PATH",
    "DEFAULT_REPORT_DIR",
    "IMPACT_VALUES",
    "SCHEMA_VERSION",
    "STATUS_VALUES",
    "append_test_result",
    "build_test_result",
    "export_results_csv",
    "load_test_results",
    "log_test_result",
]
