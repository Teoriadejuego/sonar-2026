# API High Availability Deployment

## Objetivo

Levantar dos instancias equivalentes de la API SONAR contra la misma base de
datos PostgreSQL y el mismo Redis para evitar una caída total por fallo de una
sola réplica.

## Arquitectura recomendada

### Opción A: Plataforma con réplicas nativas

Usa una sola imagen del servicio `api` y escala a 2 réplicas:

- misma imagen Docker
- mismas variables de entorno
- misma `DATABASE_URL`
- misma `REDIS_URL`
- balanceo gestionado por la plataforma

Esto es lo preferido en Railway, Render o Fly.io cuando no necesitas distinguir
visiblemente `api-a` y `api-b`.

### Opción B: Dos servicios explícitos + gateway

Usa:

- `api-a`
- `api-b`
- `api-gateway`
- `postgres`
- `redis`

El gateway enruta a cualquiera de las dos APIs y reintenta contra la otra si la
primera falla.

## Cambios de backend que hacen esto seguro

- La API es stateless: no guarda sesión crítica en memoria de proceso.
- Estado experimental, claims, payout, follow-up y snapshots viven en
  PostgreSQL.
- Los writes críticos ya usan:
  - transacciones
  - `FOR UPDATE`
  - `distributed_lock(...)` vía Redis
  - `ActionReceipt` + `idempotency_key`
- `migrate.py` ahora serializa migraciones con advisory lock de PostgreSQL para
  que dos réplicas no intenten migrar a la vez.
- `/health`, `/health/live` y `/health/ready` exponen `instance_name` para
  verificar a qué réplica estás pegando.
- esos mismos endpoints exponen `config_fingerprint` para comprobar que `api-a`
  y `api-b` comparten la misma configuración efectiva y el mismo estado
  compartido.

## Requisitos operativos

- `REQUIRE_REDIS=true`
- Redis compartido entre ambas réplicas
- PostgreSQL compartido entre ambas réplicas
- misma versión de imagen en `api-a` y `api-b`
- mismo `APP_HASH_PEPPER`
- mismo `EXPERIMENT_MASTER_SEED`

## Despliegue local o self-hosted

Archivo listo:

- `docker-compose.ha.yml`

Gateway listo:

- `ops/nginx/api-ha.conf`

### Arranque

```bash
docker compose -f docker-compose.ha.yml up -d --build
```

### Endpoints esperados

- gateway: `http://localhost:8000/health/ready`
- api-a directa: `http://localhost:8001/health/ready`
- api-b directa: `http://localhost:8002/health/ready`

### Verificación

Comprueba que `instance_name` cambie entre `8001` y `8002` y que
`config_fingerprint` sea igual en ambas.

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8000/health
python ops/ha_preflight_check.py --api-a http://localhost:8001 --api-b http://localhost:8002 --gateway http://localhost:8000
```

## Despliegue en Railway

### Recomendado

Usa un único servicio `api` y escala a `2` réplicas en `Settings > Scale`.

Configura:

- misma imagen / mismo root directory
- mismas variables
- healthcheck path: `/health/ready`
- `REQUIRE_REDIS=true`

### Alternativa con A/B explícito

Si necesitas dos servicios separados:

- crea `api-a`
- clona a `api-b`
- usa las mismas referencias de `DATABASE_URL` y `REDIS_URL`
- publica ambos detrás de un gateway externo
  - Cloudflare Load Balancer
  - Traefik
  - Nginx
  - HAProxy

## Despliegue en Render

- mismo servicio web escalado a 2 instancias, o bien dos servicios más un
  gateway
- sin disco persistente adjunto a la API
- healthcheck path: `/health/ready`

## Despliegue en Fly.io

- 2 Machines con la misma imagen
- mismo secret set
- `services.concurrency` ajustado para que Fly Proxy reparta tráfico con margen
- health endpoint: `/health`

## Estrategia de failover

### Simple

- dominio principal al gateway
- si una réplica cae, el gateway pasa tráfico a la otra
- si quieres operación manual, expones `api-a` y `api-b` por separado y cambias
  el destino del DNS o del proxy
- en el gateway QR de la app puedes forzar `primary` o `backup` al instante con
  `POST /admin/gateway/mode`

### Pro

- load balancer con round robin o least-connections
- retries automáticos sobre `502/503/504`
- healthchecks activos contra `/health/ready`
- drenado de tráfico antes de apagar una réplica
- comprobación previa de paridad con `config_fingerprint`

## Riesgos y mitigaciones

### Riesgo: migraciones concurrentes al arrancar

Mitigación:

- advisory lock en PostgreSQL dentro de `migrate.py`

### Riesgo: doble claim o doble write

Mitigación:

- `distributed_lock(...)`
- `FOR UPDATE`
- unique constraints
- `idempotency_key`
- `ActionReceipt`

### Riesgo: Redis desactivado

Mitigación:

- en HA, mantener `REQUIRE_REDIS=true`

## Prueba de resiliencia

1. Arranca las dos réplicas.
2. Lanza tráfico al gateway.
3. Apaga `api-a`.
4. Repite `GET /health` y un flujo real.
5. Verifica que sigue respondiendo `api-b`.
6. Levanta `api-a`.
7. Apaga `api-b`.
8. Repite las comprobaciones.

Ejemplo local:

```bash
docker stop sonar-api-a
curl http://localhost:8000/health
docker start sonar-api-a

docker stop sonar-api-b
curl http://localhost:8000/health
docker start sonar-api-b
```

## Política recomendada

Para producción:

- una sola definición de servicio API
- 2 réplicas activas
- Redis obligatorio
- PostgreSQL compartido
- healthcheck `/health`
- migraciones serializadas
- despliegues rolling
