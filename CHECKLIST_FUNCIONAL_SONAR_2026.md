# Checklist Funcional Sonar 2026

Documento maestro de comprobacion para backend, frontend, QA, datos y operacion.

Leyenda:
- `IMPLEMENTADO`: existe en codigo y persistencia.
- `AUTO`: comprobado por validacion automatica en esta iteracion.
- `MANUAL`: requiere prueba humana local o en entorno del festival.
- `PENDIENTE`: aun no esta cerrado para produccion.

## A. Identidad y sesion
- `IMPLEMENTADO` `AUTO` Validacion del ID de pulsera en backend.
- `IMPLEMENTADO` `AUTO` Una pulsera no puede crear multiples sesiones activas.
- `IMPLEMENTADO` `AUTO` La reentrada lleva al estado previo persistido.
- `IMPLEMENTADO` `AUTO` Si ya termino, solo vuelve a la pantalla final.
- `IMPLEMENTADO` `AUTO` Si recarga, la sesion se rehidrata desde backend.
- `IMPLEMENTADO` `AUTO` No se pierde el tratamiento asignado.
- `IMPLEMENTADO` `AUTO` No se pierde el resultado real asignado.
- `IMPLEMENTADO` `AUTO` No se pierde la elegibilidad de pago.

## B. Asignacion experimental
- `IMPLEMENTADO` `AUTO` Usuario asignado a una unica condicion.
- `IMPLEMENTADO` `AUTO` Condicion persistente e inmutable.
- `IMPLEMENTADO` `AUTO` Asignacion a una serie concreta.
- `IMPLEMENTADO` `AUTO` Posicion dentro de serie definida e inmutable.
- `IMPLEMENTADO` `AUTO` Sincronizacion correcta con series espejo por `root + position_index`.
- `IMPLEMENTADO` `AUTO` `control` sin norma social.
- `IMPLEMENTADO` `AUTO` `seed_low` mostrando norma adecuada.
- `IMPLEMENTADO` `AUTO` `seed_high` mostrando norma adecuada.

## C. Mazo balanceado
- `IMPLEMENTADO` `AUTO` Existe una raiz comun.
- `IMPLEMENTADO` `AUTO` La secuencia por posicion es compartida entre series espejo.
- `IMPLEMENTADO` `AUTO` El primer resultado real coincide entre posiciones equivalentes.
- `IMPLEMENTADO` `AUTO` La secuencia de rerolls es consistente por posicion.
- `IMPLEMENTADO` `AUTO` La distribucion esta balanceada por bloques de 24.
- `IMPLEMENTADO` `MANUAL` No hay desviaciones estructurales no deseadas en muestra larga.
- `IMPLEMENTADO` `AUTO` El sistema no usa RNG cliente para resultados criticos.

## D. Flujo del usuario
- `IMPLEMENTADO` `MANUAL` Landing clara.
- `IMPLEMENTADO` `AUTO` Consentimiento obligatorio.
- `IMPLEMENTADO` `MANUAL` Instrucciones visibles.
- `IMPLEMENTADO` `MANUAL` Pregunta de comprension minima.
- `IMPLEMENTADO` `MANUAL` Acceso al dado o mazo.
- `IMPLEMENTADO` `AUTO` Primer lanzamiento correcto.
- `IMPLEMENTADO` `AUTO` Rerolls opcionales registrados.
- `IMPLEMENTADO` `AUTO` Paso al reporte.
- `IMPLEMENTADO` `AUTO` Banner mostrado en el momento correcto.
- `IMPLEMENTADO` `AUTO` Claim guardado una sola vez.
- `IMPLEMENTADO` `AUTO` Pantalla final coherente con estado y pago.

## E. Tratamiento social
- `IMPLEMENTADO` `AUTO` `control`: no se muestra norma.
- `IMPLEMENTADO` `AUTO` `seed_low`: mensaje correcto.
- `IMPLEMENTADO` `AUTO` `seed_high`: mensaje correcto.
- `IMPLEMENTADO` `AUTO` Texto consistente con el dato mostrado.
- `IMPLEMENTADO` `AUTO` Tratamiento aparece solo justo antes del claim.
- `IMPLEMENTADO` `AUTO` El valor mostrado corresponde al estado previo a insertar el claim actual.
- `IMPLEMENTADO` `AUTO` Nunca se muestra un tratamiento de otra serie.

## F. Actualizacion de ventana social
- `IMPLEMENTADO` `AUTO` Ventana inicial cargada correctamente.
- `IMPLEMENTADO` `AUTO` Tamano 100 constante.
- `IMPLEMENTADO` `AUTO` Expulsion correcta segun regla definida.
- `IMPLEMENTADO` `AUTO` Insercion del nuevo claim correcta.
- `IMPLEMENTADO` `AUTO` Recalculo del numero de 6 correcto.
- `IMPLEMENTADO` `AUTO` Persistencia del historial de entradas y salidas.
- `IMPLEMENTADO` `AUTO` Actualizacion atomica bajo lock de experimento.
- `IMPLEMENTADO` `MANUAL` Sin corrupcion por concurrencia bajo carga real.

## G. Claim y honestidad
- `IMPLEMENTADO` `AUTO` El backend conserva el resultado real.
- `IMPLEMENTADO` `AUTO` El usuario puede declarar libremente 1-6.
- `IMPLEMENTADO` `AUTO` El claim no altera el resultado real.
- `IMPLEMENTADO` `AUTO` Se calcula si mintio.
- `IMPLEMENTADO` `AUTO` Se calcula magnitud de desviacion.
- `IMPLEMENTADO` `AUTO` Se registra si el claim coincide con primera tirada.
- `IMPLEMENTADO` `AUTO` Se registra si coincide con rerolls posteriores.
- `IMPLEMENTADO` `AUTO` Se generan variables derivadas utiles.

## H. Pago
- `IMPLEMENTADO` `AUTO` La elegibilidad de pago esta fijada desde servidor.
- `IMPLEMENTADO` `AUTO` El usuario no puede regenerarla.
- `IMPLEMENTADO` `AUTO` El resultado final usa la regla correcta.
- `IMPLEMENTADO` `AUTO` La pantalla final es coherente con claim y elegibilidad.
- `IMPLEMENTADO` `AUTO` El pago queda auditado en base de datos.
- `IMPLEMENTADO` `AUTO` No hay dobles pagos logicos.

## I. Telemetria
- `IMPLEMENTADO` `MANUAL` Tiempo de entrada por pantalla.
- `IMPLEMENTADO` `MANUAL` Tiempo de salida.
- `IMPLEMENTADO` `MANUAL` Duracion total.
- `IMPLEMENTADO` `MANUAL` Duracion visible efectiva.
- `IMPLEMENTADO` `MANUAL` Foco y blur.
- `IMPLEMENTADO` `MANUAL` `visibilitychange`.
- `IMPLEMENTADO` `MANUAL` Clicks relevantes.
- `IMPLEMENTADO` `AUTO` Eventos de reroll.
- `IMPLEMENTADO` `AUTO` Tiempo desde banner a claim.
- `IMPLEMENTADO` `AUTO` Tiempo desde mostrar resultado a continuar.
- `IMPLEMENTADO` `AUTO` Errores JS o de red relevantes.

## J. Calidad de datos
- `IMPLEMENTADO` `AUTO` Generacion de flags de inatencion.
- `IMPLEMENTADO` `AUTO` Flags de tiempos imposibles o demasiado rapidos.
- `IMPLEMENTADO` `AUTO` Flags de recargas anomalas.
- `IMPLEMENTADO` `AUTO` Flags de sesiones incompletas o snapshots ausentes.
- `IMPLEMENTADO` `AUTO` Flags de errores de red.
- `IMPLEMENTADO` `AUTO` Flags de navegacion extrana.
- `IMPLEMENTADO` `PENDIENTE` Construccion de `quality_score` agregado.
- `IMPLEMENTADO` `AUTO` No exclusion destructiva en vivo.

## K. Antifraude
- `IMPLEMENTADO` `AUTO` Bloqueo de multiples sesiones por pulsera.
- `IMPLEMENTADO` `AUTO` Deteccion de reintentos.
- `IMPLEMENTADO` `AUTO` Persistencia de `session_id`.
- `IMPLEMENTADO` `AUTO` Hash de IP.
- `IMPLEMENTADO` `AUTO` `user_agent` registrado como hash.
- `IMPLEMENTADO` `AUTO` Eventos repetidos anomalos detectados.
- `IMPLEMENTADO` `AUTO` Payloads invalidos rechazados.
- `IMPLEMENTADO` `AUTO` Estados imposibles rechazados.
- `IMPLEMENTADO` `AUTO` Replay de claim rechazado por idempotencia.

## L. UX movil
- `IMPLEMENTADO` `MANUAL` Carga rapida.
- `IMPLEMENTADO` `MANUAL` Botones grandes.
- `IMPLEMENTADO` `MANUAL` Contraste alto.
- `IMPLEMENTADO` `MANUAL` Una sola accion principal por pantalla.
- `IMPLEMENTADO` `MANUAL` Textos cortos.
- `IMPLEMENTADO` `MANUAL` No saturacion visual.
- `IMPLEMENTADO` `MANUAL` Navegacion simple.
- `IMPLEMENTADO` `MANUAL` Mensajes de error entendibles.
- `IMPLEMENTADO` `MANUAL` Recuperacion suave ante fallo de red.
- `IMPLEMENTADO` `MANUAL` Sin scroll innecesario en el camino critico.

## M. Robustez operativa
- `IMPLEMENTADO` `MANUAL` Backend aguanta concurrencia esperada.
- `IMPLEMENTADO` `MANUAL` Frontend no rompe sesion con red mala.
- `IMPLEMENTADO` `AUTO` Recarga segura.
- `IMPLEMENTADO` `AUTO` Estados consistentes.
- `IMPLEMENTADO` `AUTO` Series no se mezclan.
- `IMPLEMENTADO` `MANUAL` Reinicio de servidor no destruye integridad en entorno persistente real.
- `IMPLEMENTADO` `AUTO` Logs suficientes para reconstruccion.
- `PENDIENTE` `PENDIENTE` Dashboard capaz de detectar anomalias.

## Checklist de aceptacion final

### Funcional
- `AUTO` Se puede iniciar sesion con pulsera valida.
- `AUTO` No se puede duplicar una sesion activa.
- `AUTO` El usuario siempre cae en el estado correcto al reentrar.
- `AUTO` El tratamiento queda fijado y no cambia.
- `AUTO` El control no muestra norma.
- `AUTO` `seed_low` muestra el tratamiento correcto.
- `AUTO` `seed_high` muestra el tratamiento correcto.
- `AUTO` El primer resultado viene del servidor.
- `AUTO` Los rerolls se registran correctamente.
- `AUTO` El claim solo puede enviarse una vez.
- `AUTO` La pantalla final coincide con el estado real.
- `AUTO` El pago queda registrado correctamente.

### Experimental
- `AUTO` La unidad de comparacion por posicion es consistente.
- `AUTO` Las series espejo comparten secuencia base.
- `AUTO` La ventana de 100 funciona correctamente.
- `AUTO` El dato social mostrado es el previo al claim actual.
- `AUTO` El control puro existe de verdad.
- `MANUAL` La pregunta de comprension funciona en experiencia real.
- `AUTO` Los outcomes analiticos pueden reconstruirse integramente.

### Datos
- `AUTO` Existen timestamps suficientes.
- `AUTO` Existen logs de pantalla.
- `AUTO` Existen logs de clicks y rerolls.
- `AUTO` Existen flags de calidad.
- `AUTO` Existen flags de fraude.
- `AUTO` Se puede reconstruir toda la sesion.
- `AUTO` Se puede reconstruir toda la trayectoria de serie.

### Tecnico
- `AUTO` Las transacciones criticas son atomicas a nivel de flujo local con lock e idempotencia.
- `AUTO` Las restricciones de base de datos evitan duplicados peligrosos.
- `AUTO` Los endpoints validan estados.
- `AUTO` El frontend no inventa logica critica.
- `AUTO` La sesion resiste reload.
- `MANUAL` La app sigue siendo usable con mala red en navegador real.
- `AUTO` Se capturan errores tecnicos relevantes.

### UX
- `MANUAL` El flujo se entiende en menos de un minuto.
- `MANUAL` Los textos son claros y breves.
- `MANUAL` Los botones son visibles.
- `AUTO` El tratamiento se ve en el momento correcto.
- `MANUAL` El reporte es rapido de hacer.
- `MANUAL` Los errores son comprensibles.
- `MANUAL` La pantalla final da cierre claro.

## Comandos minimos de verificacion

### Backend
```powershell
cd "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\api-sonar-main\api-sonar-main"
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\Activate.ps1"
python migrate.py
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
```powershell
cd "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\sorteo-sonar-main"
$env:Path += ";C:\Program Files\nodejs"
npx pnpm@latest install
npx pnpm@latest dev
```

### Pulseras demo recomendadas
- `10000001` -> `control`
- `10000002` -> `seed_low`
- `10000003` -> `seed_high`

### Endpoints de inspeccion
- `http://127.0.0.1:8000/admin/roots`
- `http://127.0.0.1:8000/admin/session/10000001`
- `http://127.0.0.1:8000/admin/session/10000002`
- `http://127.0.0.1:8000/admin/session/10000003`
