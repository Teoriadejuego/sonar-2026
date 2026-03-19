# Local to Production

SONAR es la misma app en local, aula y producción.

## Qué no cambia

- modelos de datos
- tablas
- migraciones
- endpoints
- asignación experimental
- series espejo
- mazo balanceado
- snapshots
- antifraude
- exports

## Qué sí cambia

- servicio PostgreSQL local o gestionado
- servicio Redis local o gestionado
- número de réplicas del backend
- credenciales y secretos
- dominio y CORS
- observabilidad y alertas

## Secuencia recomendada

1. validar local con `docker compose`
2. pasar prueba de carga de aula
3. desplegar exactamente los mismos contenedores en cloud
4. ejecutar migraciones en producción
5. habilitar admin protegido
6. comprobar `/health/ready`

## Comandos base por entorno

### Local

```powershell
docker compose --env-file .env.local up --build
```

### Classroom

```powershell
docker compose --env-file .env.classroom up --build -d
& ".\.venv\Scripts\python.exe" ".\ops\classroom_load_test.py" --base-url http://127.0.0.1:8000 --users 60 --concurrency 60 --admin-username admin --admin-password sonar_admin_change_me
```

### Producción

1. construir imágenes
2. desplegar servicios gestionados
3. ejecutar:

```bash
python migrate.py
```

4. abrir tráfico solo cuando:

- `/health/live` sea `200`
- `/health/ready` sea `200`
- admin responda
- exports respondan

## Regla de oro

Si una funcionalidad no funciona en local con PostgreSQL y Redis, no está lista para aula ni para festival.
