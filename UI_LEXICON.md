# UI Lexicon

Fuente de verdad:
- [uiLexicon.ts](/C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/sorteo-sonar-main/app/utils/uiLexicon.ts)

## Idiomas activos
- `es`
- `ca`
- `en`
- `fr`
- `pt`
- `it`

La cobertura se valida con `validateLexiconCoverage()`.

## Estructura principal
- `common`
- `languageEntry`
- `landing`
- `infoModal`
- `instructions`
- `comprehension`
- `game`
- `report`
- `prizeReveal`
- `treatment`
- `bonusDraw`
- `winner`
- `loser`
- `paused`
- `paymentPage`
- `accessibility`
- `errors`
- `serverErrors`

## Regla de internacionalizacion
Todo texto visible debe salir de `UI_LEXICON`.

No se deben hardcodear:
- mensajes de tratamiento
- labels de payout
- textos de sorteo extra
- mensajes de error mostrados al usuario

## Mensaje social del nuevo diseno
No se mantienen 61 mensajes hardcodeados. El banner social usa un template parametrico:

`socialMessageTemplate(count, denominator, target)`

Ejemplo en espanol:
- `En un grupo de {denominator} resultados antes de ti, el numero de personas que reportaron un {target} fue {count}.`

Ejemplo en ingles:
- `In a group of {denominator} results before you, the number of people who reported a {target} was {count}.`

Para `control` no se usa ese template. Se muestra la caja neutra del bloque `treatment`.

## Secciones relevantes del flujo actual

### `landing`
Incluye:
- etiqueta de pulsera
- validaciones de consentimiento
- acceso a modal etico

### `instructions`
Describe:
- que se lanzara un dado y despues se pedira indicar el numero que salio
- que el premio depende del numero reportado
- que 1 de cada 100 recibe el pago

### `game`
Incluye:
- copy neutro sobre la tirada visible
- CTA `Lanzar`
- CTA `Lanzar otra vez`
- CTA `Continuar`
- contador de tiradas registradas

### `report`
Incluye:
- titulo `Indica tu numero`
- instruccion para marcar el numero que salio al lanzar el dado

### `comprehension`
Incluye:
- check breve de atencion
- avance automatico al acertar
- error corto sin boton extra
- telemetria con `attention_check_passed`
- telemetria con `attention_check_attempts`
- telemetria con `attention_check_first_answer`
- telemetria con `attention_check_rt_ms`
- telemetria con `attention_check_completed_at`
- telemetria con `attention_check_passed_first_try`

### `prizeReveal`
Incluye:
- helper para las 100 figuras
- copy de ganador y perdedor

### `bonusDraw`
Incluye:
- papeleta base
- prediccion de numero mas reportado
- incentivo por WhatsApp

### `paymentPage`
Incluye:
- cobro por Bizum
- opcion de donacion
- consentimiento especifico de pago
- modal de privacidad del pago
- pantalla final tras payout

## Elementos tecnicos acoplados al backend
El frontend espera del backend:
- `treatment_key`
- `displayed_count_target`
- `displayed_denominator`
- `norm_target_value`
- `is_control`
- `displayed_message_text` o capacidad de reconstruirlo con `socialMessageTemplate`

## Selector de idioma
- usa `common.languageNames`
- usa `common.welcomeWords`
- persiste idioma en `localStorage`
- la sesion backend guarda `language_at_access`, `language_at_claim` y `language_changed_during_session`

## Mensajes demo utiles
La configuracion publica expone demo IDs y el frontend mantiene fallbacks:
- `CTRL1234`
- `NORM0000`
- `NORM0001`

Su significado es:
- `CTRL1234`: control y ganador
- `NORM0000`: `norm_0` y no ganador
- `NORM0001`: `norm_1` y no ganador

## Mantenimiento
Si se cambia una pantalla o un CTA:
1. actualizar `uiLexicon.ts`
2. mantener coherencia entre idiomas
3. revisar `TEXTOS_PANTALLAS_ES.md` si cambia el flujo visible en espanol
4. ejecutar build frontend y tests estaticos
