# SONAR Architecture

SONAR se ejecuta ahora con una sola arquitectura para local, aula y producción.

## Componentes

- `sorteo-sonar-main`
  - frontend React Router / PWA
  - consume exclusivamente el backend HTTP
- `api-sonar-main/api-sonar-main`
  - backend FastAPI
  - lógica experimental única
  - admin, exports, dashboard y cobros
- PostgreSQL
  - única base de datos real
  - mismo esquema en todos los entornos
- Redis
  - locks distribuidos
  - rate limiting
  - caché de idempotencia
  - estado de pausa del experimento

## Principio operativo

`train as you play`

- no existe versión simplificada para local
- no existe flujo alternativo para aula
- no existe rama de lógica distinta para festival
- solo cambian credenciales, URLs, capacidad y servicios gestionados

## Flujo de ejecución

1. frontend solicita acceso al backend
2. backend asigna sesión, root, serie y posición en PostgreSQL
3. Redis coordina locks para secciones críticas
4. PostgreSQL persiste el estado autoritativo
5. exports, admin y dashboard leen del mismo esquema

## Garantías principales

- misma lógica experimental en todos los entornos
- migraciones reproducibles con Alembic
- health checks y readiness checks
- logs estructurados JSON
- admin protegido con Basic Auth
- despliegue listo para contenedores
