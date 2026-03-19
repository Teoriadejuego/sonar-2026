# Deployment Checklist

## Antes de desplegar

- [ ] `docker compose --env-file .env.local up --build` funciona
- [ ] migraciones ejecutan sin error
- [ ] `/health/live` responde
- [ ] `/health/ready` responde con `database_ready=true`
- [ ] Redis responde y `redis_ready=true`
- [ ] admin requiere credenciales
- [ ] exports descargan correctamente
- [ ] prueba de aula con 60 usuarios pasa

## Railway

- [ ] crear servicios `api`, `app`, `postgres`, `redis`
- [ ] cargar variables de `.env.production.example`
- [ ] ejecutar `python migrate.py` como release command o job
- [ ] fijar dominio y CORS

## Google Cloud Run

- [ ] construir imagen de API
- [ ] construir imagen de frontend
- [ ] crear Cloud SQL PostgreSQL
- [ ] crear Memorystore Redis
- [ ] guardar secretos en Secret Manager
- [ ] desplegar API con `DATABASE_URL` y `REDIS_URL`
- [ ] desplegar frontend con `VITE_API_URL`
- [ ] ejecutar migraciones antes de abrir tráfico

## AWS

- [ ] subir imágenes a ECR
- [ ] desplegar API en App Runner o ECS
- [ ] desplegar frontend en App Runner, ECS o estático con proxy
- [ ] conectar RDS PostgreSQL
- [ ] conectar ElastiCache Redis
- [ ] configurar secretos y CORS

## Después de desplegar

- [ ] comprobar dashboard
- [ ] comprobar exports
- [ ] comprobar pausa/reactivación
- [ ] comprobar cobros
- [ ] registrar versión exacta desplegada
