# Pre-Event Warmup Checklist

Checklist de preapertura para evitar cold starts y llegar al primer pico con la API caliente.

Actualizado: `2026-05-02`

## 1. Objetivo

Antes de abrir, el sistema debe tener:

- conexion estable a PostgreSQL y Redis,
- mazo activo de tratamiento ya creado,
- mazo activo de pago ya creado,
- un result deck activo para cada tratamiento `norm_0..norm_60` y `control`,
- demos vigentes precargadas,
- endpoints de salud y configuracion ya calentados.

## 2. Que se precarga

### Roots

Precargar:

- el `legacy root` asociado al primer `treatment deck` activo,
- sus `series` internas para los 62 tratamientos.

No precargar:

- un segundo `treatment deck` activo,
- roots extras "por si acaso".

Motivo:

- el runtime actual crea el root cuando crea el primer treatment deck,
- un segundo deck activo alteraria la semantica normal de consumo.

### Decks

Precargar:

- `1` treatment deck activo,
- `1` payment deck activo,
- `62` result decks activos, uno por tratamiento,
- los tres demos:
  - `CTRL1234`
  - `NORM0000`
  - `NORM0001`

No hacer:

- crear sesiones reales para calentar la app,
- consumir cartas reales con pulseras de campo,
- usar codigos de demo antiguos.

## 3. Script recomendado

Usar:

- [ops/pre_event_warmup.py](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/ops/pre_event_warmup.py>)

### Misma maquina o contenedor del backend

Si el entorno tiene `DATABASE_URL` y `REDIS_URL` reales:

```powershell
python C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\ops\pre_event_warmup.py `
  --base-url https://api-XXXX.up.railway.app `
  --iterations 5 `
  --json-out C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\outputs\qa_reports\pre_event_warmup.json
```

### Solo comprobacion HTTP

Si no quieres tocar DB desde esa maquina:

```powershell
python C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\ops\pre_event_warmup.py `
  --base-url https://api-XXXX.up.railway.app `
  --skip-db-warmup `
  --iterations 5
```

## 4. Orden recomendado

### 30-20 minutos antes de abrir

1. Confirmar deploy estable.
2. Confirmar:
   - `/health/live`
   - `/health/ready`
   - `/admin/live`
3. Ejecutar `pre_event_warmup.py` con DB warmup si es posible.

Resultado esperado:

- `1` treatment deck activo,
- `1` payment deck activo,
- `62` result decks activos,
- `redis_ping_ok = true`.

### 15-10 minutos antes de abrir

1. Ejecutar warmup HTTP con `5` iteraciones.
2. Guardar el JSON del informe.
3. Revisar latencias:
   - `/health/live`
   - `/health/ready`
   - `/health`
   - `/v1/config`

Objetivo practico:

- sin errores `5xx`,
- sin timeouts,
- sin primer request anormalmente lento por cold path.

### 5 minutos antes de abrir

1. Repetir solo el warmup HTTP.
2. Abrir `/admin/live` en una pestana dedicada.
3. Hacer una prueba humana con demo vigente.

## 5. Criterios de aceptacion

- `health/live` responde `200`
- `health/ready` responde `200`
- `v1/config` responde `200`
- Redis responde
- treatment deck activo existe
- payment deck activo existe
- existen `62` result decks activos
- demos precargadas existen
- no se han creado sesiones reales de calentamiento

## 6. Que vigilar durante el primer pico

- subida de latencia en `/v1/session/access`
- subida de latencia en `/v1/session/roll`
- errores `5xx` o `409` anormales
- si aparece un primer acceso muy lento, repetir warmup HTTP y revisar `/admin/live`

## 7. Regla operativa

No usar participantes reales para calentar el sistema.

El warmup correcto crea estructuras y calienta endpoints sin consumir cartas reales ni contaminar la operacion de campo.
