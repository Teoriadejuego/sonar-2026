# Cambio de validacion de pulseras a ultima hora

Guia rapida para cambiar la validacion de pulseras si el formato cambia en el ultimo momento antes de abrir el experimento.

Actualizado: `2026-05-05`

## 1. Como funciona hoy

La validacion actual de pulseras tiene dos capas:

- `app/backend/project_parameters.json`
  - define el patron de formato en `experiment.bracelet_pattern`
- `app/backend/experiment.py`
  - aplica la normalizacion real en `normalize_bracelet_id()`

Punto importante:

- hoy el sistema **no necesita precargar todas las pulseras reales**
- si una pulsera pasa la validacion de formato, el backend crea su registro automaticamente al entrar

Eso ocurre en:

- `app/backend/main.py`
  - dentro de `POST /v1/session/access`
  - si la pulsera no existe, se crea automaticamente

## 2. Caso mas comun: solo cambia el formato

Ejemplo:

- antes: `AB12CD34`
- nuevo formato: `12345678`
- o `SONAR-000123`

### Paso 1. Cambia el patron

Edita:

- `app/backend/project_parameters.json`

Campo:

```json
"bracelet_pattern": "^(?=(?:.*[A-Z]){4})(?=(?:.*\\d){4})[A-Z0-9]{8}$"
```

Sustituyelo por el nuevo regex.

### Ejemplos utiles

Solo 8 numeros:

```json
"bracelet_pattern": "^\\d{8}$"
```

Prefijo `SONAR-` y 6 numeros:

```json
"bracelet_pattern": "^SONAR-\\d{6}$"
```

3 letras seguidas de 5 numeros:

```json
"bracelet_pattern": "^[A-Z]{3}\\d{5}$"
```

## 3. Caso dos: cambia tambien la forma de limpiar el codigo

Si las pulseras nuevas vienen con:

- espacios
- guiones
- prefijos impresos
- minusculas
- separadores raros

entonces no basta con cambiar el regex. Tambien hay que tocar:

- `app/backend/experiment.py`

Funcion:

```python
def normalize_bracelet_id(raw_id: str) -> str:
    normalized = raw_id.strip().upper()
    if not BRACELET_PATTERN.fullmatch(normalized):
        raise ValueError(
            "El formato de pulsera no es valido. Usa 8 caracteres con 4 letras y 4 numeros."
        )
    return normalized
```

### Ejemplos de cambios tipicos

Quitar guiones:

```python
normalized = raw_id.strip().upper().replace("-", "")
```

Quitar espacios internos:

```python
normalized = raw_id.strip().upper().replace(" ", "")
```

Quitar un prefijo fijo:

```python
normalized = raw_id.strip().upper().removeprefix("SONAR-")
```

Consejo operativo:

- si cambias la logica de normalizacion, cambia tambien el mensaje de error para que el staff sepa que formato pedir

## 4. Donde se usa esa validacion

La misma validacion de pulsera se usa en dos momentos clave:

- entrada al experimento
  - `app/backend/main.py`
  - endpoint `POST /v1/session/access`
- cobro del premio
  - `app/backend/main.py`
  - endpoint `POST /v1/payment/submit`

Eso significa que, si cambia el formato, hay que actualizar la validacion **antes** de abrir al publico para que:

- la gente pueda entrar
- y el cobro siga reconociendo la misma pulsera

## 5. Hay que cargar todas las pulseras nuevas?

Con la logica actual, no.

Mientras el codigo:

- cumpla el patron,
- pase `normalize_bracelet_id()`,
- y no este ya en una sesion incompatible,

el backend crea la pulsera automaticamente al acceder.

No hace falta importar una lista completa salvo que querais cambiar el sistema a una validacion por lista cerrada.

## 6. Como recargar todo segun el entorno

## Local con backend manual

Si ejecutas:

```powershell
cd app\backend
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

haz esto:

1. guarda los cambios
2. para estar seguros, para el backend
3. vuelve a lanzarlo

Aunque `--reload` ayuda, cuando se toca `project_parameters.json` lo mas seguro es reiniciar el backend manualmente.

## Local con Docker Compose

Desde la raiz del repo:

```powershell
docker compose --env-file .env.local up --build api app
```

Si ya estaba levantado:

```powershell
docker compose restart api
docker compose restart app
```

Si cambias solo validacion de pulsera:

- reinicia `api`

Si cambias tambien textos del frontend:

- reinicia `app`

## Railway / produccion

### Si solo cambia la validacion backend

Haz deploy del servicio:

- `api`

### Si tambien cambias copy visible en la app

Haz deploy de:

- `api`
- `app`

## 7. Checklist minimo antes de abrir

Prueba estas cuatro cosas:

1. una pulsera valida nueva entra correctamente
2. una pulsera invalida da error claro
3. una pulsera valida puede llegar hasta la pantalla de instrucciones
4. si hay premio, el cobro acepta la misma pulsera

## 8. Mensaje de error que conviene revisar

Si cambias el formato, revisa tambien este texto en:

- `app/backend/experiment.py`

Texto actual:

```python
"El formato de pulsera no es valido. Usa 8 caracteres con 4 letras y 4 numeros."
```

Ese mensaje debe describir el nuevo formato real para evitar errores del staff y de los participantes.

## 9. Si alguna vez quereis pasar a lista cerrada

Hoy el sistema valida por formato y crea la pulsera al entrar.

Si quereis pasar a un sistema mas estricto, por ejemplo:

- solo aceptar una lista exacta de pulseras emitidas
- bloquear rangos o lotes concretos
- mapear pulseras a zonas o puertas

entonces ya no basta con cambiar el regex. Habria que añadir una comprobacion extra en backend antes de crear la pulsera.

Para el operativo actual, el cambio mas rapido y seguro es:

1. actualizar `bracelet_pattern`
2. ajustar `normalize_bracelet_id()` si hace falta
3. reiniciar `api`
4. probar una pulsera valida y una invalida
