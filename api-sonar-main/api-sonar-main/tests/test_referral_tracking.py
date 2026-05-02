import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_referral_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
os.environ["GATEWAY_PUBLIC_BASE_URL"] = "https://play.sonar-experiment.com"
os.environ["FRONTEND_PUBLIC_BASE_URL"] = "https://dice.sonar2026.es"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, select

import main as main_module
from database import engine
from main import app, bootstrap_demo_data
from models import ReferralClick, ReferralLink


class ReferralTrackingTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)
        with Session(engine) as db:
            bootstrap_demo_data(db)
        object.__setattr__(
            main_module.settings,
            "gateway_public_base_url",
            "https://play.sonar-experiment.com",
        )
        object.__setattr__(
            main_module.settings,
            "frontend_public_base_url",
            "https://dice.sonar2026.es",
        )
        self.client = TestClient(app)

    def create_session(
        self,
        *,
        bracelet_id: str,
        installation_id: str,
        referral_code: str | None = None,
        referral_link_id: str | None = None,
    ) -> dict:
        response = self.client.post(
            "/v1/session/access",
            json={
                "bracelet_id": bracelet_id,
                "consent_accepted": True,
                "consent_age_confirmed": True,
                "consent_info_accepted": True,
                "consent_data_accepted": True,
                "language": "es",
                "client_installation_id": installation_id,
                "referral_code": referral_code,
                "referral_link_id": referral_link_id,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["session"]

    def create_referral_link(self, session_id: str) -> dict:
        response = self.client.post(
            "/v1/referrals/link",
            json={
                "session_id": session_id,
                "channel": "whatsapp",
                "traffic_source": "whatsapp",
                "traffic_medium": "social",
                "campaign_code": "festival_invite_exit",
                "target_path": "/",
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["link"]

    def test_create_referral_link_returns_ref_id_and_share_url(self) -> None:
        session = self.create_session(
            bracelet_id="REFG1001",
            installation_id="ref-install-1",
        )

        link = self.create_referral_link(session["session_id"])

        self.assertTrue(link["ref_id"])
        self.assertEqual(link["referral_code"], session["referral_code"])
        self.assertEqual(
            link["share_url"],
            f"https://play.sonar-experiment.com/invite/{link['ref_id']}",
        )

    def test_invite_redirect_logs_click_and_redirects_with_ref_and_ref_id(self) -> None:
        session = self.create_session(
            bracelet_id="REFG1002",
            installation_id="ref-install-2",
        )
        link = self.create_referral_link(session["session_id"])

        response = self.client.get(
            f"/invite/{link['ref_id']}",
            headers={"referer": "https://festival.sonar.test/poster"},
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 307, response.text)
        parsed = urlsplit(response.headers["location"])
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.netloc, "dice.sonar2026.es")
        self.assertEqual(query["ref"], [session["referral_code"]])
        self.assertEqual(query["ref_id"], [link["ref_id"]])
        self.assertEqual(query["src"], ["whatsapp"])
        self.assertEqual(query["utm_medium"], ["social"])
        self.assertEqual(query["utm_campaign"], ["festival_invite_exit"])

        with Session(engine) as db:
            stored_link = db.get(ReferralLink, link["ref_id"])
            self.assertIsNotNone(stored_link)
            self.assertEqual(stored_link.click_count, 1)
            click = db.exec(
                select(ReferralClick).where(ReferralClick.referral_link_id == link["ref_id"])
            ).first()
            self.assertIsNotNone(click)
            self.assertEqual(click.referer, "https://festival.sonar.test/poster")
            self.assertEqual(click.traffic_source, "whatsapp")

    def test_access_with_referral_link_attaches_inviter_and_counts_conversion(self) -> None:
        inviter = self.create_session(
            bracelet_id="REFG1003",
            installation_id="ref-install-3",
        )
        link = self.create_referral_link(inviter["session_id"])

        redirect = self.client.get(f"/invite/{link['ref_id']}", follow_redirects=False)
        self.assertEqual(redirect.status_code, 307, redirect.text)

        invited = self.create_session(
            bracelet_id="REFG1004",
            installation_id="ref-install-4",
            referral_code=inviter["referral_code"],
            referral_link_id=link["ref_id"],
        )

        self.assertEqual(invited["invited_by_session_id"], inviter["session_id"])
        self.assertEqual(invited["invited_by_referral_code"], inviter["referral_code"])
        self.assertEqual(invited["referral_link_id"], link["ref_id"])

        with Session(engine) as db:
            stored_link = db.get(ReferralLink, link["ref_id"])
            self.assertIsNotNone(stored_link)
            self.assertEqual(stored_link.conversion_count, 1)
            click = db.exec(
                select(ReferralClick).where(ReferralClick.referral_link_id == link["ref_id"])
            ).first()
            self.assertIsNotNone(click)
            self.assertEqual(click.session_id, invited["session_id"])

    def test_admin_referrals_summary_reports_ratio(self) -> None:
        inviter = self.create_session(
            bracelet_id="REFG1005",
            installation_id="ref-install-5",
        )
        link = self.create_referral_link(inviter["session_id"])
        redirect = self.client.get(f"/invite/{link['ref_id']}", follow_redirects=False)
        self.assertEqual(redirect.status_code, 307, redirect.text)
        self.create_session(
            bracelet_id="REFG1006",
            installation_id="ref-install-6",
            referral_code=inviter["referral_code"],
            referral_link_id=link["ref_id"],
        )

        response = self.client.get("/admin/referrals/summary")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()

        self.assertEqual(payload["summary"]["links_total"], 1)
        self.assertEqual(payload["summary"]["clicks_total"], 1)
        self.assertEqual(payload["summary"]["conversions_total"], 1)
        self.assertEqual(payload["summary"]["invite_to_entry_ratio"], 1.0)
        self.assertEqual(payload["by_link"][0]["ref_id"], link["ref_id"])
        self.assertEqual(payload["by_link"][0]["invite_to_entry_ratio"], 1.0)
        self.assertEqual(
            payload["by_inviter_session"][0]["inviter_session_id"],
            inviter["session_id"],
        )


if __name__ == "__main__":
    unittest.main()
