# API Sonar 2026

Backend experimental en **FastAPI + SQLModel** para el estudio de honestidad de Sónar 2026.

## Qué implementa

- Sesión única persistente por pulsera.
- Tres condiciones: `control`, `seed_17`, `seed_83`.
- Series espejo agrupadas por `root`.
- Mazo balanceado preasignado por posición y por intento.
- Pago preasignado por backend.
- Rerolls registrados.
- Snapshot de tratamiento congelado justo antes del claim.
- Ventana social visible de 100 observaciones.
- Ventana real de claims para integridad y stopping rules.
- Telemetría pasiva y flags básicos de calidad/antifraude.

## Arranque

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Swagger:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

## Utilidades

Reconstruir base demo:

```powershell
python migrate.py
```

Inspeccionar seed y roots:

```powershell
python seed.py
```

## Endpoints principales

- `POST /v1/session/access`
- `GET /v1/session/{session_id}/resume`
- `POST /v1/session/{session_id}/roll`
- `POST /v1/session/{session_id}/prepare-report`
- `POST /v1/session/{session_id}/submit-report`
- `POST /v1/telemetry/batch`
- `GET /v1/config`
- `GET /admin/roots`
- `GET /admin/session/{bracelet_id}`

## Datos demo

Si la base está vacía, el backend crea automáticamente pulseras demo desde `10000001` en adelante y un `root` activo inicial.
