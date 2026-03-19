# codigo/

Esta carpeta contiene el pipeline analitico reproducible del paper SONAR antes de recoger datos reales.

## Contenido
- `data/simulated/`: datos simulados coherentes con el diseno principal.
- `src/`: simulacion, construccion del dataset analitico, analisis y figuras.
- `outputs/tables/`: tablas listas para revisar.
- `outputs/figures/`: figuras de alto nivel del paper.
- `outputs/logs/`: logs de ejecucion.
- `docs/`: plan de analisis preregistrado, codebook y plan de figuras.

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

## Generar figuras
```powershell
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/figures_main.py
& "C:\Users\Usuario\Desktop\AAC\codex\2026 SONAR\.venv\Scripts\python.exe" src/figures_exploratory.py
```

## Outputs
- Dataset analitico: `data/simulated/sonar_analysis_dataset_simulated.csv`
- Tablas: `outputs/tables/`
- Figuras: `outputs/figures/`
- Logs: `outputs/logs/`

## Sustituir datos simulados por datos reales
1. Exporta desde SONAR los datasets `sessions`, `throws`, `referrals`, `series_state` y `position_plan`.
2. Copia esos ficheros a `data/simulated/` o adapta las rutas en `src/build_analysis_dataset.py`.
3. Mantiene los nombres de columnas clave del export real para que el pipeline siga funcionando sin rehacer modelos ni figuras.
4. Reejecuta `build_analysis_dataset.py`, `analysis_main.py`, `analysis_exploratory.py`, `figures_main.py` y `figures_exploratory.py`.
