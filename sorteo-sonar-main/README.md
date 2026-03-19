## Sorteo Sónar 2026

PWA móvil para el experimento de reporte incentivado.

### Desarrollo

```powershell
npx pnpm@latest install
npx pnpm@latest dev
```

La app queda en `http://localhost:5173`.

### Variables útiles

- `VITE_API_URL=http://127.0.0.1:8000`

Si no defines ninguna, la app usa `http://127.0.0.1:8000` por defecto.

### Flujo implementado

1. Entrada con pulsera y consentimiento.
2. Instrucciones.
3. Comprensión mínima.
4. Tirada inicial y rerolls.
5. Tratamiento justo antes del claim.
6. Pantalla final de pago o no pago.

### Comprobación rápida

```powershell
pnpm build
```

El build debe completarse sin errores antes de probar en el recinto o en staging.
