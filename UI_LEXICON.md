# UI Lexicon

Fuente de verdad:
- [uiLexicon.ts](/C:/Users/Usuario/Desktop/AAC/codex/2026%20SONAR/sorteo-sonar-main/app/utils/uiLexicon.ts)

Idiomas activos:
- `es`
- `ca`
- `en`
- `fr`
- `pt`

## Estructura actual
- `common`
- `languageEntry`
- `landing`
- `infoModal`
- `instructions`
- `comprehension`
- `game`
- `report`
- `treatment`
- `winner`
- `loser`
- `paused`
- `paymentPage`
- `accessibility`
- `serverErrors`

## Base espanola actual

### `languageEntry`
- `title`: `SONAR 2026`
- `subtitle`: `Selecciona idioma`

### `landing`
- `eyebrow`: `Sorteo expres`
- `title`: `Participa en 1 minuto`
- `subtitle`: `y gana hasta 60 €`
- `intro`: `Actividad de investigacion universitaria / Voluntaria · Menos de 90 segundos · +18`
- `braceletLabel`: `ID de pulsera`
- `braceletPlaceholder`: `Ej: 10000001`
- `moreInfoButton`: `Mas informacion`
- `ageCheckbox`: `Tengo 18 anos o mas`
- `participationCheckbox`: `Acepto participar`
- `dataCheckbox`: `Acepto el tratamiento de datos`
- `cta`: `Comenzar`

### `infoModal.sections`
- `Actividad` -> `Actividad sobre decisiones individuales`
- `Uso` -> `Uso cientifico de resultados`
- `Tarea` -> `Veras una tirada privada / y elegiras un numero`
- `Datos` -> `Datos agregados / Sin publicacion de identidades`
- `Salida` -> `Puedes salir antes de enviar`
- `Contacto` -> `lbl@uloyola.es`

### `instructions`
- `title`: `Como funciona`
- `intro`: `Veras una tirada privada`
- `body`: `Puedes comprobar el sistema`
- `odds`: `1 de cada 100 recibe pago`
- `cta`: `Continuar`

### `comprehension`
- `eyebrow`: `Antes de seguir`
- `title`: `Que numero cuenta?`
- `options`: `Primera tirada`, `Ultima tirada`, `Mas alta`
- `cta`: `Seguir`

### `game`
- `title`: `Tirada`
- `firstResultTemplate`: `Tu primera tirada: {value}`
- `firstRollCta`: `Lanzar`
- `rerollCta`: `Ver otra tirada`
- `continueCta`: `Continuar`
- `attemptsTemplate`: `Tiradas registradas: {count}/{max}`

### `report`
- `title`: `Indica tu numero`
- `body`: `Selecciona tu primera tirada`

### `treatment`
- `controlTitle`: `Tu respuesta es anonima`
- `controlBody`: `Selecciona tu numero`
- `socialHeadlineTemplate`: `{count} de cada {denominator} personas`
- `socialBodyTemplate`: `eligieron {target}`

### `winner`
- `eyebrow`: `Has sido seleccionado`
- `title`: `Premio confirmado`
- `amountLabel`: `Premio`
- `codeLabelTemplate`: `Codigo: {code}`
- `cta`: `Cobrar premio`

### `loser`
- `eyebrow`: `Gracias por participar`
- `title`: `Aun puedes ganar`
- `body`: `Participas en el sorteo / de 2 entradas VIP`
- `bodySecondary`: `Invita a otras personas / para aumentar tus opciones`
- `bodyFooter`: `El resultado se publicara al finalizar`
- `shareLabel`: `Invitar por WhatsApp`

### `paused`
- `eyebrow`: `Gracias`
- `title`: `Todos los premios ya han sido repartidos`
- `body`: `La actividad esta cerrada por ahora`
- `bodySecondary`: `Si quieres recibir avisos, deja tu email`
- `cta`: `Avisarme`

### `paymentPage`
- `eyebrow`: `Cobro`
- `title`: `Introduce tu codigo / y tu telefono`
- `codeLabel`: `Codigo`
- `phoneLabel`: `Telefono`
- `messageLabel`: `Mensaje (opcional)`
- `donationHint`: `Puedes escribir ONG para donar`
- `lookupLabel`: `Validar codigo`
- `submitLabel`: `Enviar`

## Reglas tecnicas
- Todo texto visible debe salir de `UI_LEXICON`.
- El selector de idioma usa `common.languageNames` y `common.welcomeWords`.
- El sistema valida cobertura de claves con `validateLexiconCoverage()`.
- `LanguageContext` persiste idioma en `localStorage`.
- La sesion guarda `language_at_access`, `language_at_claim` y `language_changed_during_session`.
