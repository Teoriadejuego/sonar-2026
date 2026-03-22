# Paper Structure

Preestructura de paper para convertir SONAR en manuscrito academico.

Actualizado: `2026-03-22`

## 1. Titulos posibles

- `Descriptive Norms and Honest Reporting in a Mobile-First Field Experiment`
- `What Others Reported: Social Information and Dishonesty in a Cultural Event`
- `Private Randomness, Public Norms: A Mobile Field Experiment on Reporting Behavior`

## 2. Abstract en bruto

Plantilla:

1. contexto:
   - muchas decisiones privadas dependen de normas descriptivas y honestidad intrinseca;
2. diseno:
   - experimento mobile-first en contexto cultural real con tarea de dado y mensajes sociales;
3. variacion:
   - tratamiento control frente a normas descriptivas bajas y altas;
4. medida:
   - discrepancia entre primera tirada real y numero reportado;
5. resultados:
   - placeholder para patron principal;
6. contribucion:
   - evidencia sobre honestidad y normas en un entorno de alta friccion y alta rotacion.

## 3. Introduccion

### 3.1 Motivacion

- honestidad en contextos de informacion privada,
- influencia de normas descriptivas,
- interes de medir esto fuera del laboratorio tradicional.

### 3.2 Hueco que cubre SONAR

- app breve,
- contexto de evento real,
- trazabilidad digital,
- mezcla de validez ecologica y control operativo.

### 3.3 Contribucion

- diseño experimental desplegable,
- manipulacion descriptiva integrada en flujo mobile-first,
- datos de telemetria y contexto de entrada.

## 4. Marco teorico e hipotesis

### Hipotesis sugeridas

- H1: mensajes descriptivos altos sobre el `6` aumentan la probabilidad de reportar `6`.
- H2: el efecto es mayor frente a control que frente a mensajes descriptivos bajos.
- H3: la claridad metodologica sobre “primera tirada” reduce errores de comprension y ruido de medida.

## 5. Diseño experimental

Subsecciones recomendadas:

- contexto y reclutamiento,
- unidad de observacion,
- secuencia de pantallas,
- tratamientos,
- regla de pago,
- gestion de sesiones,
- exclusion de demos y testing,
- tracking QR e invitaciones.

## 6. Variables

### Dependientes

- `reported_value`
- `is_honest`
- `reported_six`
- `payment_eligible`

### Independientes

- tratamiento
- mensaje visible congelado
- QR de entrada
- referral source
- idioma

### Controles

- tiempos,
- numero de tiradas,
- comprension,
- notas operativas.

## 7. Estrategia empirica

### Analisis descriptivo

- distribucion de reportes por tratamiento,
- comparacion con distribucion uniforme esperada,
- honestidad agregada.

### Analisis inferencial

- regresiones logit / LPM sobre `reported_six`,
- robustez con controles de idioma, QR y comprension,
- analisis por fase si se activa fase 2.

## 8. Amenazas a la validez

- aprendizaje entre participantes,
- difusion de informacion en recinto,
- efecto de copy y diseño,
- posible seleccion por canal de entrada,
- tasa de payout probabilistica y no exacta.

## 9. Resultados y figuras sugeridas

### Figuras

- distribucion de reportes por tratamiento,
- evolucion de la ventana social,
- funnel por pantallas,
- origen de entrada QR / WhatsApp.

### Tablas

- balance por tratamiento,
- efectos principales,
- robustez,
- exclusion y calidad.

## 10. Seccion de etica y datos

Incluir:

- consentimiento,
- minimizacion de datos,
- trazabilidad operativa,
- limitaciones actuales de separacion de datos de payout.

## 11. Apéndices

- pantallas y copy,
- versionado del experimento,
- parametros activos,
- detalle tecnico de concurrencia,
- codebook de variables,
- plan de contingencia.

