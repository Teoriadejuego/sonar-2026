# Festival Day Runbook

Runbook operativo para el dia de despliegue real.

Actualizado: `2026-03-22`

## 1. Antes de abrir

### Salud tecnica

Comprobar:

- [https://api-production-9fe7b.up.railway.app/health/live](https://api-production-9fe7b.up.railway.app/health/live)
- [https://api-production-9fe7b.up.railway.app/health/ready](https://api-production-9fe7b.up.railway.app/health/ready)
- [https://dice.sonar2026.es](https://dice.sonar2026.es)

### Revision de entorno

- `VITE_API_URL` apunta al dominio actual del backend,
- `CORS_ORIGINS` incluye `dice.sonar2026.es`,
- admin responde,
- la app abre en Android y en iPhone.

### Prueba funcional minima

Hacer:

- 1 prueba con codigo demo ganador,
- 1 prueba con demo no ganador,
- 1 prueba con una pulsera real si procede.

## 2. Durante el evento

### Donde mirar

- dashboard admin,
- health ready,
- logs de Railway `api`,
- logs de Railway `app`.

### Que registrar

Si cambia algo relevante:

- ubicacion,
- densidad de trafico,
- corte de red,
- cambio de staff,
- cambio de QR o cartel,
- incidencia de payout,

registrar nota operativa desde dashboard.

## 3. Nombres recomendados para QR

- `puerta_norte`
- `puerta_sur`
- `barra_a`
- `barra_b`
- `hall_principal`
- `staff_demo`

Evitar nombres ambiguos como `cartel1` o `qr2`.

## 4. Si algo falla

### La app abre pero no acepta pulseras reales

Revisar:

1. `https://api-production-9fe7b.up.railway.app/health/ready`
2. `VITE_API_URL`
3. dominio actual del backend
4. `CORS_ORIGINS`

### El frontend custom domain falla

Usar mientras tanto:

- [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)

### El experimento necesita pausa

- usar el panel admin para pausar,
- registrar nota operativa,
- comunicar al staff el cambio.

## 5. Fallback a Qualtrics

No esta automatizado dentro de la app.

Plan recomendado:

1. usar una URL de redirect intermedia para QR cuando sea posible,
2. si la app cae, cambiar el redirect a Qualtrics,
3. dejar nota operativa indicando hora y motivo,
4. conservar evidencia del cambio de canal.

## 6. Checklist de cierre del dia

- exportar bundle ZIP,
- descargar `sessions.csv`,
- descargar `telemetry.csv`,
- descargar `operational_notes.csv`,
- documentar incidencias del dia,
- anotar cualquier cambio de configuracion o decision metodologica tomada en caliente.

