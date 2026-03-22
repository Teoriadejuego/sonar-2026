# Coauthor Review Guide

Guia breve para coautores que quieren evaluar la app sin necesidad de leer primero todo el codigo.

Actualizado: `2026-03-22`

## 1. Que mirar primero

- app publica principal: [https://dice.sonar2026.es](https://dice.sonar2026.es)
- app Railway: [https://app-production-4b8d.up.railway.app](https://app-production-4b8d.up.railway.app)

## 2. Codigos recomendados para revisar

- `12341`
  recorrido demo control
- `12342`
  recorrido demo `seed_low`
- `12343`
  recorrido demo `seed_high`
- `1234`
  recorrido demo ganador

## 3. Que tipo de feedback es especialmente util

- claridad del copy,
- coherencia entre pantallas,
- si la instruccion sobre la primera tirada queda clara,
- si el tratamiento social se entiende sin sonar manipulador,
- fricciones de comprension,
- problemas de responsive,
- tono general del experimento,
- dudas eticas o de interpretacion.

## 4. Flujo de pantallas a revisar

1. idioma,
2. consentimiento,
3. instrucciones,
4. comprension,
5. dado,
6. decision,
7. revelado final,
8. ganador o no ganador,
9. cobro o cierre final.

## 5. Preguntas orientativas para la revision

- Se entiende que solo cuenta la primera tirada?
- La pregunta de comprension coincide con las instrucciones?
- El mensaje social parece claro pero no agresivo?
- El final transmite bien lo del sorteo VIP y las invitaciones?
- La pantalla de pago es creible y suficientemente sobria?
- Hay algun punto donde el usuario pueda pensar que el sistema “hace trampa”?

## 6. Que no hace falta revisar como si fuera un bug

- los codigos demo no reflejan la logica estadistica real,
- la tasa de payout exacta no se puede inferir desde una sola sesion,
- algunos parametros de serie y ventana siguen siendo configurables,
- Railway puede tardar unos segundos en reflejar un deploy nuevo.

## 7. Si quieres entrar mas al fondo

Lee despues:

- [METHODOLOGY.md](./METHODOLOGY.md)
- [MICRODECISIONS.md](./MICRODECISIONS.md)
- [PAPER_STRUCTURE.md](./PAPER_STRUCTURE.md)
