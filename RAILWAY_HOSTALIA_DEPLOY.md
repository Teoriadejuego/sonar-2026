# Railway + Hostalia Deploy

Guia operativa para desplegar SONAR en Railway con la misma arquitectura que ya funciona en local:

- `api` FastAPI
- `app` frontend
- PostgreSQL gestionado
- Redis gestionado

Y publicar la app en:

- `dice.sonar2026.es`

Dejando:

- `sonar2026.es` redirigido a la web oficial que elijas

## Resumen de arquitectura

No hay que cambiar la logica de negocio.

La arquitectura queda:

- `app` publico en Railway
- `api` publico en Railway
- `postgres` gestionado por Railway
- `redis` gestionado por Railway
- `dice.sonar2026.es` apuntando al `app`
- la API puede quedarse con dominio Railway en esta primera fase

## Cambios de codigo necesarios

Ninguno obligatorio.

El proyecto ya esta preparado para este despliegue:

- backend con Dockerfile en [api Dockerfile](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/api-sonar-main/api-sonar-main/Dockerfile)
- frontend con Dockerfile en [frontend Dockerfile](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/sorteo-sonar-main/Dockerfile)
- CORS configurable por variable de entorno en [settings.py](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/api-sonar-main/api-sonar-main/settings.py)
- frontend apuntando a la API por `VITE_API_URL` en [api.ts](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/sorteo-sonar-main/app/utils/api.ts)
- health checks activos en ambos contenedores

## Paso 0. Tener el repo en GitHub

Antes de empezar:

1. sube el repo a GitHub
2. mejor en **privado**
3. verifica que Railway pueda acceder al repo

## Paso 1. Crear el proyecto en Railway

1. entra en [Railway](https://railway.com/)
2. `New Project`
3. crea un proyecto vacio

## Paso 2. Crear PostgreSQL y Redis

En el mismo proyecto:

1. `Add Service` -> `Database` -> `PostgreSQL`
2. `Add Service` -> `Database` -> `Redis`

Nombres recomendados:

- `postgres`
- `redis`

## Paso 3. Crear el servicio `api`

1. `Add Service`
2. `GitHub Repo`
3. selecciona tu repo SONAR

En configuracion del servicio:

- `Root Directory`: dejar vacio
- `Dockerfile Path`: `api-sonar-main/api-sonar-main/Dockerfile`

Importante:

El backend debe construirse desde la **raiz del repo**, porque el Dockerfile copia tambien [project_parameters.json](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/project_parameters.json).

### Variables de entorno del `api`

Configura estas variables en Railway para `api`:

```text
DATABASE_URL=<pega la URL de conexion de PostgreSQL de Railway>
REDIS_URL=<pega la URL de conexion de Redis de Railway>
REQUIRE_ADMIN_AUTH=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<una-clave-larga-y-unica>
AUTO_BOOTSTRAP_DEMO_DATA=true
REQUIRE_REDIS=true
APP_HASH_PEPPER=<un-secreto-largo>
EXPERIMENT_MASTER_SEED=<otro-secreto-largo>
DEPLOYMENT_CONTEXT=review
SITE_CODE=SONAR2026
CAMPAIGN_CODE=review_mobile
ENVIRONMENT_LABEL=review
PROJECT_PARAMETERS_PATH=/app/project_parameters.json
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
STRUCTURED_LOGS=true
SQL_ECHO=false
CORS_ORIGINS=https://placeholder.invalid
```

Notas:

- `DATABASE_URL` debe ser la cadena **Postgres** real de Railway.
- `REDIS_URL` debe ser la cadena **Redis** real de Railway.
- `CORS_ORIGINS` se corrige mas adelante cuando exista la URL publica del frontend.

## Paso 4. Hacer deploy del `api`

1. guarda variables
2. lanza deploy
3. espera a que termine en verde

Luego:

1. entra en `api` -> `Settings` -> `Networking`
2. pulsa `Generate Domain`
3. guarda la URL publica que te da Railway

Ejemplo:

```text
https://sonar-api-production-xxxx.up.railway.app
```

## Paso 5. Comprobar el `api`

Prueba:

- `https://<api-domain>/health/live`
- `https://<api-domain>/health/ready`

Debe responder bien y `ready` debe indicar:

- `database_ready = true`
- `redis_ready = true`

## Paso 6. Crear el servicio `app`

1. `Add Service`
2. `GitHub Repo`
3. selecciona el mismo repo SONAR

En configuracion del servicio:

- `Root Directory`: `sorteo-sonar-main`

No hace falta tocar el Dockerfile path.

### Variables de entorno del `app`

Configura:

```text
VITE_API_URL=https://<api-domain-railway>
```

Usa la URL real que te dio Railway para `api`.

## Paso 7. Hacer deploy del `app`

1. guarda variables
2. lanza deploy
3. espera a que termine en verde

Luego:

1. entra en `app` -> `Settings` -> `Networking`
2. pulsa `Generate Domain`
3. guarda la URL publica del frontend

Ejemplo:

```text
https://sonar-app-production-xxxx.up.railway.app
```

## Paso 8. Corregir CORS en el `api`

Vuelve al servicio `api` y cambia:

```text
CORS_ORIGINS=https://<app-domain-railway>
```

Haz redeploy del `api`.

En esta fase ya deberias poder abrir la app desde el dominio Railway del frontend.

## Paso 9. Probar la app en dominio Railway

Abre en el navegador:

- `https://<app-domain-railway>`

Comprueba:

1. carga la pantalla inicial
2. puedes entrar con una pulsera demo
3. el frontend habla con la API
4. no hay errores CORS

Codigos demo utiles:

- `1234` -> ganador demo
- `12341` -> control demo
- `12342` -> `seed_low` demo
- `12343` -> `seed_high` demo

## Paso 10. Configurar `dice.sonar2026.es`

### En Railway

1. entra en el servicio `app`
2. `Settings` -> `Networking`
3. `+ Custom Domain`
4. escribe:

```text
dice.sonar2026.es
```

Railway te dara un destino CNAME, parecido a:

```text
abc123.up.railway.app
```

Guardalo.

### En Hostalia

En el panel DNS de Hostalia crea:

- Tipo: `CNAME`
- Host / Nombre: `dice`
- Destino / Value: el CNAME exacto que te da Railway

No pongas `https://`, solo el host.

Es decir, algo parecido a:

```text
dice  ->  abc123.up.railway.app
```

Guarda el registro y espera la verificacion.

Railway emitira el certificado SSL automaticamente cuando verifique el dominio.

## Paso 11. Anadir el dominio custom a CORS

Cuando `dice.sonar2026.es` aparezca verificado en Railway, vuelve a `api` y deja:

```text
CORS_ORIGINS=https://<app-domain-railway>,https://dice.sonar2026.es
```

Haz redeploy del `api`.

Con eso funcionaran:

- el dominio Railway del frontend
- el subdominio final `dice.sonar2026.es`

## Paso 12. Redirigir `sonar2026.es` a la web oficial

No montes la app en el dominio raiz.

Para dejar `sonar2026.es` apuntando a la web oficial:

1. entra en el panel de Hostalia del dominio
2. busca la opcion `Redireccion web`
3. configura una redireccion desde:

```text
https://sonar2026.es
```

hacia la URL oficial que quieras mostrar, por ejemplo la web oficial de SONAR o la landing institucional correspondiente.

Recomendacion:

- usa redireccion permanente `301` si ya lo tienes claro
- usa `302` si aun estas decidiendo el destino final

Si quieres que tambien funcione `www.sonar2026.es`, crea la misma redireccion para `www`.

## Variables de entorno finales

### `api`

```text
DATABASE_URL=<Railway Postgres URL>
REDIS_URL=<Railway Redis URL>
CORS_ORIGINS=https://<app-domain-railway>,https://dice.sonar2026.es
REQUIRE_ADMIN_AUTH=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<secreto-largo>
AUTO_BOOTSTRAP_DEMO_DATA=true
REQUIRE_REDIS=true
APP_HASH_PEPPER=<secreto-largo>
EXPERIMENT_MASTER_SEED=<secreto-largo>
DEPLOYMENT_CONTEXT=review
SITE_CODE=SONAR2026
CAMPAIGN_CODE=review_mobile
ENVIRONMENT_LABEL=review
PROJECT_PARAMETERS_PATH=/app/project_parameters.json
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
STRUCTURED_LOGS=true
SQL_ECHO=false
```

### `app`

```text
VITE_API_URL=https://<api-domain-railway>
```

## Logs y observabilidad

En Railway:

- entra en cada servicio
- abre la pestana `Deployments` o `Logs`

Debes revisar:

- `api`: arranca sin error y pasa migraciones
- `app`: build correcto y servicio escuchando
- `postgres`: operativo
- `redis`: operativo

## Health checks

Ya vienen configurados en los contenedores.

Checks utiles:

- `https://<api-domain>/health/live`
- `https://<api-domain>/health/ready`
- `https://dice.sonar2026.es`

## Como testear que funciona

### Test minimo

1. abre `https://dice.sonar2026.es` en el movil
2. comprueba que carga
3. usa `12341`
4. entra y recorre una sesion demo
5. prueba tambien `1234` para la pantalla ganadora

### Test tecnico

1. abre `https://<api-domain>/health/ready`
2. comprueba `database_ready=true`
3. comprueba `redis_ready=true`
4. abre la consola del navegador y verifica que no hay errores CORS

### Test de admin

No compartas el admin con coautores.

Solo para ti:

1. entra en `/admin/dashboard`
2. verifica que pide usuario y contrasena
3. comprueba que carga

## Como escalar luego para festival

Cuando pases de review a uso real:

1. sube recursos de PostgreSQL
2. sube recursos de Redis
3. aumenta replicas del `api`
4. deja el `app` con mas CPU o replicas solo si hace falta
5. cambia:

```text
DEPLOYMENT_CONTEXT=production
ENVIRONMENT_LABEL=production
CAMPAIGN_CODE=festival_main
AUTO_BOOTSTRAP_DEMO_DATA=false
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=60
```

6. si quieres un despliegue mas limpio, anade tambien un dominio para la API, por ejemplo:

```text
api-dice.sonar2026.es
```

No hace falta cambiar codigo para ese escalado.

## Fuentes oficiales usadas

- Railway custom domains y SSL: [Working with Domains](https://docs.railway.com/networking/domains/working-with-domains)
- Railway public networking: [Public Networking](https://docs.railway.com/networking/public-networking)
- Railway monorepo: [Deploying a Monorepo](https://docs.railway.com/tutorials/deploying-a-monorepo)
- Hostalia dominios y redireccion web: [Hostalia dominios](https://www.hostalia.com/dominios/dominios-genericos/)
