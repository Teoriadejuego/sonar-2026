# Experiment Versions

Cada sesión persiste estas versiones:
- `experiment_version`
- `experiment_phase`
- `phase_version`
- `ui_version`
- `consent_version`
- `treatment_version`
- `treatment_text_version`
- `allocation_version`
- `deck_version`
- `payment_version`
- `telemetry_version`
- `lexicon_version`

También guarda:
- `language_at_access`
- `language_at_claim`
- `language_changed_during_session`
- `deployment_context`
- `site_code`
- `campaign_code`
- `environment_label`

## Fuente de verdad
La configuración maestra está en:
- [project_parameters.json](/C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/project_parameters.json)

La carga operativa la resuelve:
- [experiment.py](/C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/api-sonar-main/api-sonar-main/experiment.py)

## Regla
La sesión queda congelada con la versión activa en el momento de asignación. No se reescribe retrospectivamente si más tarde cambia la fase o el copy.
