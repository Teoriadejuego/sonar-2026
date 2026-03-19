# Railway Review Deploy

Esta guia deja SONAR online con la arquitectura real, pero en una version minima pensada para revision en movil y comentarios de coautores.

## Objetivo

Desplegar:

- frontend publico para abrir la app en el movil
- backend FastAPI real
- PostgreSQL gestionado
- Redis gestionado

Sin cambiar:

- logica experimental
- endpoints
- flujo
- modelos de datos

## Recomendacion de uso

- usa un repositorio **privado** en GitHub
- comparte solo la URL publica del frontend
- no compartas las credenciales del admin

## Servicios que hay que crear

En Railway crea un proyecto nuevo y anade estos cuatro servicios:

1. `postgres`
2. `redis`
3. `api`
4. `app`

## Orden recomendado

1. crear `postgres`
2. crear `redis`
3. crear `api`
4. crear `app`
5. hacer un primer deploy
6. generar dominio publico para `api` y `app`
7. fijar `CORS_ORIGINS` y `VITE_API_URL`
8. redeploy de `api` y `app`

## Servicio `postgres`

Anade un servicio desde la plantilla de PostgreSQL.

No hace falta tocar nada mas para el primer arranque.

## Servicio `redis`

Anade un servicio desde la plantilla de Redis.

No hace falta tocar nada mas para el primer arranque.

## Servicio `api`

Conecta el repositorio GitHub y usa:

- Source repo: este repositorio
- Root directory: dejar vacio
- Dockerfile path: `api-sonar-main/api-sonar-main/Dockerfile`

Importante:

El backend debe construirse desde la **raiz del repo**, porque el Dockerfile copia tambien [project_parameters.json](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/project_parameters.json).

### Variables minimas de `api`

Configura estas variables:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
REQUIRE_ADMIN_AUTH=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<pon-una-clave-larga>
AUTO_BOOTSTRAP_DEMO_DATA=true
REQUIRE_REDIS=true
APP_HASH_PEPPER=<pon-un-secreto-largo>
EXPERIMENT_MASTER_SEED=<pon-otro-secreto-largo>
DEPLOYMENT_CONTEXT=review
SITE_CODE=SONAR2026
CAMPAIGN_CODE=coauthor_review
ENVIRONMENT_LABEL=review
PROJECT_PARAMETERS_PATH=/app/project_parameters.json
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

Al principio puedes dejar `CORS_ORIGINS` sin fijar y anadirlo despues de generar el dominio del frontend.

## Servicio `app`

Conecta el mismo repositorio GitHub y usa:

- Root directory: `sorteo-sonar-main`

Railway usara automaticamente el Dockerfile de esa carpeta.

### Variables minimas de `app`

En el primer despliegue puedes poner temporalmente:

```text
VITE_API_URL=https://example.invalid
```

Luego, cuando el servicio `api` tenga dominio publico, cambialo a:

```text
VITE_API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
```

Y redeploy del frontend.

## Dominios publicos

Cuando `api` y `app` hayan desplegado:

1. entra en `api` -> `Settings` -> `Networking`
2. genera dominio publico
3. entra en `app` -> `Settings` -> `Networking`
4. genera dominio publico

Luego fija estas variables:

### En `api`

```text
CORS_ORIGINS=https://${{app.RAILWAY_PUBLIC_DOMAIN}}
```

### En `app`

```text
VITE_API_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
```

Despues redeploy de los dos servicios.

## Migraciones

El contenedor del backend ya ejecuta:

```text
python migrate.py && uvicorn main:app ...
```

No hace falta anadir un comando manual extra para una primera revision ligera.

## Comprobaciones finales

Cuando termine el deploy:

1. abre `https://<api-domain>/health/live`
2. abre `https://<api-domain>/health/ready`
3. abre `https://<app-domain>` en el navegador
4. abre esa URL en tu movil

La API esta bien si `ready` devuelve que:

- `database_ready = true`
- `redis_ready = true`

## Uso de demo para revision

Para revisar pantallas sin contaminar series reales, puedes usar los codigos demo del frontend:

- `1234` -> ganador demo
- `12341` -> control demo
- `12342` -> `seed_low` demo
- `12343` -> `seed_high` demo

## Seguridad minima recomendada

- repo privado
- contrasena admin larga
- no compartir `/admin/*`
- no reutilizar secretos de local

## Si quieres apagarla despues

Puedes:

- pausar el experimento desde admin, o
- apagar el proyecto en Railway

Para una revision corta con pocos usuarios, esta configuracion es suficiente para verla funcionar en movil sin redisenar nada.
