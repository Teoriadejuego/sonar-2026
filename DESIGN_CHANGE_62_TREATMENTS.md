# Design Change: 62 Treatments

## Estado del cambio
SONAR deja de usar la logica experimental anterior basada en series espejo, seeds low/high y ventanas endogenas como estructura causal principal.

La version actual usa tres mazos independientes y persistentes:
- mazo de tratamientos de 62 cartas
- mazo de resultados de 24 cartas
- mazo de pagos de 100 cartas

## Tratamientos

### Universo de tratamientos
Existen exactamente 62 tratamientos:
- `norm_0`
- `norm_1`
- ...
- `norm_60`
- `control`

Interpretacion:
- `norm_k`: el participante ve `En un grupo de 60 resultados antes de ti, k personas reportaron un 6.`
- `control`: se muestra la caja neutra sin mensaje social

### Asignacion
Cada nuevo participante consume una carta del mazo de tratamientos activo.

Propiedades:
- cada mazo contiene exactamente una vez cada tratamiento
- cada bloque completo de 62 participantes consume el mazo entero
- el orden interno del mazo es aleatorio pero reproducible por semilla
- cuando se agota un mazo, se crea el siguiente
- una carta asignada queda consumida y no se recicla

Persistencia:
- `treatment_decks`
- `treatment_deck_cards`
- referencias en `sessions`

## Resultado real

### Mazo de resultados
La primera tirada real se asigna desde un mazo independiente de 24 cartas:
- 4 cartas con `1`
- 4 cartas con `2`
- 4 cartas con `3`
- 4 cartas con `4`
- 4 cartas con `5`
- 4 cartas con `6`

Propiedades:
- balance exacto 4x por valor dentro de cada bloque
- orden aleatorio reproducible por semilla
- independencia respecto al mazo de tratamientos
- cuando se agota, se crea un nuevo mazo

Objetivo:
- balancear la frecuencia real de `1` a `6`
- reducir rachas espurias
- estabilizar muestras finitas
- mejorar comparabilidad entre tratamientos

Persistencia:
- `result_decks`
- `result_deck_cards`
- referencias en `sessions`

## Rerolls
Los rerolls no usan el mazo de 24.

Regla implementada:
- la primera tirada queda balanceada por mazo
- los rerolls se generan por servidor con RNG reproducible derivado de:
  - semilla maestra
  - `session_id`
  - `attempt_index`

Esto permite:
- mantener balance estricto en la primera tirada
- mantener reproducibilidad e idempotencia en intentos posteriores
- evitar mezclar dos objetivos experimentales distintos en el mismo mazo

## Pago exacto 1/100

### Mazo de pagos
La elegibilidad de pago se asigna desde un mazo independiente de 100 cartas:
- 1 carta ganadora
- 99 cartas no ganadoras

Propiedades:
- exactamente 1 elegible por cada bloque de 100
- orden aleatorio reproducible por semilla
- backend autoritativo
- persistencia completa y exportable
- una carta asignada queda consumida y no se recicla

Persistencia:
- `payment_decks`
- `payment_deck_cards`
- referencias en `sessions`

## Concurrencia
La asignacion de acceso nuevo hace en una sola transaccion:
1. reserva de sesion
2. asignacion de tratamiento
3. asignacion de primera tirada real
4. asignacion de pago

Regla elegida:
- una vez asignada una carta, queda consumida aunque el participante abandone
- no se reciclan cartas para evitar ambiguedad metodologica y problemas de concurrencia

## Compatibilidad heredada
Se mantienen partes del sistema anterior cuando son utiles para infraestructura:
- backend autoritativo
- consentimiento
- payout separado
- referidos
- telemetria
- admin dashboard
- exports
- Railway, Docker y despliegue local

Las entidades legacy `root` y `series` permanecen solo como compatibilidad operativa para no romper paneles o campos historicos, pero ya no son la estructura causal principal del experimento.

## Demo IDs
Demo IDs documentados y estables:
- `CTRL1234`: `control`, ganador, primera tirada `6`
- `NORM0000`: `norm_0`, no ganador, primera tirada `4`
- `NORM0001`: `norm_1`, no ganador, primera tirada `5`

Todos cumplen el patron de pulsera:
- 8 caracteres
- exactamente 4 letras
- exactamente 4 numeros

## Como probar

### Acceso
- introducir `CTRL1234`, `NORM0000` o `NORM0001`
- aceptar consentimiento

### Verificacion minima
- `CTRL1234` debe mostrar control y terminar como ganador
- `NORM0000` debe mostrar `norm_0` y no ganar
- `NORM0001` debe mostrar `norm_1` y no ganar

### Salud backend
- `GET /health/live`
- `GET /health/ready`

### Export
Comprobar en `sessions.csv`:
- `treatment_key`
- `displayed_count_target`
- `displayed_denominator`
- `treatment_deck_index`
- `result_deck_index`
- `payment_deck_index`
- `payout_eligible`

## Interpretacion de exports

### Tratamiento asignado
Se reconstruye con:
- `sessions.treatment_key`
- `sessions.treatment_deck_index`
- `sessions.treatment_card_position`
- `treatment_deck_cards`

### Primera tirada real
Se reconstruye con:
- `sessions.result_deck_index`
- `sessions.result_card_position`
- `result_deck_cards.result_value`

### Pago
Se reconstruye con:
- `sessions.payment_deck_index`
- `sessions.payment_card_position`
- `payment_deck_cards.payout_eligible`

## Reset y migracion
La migracion añade tablas y columnas nuevas sin romper despliegues existentes.

Si se necesita reset limpio del experimento:
- reinicializar base de datos
- ejecutar migraciones
- arrancar backend
- `bootstrap_demo_data` recrea demos y mazos iniciales

No es necesario resetear Docker o Railway si la migracion se aplica correctamente.
