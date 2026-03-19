# simulation_validation

Validación sintética integral de SONAR con dos modos:

- simulación analítica directa de 6000 sujetos válidos
- simulación de flujo contra el backend real usando `access`, `roll`, `prepare-report` y `submit-report`

## Robots

### Tipo A — Imitador de norma

- en `seed_17` reporta `6` con probabilidad `0.17`
- en `seed_83` reporta `6` con probabilidad `0.83`
- si no reporta `6`, reporta la verdad
- en control sigue una regla neutra: alta probabilidad de verdad y baja probabilidad base de `6`

### Tipo B — Mixto aleatorio / honesto

- 50% dice la verdad
- 50% reporta un número uniforme entre `1` y `6`
- el aleatorio sí puede coincidir con el valor verdadero

### Tipo C — Mentiroso prudente 5

- si la verdad es `1` o `2`, reporta `5`
- en cualquier otro caso, reporta la verdad

### Tipo D — Honesto puro

- siempre reporta la verdad

## Configuración

Archivo:

- `config/robot_simulation_config.json`

Parámetros principales:

- tamaño total de muestra
- mezcla de robots
- pesos por tratamiento
- idiomas
- propensión a rerolls
- ruido técnico básico

## Cómo ejecutar

Desde:

```powershell
cd "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\codigo\simulation_validation"
```

### 1. Generar población robótica

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/generate_robot_population.py
```

### 2. Simulación directa de 6000 sujetos

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/run_direct_simulation.py
```

### 3. Simulación del flujo real del backend

Por defecto usa el tamaño configurado para validación rápida del flujo.

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/run_backend_flow_simulation.py
```

Para lanzarla a 6000:

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/run_backend_flow_simulation.py --participants 6000
```

### 4. Validar resultados

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/validate_simulation_outputs.py
```

### 5. Construir tablas

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/build_robot_analysis_tables.py
```

### 6. Generar figuras

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/figures_robot_validation.py
```

## Qué mirar

- `data/simulated_sessions.csv`
- `data/simulated_series.csv`
- `data/simulated_position_plan.csv`
- `data/backend_flow_sessions.csv`
- `outputs/tables/table_4_validation_checks.csv`
- `outputs/figures/`
- `outputs/logs/`

## Qué patrones esperamos observar

- Tipo A reporta más `6` en `seed_83` que en `seed_17`
- Tipo C produce exceso de `5` cuando la verdad es `1` o `2`
- Tipo D es completamente honesto
- `seed_83` muestra más `reported_6` que `seed_17`
- las series espejo comparten la misma verdad por posición
- el backend flow produce sesiones completadas sin corrupción de estado
