# Data Exports

Puerta de export para investigador:
- [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)

En Railway:
- `https://TU_API/admin/exports`

## Datasets CSV directos

### Analytic
- `/admin/export/sessions.csv`
- `/admin/export/throws.csv`
- `/admin/export/claims.csv`
- `/admin/export/referrals.csv`
- `/admin/export/treatment_decks.csv`
- `/admin/export/treatment_deck_cards.csv`
- `/admin/export/result_decks.csv`
- `/admin/export/result_deck_cards.csv`
- `/admin/export/payment_decks.csv`
- `/admin/export/payment_deck_cards.csv`
- `/admin/export/quality_flags.csv`
- `/admin/export/consent_records.csv`
- `/admin/export/snapshot_records.csv`

### Operational
- `/admin/export/telemetry.csv`
- `/admin/export/technical_events.csv`
- `/admin/export/screen_events.csv`
- `/admin/export/client_contexts.csv`
- `/admin/export/fraud_flags.csv`
- `/admin/export/audit_events.csv`
- `/admin/export/operational_notes.csv`

### Administrative
- `/admin/export/payments_admin.csv`
- `/admin/export/interest_signups.csv`

## Bundles ZIP
- `/admin/export/bundle/analytic.zip`
- `/admin/export/bundle/operational.zip`
- `/admin/export/bundle/administrative.zip`
- `/admin/export/bundle/all.zip`

## Que incluye cada bundle

### analytic.zip
- `sessions.csv`
- `throws.csv`
- `claims.csv`
- `referrals.csv`
- `treatment_decks.csv`
- `treatment_deck_cards.csv`
- `result_decks.csv`
- `result_deck_cards.csv`
- `payment_decks.csv`
- `payment_deck_cards.csv`
- `quality_flags.csv`
- `consent_records.csv`
- `snapshot_records.csv`

Uso:
- analisis principal
- reconstruccion completa del tratamiento individual
- reconstruccion de la primera tirada real
- reconstruccion exacta del pago 1/100

### operational.zip
- `telemetry.csv`
- `technical_events.csv`
- `screen_events.csv`
- `client_contexts.csv`
- `fraud_flags.csv`
- `audit_events.csv`
- `operational_notes.csv`

Uso:
- QA
- depuracion
- trazabilidad de sesiones
- auditoria tecnica del despliegue

### administrative.zip
- `payments_admin.csv`
- `interest_signups.csv`

Uso:
- cobro
- donaciones
- gestion de opt-ins

### all.zip
Incluye todos los datasets anteriores mas:
- `manifest.json`
- `README_EXPORT.md`
- `DATASETS_CODEBOOK.md`

## Manifest
Cada ZIP incluye un `manifest.json` con:
- fecha y hora UTC de generacion
- bundle generado
- datasets incluidos
- numero de filas por dataset
- huella SHA-256 del contenido
- versiones activas del experimento

## Interpretacion del nuevo diseno experimental

### Tratamiento
Se reconstruye con:
- `sessions.treatment_key`
- `sessions.treatment_deck_index`
- `sessions.treatment_card_position`
- `treatment_deck_cards.treatment_key`

### Primera tirada real
Se reconstruye con:
- `sessions.result_deck_index`
- `sessions.result_card_position`
- `result_deck_cards.result_value`

### Pago
Se reconstruye con:
- `sessions.payment_deck_index`
- `sessions.payment_card_position`
- `payment_deck_cards.payout_eligible`

## Datasets recomendados por tarea

### Analisis experimental
Descargar:
- `analytic.zip`

### Monitoreo tecnico en campo
Descargar:
- `operational.zip`

### Cierre administrativo
Descargar:
- `administrative.zip`

### Archivo completo de jornada
Descargar:
- `all.zip`

## Sensibilidad
- `sessions.csv` esta preparado para analisis y no incluye telefonos de cobro.
- `payments_admin.csv` contiene datos administrativos sensibles.
- `telemetry.csv`, `screen_events.csv` y `client_contexts.csv` contienen trazabilidad tecnica detallada.

## Comprobaciones minimas despues de exportar
- `sessions.csv` debe incluir `treatment_key`, `displayed_count_target`, `displayed_denominator`, `treatment_deck_index`, `result_deck_index`, `payment_deck_index`, `payout_eligible`
- `treatment_deck_cards.csv` debe contener 62 cartas por mazo
- `result_deck_cards.csv` debe contener 24 cartas por mazo
- `payment_deck_cards.csv` debe contener 100 cartas por mazo y una sola carta ganadora por bloque
