# Concurrency Guarantees

SONAR combina Redis, PostgreSQL e idempotencia persistente para evitar corrupción bajo concurrencia.

## Capas de protección

## 1. Redis distributed locks

Se usan locks en:

- `bracelet:{bracelet_id}`
- `assignment`
- `session:{session_id}`
- `series:{series_id}`
- `payment:{code}`
- `experiment-control`

Sirven para coordinar múltiples procesos o réplicas del backend.

## 2. PostgreSQL row-level locking

En rutas críticas se leen entidades con `FOR UPDATE` cuando la base no es SQLite:

- estado global del experimento
- roots activas
- series de asignación
- sesiones durante `roll`, `prepare-report`, `submit-report`
- pagos durante `payment_submit`

## 3. Unique constraints

La base impide duplicados peligrosos mediante restricciones como:

- una sesión por usuario
- una posición por `(series_id, position_index)`
- una tirada por `(session_id, attempt_index)`
- un claim por sesión
- un pago por claim
- un `payout_request` por pago
- una receipt por `(session_id, endpoint, idempotency_key)`

## 4. Idempotencia

Las rutas críticas guardan receipts en PostgreSQL y Redis:

- `roll`
- `prepare-report`
- `submit-report`

Si llega el mismo `idempotency_key`, se devuelve la misma respuesta.

## 5. Rate limiting

Redis limita ráfagas en:

- `access`
- acciones de sesión
- pagos

## Riesgos mitigados

- dos alumnos ocupando la misma posición
- doble claim
- doble cobro
- doble activación de fase 2
- colisión entre réplicas del backend
- reintentos de red que repiten side effects
