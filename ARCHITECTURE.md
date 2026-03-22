# SONAR Architecture

Resumen tecnico de la arquitectura actual de SONAR 2026.

Actualizado: `2026-03-22`

## Objetivo de arquitectura

Mantener una sola pila reproducible para:

- trabajo local,
- review con coautores,
- aula o piloto,
- despliegue de evento.

La idea central es simple:

- no hay una logica experimental para local y otra para produccion,
- no hay un frontend “demo” separado del flujo real,
- no hay una segunda base de datos para el estado del experimento.

Cambian credenciales, dominios y capacidad. La logica base es la misma.

## Componentes

### Frontend

Ruta: `sorteo-sonar-main/`

Responsabilidades:

- UI mobile-first de la experiencia,
- internacionalizacion,
- captura de telemetria de interfaz,
- manejo de sesion en cliente,
- codigos demo para review visual sin contaminar datos reales.

### Backend

Ruta: `api-sonar-main/api-sonar-main/`

Responsabilidades:

- asignacion experimental,
- control de fases, roots y series,
- captura de claims y snapshots,
- logica de payout,
- paneles admin,
- exports y auditoria.

### PostgreSQL

Responsabilidades:

- persistencia autoritativa de sesiones,
- claims,
- payments,
- payout requests,
- telemetry,
- exports y trazas operativas.

### Redis

Responsabilidades:

- locks distribuidos,
- rate limiting,
- idempotencia,
- coordinacion de secciones criticas,
- estado de pausa del experimento.

## Flujo de alto nivel

1. El frontend solicita acceso con una pulsera.
2. El backend valida, asigna tratamiento, root, posicion y estado inicial.
3. El participante avanza por instrucciones, comprension y dado.
4. Antes del reporte final se congela el snapshot visible que vera ese participante.
5. El claim actualiza la ventana social y, si procede, el estado de pago.
6. La app muestra salida de ganador o no ganador y capas finales de engagement.
7. Admin, exports y paneles leen el mismo esquema operativo.

## Fuente de verdad configuracional

Archivo maestro:

- [project_parameters.json](./project_parameters.json)

Ese archivo define:

- versiones del experimento,
- fases,
- tratamientos,
- tamanos de ventana,
- limites de serie,
- premios,
- umbrales de calidad.

## Concurrencia y consistencia

La consistencia del experimento no descansa en el frontend. El backend usa:

- locks Redis,
- transacciones SQL,
- `FOR UPDATE` donde corresponde,
- idempotency keys,
- constraints para evitar dobles claims o dobles payout requests.

Documento tecnico:

- [CONCURRENCY_GUARANTEES.md](./CONCURRENCY_GUARANTEES.md)

## Dominios y entornos actuales

### Publico

- app principal: [https://dice.sonar2026.es](https://dice.sonar2026.es)
- app Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)
- api Railway actual: [https://api-production-9fe7b.up.railway.app](https://api-production-9fe7b.up.railway.app)

### Local

- app: [http://localhost:3000](http://localhost:3000)
- api: [http://127.0.0.1:8000](http://127.0.0.1:8000)

## Principios de diseno del sistema

- mobile-first real,
- una sola accion principal por pantalla,
- logica experimental en backend,
- trazabilidad suficiente para reconstruir lo visible,
- posibilidad de auditar QR, invitaciones y notas operativas,
- despliegue contenedorizado desde Dockerfiles existentes.

## Limitaciones y caveats honestos

- la tasa `1/100` es esperada, no una cuota exacta cerrada,
- si Railway regenera el dominio de la API, el frontend debe actualizar `VITE_API_URL`,
- los datos de payout no viven todavia en una base fisicamente separada del experimento,
- el fallback a Qualtrics requiere operativa externa o una capa de redirect controlado.
