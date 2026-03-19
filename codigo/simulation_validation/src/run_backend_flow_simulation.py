from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from utils import (
    DATA_DIR,
    LOGS_DIR,
    PROJECT_ROOT,
    ensure_directories,
    load_config,
    make_population_table,
    payout_amount_for_claim,
    report_value_for_robot,
    sample_reroll_count,
    save_dataframe,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ejecuta robots contra el backend real de SONAR usando TestClient.",
    )
    parser.add_argument("--participants", type=int, default=None)
    parser.add_argument("--bracelet-start", type=int, default=10000001)
    return parser.parse_args()


def bootstrap_test_backend() -> tuple[TestClient, Any]:
    test_db_dir = tempfile.mkdtemp(prefix="sonar_robot_flow_")
    os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(test_db_dir, 'flow.db')}"
    os.environ["REQUIRE_REDIS"] = "false"
    os.environ["REQUIRE_ADMIN_AUTH"] = "false"
    backend_dir = PROJECT_ROOT / "api-sonar-main" / "api-sonar-main"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from sqlmodel import SQLModel, Session  # noqa: WPS433

    from database import engine  # noqa: WPS433
    from main import app, bootstrap_demo_data  # noqa: WPS433

    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        bootstrap_demo_data(db)
    return TestClient(app), test_db_dir


def run_backend_flow(participants: int, bracelet_start: int) -> dict[str, Path]:
    ensure_directories()
    config = load_config()
    population = make_population_table(config).head(participants).copy()
    robot_behavior = config["robot_behavior"]
    client, temp_dir = bootstrap_test_backend()
    rows: list[dict] = []
    errors: list[dict] = []

    try:
        for offset, person in population.reset_index(drop=True).iterrows():
            bracelet_id = str(bracelet_start + offset)
            access_response = client.post(
                "/v1/session/access",
                json={
                    "bracelet_id": bracelet_id,
                    "consent_accepted": True,
                    "consent_age_confirmed": True,
                    "consent_info_accepted": True,
                    "consent_data_accepted": True,
                    "language": person["language"],
                    "landing_visible_ms": 1800,
                    "info_panels_opened": [],
                    "info_panel_durations_ms": {},
                    "client_installation_id": f"robot-flow-{bracelet_id}",
                },
            )
            if access_response.status_code != 200:
                errors.append({"bracelet_id": bracelet_id, "step": "access", "detail": access_response.text})
                continue
            session = access_response.json()["session"]
            session_id = session["session_id"]

            roll_response = client.post(
                f"/v1/session/{session_id}/roll",
                json={
                    "attempt_index": 1,
                    "reaction_ms": 1100,
                    "idempotency_key": f"roll-{session_id}-1",
                },
            )
            if roll_response.status_code != 200:
                errors.append({"bracelet_id": bracelet_id, "step": "roll", "detail": roll_response.text})
                continue
            first_attempt = roll_response.json()["attempt"]
            true_first_result = int(first_attempt["result_value"])

            reroll_count = sample_reroll_count(
                robot_type=person["robot_type"],
                robot_behavior=robot_behavior,
                rng=__import__("random").Random(20260319 + offset),
            )
            seen_values = [true_first_result]
            for reroll_index in range(2, reroll_count + 2):
                reroll_response = client.post(
                    f"/v1/session/{session_id}/roll",
                    json={
                        "attempt_index": reroll_index,
                        "reaction_ms": 900 + 100 * reroll_index,
                        "idempotency_key": f"roll-{session_id}-{reroll_index}",
                    },
                )
                if reroll_response.status_code != 200:
                    errors.append(
                        {
                            "bracelet_id": bracelet_id,
                            "step": f"reroll_{reroll_index}",
                            "detail": reroll_response.text,
                        }
                    )
                    break
                seen_values.append(int(reroll_response.json()["attempt"]["result_value"]))

            prepare_response = client.post(
                f"/v1/session/{session_id}/prepare-report",
                json={"idempotency_key": f"prepare-{session_id}"},
            )
            if prepare_response.status_code != 200:
                errors.append({"bracelet_id": bracelet_id, "step": "prepare", "detail": prepare_response.text})
                continue
            prepared_session = prepare_response.json()["session"]
            report_snapshot = prepared_session["report_snapshot"]

            rng = __import__("random").Random(909000 + offset)
            reported_value = report_value_for_robot(
                robot_type=person["robot_type"],
                true_first_result=true_first_result,
                treatment_key=prepared_session["treatment_key"],
                displayed_count_target=report_snapshot["count_target"],
                displayed_denominator=report_snapshot["denominator"],
                rng=rng,
                robot_behavior=robot_behavior,
            )

            client.post(
                f"/v1/session/{session_id}/display-snapshot",
                json={
                    "screen_name": "report",
                    "language": person["language"],
                    "treatment_message_text": report_snapshot["message"] if not report_snapshot["is_control"] else None,
                    "control_message_text": report_snapshot["message"] if report_snapshot["is_control"] else None,
                    "rerolls_visible": seen_values[1:],
                },
            )

            submit_response = client.post(
                f"/v1/session/{session_id}/submit-report",
                json={
                    "reported_value": reported_value,
                    "reaction_ms": 1400,
                    "idempotency_key": f"submit-{session_id}",
                    "language": person["language"],
                },
            )
            if submit_response.status_code != 200:
                errors.append({"bracelet_id": bracelet_id, "step": "submit", "detail": submit_response.text})
                continue
            completed_session = submit_response.json()["session"]

            client.post(
                f"/v1/session/{session_id}/display-snapshot",
                json={
                    "screen_name": "exit",
                    "language": person["language"],
                    "final_message_text": "flow_validation_exit",
                    "final_amount_eur": int(completed_session["payment"]["amount_cents"] / 100),
                    "payout_reference_shown": (
                        completed_session.get("payment", {}).get("reference_code")
                        if completed_session.get("payment")
                        else None
                    ),
                    "rerolls_visible": seen_values[1:],
                },
            )

            rows.append(
                {
                    "session_id": session_id,
                    "robot_id": person["robot_id"],
                    "robot_type": person["robot_type"],
                    "language": person["language"],
                    "true_first_result": true_first_result,
                    "reported_value": reported_value,
                    "reported_6": int(reported_value == 6),
                    "reported_5": int(reported_value == 5),
                    "is_honest_robot_eval": int(reported_value == true_first_result),
                    "lie_amount_robot_eval": reported_value - true_first_result,
                    "opportunity_to_lie": 6 - true_first_result,
                    "relative_lie": round(
                        (reported_value - true_first_result) / max(6 - true_first_result, 1),
                        4,
                    ),
                    "displayed_count_target": report_snapshot["count_target"],
                    "displayed_denominator": report_snapshot["denominator"],
                    "norm_target_value": report_snapshot["target_value"],
                    "visible_message": report_snapshot["message"],
                    "reroll_count": len(seen_values) - 1,
                    "used_any_reroll": int(len(seen_values) > 1),
                    "payment_eligible": int(completed_session["selected_for_payment"]),
                    "payment_amount": completed_session["payment"]["amount_cents"],
                    "experiment_phase": completed_session["experiment_phase"],
                    "quality_flags_json": json.dumps(completed_session["quality_flags"]),
                    "technical_error_flag": 0,
                    "all_values_seen_json": json.dumps(seen_values),
                    "final_visible_snapshot_json": json.dumps(report_snapshot),
                }
            )

        for dataset_name, output_name in [
            ("sessions", "backend_flow_sessions_export.csv"),
            ("series_state", "backend_flow_series_state.csv"),
            ("position_plan", "backend_flow_position_plan.csv"),
            ("telemetry", "backend_flow_telemetry.csv"),
            ("snapshot_records", "backend_flow_snapshot_records.csv"),
        ]:
            response = client.get(f"/admin/export/{dataset_name}.csv")
            response.raise_for_status()
            (DATA_DIR / output_name).write_text(response.text, encoding="utf-8")

        robot_df = pd.DataFrame(rows)
        exported_sessions = pd.read_csv(DATA_DIR / "backend_flow_sessions_export.csv")
        sessions_df = exported_sessions.merge(robot_df, on="session_id", how="left")
        save_dataframe(sessions_df, DATA_DIR / "backend_flow_sessions.csv")

        summary = {
            "participants_requested": participants,
            "participants_completed": int(len(sessions_df)),
            "errors": errors[:50],
            "winner_count": int(sessions_df["payment_eligible"].sum()) if not sessions_df.empty else 0,
            "total_prize_amount_eur": round(float(sessions_df["payment_amount"].sum()) / 100, 2)
            if not sessions_df.empty
            else 0.0,
        }
        (LOGS_DIR / "run_backend_flow_simulation_summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "sessions": DATA_DIR / "backend_flow_sessions.csv",
            "series": DATA_DIR / "backend_flow_series_state.csv",
            "position_plan": DATA_DIR / "backend_flow_position_plan.csv",
        }
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    args = parse_args()
    config = load_config()
    participants = args.participants or int(config["backend_flow_default_participants"])
    outputs = run_backend_flow(participants=participants, bracelet_start=args.bracelet_start)
    print(json.dumps({key: str(value) for key, value in outputs.items()}, indent=2, ensure_ascii=False))
