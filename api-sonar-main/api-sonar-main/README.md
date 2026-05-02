# API Sonar 2026

Backend experimental en FastAPI + SQLModel para el estudio de honestidad de SONAR 2026.

## Diseno experimental activo

El backend implementa un unico diseno publico:

- `control`
- `norm_0..norm_60`
- denominador fijo `60`
- `control` no muestra norma social
- `norm_X` muestra una norma fija equivalente a `X/60`
- el valor mostrado depende solo del tratamiento asignado
- la norma visible no se recalcula con claims previos
- `prepare-report` congela el snapshot antes del claim
- `submit-report` no recalcula ni actualiza una ventana social dinamica

## Que implementa

- sesion unica persistente por pulsera
- asignacion balanceada de 62 tratamientos
- mazos balanceados de tratamiento, resultado y pago
- pago preasignado por backend
- rerolls registrados
- snapshot congelado justo antes del claim
- telemetria minima y no bloqueante
- admin, exports, dashboard y control de cierre

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

Inspeccionar bootstrap y series:

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

Si la base esta vacia, el backend crea automaticamente demos compatibles con el diseno vigente:

- `CTRL1234`
- `NORM0000`
- `NORM0001`
