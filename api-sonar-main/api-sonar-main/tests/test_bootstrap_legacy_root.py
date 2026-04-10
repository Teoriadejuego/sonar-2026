import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


TEST_DB_DIR = tempfile.mkdtemp(prefix="sonar_bootstrap_legacy_root_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(TEST_DB_DIR, 'test.db')}"
os.environ["REQUIRE_REDIS"] = "false"
os.environ["REQUIRE_ADMIN_AUTH"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, SQLModel, select

from database import engine
from main import PHASE_1_MAIN, TREATMENT_KEYS, create_root_with_series, get_active_treatment_deck
from models import SeriesRoot, TreatmentDeck


class BootstrapLegacyRootTests(unittest.TestCase):
    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(TEST_DB_DIR, ignore_errors=True)

    def setUp(self) -> None:
        SQLModel.metadata.drop_all(engine)
        SQLModel.metadata.create_all(engine)

    def test_first_treatment_deck_skips_legacy_root_sequence_conflict(self) -> None:
        with Session(engine) as db:
            legacy_root = create_root_with_series(
                db,
                PHASE_1_MAIN,
                root_sequence=1,
                treatment_keys=TREATMENT_KEYS,
                deck_status="active",
            )
            db.commit()
            db.refresh(legacy_root)

        with Session(engine) as db:
            deck = get_active_treatment_deck(db)
            db.commit()
            db.refresh(deck)

            self.assertEqual(deck.deck_index, 2)
            root = db.get(SeriesRoot, deck.legacy_root_id)
            self.assertIsNotNone(root)
            self.assertEqual(root.root_sequence, 2)

            all_decks = db.exec(select(TreatmentDeck)).all()
            self.assertEqual(len(all_decks), 1)


if __name__ == "__main__":
    unittest.main()
