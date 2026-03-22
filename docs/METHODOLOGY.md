# Methodology

Resumen metodologico de SONAR 2026.

Actualizado: `2026-03-22`

## 1. Pregunta de investigacion

SONAR 2026 estudia como cambia el comportamiento de reporte en una tarea de honestidad privada cuando se introduce informacion social descriptiva sobre lo que han hecho participantes anteriores.

La variable social no se presenta como norma moral. Se presenta como norma descriptiva visible.

## 2. Unidad de participacion

Una participacion corresponde a una sesion asociada a una pulsera.

Cada sesion registra:

- identificador de pulsera,
- idioma,
- tratamiento,
- secuencia de pantallas,
- tiradas,
- tiempo de respuesta,
- claim final,
- elegibilidad de pago,
- snapshots visibles,
- telemetria,
- fuente de entrada QR o invitacion.

## 3. Flujo experimental

1. Acceso con pulsera.
2. Consentimiento y checks basicos.
3. Instrucciones.
4. Pregunta de comprension.
5. Tirada privada inicial del dado.
6. Tiradas extra de comprobacion opcionales.
7. Preparacion del reporte con snapshot congelado.
8. Reporte del numero de la primera tirada.
9. Resolucion de ganador/no ganador.
10. Pantallas finales de engagement, pago o cierre.

## 4. Variable clave de comportamiento

La instruccion central es:

- solo cuenta la primera tirada,
- el participante puede ver tiradas extra,
- el backend guarda tanto la primera tirada real como el numero reportado,
- la deshonestidad no se observa individualmente en interfaz, pero puede analizarse estadisticamente y, cuando procede, a nivel de sesion dado que el backend si conoce la primera tirada real.

## 5. Tratamientos

La fase principal actual incluye:

- `control`
- `seed_low`
- `seed_high`

La informacion maestra esta en [../project_parameters.json](../project_parameters.json).

Configuracion de trabajo actual:

- ventana visible: `60`
- longitud de serie: `120`
- objetivo normativo: `6`
- `seed_low`: arranque con `10` objetivos en ventana
- `seed_high`: arranque con `50` objetivos en ventana

El mensaje que ve el participante se genera a partir del estado visible de la ventana, no de una frase fija hardcodeada.

## 6. Snapshot visible y concurrencia

Una decision importante del sistema es que el mensaje visible para cada participante se congela cuando entra en la fase de reporte.

Eso significa:

- si dos personas llegan casi a la vez a la pantalla de decision,
- ambas pueden ver el mismo mensaje social,
- la ventana solo cambia cuando cada una envia su claim.

Esto evita que el contenido visible “salte” mientras alguien esta decidiendo.

## 7. Pagos e incentivos

La seleccion para pago se resuelve en backend.

La tasa configurada hoy es:

- `1 / 100`

Importante:

- es una tasa esperada probabilistica,
- no una cuota exacta blindada a un numero cerrado de ganadores.

Si una sesion es elegible, el importe depende del numero reportado.

## 8. Capas finales de engagement

Despues de la resolucion principal, la app puede mostrar:

- pantalla de revelado visual de fichas,
- pantalla final con sorteo VIP,
- prediccion adicional del numero mas reportado,
- enlace de invitacion por WhatsApp.

Estas capas no cambian la logica experimental principal. Funcionan como extension de engagement y trazabilidad.

## 9. Medidas principales y auxiliares

### Principales

- `reported_value`
- `true_first_result`
- `is_honest`
- `payment_eligible`
- `amount_eur`

### Auxiliares

- tiempos por pantalla,
- numero de tiradas,
- comprension,
- QR de entrada,
- referral source,
- idioma,
- notas operativas activas en ese momento.

## 10. Telemetria y reconstruccion

La app guarda suficiente informacion para reconstruir:

- que vio el participante,
- en que orden,
- con que tratamiento,
- con que idioma,
- con que contexto operativo.

Documentos relacionados:

- [../TELEMETRY_SPEC.md](../TELEMETRY_SPEC.md)
- [../DATA_EXPORTS.md](../DATA_EXPORTS.md)
- [../DATASETS_CODEBOOK.md](../DATASETS_CODEBOOK.md)

## 11. Etica y privacidad

El sistema minimiza datos visibles en frontend y usa la pulsera como identificador operativo.

Puntos honestos a tener en cuenta:

- el sistema esta pensado para analisis agregado y trazabilidad operativa,
- hoy los datos de payout no estan en una base fisicamente separada del resto,
- las decisiones de copy etico deben seguir siendo consistentes con la implementacion real.

## 12. Estado metodologico actual

SONAR ya es util para:

- revision de UX y copy,
- pruebas de flujo,
- pilotos controlados,
- despliegue de review con coautores.

Antes de una recogida final cerrada conviene fijar de manera definitiva:

- ventana,
- longitud de serie,
- politica exacta de payout,
- redaccion etica final,
- plan de contingencia y redirect externo.

