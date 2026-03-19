# Classroom Load Test

Esta prueba valida el escenario de aula con 60 accesos casi simultáneos usando los endpoints reales.

## Requisitos

- stack levantado con PostgreSQL y Redis
- pulseras demo disponibles en el rango que se vaya a usar
- admin protegido conocido

## Arranque del stack

```powershell
docker compose --env-file .env.classroom up --build -d
```

## Comando de carga

```powershell
& ".\.venv\Scripts\python.exe" ".\ops\classroom_load_test.py" `
  --base-url http://127.0.0.1:8000 `
  --users 60 `
  --concurrency 60 `
  --bracelet-start 10002000 `
  --admin-username admin `
  --admin-password sonar_admin_change_me
```

## Qué hace

Cada sujeto sintético ejecuta:

1. `POST /v1/session/access`
2. `POST /v1/session/{id}/roll`
3. `POST /v1/session/{id}/prepare-report`
4. `POST /v1/session/{id}/submit-report`

## Criterios de éxito

- `failed_users = 0`
- `duplicate_series_positions = 0`
- todos los estados finales son `completed_win` o `completed_no_win`
- `invalid_series_rows = []`
- latencia p95 razonable para el entorno

## Outputs

Se guardan en:

- `outputs/classroom_load_test/classroom_load_test_results.csv`
- `outputs/classroom_load_test/classroom_load_test_summary.json`
