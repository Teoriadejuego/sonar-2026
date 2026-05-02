# CODEBOOK_SIMULATED

Codebook resumido del dataset simulado alineado con el diseno vigente.

## Tratamientos

- `control`
- `norm_0..norm_60`

## Variables clave

- `treatment_key`
- `displayed_count_target`
- `displayed_denominator`
- `norm_target_value`
- `true_first_result`
- `reported_value`
- `is_honest`
- `reroll_count`
- `treatment_display_count`

## Nota metodologica

La simulacion activa no asume una actualizacion dinamica de la norma visible. La norma social es fija por tratamiento y se reconstruye desde `treatment_key` y `displayed_count_target`.
