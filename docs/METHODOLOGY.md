# Methodology

Resumen metodologico del diseno vigente de SONAR 2026.

Actualizado: `2026-05-02`

## 1. Pregunta de investigacion

SONAR 2026 estudia como cambia el reporte en una tarea de honestidad privada cuando se introduce una norma descriptiva visible fija.

## 2. Unidad de participacion

Cada participacion es una sesion asociada a una pulsera.

La sesion registra:

- pulsera
- idioma
- tratamiento
- secuencia de pantallas
- tiradas
- snapshot visible antes del claim
- claim final
- elegibilidad de pago
- trazabilidad operativa minima

## 3. Flujo experimental

1. acceso con pulsera
2. consentimiento
3. instrucciones
4. comprension
5. primera tirada privada
6. rerolls opcionales
7. `prepare-report`
8. reporte del numero de la primera tirada
9. resolucion final

## 4. Diseno experimental vigente

El diseno experimental vigente es:

- `control`
- `norm_0`
- `norm_1`
- ...
- `norm_60`

Propiedades fijas:

- `62` tratamientos en total
- denominador fijo `60`
- valor objetivo fijo `6`
- `control` no muestra norma social
- `norm_X` muestra `X de 60 participantes...`

Frase canonica:

> El diseno experimental vigente es `control + norm_0..norm_60`. La norma social es fija por tratamiento y no se actualiza dinamicamente durante la sesion.

## 5. Que ve el participante

En `control`, el participante ve un mensaje neutro sin conteo social.

En `norm_X`, el participante ve un mensaje fijo derivado del tratamiento asignado. El conteo mostrado depende solo de `X` y del denominador `60`.

La norma social mostrada no cambia durante la sesion del participante.

## 6. Snapshot visible y claim

La decision metodologica central es:

- `prepare-report` congela el mensaje visible
- `submit-report` reutiliza exactamente ese snapshot
- el claim no depende de claims previos de otros participantes

Eso significa que:

- el mensaje visible no fluctua mientras una persona esta decidiendo
- el snapshot persistido y el claim deben coincidir siempre

## 7. Que no forma parte del runtime activo

No forman parte del runtime metodologico vigente:

- un diseno antiguo de dos brazos de norma baja/alta
- etiquetas antiguas de seeds discretas
- una norma social recalculada con claims previos
- ventanas sociales dinamicas como requisito operativo

Si existen tablas o campos heredados para compatibilidad, no deben interpretarse como parte causal del diseno actual.

## 8. Incentivos

La seleccion para pago se resuelve en backend.

La tasa configurada actual es `1/100`, y el importe depende del numero reportado si la sesion resulta elegible.

## 9. Telemetria minima

La telemetria cientificamente retenida se reduce a:

- `session_start`
- `first_throw`
- `reroll_count`
- `reported_value`
- `reaction_time`
- `session_end`

## 10. Interpretacion

El contraste principal del sistema vigente es un gradiente de norma descriptiva fija entre `norm_0` y `norm_60`, con `control` como referencia sin norma visible.
