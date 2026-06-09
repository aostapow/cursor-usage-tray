# cursor-usage-tray

Icono en la **bandeja del sistema de Windows** con un **monto flotante** que muestra el consumo de tu cuenta Cursor (USD, tokens del ciclo, uso del plan).

## Descarga (última versión)

**[v1.1.1 — cursor-usage-tray-v1.1.1-windows.zip](https://github.com/aostapow/cursor-usage-tray/releases/download/v1.1.1/cursor-usage-tray-v1.1.1-windows.zip)**

1. Descomprimí el zip (necesitás **toda la carpeta**, incluida `float\`).
2. Ejecutá **`Iniciar.cmd`** (recomendado). Desbloquea archivos y abre el supervisor de bandeja.

Windows suele **bloquear** programas descargados de Internet. Si el `.exe` no abre al doble clic, usá **`Iniciar.cmd`** o `Get-ChildItem -Recurse | Unblock-File`.

## Arquitectura (v1.1+)

- **`cursor-usage-tray.exe`**: icono en bandeja, lanza el flotante, busca e instala actualizaciones.
- **`float/cursor-usage-float.exe`**: monto flotante, API, configuración y alternancia de datos.

## Requisitos

- Windows 10+
- Python 3.10+ (solo para desarrollo)
- **Cursor instalado** con sesión iniciada

## Desarrollo

```powershell
.\run-tray.ps1    # supervisor (lanza float automáticamente)
.\run-float.ps1   # solo el monto flotante
.\run.ps1         # alias de run-tray.ps1
```

## Autenticación

El token se lee desde `%APPDATA%\Cursor\User\globalStorage\state.vscdb` y **no se guarda** en configuración.

Config: `%LOCALAPPDATA%\cursor-usage-tray\config.json`

## Uso

- **Monto flotante**: arrastrable; clic derecho → menú (actualizar, dashboard, configuración, salir)
- **Icono en bandeja**: reiniciar flotante, buscar actualizaciones, salir
- **Alternancia**: en Configuración, elegí USD / tokens / plan e intervalo en segundos

## Build (.exe)

```powershell
.\build.ps1
```

Salida:

- `dist\cursor-usage-tray\cursor-usage-tray.exe`
- `dist\cursor-usage-tray\float\cursor-usage-float.exe`
- `dist\cursor-usage-tray-v1.1.1-windows.zip`

## Diagnóstico

```powershell
.\.venv\Scripts\python.exe -m src.main --show-config
```
