from sqlmodel import Session, select, func

from database import engine
from main import bootstrap_demo_data
from models import DeckPosition, ExperimentState, Pulsera, Series, SeriesRoot, SessionRecord


def seed_demo() -> None:
    with Session(engine) as session:
        bootstrap_demo_data(session)

    with Session(engine) as session:
        pulseras = session.exec(select(func.count()).select_from(Pulsera)).one()
        sessions = session.exec(select(func.count()).select_from(SessionRecord)).one()
        experiment_state = session.get(ExperimentState, "global")
        roots = session.exec(select(SeriesRoot).order_by(SeriesRoot.root_sequence)).all()

        print(f"Pulseras disponibles: {pulseras}")
        print(f"Sesiones creadas: {sessions}")
        if experiment_state:
            print(
                "Estado experimental: "
                f"phase={experiment_state.current_phase}, "
                f"valid_completed_count={experiment_state.valid_completed_count}, "
                f"threshold={experiment_state.phase_transition_threshold}"
            )
        for root in roots:
            print(
                f"\nRoot {root.root_sequence} [{root.status}] "
                f"phase={root.experiment_phase}"
            )
            series_items = session.exec(
                select(Series).where(Series.root_id == root.id).order_by(Series.treatment_key)
            ).all()
            payout_positions = [
                item.position_index
                for item in session.exec(
                    select(DeckPosition).where(
                        DeckPosition.root_id == root.id,
                        DeckPosition.attempt_index == 1,
                        DeckPosition.payout_eligible == True,  # noqa: E712
                    )
                ).all()
            ]
            print(f"Posiciones elegibles para pago: {payout_positions}")
            for item in series_items:
                print(
                    f" - {item.treatment_key}: "
                    f"phase={item.experiment_phase}, "
                    f"family={item.treatment_family}, "
                    f"target={item.norm_target_value}, "
                    f"asignados={item.position_counter}, "
                    f"completados={item.completed_count}, "
                    f"visible_target={item.visible_count_target}, "
                    f"actual_target={item.actual_count_target}"
                )


if __name__ == "__main__":
    seed_demo()
