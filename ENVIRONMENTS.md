# Environments

SONAR usa el mismo código y la misma lógica en los tres entornos.

## Local

- frontend local
- backend local
- PostgreSQL en Docker
- Redis en Docker

### Arranque

```powershell
docker compose --env-file .env.local up --build
```

## Classroom

- misma app
- mismo esquema
- misma configuración base
- pool de BD y límites algo más altos

### Arranque

```powershell
docker compose --env-file .env.classroom up --build -d
```

### Prueba de carga

```powershell
& ".\.venv\Scripts\python.exe" ".\ops\classroom_load_test.py" --base-url http://127.0.0.1:8000 --users 60 --concurrency 60 --admin-username admin --admin-password sonar_admin_change_me
```

## Production

- mismos contenedores
- PostgreSQL gestionado
- Redis gestionado
- secretos en el proveedor cloud
- múltiples réplicas del backend si hace falta

### Railway

1. crear proyecto nuevo
2. añadir servicio `PostgreSQL`
3. añadir servicio `Redis`
4. desplegar `api-sonar-main/api-sonar-main` como servicio web
5. desplegar `sorteo-sonar-main` como servicio web
6. copiar variables de `.env.production.example`
7. ejecutar migraciones:

```bash
python migrate.py
```

### Google Cloud Run

1. construir imagen API:

```bash
gcloud builds submit ./api-sonar-main/api-sonar-main --tag gcr.io/$PROJECT_ID/sonar-api
```

2. construir imagen frontend:

```bash
gcloud builds submit ./sorteo-sonar-main --tag gcr.io/$PROJECT_ID/sonar-app
```

3. crear Cloud SQL PostgreSQL y Memorystore Redis
4. guardar secretos en Secret Manager
5. desplegar API:

```bash
gcloud run deploy sonar-api \
  --image gcr.io/$PROJECT_ID/sonar-api \
  --region europe-west1 \
  --allow-unauthenticated \
  --set-env-vars REQUIRE_ADMIN_AUTH=true,ENVIRONMENT_LABEL=production
```

6. desplegar frontend:

```bash
gcloud run deploy sonar-app \
  --image gcr.io/$PROJECT_ID/sonar-app \
  --region europe-west1 \
  --allow-unauthenticated
```

### AWS equivalente

Arquitectura recomendada:

- App Runner o ECS Fargate para API
- App Runner, ECS o frontend estático detrás de CloudFront
- RDS PostgreSQL
- ElastiCache Redis
- Secrets Manager o SSM Parameter Store

### Variables que cambian

- `DATABASE_URL`
- `REDIS_URL`
- `CORS_ORIGINS`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `DB_POOL_SIZE`
- `DB_MAX_OVERFLOW`
- `ENVIRONMENT_LABEL`
- `DEPLOYMENT_CONTEXT`
- `SITE_CODE`
- `CAMPAIGN_CODE`

No cambia:

- la lógica experimental
- el esquema
- los endpoints
- el flujo de usuario
