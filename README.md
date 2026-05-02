# SONAR 2026

Repositorio principal de la app experimental SONAR 2026.

SONAR 2026 es una infraestructura full-stack para ejecutar, monitorizar y documentar un experimento mobile-first sobre honestidad y normas descriptivas en un contexto cultural real.

Actualizado: `2026-05-02`

## Diseno experimental vigente

La unica verdad experimental activa es:

- `control`
- `norm_0`, `norm_1`, ..., `norm_60`
- denominador fijo `60`
- `control` no muestra norma social
- `norm_X` muestra una norma fija equivalente a `X de 60`
- la norma visible depende solo del tratamiento asignado
- la norma visible no se actualiza dinamicamente durante la sesion
- `prepare-report` congela el snapshot antes del claim

Frase canonica:

> El diseno experimental vigente es `control + norm_0..norm_60`. La norma social es fija por tratamiento y no se actualiza dinamicamente durante la sesion.

## Estado del sistema

- frontend React Router + Vite
- backend FastAPI + SQLModel
- PostgreSQL/Redis como capa operativa objetivo
- gateway QR con redireccion dinamica y tracking
- dashboard live con metricas de experimento, pagos, QR y referrals
- doble API con failover manual y automatico
- telemetria minima no bloqueante

## Enlaces publicos actuales

- App principal: [https://dice.sonar2026.es](https://dice.sonar2026.es)
- App Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
- API Railway actual: [https://api-production-9fe7b.up.railway.app](https://api-production-9fe7b.up.railway.app)
- Health live: [https://api-production-9fe7b.up.railway.app/health/live](https://api-production-9fe7b.up.railway.app/health/live)
- Health ready: [https://api-production-9fe7b.up.railway.app/health/ready](https://api-production-9fe7b.up.railway.app/health/ready)

## Flujo participante

1. acceso con pulsera o demo,
2. consentimiento,
3. instrucciones,
4. comprension,
5. primera tirada privada,
6. rerolls opcionales,
7. snapshot congelado de reporte,
8. claim del numero de la primera tirada,
9. salida, premio o payout.

La logica experimental y el estado visible se resuelven en backend. El frontend solo representa el estado autorizado por backend.

## Codigos demo utiles

- `CTRL1234`: control demo ganador
- `NORM0000`: `norm_0`
- `NORM0001`: `norm_1`

## Mapa del repositorio

- `sorteo-sonar-main/`
  frontend React Router de la app experimental.
- `api-sonar-main/api-sonar-main/`
  backend FastAPI, migraciones, admin, exports y logica experimental.
- `codigo/`
  pipeline analitico, simulaciones y validacion.
- `ops/`
  utilidades operativas y de despliegue.
- `docs/`
  documentacion de metodologia, operacion y arquitectura.

## Lectura recomendada

1. [docs/REQUIREMENTS_CONSOLIDATED.md](./docs/REQUIREMENTS_CONSOLIDATED.md)
2. [docs/METHODOLOGY.md](./docs/METHODOLOGY.md)
3. [docs/COAUTHOR_REVIEW_GUIDE.md](./docs/COAUTHOR_REVIEW_GUIDE.md)
4. [GUIA_OPERATIVA_RAPIDA_SONAR.md](./GUIA_OPERATIVA_RAPIDA_SONAR.md)
5. [docs/FESTIVAL_DAY_RUNBOOK.md](./docs/FESTIVAL_DAY_RUNBOOK.md)

## Arranque rapido local

1. Copia el entorno local:

```powershell
Copy-Item .env.local.example .env.local
```

2. Levanta la arquitectura:

```powershell
docker compose --env-file .env.local up --build
```

3. Comprueba:

- frontend: [http://localhost:3000](http://localhost:3000)
- API live: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- API ready: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)
