# SONAR Event-Ready System Architecture

## Objetivo

Este documento consolida la arquitectura operativa completa del sistema SONAR para un evento real. Integra:

- gateway de entrada para QR
- frontend público
- backend duplicado
- PostgreSQL compartido
- Redis compartido
- failover manual y automático
- tracking de QR y referrals
- dashboard de observabilidad y métricas en tiempo real

## Topología final

```text
Usuario
  -> QR impreso
  -> play.sonar-experiment.com
       -> Gateway SONAR
           -> principal o backup
               -> Frontend público
                   -> API A / API B
                       -> PostgreSQL compartido
                       -> Redis compartido
                           -> métricas runtime, locks, idempotencia

Operación / staff
  -> /admin/live
  -> /admin/metrics
  -> /admin/gateway/*
  -> /admin/referrals/summary
```

## Componentes

### 1. Gateway de entrada

Función:

- recibe tráfico desde QR
- identifica `qr`, `qr_id` o `path`
- registra cada acceso
- redirige al destino activo
- conmuta entre principal y backup sin redeploy

Endpoints principales:

- `GET /play`
- `GET /play/{qr_code}`
- `GET /admin/gateway/routes`
- `POST /admin/gateway/routes`
- `GET /admin/gateway/mode`
- `POST /admin/gateway/mode`
- `GET /admin/gateway/failover`
- `POST /admin/gateway/failover/check-now`
- `POST /admin/gateway/routes/{qr_code}/switch`
- `GET /admin/gateway/summary`
- `GET /admin/gateway/logs`

### 2. Frontend público

Función:

- recibe usuarios desde el gateway
- conserva `qr`, `link_id`, `ref_id`
- ejecuta el flujo experimental
- es cliente puro: el backend es la única fuente de verdad
- tolera red inestable con retry y reentrada

Variable crítica:

- `VITE_API_URL=https://api.sonar2026.es`

### 3. Backend duplicado

Función:

- `API A` y `API B` usan el mismo código
- comparten la misma base de datos
- comparten el mismo Redis
- exponen healthchecks
- mantienen idempotencia y consistencia de claims

Healthchecks:

- `GET /health/live`
- `GET /health/ready`
- `GET /health`

### 4. PostgreSQL compartido

Fuente de verdad de:

- usuarios
- sesiones
- tiradas
- claims
- pagos
- snapshots
- scans de QR
- referrals
- métricas derivadas persistidas

### 5. Redis compartido

Uso operativo:

- locks distribuidos
- receipts de idempotencia
- coordinación HA
- métricas runtime compartidas

## Módulos integrados

### Redirección y QR

- soporta `play.sonar-experiment.com/?qr_id=ZONE_A_01`
- soporta `play.sonar-experiment.com/play/ZONE_A_01`
- registra zona, QR, agente, host, query, destino resuelto y `gateway_visit_id`
- enlaza más tarde el acceso QR con la `session_id`

### Tracking completo

Cobertura actual:

- escaneos QR por código y por zona
- sesiones iniciadas por QR
- ratio escaneo -> entrada
- referral links
- referral clicks
- conversiones por invitación
- invitador -> invitado
- rendimiento por endpoint
- alertas y calidad de datos

### Failover

Modos soportados:

- manual global `primary | backup`
- manual por QR
- automático por healthcheck

Reglas:

- threshold de fallos consecutivos
- cambio inmediato sin reinicio
- bloqueo del failover si faltan backups válidos
- logging estructurado de cada evento de conmutación

### Dashboard en tiempo real

Cobertura:

- participantes totales
- activos
- completados
- tasa de finalización
- reportes de `6`
- mentiras
- distribución de resultados
- ganadores
- importe total
- tráfico por QR
- rendimiento por zona
- invitaciones y conversiones
- latencia por endpoint
- errores por endpoint
- abandono y calidad de datos

## Endpoints operativos finales

### Entrada y seguimiento

- `GET /play`
- `GET /play/{qr_code}`
- `GET /invite/{referral_link_id}`
- `POST /v1/referrals/link`

### Estado del backend

- `GET /health/live`
- `GET /health/ready`
- `GET /health`

### Gateway

- `GET /admin/gateway/routes`
- `POST /admin/gateway/routes`
- `GET /admin/gateway/mode`
- `POST /admin/gateway/mode`
- `GET /admin/gateway/failover`
- `POST /admin/gateway/failover/check-now`
- `POST /admin/gateway/routes/{qr_code}/switch`
- `GET /admin/gateway/summary`
- `GET /admin/gateway/logs`

### Dashboard y métricas

- `GET /admin/live`
- `GET /admin/dashboard/live`
- `GET /admin/metrics`
- `GET /admin/metrics/experiment`
- `GET /admin/metrics/experiment/timeseries`
- `GET /admin/referrals/summary`

## Estructura de datos

### Tablas núcleo de operación

- `users`
- `sessions`
- `throws`
- `claims`
- `payments`
- `payout_requests`
- `snapshot_records`
- `telemetry_events`

### Tablas de gateway y tracking

- `gateway_routes`
- `gateway_access_logs`
- `referral_links`
- `referral_clicks`

### Campos clave por flujo

#### Sesión

- `session_id`
- `user_id`
- `bracelet_id`
- `treatment_key`
- `position_index`
- `state`
- `screen_cursor`
- `first_result_value`
- `reported_value`
- `is_honest`
- `claim_submitted_at`
- `completed_at`
- `qr_entry_code`
- `referral_link_id`
- `invited_by_session_id`

#### Claim

- `session_id`
- `true_first_result`
- `reported_value`
- `is_honest`
- `reroll_count`
- `displayed_count_target`
- `displayed_denominator`
- `reaction_ms`

#### Pago

- `session_id`
- `claim_id`
- `eligible`
- `amount_cents`
- `status`
- `payout_reference`

#### Solicitud de pago

- `payment_id`
- `requested_phone`
- `donation_requested`
- `status`

#### Scan QR

- `qr_code`
- `zone_code`
- `gateway_visit_id`
- `session_id`
- `selected_target`
- `resolved_target_url`
- `traffic_source`
- `traffic_medium`
- `request_user_agent`
- `created_at`

#### Referral

- `referral_link_id`
- `inviter_session_id`
- `inviter_referral_code`
- `click_count`
- `conversion_count`
- `session_id`

## Flujo de datos

### 1. Entrada desde QR

1. usuario escanea QR
2. `GET /play` o `GET /play/{qr_code}`
3. gateway identifica QR y zona
4. gateway registra scan en `gateway_access_logs`
5. gateway decide `primary` o `backup`
6. gateway redirige al frontend con `qr`, `link_id` y metadatos

### 2. Inicio de sesión experimental

1. frontend recoge `qr`, `link_id`, `ref_id`
2. usuario introduce pulsera y consiente
3. frontend llama a `access`
4. backend crea o reanuda sesión
5. backend enlaza el `gateway_visit_id` a `session_id`
6. backend persiste tratamiento, decks y referencias

### 3. Flujo experimental

1. roll
2. prepare-report
3. submit-report
4. claim y snapshot persistidos
5. outcome final calculado en backend
6. si hay pago, `payments` y `payout_requests`

### 4. Viralidad

1. usuario genera link con `POST /v1/referrals/link`
2. invitado entra por `GET /invite/{referral_link_id}`
3. se registra click en `referral_clicks`
4. cuando el invitado inicia sesión, se enlaza la conversión

### 5. Observabilidad

1. middleware registra latencia y errores
2. runtime agrega métricas en Redis o memoria
3. queries y payloads agregan sesiones, claims, pagos, QR y referrals
4. `/admin/dashboard/live` sirve el snapshot unificado
5. `/admin/live` lo presenta en HTML con polling cada 5s

## Garantías del sistema

### Consistencia de datos

- PostgreSQL como fuente de verdad
- frontend sin lógica crítica local
- claim idempotente
- snapshot congelado antes del claim
- sessions y claims no dependen del nodo API

### Resiliencia

- 2 backends idénticos
- failover manual y automático
- healthchecks de readiness
- sesión persistida y reentrada
- retry en acciones críticas

### Baja latencia

- endpoints calientes optimizados
- índices en rutas críticas
- dashboard basado en agregados ya preparados
- frontend con telemetría mínima y batching

## Checklist de despliegue

### Infraestructura

- [ ] dominio `play.*` apuntando al gateway
- [ ] dominio frontend activo con HTTPS
- [ ] dominio API activo con HTTPS
- [ ] PostgreSQL gestionado listo
- [ ] Redis compartido listo
- [ ] dos instancias backend desplegadas con misma imagen
- [ ] variables de entorno iguales en A y B
- [ ] `INSTANCE_NAME` distinto en A y B

### Base de datos y migraciones

- [ ] `alembic head` aplicado
- [ ] `gateway_routes` creadas
- [ ] backups configurados
- [ ] warmup de decks ejecutado

### Gateway

- [ ] rutas QR cargadas
- [ ] `primary_target_url` configurado
- [ ] `backup_target_url` configurado
- [ ] failover automático habilitado
- [ ] thresholds validados
- [ ] conmutación manual probada

### Backend

- [ ] `/health/live` = 200
- [ ] `/health/ready` = 200
- [ ] `/health` = 200
- [ ] `access -> roll -> prepare-report -> submit-report` validado
- [ ] `claim-followup` validado

### Tracking

- [ ] QR con `qr_id` o `path` único
- [ ] scans registrados con `gateway_visit_id`
- [ ] enlace `scan -> session` validado
- [ ] referral link creado y click registrado
- [ ] conversión referral validada

### Dashboard

- [ ] `/admin/metrics` responde
- [ ] `/admin/dashboard/live` responde
- [ ] `/admin/live` renderiza
- [ ] pagos aparecen
- [ ] QR y zonas aparecen
- [ ] referrals aparecen
- [ ] latencia y errores aparecen

### Ensayos antes de abrir

- [ ] warmup pre-evento ejecutado
- [ ] smoke test de 1 sesión real de extremo a extremo
- [ ] prueba de failover manual
- [ ] prueba de failover automático
- [ ] revisión de panel en móvil y desktop

## Verificación recomendada de go-live

1. crear al menos 2 rutas QR con primary y backup
2. abrir `/admin/live`
3. escanear un QR y verificar redirección y log
4. completar una sesión
5. verificar:
   - aparición en métricas
   - scan asociado a sesión
   - referral operativo si aplica
   - healthchecks en verde
6. forzar failover
7. repetir scan y comprobar salida por backup

## Estado esperado de producción

El sistema se considera listo para evento cuando:

- el gateway puede dirigir tráfico al frontend correcto
- el backend duplicado comparte estado sin duplicar claims
- los scans QR quedan atribuidos
- el dashboard refleja sesiones, pagos, QR, referrals y rendimiento
- la conmutación a backup funciona en segundos sin reiniciar servicios
