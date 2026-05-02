# codigo/

Pipeline analitico reproducible de SONAR 2026.

## Diseno experimental asumido

Todo el codigo analitico activo debe asumir un unico diseno:

- `control`
- `norm_0..norm_60`
- denominador fijo `60`
- mensaje social fijo por tratamiento

No debe asumir:

- un diseno antiguo de baja/alta norma en dos brazos
- fases antiguas
- una norma social recalculada a partir de claims previos

## Contenido

- `data/simulated/`: datos simulados coherentes con el diseno vigente.
- `src/`: simulacion, construccion del dataset analitico, analisis y figuras.
- `outputs/tables/`: tablas listas para revisar.
- `outputs/figures/`: figuras de alto nivel del paper.
- `outputs/logs/`: logs de ejecucion.
- `docs/`: notas analiticas y documentos historicos o activos.

La configuracion experimental principal se sincroniza con [project_parameters.json](</C:/Users/Usuario/Desktop/AAC/codex/2026 SONAR/project_parameters.json>).

## Instalacion

```powershell
cd "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\codigo"
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```

## Regenerar la simulacion

```powershell
cd "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\codigo"
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/simulate_data.py
```

## Construir dataset analitico

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/build_analysis_dataset.py
```

## Correr analisis

```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/analysis_main.py
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/analysis_exploratory.py
```
