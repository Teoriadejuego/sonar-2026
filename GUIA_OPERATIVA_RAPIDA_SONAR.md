# Guia Operativa Rapida SONAR

Documento de referencia rapida para usar, revisar y actualizar SONAR sin tener que reconstruir todo el contexto cada vez.

## 1. Direcciones importantes

### Entorno local

- Frontend local: [http://localhost:3000](http://localhost:3000)
  Uso: probar la app completa en el ordenador o en el movil dentro de tu misma red local.

- API local live: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
  Uso: comprobar que el backend esta arrancado.

- API local ready: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)
  Uso: comprobar que backend, Postgres y Redis estan listos.

### Entorno Railway actual

- API Railway: [https://sonar-2026private-production.up.railway.app](https://sonar-2026private-production.up.railway.app)
  Uso: backend publico actual.

- API Railway live: [https://sonar-2026private-production.up.railway.app/health/live](https://sonar-2026private-production.up.railway.app/health/live)
  Uso: comprobar que el backend esta vivo.

- API Railway ready: [https://sonar-2026private-production.up.railway.app/health/ready](https://sonar-2026private-production.up.railway.app/health/ready)
  Uso: comprobar que backend, Postgres y Redis estan listos.

- Frontend Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
  Uso: app publica actual para pruebas.

- Dominio final de la app: [https://dice.sonar2026.es](https://dice.sonar2026.es)
  Estado: configurado en DNS y apuntando a Railway. Si no abre todavia, suele ser propagacion de DNS o cache local.

- Dominio raiz institucional: `sonar2026.es`
  Uso previsto: redirigirlo a la web oficial o institucional que elijas.

## 2. Paneles y zonas de datos

Todos los paneles admin viven en la API y requieren autenticacion basica.

- Dashboard cientifico-operativo local:
  [http://127.0.0.1:8000/admin/dashboard](http://127.0.0.1:8000/admin/dashboard)
  Uso: ver estado general, fase, premios, balance y controles operativos en local.

- Dashboard cientifico-operativo:
  [https://sonar-2026private-production.up.railway.app/admin/dashboard](https://sonar-2026private-production.up.railway.app/admin/dashboard)
  Uso: ver estado general, fase, premios, balance y controles operativos.

- Estado del experimento local:
  [http://127.0.0.1:8000/admin/experiment](http://127.0.0.1:8000/admin/experiment)
  Uso: ver fase activa, pausa/reactivacion y nota operativa activa en local.

- Estado del experimento:
  [https://sonar-2026private-production.up.railway.app/admin/experiment](https://sonar-2026private-production.up.railway.app/admin/experiment)
  Uso: ver fase activa, pausa/reactivacion, premios, nota operativa activa.

- Roots y series local:
  [http://127.0.0.1:8000/admin/roots](http://127.0.0.1:8000/admin/roots)
  Uso: inspeccionar series, roots y evolucion de ventanas en local.

- Roots y series:
  [https://sonar-2026private-production.up.railway.app/admin/roots](https://sonar-2026private-production.up.railway.app/admin/roots)
  Uso: inspeccionar series, roots y evolucion de ventanas.

- Exports local:
  [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)
  Uso: descargar datasets y paquetes ZIP en local.

- Exports:
  [https://sonar-2026private-production.up.railway.app/admin/exports](https://sonar-2026private-production.up.railway.app/admin/exports)
  Uso: descargar datasets y paquetes ZIP.

- Export CSV de sesiones local:
  [http://127.0.0.1:8000/admin/export/sessions.csv](http://127.0.0.1:8000/admin/export/sessions.csv)
  Uso: dataset analitico base por sesion en local.

- Export CSV de sesiones:
  [https://sonar-2026private-production.up.railway.app/admin/export/sessions.csv](https://sonar-2026private-production.up.railway.app/admin/export/sessions.csv)
  Uso: dataset analitico base por sesion.

- Export ZIP completo local:
  [http://127.0.0.1:8000/admin/export/bundle/all.zip](http://127.0.0.1:8000/admin/export/bundle/all.zip)
  Uso: paquete completo con manifest y datasets en local.

- Export ZIP completo:
  [https://sonar-2026private-production.up.railway.app/admin/export/bundle/all.zip](https://sonar-2026private-production.up.railway.app/admin/export/bundle/all.zip)
  Uso: paquete completo con manifest y datasets.

- Export de notas operativas local:
  [http://127.0.0.1:8000/admin/export/operational_notes.csv](http://127.0.0.1:8000/admin/export/operational_notes.csv)
  Uso: recuperar anotaciones de contexto operativo en local.

- Export de notas operativas:
  [https://sonar-2026private-production.up.railway.app/admin/export/operational_notes.csv](https://sonar-2026private-production.up.railway.app/admin/export/operational_notes.csv)
  Uso: recuperar anotaciones de contexto operativo.

- Inspeccion de una pulsera concreta:
  `https://sonar-2026private-production.up.railway.app/admin/session/<BRACELET_ID>`
  Uso: revisar el historial de una pulsera o sesion concreta.

## 3. Credenciales y acceso

### Local

- Usuario admin local: `admin`
- Password admin local: ver [\.env.local](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/.env.local)
  Valor actual: `sonar-local-admin`

### Railway

- Usuario admin Railway: `admin`
- Password admin Railway: el que hayas puesto en Railway `api -> Variables -> ADMIN_PASSWORD`

No compartas el admin con coautores si solo quieres que prueben la app.

## 4. Codigos demo que funcionan

Estos codigos son para revisar pantallas y no deben contaminar las series reales porque funcionan como modo demo del frontend:

- `1234`
  Uso: ganador demo.

- `12341`
  Uso: tratamiento `control` demo.

- `12342`
  Uso: tratamiento `seed_low` demo.

- `12343`
  Uso: tratamiento `seed_high` demo.

## 5. Parametros QR y carteles

Puedes etiquetar carteles fisicos usando URLs como:

- `https://dice.sonar2026.es/?qr=cartel_entrada_a`
- `https://dice.sonar2026.es/?qr=hall_b`
- `https://dice.sonar2026.es/?qr=barra_1&utm_campaign=carteles_sonar`

La app guarda `qr_entry_code` y, si no indicas otra cosa, completa:

- `referral_source = "qr"`
- `referral_medium = "offline_poster"`

## 6. Notas operativas de campo

Si ocurre algo durante el despliegue real:

- cambio de localizacion
- cambio de dinamica
- incidencia con premios
- saturacion o corte de red

puedes registrarlo desde:

- [https://sonar-2026private-production.up.railway.app/admin/dashboard](https://sonar-2026private-production.up.railway.app/admin/dashboard)

Bloque:

- `Contexto operativo`

La nota queda grabada y se adjunta a registros nuevos desde ese momento.

## 6.1 Donde se guarda la pantalla "Clica una"

La seleccion de la pantalla final de iconos queda guardada en telemetria con:

- `event_name = prize_reveal_pick`
- `event_name = prize_reveal_resolved`

Y dentro del `payload_json` veras:

- `selected_index`
- `winner_index`
- `selected_category`
- `winner_category`
- `eligible_for_payment`

Para revisarlo, lo mas comodo es descargar el bundle completo desde:

- local: [http://127.0.0.1:8000/admin/export/bundle/all.zip](http://127.0.0.1:8000/admin/export/bundle/all.zip)
- Railway: [https://sonar-2026private-production.up.railway.app/admin/export/bundle/all.zip](https://sonar-2026private-production.up.railway.app/admin/export/bundle/all.zip)

Y abrir dentro el CSV de telemetria.

## 6.2 Ojo con las URLs de base de datos

Las URLs de Postgres y Redis no se prueban en el navegador.

- `DATABASE_URL` sirve para que conecte el backend
- `REDIS_URL` sirve para locks, cache y estado

Si quieres comprobar que esas bases estan funcionando, usa:

- [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)
- [https://sonar-2026private-production.up.railway.app/health/ready](https://sonar-2026private-production.up.railway.app/health/ready)

Si `ready` responde bien, backend, Postgres y Redis estan conectados.

## 7. Protocolo rapido para subir una version local a la web

### Antes de subir

1. Arranca en local:

```powershell
docker compose --env-file .env.local up --build
```

2. Comprueba:

- [http://localhost:3000](http://localhost:3000)
- [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)

3. Prueba al menos:

- `12341`
- `12342`
- `12343`
- `1234`

4. Revisa si has tocado:

- frontend visual
- backend
- migraciones
- variables de entorno
- CORS

### Publicar en GitHub

```powershell
git status
git add .
git commit -m "Describe el cambio"
git push origin main
```

### Desplegar en Railway

1. Entra en Railway
2. Servicio `api`:
   - si hubo cambios backend o migraciones, espera a que despliegue
3. Servicio `app`:
   - si hubo cambios frontend, espera a que despliegue

Si Railway no dispara solo el despliegue:

- usa `Deploy Latest Commit`

### Comprobacion minima post-deploy

1. Backend:
- [https://sonar-2026private-production.up.railway.app/health/live](https://sonar-2026private-production.up.railway.app/health/live)
- [https://sonar-2026private-production.up.railway.app/health/ready](https://sonar-2026private-production.up.railway.app/health/ready)

2. Frontend:
- [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
- [https://dice.sonar2026.es](https://dice.sonar2026.es)

3. Prueba rapida:
- `12341`
- `1234`

4. Si cambiaste el dominio del frontend, recuerda actualizar en `api`:

```text
CORS_ORIGINS=https://app-production-4b8d.up.railway.app,https://dice.sonar2026.es
```

5. Si cambiaste el dominio del backend, recuerda actualizar en `app`:

```text
VITE_API_URL=https://<nuevo-dominio-api>
```

## 8. Donde mirar si algo falla

### Si falla la app publica

Revisar:

- Railway `app -> Deployments -> Logs`
- Railway `api -> Deployments -> Logs`

### Si falla el backend

Comprobar:

- `DATABASE_URL`
- `REDIS_URL`
- migraciones
- `PORT`
- `CORS_ORIGINS`

### Si falla el dominio `dice.sonar2026.es`

Comprobar:

- Railway `app -> Settings -> Networking -> Custom Domain`
- Hostalia DNS:

```text
CNAME
Host: dice
Destino: xzo5sj0s.up.railway.app
```

Y si aun no abre:

```powershell
ipconfig /flushdns
```

o probar con datos moviles.

## 9. Checklist minimo de salida a campo

- `api` responde en `/health/ready`
- `app` carga en movil
- `dice.sonar2026.es` abre
- codigos demo funcionan
- admin pide credenciales
- dashboard carga
- exports cargan
- si hay cambio de contexto, se registra nota operativa

## 10. Archivos utiles del proyecto

- Guia Railway minima:
  [RAILWAY_REVIEW_DEPLOY.md](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/RAILWAY_REVIEW_DEPLOY.md)

- Guia Railway + Hostalia:
  [RAILWAY_HOSTALIA_DEPLOY.md](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/RAILWAY_HOSTALIA_DEPLOY.md)

- Checklist de despliegue:
  [DEPLOYMENT_CHECKLIST.md](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/DEPLOYMENT_CHECKLIST.md)

- README raiz:
  [README.md](C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/README.md)
