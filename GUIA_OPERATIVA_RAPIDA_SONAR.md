# Guia Operativa Rapida SONAR

Documento rapido para operar, revisar y actualizar SONAR sin reconstruir el contexto desde cero.

Actualizado: `2026-03-22`

## 1. Direcciones importantes

### Entorno local

- Frontend local: [http://localhost:3000](http://localhost:3000)
- API local live: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- API local ready: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)

### Entorno publico actual

- App principal: [https://dice.sonar2026.es](https://dice.sonar2026.es)
- App Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
- API Railway: [https://api-production-9fe7b.up.railway.app](https://api-production-9fe7b.up.railway.app)
- API live: [https://api-production-9fe7b.up.railway.app/health/live](https://api-production-9fe7b.up.railway.app/health/live)
- API ready: [https://api-production-9fe7b.up.railway.app/health/ready](https://api-production-9fe7b.up.railway.app/health/ready)

Nota:

- si Railway regenera el dominio del backend, revisa `api -> Settings -> Networking`,
- y confirma que `app -> Variables -> VITE_API_URL` apunta al dominio nuevo.

## 2. Paneles y zonas de datos

Todos los paneles admin viven en la API y requieren autenticacion basica.

### Local

- Dashboard: [http://127.0.0.1:8000/admin/dashboard](http://127.0.0.1:8000/admin/dashboard)
- Estado del experimento: [http://127.0.0.1:8000/admin/experiment](http://127.0.0.1:8000/admin/experiment)
- Roots y series: [http://127.0.0.1:8000/admin/roots](http://127.0.0.1:8000/admin/roots)
- Exports: [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)
- Bundle ZIP: [http://127.0.0.1:8000/admin/export/bundle/all.zip](http://127.0.0.1:8000/admin/export/bundle/all.zip)

### Publico

- Dashboard: [https://api-production-9fe7b.up.railway.app/admin/dashboard](https://api-production-9fe7b.up.railway.app/admin/dashboard)
- Estado del experimento: [https://api-production-9fe7b.up.railway.app/admin/experiment](https://api-production-9fe7b.up.railway.app/admin/experiment)
- Roots y series: [https://api-production-9fe7b.up.railway.app/admin/roots](https://api-production-9fe7b.up.railway.app/admin/roots)
- Exports: [https://api-production-9fe7b.up.railway.app/admin/exports](https://api-production-9fe7b.up.railway.app/admin/exports)
- Bundle ZIP: [https://api-production-9fe7b.up.railway.app/admin/export/bundle/all.zip](https://api-production-9fe7b.up.railway.app/admin/export/bundle/all.zip)

Inspeccion de una pulsera concreta:

- `https://api-production-9fe7b.up.railway.app/admin/session/<BRACELET_ID>`

## 3. Credenciales y acceso

### Local

- usuario: `admin`
- password: ver `.env.local`

### Railway

- usuario: `admin`
- password: valor actual de `ADMIN_PASSWORD` en el servicio `api`

## 4. Codigos demo

Para revision visual o de copy:

- `1234`: ganador demo
- `12341`: control demo
- `12342`: `seed_low` demo
- `12343`: `seed_high` demo

Estos codigos no deben contaminar las series reales.

## 5. QR, carteles e invitaciones

Ejemplos de URLs:

- `https://dice.sonar2026.es/?qr=puerta_norte`
- `https://dice.sonar2026.es/?qr=barra_a`
- `https://dice.sonar2026.es/?qr=hall_b&utm_campaign=carteles_sonar`

La app guarda:

- `qr_entry_code`
- `referral_source`
- `referral_medium`
- `invited_by_referral_code`

La invitacion por WhatsApp utiliza `?ref=<codigo>&src=whatsapp`.

## 6. Notas operativas de campo

Si ocurre una incidencia o cambio de contexto:

- cambio de localizacion,
- corte de red,
- cambio de dinamica,
- pausa operativa,
- observacion metodologica importante,

registrala desde:

- [https://api-production-9fe7b.up.railway.app/admin/dashboard](https://api-production-9fe7b.up.railway.app/admin/dashboard)

Bloque:

- `Contexto operativo`

La nota queda grabada y se propaga a registros nuevos.

## 7. Donde mirar si algo falla

### La demo funciona pero las pulseras reales no

Revisar:

1. `https://api-production-9fe7b.up.railway.app/health/ready`
2. `app -> Variables -> VITE_API_URL`
3. `api -> Variables -> CORS_ORIGINS`

### El frontend abre pero el backend no responde

Revisar:

- health live,
- health ready,
- logs del servicio `api`,
- dominio actual en Railway `api -> Networking`.

### El dominio custom falla pero Railway funciona

Revisar:

- DNS en Hostalia,
- custom domain en Railway `app -> Networking`,
- estado SSL y propagacion.

## 8. Protocolo rapido para subir una version nueva

### Antes de publicar

1. probar en local,
2. validar:
   - `tsc --noEmit`
   - `react-router build`
   - `python -m py_compile` del backend tocado,
3. comprobar los demos y, si aplica, una pulsera real.

### Publicar en GitHub

```powershell
git status
git add .
git commit -m "Describe el cambio"
git push origin main
```

### Despliegue en Railway

- `api`: esperar o forzar `Deploy latest commit` si hubo cambios backend,
- `app`: esperar o forzar `Deploy latest commit` si hubo cambios frontend.

### Comprobacion minima post-deploy

1. Backend:
   - [https://api-production-9fe7b.up.railway.app/health/live](https://api-production-9fe7b.up.railway.app/health/live)
   - [https://api-production-9fe7b.up.railway.app/health/ready](https://api-production-9fe7b.up.railway.app/health/ready)
2. Frontend:
   - [https://dice.sonar2026.es](https://dice.sonar2026.es)
   - [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)

## 9. Fallback a Qualtrics

Hoy no es automatico.

Recomendacion operativa:

- no imprimir QR apuntando de forma irreversible a la app,
- usar una URL de redirect intermedia cuando sea posible,
- si la app cae, cambiar el redirect a Qualtrics,
- registrar una nota operativa indicando desde que momento cambio el flujo.
