# Microdecisions

Wiki breve de microdecisiones de producto, metodologia y operacion que han ido dando forma a la app.

Actualizado: `2026-03-22`

## 1. Una sola accion principal por pantalla

Decision:

- cada pantalla empuja una sola accion clara.

Por que:

- reduce friccion,
- favorece uso rapido en movil,
- hace mas facil interpretar abandonos o errores.

## 2. Repetir en varias pantallas que solo cuenta la primera tirada

Decision:

- instrucciones, comprension, dado y decision repiten la misma regla central.

Por que:

- el experimento pierde validez si el participante confunde “primera” con “ultima” o “mas alta”,
- la consistencia entre pantallas importa tanto como la literalidad del texto.

## 3. Pregunta de comprension con autoadvance al acertar

Decision:

- si acierta, avanza sin boton extra.

Por que:

- la pantalla es un chequeo, no una tarea adicional,
- reduce friccion y deja clara la logica de la instruccion.

## 4. Tiradas extra permitidas, pero desacopladas de la tirada que cuenta

Decision:

- se permite “probar el dado”, pero el sistema sigue guardando la primera tirada como la relevante.

Por que:

- mejora credibilidad del sistema,
- permite a la persona comprobar que no hay truco tecnico,
- mantiene la variable clave intacta.

## 5. Snapshot visible congelado al llegar a la decision

Decision:

- el mensaje social que ve una persona no cambia aunque otra reporte mientras tanto.

Por que:

- evita un objetivo movil,
- hace auditable lo que realmente vio cada participante,
- reduce problemas de concurrencia en interpretacion.

## 6. Demo codes solo en frontend

Decision:

- los codigos demo no generan sesion real en backend.

Por que:

- permiten revisar pantallas libremente,
- no contaminan series ni exports reales,
- aceleran la revision con coautores.

## 7. El mensaje social es descriptivo, no moralizante

Decision:

- el tratamiento usa “X de cada Y eligieron 6” y no un mensaje injuntivo.

Por que:

- interesa manipular percepcion descriptiva,
- no decir a la persona lo que “deberia” hacer.

## 8. Pantalla de fichas equilibradas antes del final

Decision:

- se anadio una pantalla de seleccion visual equilibrada antes de la resolucion final.

Por que:

- reduce la sensacion de arbitrariedad o “truco” visual,
- ofrece una capa final mas creible y elegante,
- no altera la logica real de elegibilidad.

## 9. Payment code de solo lectura

Decision:

- el codigo de cobro se muestra ya escrito y no se edita.

Por que:

- reduce errores de transcripcion,
- comunica mayor seriedad,
- separa la verificacion del codigo del resto de decisiones.

## 10. Bizum y donacion como acciones distintas

Decision:

- Bizum requiere telefono y autorizacion,
- donacion a ONG puede hacerse sin ambos.

Por que:

- para donacion no hace falta recoger datos personales de pago del participante,
- el flujo debe ser mas corto si no hay transferencia a un telefono.

## 11. QR, WhatsApp y notas operativas trazados desde el principio

Decision:

- la procedencia de entrada y el contexto de campo se guardan como datos.

Por que:

- en un evento real importa saber desde donde entra la gente,
- tambien importa poder anotar cambios contextuales sin perderlos.

## 12. Estetica editorial sobria en lugar de “formulario web”

Decision:

- visual limpia, institucional y mobile-first.

Por que:

- el tono afecta la confianza del participante,
- la app debia sentirse seria y publicable, no como landing generica.

## 13. Caveats que no conviene esconder

Hay tres microdecisiones abiertas o parcialmente abiertas:

- payout esperado `1/100`, pero no capado exactamente,
- payout y experimento comparten hoy infraestructura SQL,
- fallback a Qualtrics no es automatico.

Documentarlas es parte de la calidad del proyecto, no una debilidad.

