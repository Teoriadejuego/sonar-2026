# Data Exports

SONAR expone una puerta simple para investigador en:
- [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)

## Botones principales
- `Exportar dataset analitico completo`
- `Exportar telemetria completa`
- `Exportar pagos administrativos`
- `Exportar red de referidos`
- `Exportar posicion y series`
- `Generar paquete para analisis`

## Exportes directos
- `/admin/export/sessions.csv`
- `/admin/export/throws.csv`
- `/admin/export/claims.csv`
- `/admin/export/telemetry.csv`
- `/admin/export/technical_events.csv`
- `/admin/export/screen_events.csv`
- `/admin/export/client_contexts.csv`
- `/admin/export/referrals.csv`
- `/admin/export/series_state.csv`
- `/admin/export/position_plan.csv`
- `/admin/export/quality_flags.csv`
- `/admin/export/fraud_flags.csv`
- `/admin/export/consent_records.csv`
- `/admin/export/snapshot_records.csv`
- `/admin/export/payments_admin.csv`
- `/admin/export/interest_signups.csv`
- `/admin/export/audit_events.csv`

## Bundles ZIP
- `/admin/export/bundle/analytic.zip`
- `/admin/export/bundle/operational.zip`
- `/admin/export/bundle/administrative.zip`
- `/admin/export/bundle/all.zip`

## Que incluye cada capa
### Analytic
- `sessions`
- `throws`
- `claims`
- `referrals`
- `series_state`
- `position_plan`
- `quality_flags`
- `consent_records`
- `snapshot_records`

### Operational
- `telemetry`
- `technical_events`
- `screen_events`
- `client_contexts`
- `fraud_flags`
- `audit_events`

### Administrative
- `payments_admin`
- `interest_signups`

## Manifest y documentacion
Cada ZIP incluye:
- `manifest.json`
- `README_EXPORT.md`
- `DATASETS_CODEBOOK.md`

`manifest.json` contiene:
- fecha de export
- bundle generado
- hash SHA-256 del contenido
- numero de registros por dataset
- categoria y sensibilidad
- versiones activas del experimento

## Uso recomendado
1. Descargar `analytic.zip` para analisis estadistico.
2. Descargar `operational.zip` para QA, trazabilidad y auditoria de atencion/red.
3. Descargar `administrative.zip` solo para gestion de premios y contactos opt-in.
4. Descargar `all.zip` si se quiere archivar el estado completo del estudio.

## Advertencia de sensibilidad
- `payments_admin` e `interest_signups` contienen datos administrativos sensibles.
- `telemetry`, `technical_events`, `screen_events` y `client_contexts` contienen trazabilidad tecnica detallada.
- `sessions` y `snapshot_records` estan preparados para analisis y excluyen telefono solicitado de cobro.
