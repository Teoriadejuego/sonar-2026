# Guia Operativa Rapida SONAR

Documento rapido para operar, revisar y actualizar SONAR sin reconstruir el contexto desde cero.

Actualizado: `2026-05-14`

Nota:

- para operativa de staff y reduccion de errores humanos, usar como referencia principal `docs/FIELD_OPERATIONS_PROTOCOL.md`
- el diseno experimental vigente es `control + norm_0..norm_60`; la norma social es fija por tratamiento y no se actualiza dinamicamente durante la sesion

## 1. Direcciones importantes

### Entorno local

- Frontend local: [http://localhost:3000](http://localhost:3000)
- API local live: [http://127.0.0.1:8000/health/live](http://127.0.0.1:8000/health/live)
- API local ready: [http://127.0.0.1:8000/health/ready](http://127.0.0.1:8000/health/ready)

### Entorno publico actual

- App principal: [https://dice.sonar2026.es](https://dice.sonar2026.es)
- App Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
- API Railway: [https://api-production-9151.up.railway.app](https://api-production-9151.up.railway.app)
- API live: [https://api-production-9151.up.railway.app/health/live](https://api-production-9151.up.railway.app/health/live)
- API ready: [https://api-production-9151.up.railway.app/health/ready](https://api-production-9151.up.railway.app/health/ready)

Nota:

- si Railway regenera el dominio del backend, revisa `api -> Settings -> Networking`,
- y confirma que `app -> Variables -> VITE_API_URL` apunta al dominio nuevo.

### Fuente de verdad temporal

Hasta que Railway quede migrado de forma inequívoca a la estructura nueva, tratar:

- `app/frontend` y `app/backend` como fuente de desarrollo e investigacion;
- `.deploy_main/sorteo-sonar-main` y `.deploy_main/api-sonar-main/api-sonar-main` como espejo temporal de produccion si Railway sigue enlazado al repositorio antiguo;
- cualquier hotfix de campo debe quedar replicado en ambos lados antes de publicar.

No aceptar un despliegue como correcto solo por haber hecho `git push`: siempre verificar la firma del bundle servido por produccion.

## 2. Paneles y zonas de datos

Todos los paneles admin viven en la API y requieren autenticacion basica.

### Local

- Dashboard: [http://127.0.0.1:8000/admin/dashboard](http://127.0.0.1:8000/admin/dashboard)
- Estado del experimento: [http://127.0.0.1:8000/admin/experiment](http://127.0.0.1:8000/admin/experiment)
- Roots y series: [http://127.0.0.1:8000/admin/roots](http://127.0.0.1:8000/admin/roots)
- Exports: [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)
- Bundle ZIP: [http://127.0.0.1:8000/admin/export/bundle/all.zip](http://127.0.0.1:8000/admin/export/bundle/all.zip)

### Publico

- Dashboard: [https://api-production-9151.up.railway.app/admin/dashboard](https://api-production-9151.up.railway.app/admin/dashboard)
- Estado del experimento: [https://api-production-9151.up.railway.app/admin/experiment](https://api-production-9151.up.railway.app/admin/experiment)
- Roots y series: [https://api-production-9151.up.railway.app/admin/roots](https://api-production-9151.up.railway.app/admin/roots)
- Exports: [https://api-production-9151.up.railway.app/admin/exports](https://api-production-9151.up.railway.app/admin/exports)
- Bundle ZIP: [https://api-production-9151.up.railway.app/admin/export/bundle/all.zip](https://api-production-9151.up.railway.app/admin/export/bundle/all.zip)
- Dataset analitico humano: [https://api-production-9151.up.railway.app/admin/export/participant-analysis.csv](https://api-production-9151.up.railway.app/admin/export/participant-analysis.csv)
- Bundle analitico: [https://api-production-9151.up.railway.app/admin/export/bundle/analytic.zip](https://api-production-9151.up.railway.app/admin/export/bundle/analytic.zip)

Inspeccion de una pulsera concreta:

- `https://api-production-9151.up.railway.app/admin/session/<BRACELET_ID>`

## 3. Credenciales y acceso

### Local

- usuario: `admin`
- password: ver `.env.local`

### Railway

- usuario: `admin`
- password: valor actual de `ADMIN_PASSWORD` en el servicio `api`

## 4. Codigos demo

Para revision visual o de copy:

- `CTRL1234`: control demo
- `NORM0000`: norma demo `0/60`
- `NORM0001`: norma demo `1/60`

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
- `referral_link_id`
- `referral_landing_path`
- `invited_by_referral_code`

La invitacion por WhatsApp utiliza `?ref=<codigo>&src=whatsapp`.

En el dataset `participant-analysis.csv`, mirar:

- `entered_from_whatsapp`: el acceso vino marcado como WhatsApp;
- `shared_whatsapp_link_i`: el participante genero un enlace de invitacion por WhatsApp;
- `whatsapp_invite_clicks`: clicks acumulados en sus enlaces de invitacion;
- `throws_vector`: todas las tiradas servidas por backend en orden.

## 6. Notas operativas de campo

Si ocurre una incidencia o cambio de contexto:

- cambio de localizacion,
- corte de red,
- cambio de dinamica,
- pausa operativa,
- observacion metodologica importante,

registrala desde:

- [https://api-production-9151.up.railway.app/admin/dashboard](https://api-production-9151.up.railway.app/admin/dashboard)

Bloque:

- `Contexto operativo`

La nota queda grabada y se propaga a registros nuevos.

## 7. Donde mirar si algo falla

### La demo funciona pero las pulseras reales no

Revisar:

1. `https://api-production-9151.up.railway.app/health/ready`
2. `app -> Variables -> VITE_API_URL`
3. `api -> Variables -> CORS_ORIGINS`

Si el problema es un cambio de formato o de logica de validacion de pulseras, usar:

- [BRACELET_VALIDATION_LAST_MINUTE_GUIDE.md](BRACELET_VALIDATION_LAST_MINUTE_GUIDE.md)

Antes de abrir campo con pulseras nuevas:

1. probar una pulsera real en iPhone Safari;
2. probar una pulsera real en Android Chrome;
3. confirmar que el dashboard registra `qr_entry_code` y `referral_landing_path`;
4. registrar una nota operativa si cambia staff, ubicacion, red o validacion.

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

- confirmar en Railway que `api` y `app` apuntan al repo, rama y carpeta esperados;
- `api`: esperar o forzar `Deploy latest commit` si hubo cambios backend;
- `app`: esperar o forzar `Deploy latest commit` si hubo cambios frontend;
- fijar `SONAR_DATA_STATUS=pilot`, `SONAR_DATA_STATUS=final` o `SONAR_DATA_STATUS=synthetic` antes de generar el bundle final.

### Comprobacion minima post-deploy

1. Backend:
   - [https://api-production-9151.up.railway.app/health/live](https://api-production-9151.up.railway.app/health/live)
   - [https://api-production-9151.up.railway.app/health/ready](https://api-production-9151.up.railway.app/health/ready)
2. Frontend:
   - [https://dice.sonar2026.es](https://dice.sonar2026.es)
   - [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
3. Firma del bundle frontend:

```powershell
$html = Invoke-WebRequest -UseBasicParsing https://dice.sonar2026.es
$assets = ($html.Content | Select-String -Pattern 'assets/[^" ]+\.js' -AllMatches).Matches.Value
$assets
```

Despues de un hotfix de WhatsApp, la version correcta debe servir algun bundle que contenga:

- `whatsapp://send?text=`
- `https://api.whatsapp.com/send?text=`

4. Firma del backend:

```powershell
Invoke-WebRequest -UseBasicParsing https://api-production-9151.up.railway.app/health/ready
```

Con credenciales admin, confirmar que existen:

- `/admin/export/participant-analysis.csv`
- `/admin/export/bundle/analytic.zip`
- `analysis_ready_extended.csv` dentro del ZIP analitico

## 10. QA movil obligatorio antes de abrir campo

Probar flujo completo en:

- iPhone Safari normal;
- Android Chrome normal;
- modo incognito;
- red mala o 4G compartido.

Cubrir como minimo:

- no ganador;
- ganador;
- donacion ONG;
- reclamo de premio;
- WhatsApp invite;
- cierre final;
- QR real;
- pulsera real.

## 11. Fallback a Qualtrics

Hoy no es automatico.

Recomendacion operativa:

- no imprimir QR apuntando de forma irreversible a la app,
- usar una URL de redirect intermedia cuando sea posible,
- si la app cae, cambiar el redirect a Qualtrics,
- registrar una nota operativa indicando desde que momento cambio el flujo.
