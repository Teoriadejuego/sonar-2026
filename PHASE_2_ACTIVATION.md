# Phase 2 Activation

## Regla
La Fase 2 se activa automáticamente cuando `valid_completed_count` alcanza `6000`.

Cuenta como válida una sesión que cumple:
- consentimiento aceptado
- primera tirada realizada
- claim final registrado
- estado final completado
- no fraude crítico
- no corrupción de estado

## Tratamientos
### Fase 1
- `control`
- `seed_low`
- `seed_high`

### Fase 2
- `control`
- `seed_low`
- `seed_high`
- `seed_low_5`
- `seed_high_5`

## Persistencia
La activación queda guardada en `experiment_state`:
- `current_phase`
- `phase_2_activated_at`
- `valid_completed_count`
- `treatment_version`
- `allocation_version`

Cada sesión guarda:
- `experiment_phase`
- `phase_activation_status`

## Separación analítica
- Fase 2 crea roots nuevas y separadas.
- No se mezclan series de Fase 1 y Fase 2.
- `treatment_family` permite distinguir `control`, normas sobre `6` y normas sobre `5`.

## Cómo probarla
1. Resetear base con `python migrate.py`.
2. Poner `valid_completed_count = 5999`.
3. Completar una sesión válida nueva.
4. Comprobar:
   - [admin/experiment](http://127.0.0.1:8000/admin/experiment)
   - [admin/roots](http://127.0.0.1:8000/admin/roots)
5. La siguiente sesión nueva ya debe asignarse en `phase_2_robustness`.
