from __future__ import annotations

import json

from utils import DATA_DIR, ensure_directories, load_config, make_population_table, save_dataframe


def main() -> None:
    ensure_directories()
    config = load_config()
    population = make_population_table(config)
    output_path = DATA_DIR / "robot_population.csv"
    save_dataframe(population, output_path)
    summary = {
        "rows": int(len(population)),
        "robot_counts": population["robot_type"].value_counts().sort_index().to_dict(),
        "language_counts": population["language"].value_counts().sort_index().to_dict(),
        "output_path": str(output_path),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
