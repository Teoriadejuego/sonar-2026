from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx


BASE_URL = "https://api-production-9fe7b.up.railway.app"
DEFAULT_DATASETS = [
    "sessions",
    "throws",
    "claims",
    "referrals",
    "treatment_decks",
    "treatment_deck_cards",
    "result_decks",
    "result_deck_cards",
    "payment_decks",
    "payment_deck_cards",
    "quality_flags",
    "consent_records",
    "snapshot_records",
    "telemetry",
    "technical_events",
    "screen_events",
    "client_contexts",
    "fraud_flags",
    "audit_events",
    "operational_notes",
    "payments_admin",
]
DEFAULT_BUNDLES = ["analytic", "operational", "administrative", "all"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Descarga admin exports de SONAR si se dispone de credenciales.",
    )
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--username", default=os.getenv("SONAR_ADMIN_USERNAME", ""))
    parser.add_argument("--password", default=os.getenv("SONAR_ADMIN_PASSWORD", ""))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    auth = (args.username, args.password) if args.username and args.password else None
    manifest: dict[str, object] = {
        "base_url": args.base_url,
        "username_supplied": bool(args.username),
        "exports_page_status": None,
        "downloads": [],
    }

    headers = {"User-Agent": "SONAR-admin-export-downloader/1.0"}
    with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers, auth=auth) as session:
        exports_response = session.get(f"{args.base_url}/admin/exports")
        manifest["exports_page_status"] = exports_response.status_code
        if exports_response.status_code != 200:
            (output_dir / "admin_export_blocked.txt").write_text(
                "No fue posible descargar los exports admin.\n"
                f"HTTP status: {exports_response.status_code}\n"
                "Comprueba SONAR_ADMIN_USERNAME y SONAR_ADMIN_PASSWORD.\n",
                encoding="utf-8",
            )
            (output_dir / "download_manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return 1

        for dataset in DEFAULT_DATASETS:
            response = session.get(f"{args.base_url}/admin/export/{dataset}.csv")
            target_path = output_dir / f"{dataset}.csv"
            manifest["downloads"].append(
                {
                    "kind": "dataset",
                    "name": dataset,
                    "status_code": response.status_code,
                    "path": str(target_path),
                }
            )
            if response.status_code == 200:
                target_path.write_bytes(response.content)

        for bundle in DEFAULT_BUNDLES:
            response = session.get(f"{args.base_url}/admin/export/bundle/{bundle}.zip")
            target_path = output_dir / f"{bundle}.zip"
            manifest["downloads"].append(
                {
                    "kind": "bundle",
                    "name": bundle,
                    "status_code": response.status_code,
                    "path": str(target_path),
                }
            )
            if response.status_code == 200:
                target_path.write_bytes(response.content)
        (output_dir / "download_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
