# simulation_validation

Validacion sintetica integral de SONAR con dos modos:

- simulacion analitica directa de sujetos validos
- simulacion de flujo contra el backend real usando `access`, `roll`, `prepare-report` y `submit-report`

## Diseno experimental asumido

La simulacion activa solo asume:

- `control`
- `norm_0..norm_60`
- denominador fijo `60`
- mensaje social fijo por tratamiento

## Robots

### Tipo A - Imitador de norma

- en `norm_0` reporta `6` con probabilidad baja
- en `norm_60` reporta `6` con probabilidad alta
- en general, la probabilidad de reportar `6` sigue la intensidad visible del tratamiento asignado
- en control sigue una regla neutra: alta probabilidad de verdad y baja probabilidad base de `6`

### Tipo B - Mixto aleatorio / honesto

- 50% dice la verdad
- 50% reporta un numero uniforme entre `1` y `6`

### Tipo C - Mentiroso prudente 5

- si la verdad es `1` o `2`, reporta `5`
- en cualquier otro caso, reporta la verdad

### Tipo D - Honesto puro

- siempre reporta la verdad

## Configuracion

Archivo:

- `config/robot_simulation_config.json`

La logica experimental se sincroniza con `project_parameters.json`.

## Patrones esperados

- Tipo A reporta mas `6` en `norm_60` que en `norm_0`
- Tipo C produce exceso de `5` cuando la verdad es `1` o `2`
- Tipo D es completamente honesto
- `norm_60` muestra mas `reported_6` que `norm_0`
- las series espejo comparten la misma verdad por posicion
- el backend flow produce sesiones completadas sin corrupcion de estado
