# SONAR 2026

Infraestructura experimental full-stack para el estudio SONAR 2026. El proyecto combina:

- frontend mobile-first para la tarea experimental,
- backend FastAPI con asignacion experimental, pagos y administracion,
- PostgreSQL y Redis como base operativa unica,
- paneles de export, dashboard cientifico y documentacion para despliegue, auditoria y analisis.

## Que contiene este repositorio

- `sorteo-sonar-main/`: frontend React Router de la app experimental.
- `api-sonar-main/api-sonar-main/`: backend FastAPI, migraciones, tests y admin.
- `codigo/`: codigo analitico, simulaciones y utilidades de validacion.
- `ops/`: scripts operativos, incluida la prueba de carga de aula.
- documentacion raiz: arquitectura, entornos, concurrencia, exports, datasets y despliegue.

## Principios del proyecto

- una sola arquitectura para local, aula y produccion,
- misma logica experimental en todos los entornos,
- PostgreSQL como base real desde desarrollo,
- Redis integrado para locks, rate limiting e idempotencia,
- i18n, telemetria, exports y trazabilidad listos para recogida seria de datos.

## Arranque rapido local

1. Copia el ejemplo de entorno:

```powershell
Copy-Item .env.local.example .env.local
```

2. Levanta toda la arquitectura:

```powershell
docker compose --env-file .env.local up --build
```

3. Comprueba que todo esta arriba:

- frontend: [http://localhost:3000](http://localhost:3000)
- API live: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- API ready: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)

## Documentacion clave

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [ENVIRONMENTS.md](./ENVIRONMENTS.md)
- [LOCAL_TO_PRODUCTION.md](./LOCAL_TO_PRODUCTION.md)
- [CONCURRENCY_GUARANTEES.md](./CONCURRENCY_GUARANTEES.md)
- [CLASSROOM_LOAD_TEST.md](./CLASSROOM_LOAD_TEST.md)
- [DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)
- [DATA_EXPORTS.md](./DATA_EXPORTS.md)
- [DATASETS_CODEBOOK.md](./DATASETS_CODEBOOK.md)
- [TELEMETRY_SPEC.md](./TELEMETRY_SPEC.md)
- [UI_LEXICON.md](./UI_LEXICON.md)
- [REPOSITORY_SETUP.md](./REPOSITORY_SETUP.md)

## Que no se publica

Este repositorio esta preparado para no subir:

- secretos reales de `.env`, `.env.local` y `.env.classroom`,
- bases de datos locales,
- `node_modules`, builds y caches,
- salidas generadas de simulacion y analisis,
- logs y artefactos temporales.

Los ejemplos compartibles quedan en:

- `.env.local.example`
- `.env.classroom.example`
- `.env.production.example`

## Flujo recomendado para publicar

1. Inicializar el repo local.
2. Revisar `git status`.
3. Hacer el primer commit.
4. Crear el remoto en GitHub o GitLab.
5. Conectar `origin` y hacer el primer push.

Los comandos exactos estan en [REPOSITORY_SETUP.md](./REPOSITORY_SETUP.md).
