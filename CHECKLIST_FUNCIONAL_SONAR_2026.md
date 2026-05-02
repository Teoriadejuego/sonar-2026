# Checklist Funcional SONAR 2026

Este checklist queda realineado con el diseno experimental vigente.

## Diseno canonico a validar

- `control`
- `norm_0..norm_60`
- denominador `60`
- norma fija por tratamiento
- snapshot congelado antes del claim

## Comprobaciones clave

- `control` no muestra norma social
- `norm_X` muestra el conteo correcto `X/60`
- `prepare-report` congela el mensaje visible
- `submit-report` reutiliza el mismo snapshot
- el frontend no inventa la norma social
- la norma social es fija por tratamiento y no depende de claims previos
