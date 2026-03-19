# Admin Guide

## URLs clave
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Estado general: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Estado experimental: [http://127.0.0.1:8000/admin/experiment](http://127.0.0.1:8000/admin/experiment)
- Roots y series: [http://127.0.0.1:8000/admin/roots](http://127.0.0.1:8000/admin/roots)
- Dashboard científico: [http://127.0.0.1:8000/admin/dashboard](http://127.0.0.1:8000/admin/dashboard)
- Exports: [http://127.0.0.1:8000/admin/exports](http://127.0.0.1:8000/admin/exports)

## Qué mirar durante campo
- `current_phase`
- `valid_completed_count`
- balance por tratamiento
- dropout por pantalla
- frecuencia de 5 y 6
- flags de calidad
- flags de fraude
- evolución de `visible_count_target` y `actual_count_target`

## Sesión concreta
Para inspeccionar una pulsera:
- `GET /admin/session/{bracelet_id}`

Ejemplo:
- [http://127.0.0.1:8000/admin/session/10000002](http://127.0.0.1:8000/admin/session/10000002)

## Export recomendado
- Investigador analítico: `analytic.zip`
- Operación técnica: `operational.zip`
- Gestión de pagos: `administrative.zip`

## Cobro
El flujo administrativo de cobro está separado del experimento:
- la persona ganadora recibe un código
- usa la página `/payout?code=...`
- el backend valida y bloquea reutilización del código
