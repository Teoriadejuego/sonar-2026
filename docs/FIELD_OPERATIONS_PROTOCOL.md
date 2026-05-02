# Field Operations Protocol

Protocolo de campo para reducir errores humanos durante el experimento SONAR.

Actualizado: `2026-05-02`

## 1. Objetivo operativo

Este documento convierte el flujo de la app en un procedimiento simple para staff:

- el participante escanea,
- introduce su pulsera,
- sigue las pantallas,
- el staff solo guia el uso,
- el backend decide todo lo experimental.

Principios:

- no explicar la logica experimental,
- no sugerir respuestas,
- no tocar el telefono del participante salvo incidencia tecnica clara,
- no improvisar si hay fallo repetido: usar fallback.

## 2. Errores humanos mas probables

### QR y carteleria

- QR demasiado pequeno o con reflejos.
- QR apuntando a una URL vieja.
- dos QR distintos en el mismo punto.
- cartel colocado en zona sin cobertura o con cola bloqueando la circulacion.

### Participantes

- no entienden que deben introducir su pulsera, no su telefono.
- creen que tienen que elegir un premio, no reportar el numero que salio.
- no entienden que pueden relanzar, pero que el primer resultado cuenta.
- abandonan porque el staff les explica demasiado y genera dudas.

### Staff

- explica la norma social en voz alta y contamina el tratamiento.
- dice `elige el premio` o `pon el numero que te convenga`.
- usa codigos demo antiguos.
- refresca varias veces o reinicia el flujo sin criterio.
- mezcla captacion, soporte y payout en la misma persona cuando hay cola.

### Operacion

- red inestable.
- una racha corta de errores se interpreta como error aislado cuando ya es incidencia general.
- no queda registro de cuando se cambio QR, fallback o dinamica.

## 3. Roles minimos en campo

### 3.1 Captacion

Responsable de:

- invitar a escanear,
- indicar donde esta el QR correcto,
- dar una explicacion de una sola frase,
- no resolver incidencias tecnicas largas.

Script recomendado:

- `Escanea este QR, introduce tu pulsera y sigue las pantallas. Si algo no carga, te ayudamos aqui.`

### 3.2 Soporte

Responsable de:

- ayudar si no carga,
- comprobar si el problema es QR, red o sesion,
- aplicar el fallback rapido,
- decidir si se para captacion.

Script recomendado:

- `No hace falta empezar de cero. Vamos a recuperar la sesion o a reintentar una vez.`

### 3.3 Payout

Responsable de:

- atender solo a personas que ya hayan terminado el flujo,
- separar claramente experimento y cobro,
- no reenviar al participante al experimento para resolver un problema de pago.

Script recomendado:

- `La parte del experimento ya ha terminado. Ahora solo revisamos tu codigo de cobro.`

### 3.4 Responsable de incidencias

Responsable de:

- mirar healthchecks y panel admin,
- decidir pausa o cambio a fallback,
- registrar nota operativa,
- comunicar al staff una instruccion unica.

## 4. Checklist antes de abrir

1. Verificar que el QR publico abre `https://dice.sonar2026.es`.
2. Verificar backend:
   - `/health/live`
   - `/health/ready`
3. Hacer una prueba completa con un codigo demo vigente:
   - `CTRL1234`
   - `NORM0000`
   - `NORM0001`
4. Verificar que el cartel tiene:
   - un solo QR visible,
   - buen contraste,
   - altura comoda,
   - sin reflejos,
   - espacio para que 2-3 personas escaneen sin bloquear paso.
5. Verificar que el staff conoce la frase corta de invitacion.
6. Verificar que existe un fallback manual:
   - URL corta,
   - dominio Railway de respaldo,
   - persona responsable de cambiar redirect o pausar.
7. Verificar material minimo:
   - 1 telefono de staff,
   - 1 powerbank,
   - 1 hotspot o red alternativa si aplica.

## 5. Instrucciones exactas para staff

### Lo que si debe decirse

- `Escanea este QR.`
- `Introduce tu codigo de pulsera.`
- `Lee la pantalla y pulsa continuar.`
- `Si se corta, no pasa nada: recuperamos la sesion.`
- `En esta pantalla indica que numero salio.`

### Lo que no debe decirse

- `Aqui veras lo que ha dicho otra gente.`
- `Pon el seis.`
- `Elige el premio.`
- `Si ganas, mejor haz esto.`
- `Vuelve atras y prueba otra vez hasta que salga bien.`
- `Usa este codigo demo`, salvo en pruebas internas de staff.

### Regla simple de conducta

- explicar uso, no contenido,
- guiar la pantalla actual, no la decision,
- si hay duda metodologica, derivar al responsable, no improvisar.

## 6. Flujo operativo del participante

### Paso 1. Entrada

Staff dice:

- `Escanea este QR e introduce tu pulsera.`

Objetivo:

- que el participante llegue a la landing correcta,
- que no escriba telefono, nombre ni otro identificador.

### Paso 2. Onboarding

Staff dice:

- `Marca las casillas y sigue las pantallas.`

Objetivo:

- no sobreexplicar,
- no leer en voz alta el contenido experimental,
- dejar que la app haga el onboarding.

### Paso 3. Juego y reporte

Staff dice:

- `Lanza, y cuando llegue el momento indica que numero salio.`

Objetivo:

- reforzar que se reporta un numero,
- no hablar de premio antes del outcome,
- no presionar durante el reroll.

### Paso 4. Salida y pago

Staff dice:

- `Si te aparece la parte de cobro, te ayudamos en esta mesa.`

Objetivo:

- separar el final del experimento del flujo administrativo.

## 7. Fallback rapido

### Caso A. Un solo movil no carga

1. Confirmar que el QR es correcto.
2. Pedir cerrar y reabrir una sola vez.
3. Si sigue igual, usar el dominio backup de la app.
4. Si el problema persiste, pasar a soporte.

No hacer:

- cinco recargas seguidas,
- cambiar de QR sin verificar,
- inventar un codigo.

### Caso B. La app carga pero no deja continuar

1. Soporte comprueba `/health/ready`.
2. Si esta verde, recuperar sesion y reintentar una vez.
3. Si falla otra vez, registrar incidencia y sacar al participante de la cola principal.

### Caso C. Tres fallos similares en dos minutos

Tratarlo como incidencia general:

1. parar captacion nueva en ese punto,
2. revisar admin y healthchecks,
3. comunicar una instruccion unica al staff,
4. si no remite rapido, activar fallback de redirect o pausa.

### Caso D. Fallo de payout

1. no repetir el experimento,
2. separar a la persona de la cola principal,
3. resolverlo desde payout/soporte,
4. registrar la incidencia si afecta a mas de un caso.

## 8. Mensajes UX recomendados

### Cartel QR

Titulo:

- `Escanea, introduce tu pulsera y sigue las pantallas`

Apoyo:

- `Si algo no carga, el staff te ayuda aqui`

### Landing

Refuerzo sugerido:

- `Solo necesitas tu codigo de pulsera`

Error sugerido:

- `Revisa el codigo de pulsera y vuelve a intentarlo`

### Instrucciones

Refuerzo sugerido:

- `Sigue las pantallas. No necesitas decidir nada ahora.`

### Juego

Refuerzo sugerido:

- `Tu primer resultado cuenta. Si quieres, puedes volver a lanzar.`

### Reporte

Refuerzo critico:

- `Indica que numero salio`

Texto a evitar:

- cualquier variante de `elige premio` o `elige opcion`.

### Red inestable

Mensajes recomendados:

- `Reconectando...`
- `Seguimos guardando tu sesion`
- `No cierres la pagina`

## 9. Simplificaciones recomendadas

### Interaccion

- un solo QR por punto fisico,
- una sola frase de invitacion,
- una sola accion principal por pantalla,
- una sola persona resolviendo incidencias tecnicas.

### Onboarding

- no leer la app al participante,
- no anticipar pantallas futuras,
- no explicar la norma social,
- no mencionar payout hasta que aparezca.

### Operacion

- separar captacion y soporte cuando haya cola,
- mover payout fuera de la trayectoria principal,
- registrar cualquier cambio de QR, pausa o fallback en admin.

## 10. Regla de oro

Si el staff tiene que explicar demasiado, el flujo esta mal operado.

La operacion correcta en campo es:

- senal clara,
- frase corta,
- una ayuda tecnica rapida,
- cero improvisacion metodologica.
