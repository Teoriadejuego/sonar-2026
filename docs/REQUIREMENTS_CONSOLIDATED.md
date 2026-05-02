# Consolidated Requirements

## Scope and precedence

When sources conflict, the authoritative order is:

1. `project_parameters.json`
2. `api-sonar-main/api-sonar-main/experiment.py`
3. `api-sonar-main/api-sonar-main/main.py`
4. `sorteo-sonar-main/app/utils/SessionContext.tsx`
5. `sorteo-sonar-main/app/welcome/welcome.tsx`
6. `sorteo-sonar-main/app/utils/uiLexicon.ts`
7. Operational docs and QA reports

Legacy references to older two-arm seed designs, old demo IDs, or endogenous visible windows are superseded by the active 62-treatment design and the current runtime implementation.

## Functional requirements

1. `F-01` The participant flow must run through a single mobile-first web app with the sequence `language entry -> landing/consent -> instructions -> comprehension -> game -> report -> exit`, with optional `prize reveal` and `final` branches after `exit`, and an optional `payout` branch only for payout-eligible winners.
2. `F-02` The system must support six active UI languages: `es`, `ca`, `en`, `fr`, `pt`, `it`.
3. `F-03` Access must accept only a valid bracelet ID or an approved demo bracelet ID.
4. `F-04` The landing screen must require explicit confirmation of age, participation consent, and data-processing consent before session start.
5. `F-05` The participant must be able to open study, privacy, withdrawal, and contact information before starting.
6. `F-06` A session must be created or resumed by the backend, not synthesized by the frontend.
7. `F-07` Screen progression must be sequential and state-aware; the backend must reject invalid jumps.
8. `F-08` The game flow must show the first real die result, allow additional rerolls up to the configured maximum, and preserve the first result as the experimental truth.
9. `F-09` The report screen must ask the participant to indicate which number came out, not which prize they prefer.
10. `F-10` The backend must prepare and freeze a report snapshot before claim submission.
11. `F-11` Claim submission must produce a complete backend outcome, including honesty classification, payout eligibility, payment amount, and next screen state.
12. `F-12` Winners must be able to redeem via a separate payout flow with code lookup and payout submission.
13. `F-13` The payout flow must support Bizum payout, optional donation instead of payout, and the ability to continue without claiming.
14. `F-14` After the core experiment, the system must support a follow-up claim screen for crowd prediction and social recall.
15. `F-15` Non-winning and post-claim flows must support final engagement actions such as a VIP draw message and WhatsApp sharing.
16. `F-16` If the experiment is paused or closed, the participant app must show a paused state and may offer interest signup instead of access.
17. `F-17` The system must expose exportable admin and QA artifacts from the same operational dataset used by the experiment.

## Experimental requirements

1. `E-01` The only active experimental design is `design_62_treatments_v1`.
2. `E-02` The treatment universe must contain exactly `62` treatments: `norm_0..norm_60` plus `control`.
3. `E-03` For `norm_k`, the visible social message must state that `k` out of `60` previous reports said they got a `6`; this visible count is treatment-assigned exogenously, not generated live from the current session population.
4. `E-04` The `control` treatment must not display a social-norm count message.
5. `E-05` The visible denominator must equal the configured window size, currently `60`.
6. `E-06` The normative target value used in the visible message must be `6`.
7. `E-07` Each participant must consume exactly one card from a balanced 62-card treatment deck, with each treatment appearing exactly once per deck.
8. `E-08` Treatment deck order must be randomized but reproducible from seed material.
9. `E-09` Once assigned, treatment cards must be consumed permanently and never recycled, even if the participant abandons.
10. `E-10` The first real result must come from an independent 24-card result deck with exactly four copies of each value `1..6`.
11. `E-11` Result deck order must be randomized but reproducible and independent of treatment assignment.
12. `E-12` Rerolls must not consume the 24-card result deck; they must be produced server-side with deterministic RNG derived from master seed, `session_id`, and `attempt_index`.
13. `E-13` Payment eligibility must come from an independent 100-card payment deck with exactly one winning card per deck.
14. `E-14` Payment assignment must be exact `1/100` by deck design, not approximate.
15. `E-15` The backend must assign treatment, first result, and payment eligibility authoritatively inside the access pipeline.
16. `E-16` The participant may see up to `10` attempts in total, with the first result preserved as the one that matters experimentally.
17. `E-17` The per-series `participant_limit` parameter must remain configurable and is currently `120`; it must not be interpreted as the total global capacity of the experiment.
18. `E-18` The threshold for the configured phase-transition counter must remain configurable and is currently `6000` valid completed sessions.
19. `E-19` Demo IDs must remain deterministic and stable: `CTRL1234`, `NORM0000`, `NORM0001`.
20. `E-20` The backend must persist enough information to reconstruct the assigned treatment, the first real result, the payment assignment, and the exact visible message from exports.
21. `E-21` The report snapshot must be frozen before claim submission and reused consistently when determining the claim and final visible outcome.
22. `E-22` Legacy `root` and `series` entities may remain for compatibility and analytics, but they must not replace the 62/24/100 deck design as the causal assignment mechanism.
23. `E-23` Legacy `series_window_entries` may remain only for migration or export compatibility, but they must not be required by the active runtime and must not be updated as part of the participant-facing social-norm flow.

## Technical requirements

1. `T-01` The frontend must use React Router and Vite; the backend must use FastAPI.
2. `T-02` PostgreSQL must be the authoritative persistent store in deployed environments.
3. `T-03` Redis must be used for distributed locks, rate limiting, and idempotency coordination in deployed environments.
4. `T-04` The API must remain stateless; critical session and experiment state must not depend on in-process memory.
5. `T-05` The same experimental logic must be used across local, review, and production environments.
6. `T-06` The backend must provide at least these operational endpoints: `config`, `access`, `resume`, `screen`, `roll`, `prepare-report`, `submit-report`, `claim-followup`, `telemetry batch`, `payment lookup`, `payment submit`, `interest signup`, `health/live`, and `health/ready`.
7. `T-07` Each participant-facing action must map to at most one blocking critical backend request; auxiliary work must be merged into that request or executed non-blockingly.
8. `T-08` `roll`, `prepare-report`, and `submit-report` must be protected by idempotency keys and persistent action receipts.
9. `T-09` Critical writes must use database transactions, locking, and uniqueness constraints so that duplicate side effects are rejected safely.
10. `T-10` The system must use unique constraints to prevent duplicate session, throw, claim, payout, and receipt records.
11. `T-11` Migrations must be reproducible, idempotent, and able to recover from stale or invalid Alembic revision pointers without blocking deployment.
12. `T-12` A `RESET_DB=true` mode must exist for development reset flows that drop and recreate the schema before migration.
13. `T-13` Docker startup must run migrations before starting the API process.
14. `T-14` Railway-style deployment must be reproducible from `api-sonar-main/api-sonar-main` with Python `3.11`, the project parameters file inside build context, and a working healthcheck.
15. `T-15` The system must expose `/health/live` and `/health/ready`; readiness must reflect database, Redis, schema, and startup status.
16. `T-16` The API must support two equivalent instances in parallel against the same PostgreSQL and Redis for high availability.
17. `T-17` HA deployments must use the same image, same environment variables, same `APP_HASH_PEPPER`, and same `EXPERIMENT_MASTER_SEED` across replicas.
18. `T-18` Migration execution must be serialized across replicas.
19. `T-19` The frontend build must minimize initial load through lazy loading, critical CSS, and removal of unnecessary heavy dependencies.
20. `T-20` The frontend must not depend on remote fonts for first render.
21. `T-21` Local development must work across arbitrary `localhost` and `127.0.0.1` ports without CORS failures.
22. `T-22` Critical endpoints must target sub-200ms local response times under normal sequential conditions.
23. `T-23` The deployed architecture must be able to sustain high classroom or festival concurrency on PostgreSQL-class infrastructure.
24. `T-24` QA reporting must persist normalized test results in append-safe JSONL and export-friendly CSV.

## UX requirements

1. `U-01` The experience must be explicitly mobile-first.
2. `U-02` Each screen must expose one clear dominant primary action; secondary alternatives are allowed only when ethically or operationally necessary, such as donation or continue-without-claim in payout.
3. `U-03` The frontend must render backend truth, not rewrite experimental logic.
4. `U-04` Screen changes must feel immediate; avoid waiting visibly on nonessential round trips before updating the view.
5. `U-05` The frontend may optimistically transition screens, but it must never invent critical experimental data such as treatment, first result, report snapshot, claim, or payout.
6. `U-06` Buttons must respond immediately and perceived delays above `100ms` should be minimized.
7. `U-07` The die animation must be lightweight, CSS-driven or transform-based, and run in parallel with the backend call.
8. `U-08` The die must never reveal a client-generated random result; the visible final face must remain synchronized with the backend response.
9. `U-09` The report and claim flow must avoid long blocking spinners and artificial delays.
10. `U-10` Error copy shown to participants must be short, nontechnical, and localized.
11. `U-11` Network degradation must surface brief recovery states such as reconnecting rather than stack traces or transport jargon.
12. `U-12` Session state must survive reload or re-entry at least at `instructions`, `game`, `report`, and `exit`.
13. `U-13` All visible copy must come from the centralized lexicon or parameterized project copy; user-facing hardcoded strings are not allowed.
14. `U-14` The system must provide localized winner, loser, paused, prize reveal, payment, and follow-up experiences.
15. `U-15` The payment flow must clearly separate administrative payment handling from the experiment itself.
16. `U-16` The app must remain usable on slow or unstable festival networks.

## Antifraud requirements

1. `A-01` Bracelet IDs must be normalized and validated against the configured pattern of `8` alphanumeric characters with exactly `4` letters and `4` digits.
2. `A-02` A bracelet may not be silently reattached to a second device while it already has an active session on another installation.
3. `A-03` Critical session actions must be bound to the originating client installation via a persistent installation identifier.
4. `A-04` The backend must reject out-of-order screen transitions.
5. `A-05` The backend must reject skipped attempt indices in die rolls.
6. `A-06` The backend must reject duplicate claims, duplicate payments, and duplicate payout requests.
7. `A-07` Access, session actions, and payments must be rate limited.
8. `A-08` The backend must flag cases where the same device starts multiple bracelet sessions within a short time window.
9. `A-09` Winners associated with suspicious device reuse must be marked for manual review.
10. `A-10` Quality and antifraud flags must be persisted and exportable for audit.
11. `A-11` Demo flows must remain identifiable so they can be excluded from real field analysis.
12. `A-12` The system must record sufficient audit events to reconstruct who did what and with which idempotency key.

## Telemetry requirements

1. `G-01` Production participant event telemetry must be reduced to the minimum experimental set: `session_start`, `first_throw`, `reroll_count`, `report_value`, `reaction_time_ms`, `session_end`.
2. `G-02` Telemetry must not block navigation, dice interaction, claim submission, or other critical UX paths.
3. `G-03` Telemetry events must be queued client-side in memory and sent in background batches rather than flushed synchronously per interaction.
4. `G-04` Telemetry must flush at session end, on page hide, or on a bounded periodic interval rather than on every event.
5. `G-05` Telemetry delivery must retry in background with backoff if the network fails.
6. `G-06` The backend must ignore or reject nonapproved event names on the minimal participant telemetry path.
7. `G-07` Intrusive permissions and unrelated personal telemetry must not be collected, including precise geolocation, camera, microphone, contacts, clipboard contents, or browsing history.
8. `G-08` The telemetry path must keep payloads bounded by per-session caps and batching rules.
9. `G-09` Session-level technical context, counters, and audit metadata may be stored separately from participant event telemetry only to the extent required for QA, recovery, antifraud, and audit, not for rewriting experimental assignment.
10. `G-10` QA reporting must remain separate from participant telemetry and use the normalized reporting schema for test artifacts.
