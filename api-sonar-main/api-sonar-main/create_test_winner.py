import sys
from dataclasses import dataclass

from sqlmodel import Session

from database import engine
from main import create_audit, ensure_user_and_session, get_or_create_pulseras
from models import SessionRecord


@dataclass
class FakeClient:
    host: str = "127.0.0.1"


class FakeRequest:
    def __init__(self) -> None:
        self.headers = {"user-agent": "qa-test-winner-script"}
        self.client = FakeClient()


def prepare_test_winner(bracelet_id: str) -> SessionRecord:
    fake_request = FakeRequest()
    with Session(engine) as db:
        get_or_create_pulseras(db)
        _, session_record, created_now = ensure_user_and_session(
            db,
            bracelet_id=bracelet_id,
            consent_accepted=True,
            consent_age_confirmed=True,
            consent_info_accepted=True,
            consent_data_accepted=True,
            client_installation_id=f"qa-winner-{bracelet_id}",
            incoming_referral_code=None,
            referral_source=None,
            referral_path=None,
            request=fake_request,
        )
        previous = session_record.selected_for_payment
        session_record.selected_for_payment = True
        db.add(session_record)
        create_audit(
            db,
            entity_type="session",
            entity_id=session_record.id,
            action="qa_force_winner",
            session_id=session_record.id,
            old_state=session_record.state,
            new_state=session_record.state,
            payload={
                "bracelet_id": bracelet_id,
                "created_now": created_now,
                "previous_selected_for_payment": previous,
            },
        )
        db.commit()
        db.refresh(session_record)
        return session_record


if __name__ == "__main__":
    bracelet = sys.argv[1] if len(sys.argv) > 1 else "10000999"
    session_record = prepare_test_winner(bracelet)
    print(
        f"Pulsera QA premiada lista: {bracelet} | "
        f"phase={session_record.experiment_phase} | "
        f"tratamiento={session_record.treatment_key} | "
        f"posicion={session_record.position_index} | "
        f"session_id={session_record.id}"
    )
