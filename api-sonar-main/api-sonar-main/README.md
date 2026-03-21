# API Sonar 2026

Backend experimental en FastAPI + SQLModel para el estudio de honestidad de Sonar 2026.

## Que implementa

- Sesion unica persistente por pulsera.
- Tres condiciones configurables: `control`, `seed_low`, `seed_high`.
- Series espejo agrupadas por `root`.
- Mazo balanceado preasignado por posicion y por intento.
- Pago preasignado por backend.
- Rerolls registrados.
- Snapshot de tratamiento congelado justo antes del claim.
- Ventana social visible configurable, actualmente de 60 observaciones.
- Longitud de serie configurable, actualmente 120 participantes por serie.
- Telemetria pasiva y flags basicos de calidad y antifraude.

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

Si la base esta vacia, el backend crea automaticamente pulseras demo desde `10000001` en adelante y un `root` activo inicial.
