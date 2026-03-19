from __future__ import annotations

import json

import pandas as pd

from utils import DATA_DIR, TABLES_DIR, ensure_directories, save_dataframe
from validate_simulation_outputs import run_validation


def build_tables() -> dict[str, str]:
    ensure_directories()
    sessions = pd.read_csv(DATA_DIR / "simulated_sessions.csv")
    validation_path = TABLES_DIR / "table_4_validation_checks.csv"
    if not validation_path.exists():
        run_validation()
    validation = pd.read_csv(validation_path)

    table_1 = (
        sessions.groupby(["robot_type", "treatment_key"])
        .size()
        .reset_index(name="n_subjects")
        .sort_values(["robot_type", "treatment_key"])
    )
    table_2 = (
        sessions.groupby("robot_type")[["reported_6", "reported_5", "is_honest", "lie_amount"]]
        .mean()
        .reset_index()
        .sort_values("robot_type")
    )
    table_3 = (
        sessions.groupby("treatment_key")[
            [
                "reported_6",
                "reported_5",
                "is_honest",
                "lie_amount",
                "reroll_count",
                "payment_eligible",
                "payment_amount",
            ]
        ]
        .mean()
        .reset_index()
        .sort_values("treatment_key")
    )

    save_dataframe(table_1, TABLES_DIR / "table_1_robot_by_treatment.csv")
    save_dataframe(table_2, TABLES_DIR / "table_2_robot_means.csv")
    save_dataframe(table_3, TABLES_DIR / "table_3_treatment_summary.csv")
    save_dataframe(validation, TABLES_DIR / "table_4_validation_checks.csv")

    summary = {
        "table_1_rows": int(len(table_1)),
        "table_2_rows": int(len(table_2)),
        "table_3_rows": int(len(table_3)),
        "table_4_rows": int(len(validation)),
    }
    return {
        "summary": json.dumps(summary, ensure_ascii=False),
    }


if __name__ == "__main__":
    output = build_tables()
    print(output["summary"])
