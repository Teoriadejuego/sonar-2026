# Partial Failure Recovery

Estrategia de recuperacion tras fallo parcial del sistema SONAR.

Actualizado: `2026-05-02`

## 1. Objetivo

Recuperar el sistema con estas prioridades:

1. no perder sesiones ya iniciadas,
2. no duplicar acciones criticas,
3. no pedir al participante que empiece de cero si no hace falta,
4. separar recuperacion de participantes en curso y entrada de participantes nuevos.

## 2. Garantias actuales del sistema

### Frontend

El frontend ya conserva:

- `session_id`
- `client_installation_id`
- ultima `session` confirmada
- `pendingAction` para:
  - `roll`
  - `prepare_report`
  - `submit_claim`

Comportamiento actual:

- guarda sesion y accion pendiente en `localStorage`,
- reintenta rapido a `350 ms` y `900 ms`,
- despues reintenta en background cada `5 s`,
- reintenta tambien al volver `online`,
- muestra mensaje corto de reconexion,
- usa la misma `idempotency_key` en la recuperacion.

### Backend

El backend ya protege:

- `roll`
- `prepare-report`
- `submit-report`

con:

- idempotencia persistente,
- receipts,
- transacciones,
- locks de sesion.

### Health

- `/health/live` indica si el proceso API esta vivo.
- `/health/ready` indica si el sistema esta realmente listo, incluyendo dependencias.

Interpretacion operativa:

- `live = 200` y `ready = 503`:
  - la API sigue arrancada,
  - pero no esta lista para operar con seguridad.
- `live = 503 o timeout`:
  - la API esta caida o inaccesible.

## 3. Escenario A: caida de API

### Sintomas

- `health/live` falla o timeout
- `health/ready` falla o timeout
- el frontend no puede completar requests criticas
- los participantes ven `Reconectando...`

### Comportamiento esperado del frontend

- mantener al usuario en la pantalla actual,
- no borrar la sesion local,
- no inventar resultado, snapshot ni claim,
- conservar la accion pendiente,
- reintentar automaticamente en background.

### Comportamiento operativo

#### Participantes ya en curso

- pedir que no cierren la pagina,
- no reiniciar el flujo manualmente,
- no cambiar de pulsera,
- no moverlos a un flujo alternativo mientras haya posibilidad de recuperacion.

#### Participantes nuevos

- parar captacion nueva si el fallo dura mas de unos pocos intentos consecutivos,
- usar dominio backup si el problema es solo del frontend custom domain,
- si el problema es API real, no abrir nuevas sesiones.

### Recuperacion

1. restaurar o redeployar la API,
2. confirmar:
   - `/health/live = 200`
   - `/health/ready = 200`
3. dejar que el frontend reintente solo,
4. si un participante sigue atascado, recargar una vez,
5. comprobar que `resume` devuelve la misma sesion.

### Resultado esperado

- `roll` pendiente se reaplica o se detecta ya aplicada,
- `prepare-report` pendiente se reaplica o se detecta ya aplicado,
- `submit-claim` pendiente se reaplica o se detecta ya aplicado,
- no hay duplicados por `idempotency_key`.

## 4. Escenario B: caida de DB

### Sintomas

- `health/live = 200`
- `health/ready = 503`
- `/admin/live` y `/admin/metrics` muestran backend no listo
- acciones criticas pueden fallar o quedar suspendidas

### Comportamiento esperado del frontend

- igual que en caida de API:
  - mantener pantalla,
  - mostrar reconexion,
  - conservar sesion y accion pendiente,
  - no inventar datos criticos.

### Comportamiento operativo

#### Participantes ya en curso

- mantenerlos en espera corta,
- no reiniciar desde landing,
- no repetir el experimento,
- no pasarlos a payout aunque crean que han terminado si el claim no esta confirmado.

#### Participantes nuevos

- detener captacion inmediatamente,
- no abrir nuevas sesiones mientras `ready` siga rojo.

### Recuperacion

1. restaurar PostgreSQL,
2. esperar a que la API vuelva a `ready = 200`,
3. verificar `admin/metrics`,
4. reanudar solo cuando `ready` sea verde,
5. dejar que las sesiones pendientes se recuperen por `resume` y retry.

### Regla critica

Si la DB cae:

- no redirigir sesiones en curso a un flujo alternativo,
- solo considerar fallback para participantes nuevos,
- registrar externamente la hora de corte si el admin tampoco esta operativo.

## 5. Fallback por severidad

### Nivel 1: fallo corto

Condicion:

- 1 o 2 errores aislados,
- recuperacion en menos de 1 minuto.

Accion:

- mantener participantes en la pagina,
- dejar actuar al retry automatico,
- soporte acompana sin reiniciar.

### Nivel 2: fallo parcial sostenido

Condicion:

- 3 fallos similares en 2 minutos,
- `ready` rojo,
- `live` verde o intermitente.

Accion:

- detener entrada nueva,
- mantener participantes en curso,
- revisar logs y dependencia afectada,
- no cambiar aun a canal alternativo para sesiones abiertas.

### Nivel 3: caida sostenida

Condicion:

- API o DB fuera mas de unos minutos,
- sin perspectiva rapida de recuperacion.

Accion:

- cerrar temporalmente captacion nueva,
- si procede, redirigir solo a nuevos participantes a canal alternativo,
- no mezclar datos de sesiones medias con canal fallback,
- cuando vuelva el sistema, reabrir solo tras `ready = 200`.

## 6. Que no debe hacer el equipo

- no pedir a todos que refresquen a la vez,
- no borrar storage del navegador,
- no usar una pulsera nueva para "probar a ver",
- no reenviar a payout si no hay confirmacion backend,
- no mezclar una sesion rota con un segundo intento manual,
- no mover una sesion iniciada a Qualtrics u otro canal alternativo.

## 7. Drill de simulacion recomendado

### Drill A: API down

1. abrir una sesion hasta `game`,
2. disparar un `roll`,
3. cortar la API,
4. confirmar que la app muestra reconexion y conserva sesion,
5. levantar la API,
6. confirmar que el `roll` se recupera sin duplicarse.

### Drill B: DB down

1. abrir una sesion hasta `report`,
2. lanzar `submit-report`,
3. cortar PostgreSQL o romper la conectividad,
4. confirmar que la app no pierde la sesion,
5. restaurar DB,
6. confirmar que el claim se confirma o se reintenta limpiamente.

## 8. Checklist de recuperacion

- `health/live` verde
- `health/ready` verde
- `/admin/live` accesible
- `/admin/metrics` sin alerta critica de integridad
- participantes en curso recuperan la sesion
- no aparecen claims o rolls duplicados
- solo entonces se reabre captacion nueva

## 9. Regla de oro

Una sesion en curso se recupera.

No se reinventa, no se repite y no se mezcla con un canal alternativo salvo cierre controlado del flujo para participantes nuevos.
