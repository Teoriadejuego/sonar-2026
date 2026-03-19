# Repository Setup

Guia operativa para publicar SONAR 2026 en un repositorio git sin subir secretos, bases locales ni artefactos de desarrollo.

## 1. Que entra en git

Si entra:

- frontend `sorteo-sonar-main/`
- backend `api-sonar-main/api-sonar-main/`
- `codigo/` con scripts, documentacion y configuracion reproducible
- `ops/`
- documentacion raiz
- `docker-compose.yml`
- ejemplos de entorno `*.example`

No entra:

- `.env`, `.env.local`, `.env.classroom`
- bases de datos `.db`
- `node_modules/`
- builds
- `__pycache__/`
- outputs generados en `codigo/**/data` y `codigo/**/outputs`

## 2. Inicializar el repositorio

Desde la raiz del proyecto:

```powershell
git init -b main
git status
```

## 3. Primer commit local

```powershell
git add .
git status
git commit -m "Initialize SONAR 2026 repository"
```

Antes del commit, comprueba que `git status` no muestra:

- `.env`
- `.env.local`
- `.env.classroom`
- `database.db`
- `node_modules`
- outputs generados

## 4. Crear el remoto

### GitHub

1. Crea un repositorio vacio en GitHub.
2. No anadas README ni `.gitignore` desde la web.
3. Copia la URL del repositorio.

### GitLab

1. Crea un proyecto vacio.
2. No inicialices archivos desde la interfaz.
3. Copia la URL del remoto.

## 5. Conectar y subir

```powershell
git remote add origin <URL_DEL_REPOSITORIO>
git branch -M main
git push -u origin main
```

## 6. Verificacion post-push

Revisa en la web del repositorio que:

- no hay archivos `.env` reales,
- no hay bases locales,
- no hay `node_modules`,
- no hay outputs generados,
- si estan los docs operativos,
- si estan las migraciones,
- si estan los Dockerfiles,
- si estan los tests y scripts de carga.

## 7. Siguiente capa recomendable

Despues del primer push, conviene configurar:

- rama protegida `main`,
- reviewers o reglas minimas de merge,
- secrets del CI o despliegue fuera del repositorio,
- tags de version para hitos del experimento.

## 8. Comandos utiles

Ver remoto:

```powershell
git remote -v
```

Ver archivos ignorados:

```powershell
git status --ignored
```

Actualizar ejemplos de entorno:

```powershell
Copy-Item .env.local.example .env.local
Copy-Item .env.classroom.example .env.classroom
```
