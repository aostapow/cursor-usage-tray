# cursor-usage-tray

Icono en la **bandeja del sistema de Windows** con un **monto flotante** que muestra el consumo on-demand en **USD** de tu cuenta Cursor.

## Descarga (última versión)

**[v1.0.0 — cursor-usage-tray-v1.0.0-windows.zip](https://github.com/aostapow/cursor-usage-tray/releases/download/v1.0.0/cursor-usage-tray-v1.0.0-windows.zip)**

1. Descomprimí el zip (necesitás **toda la carpeta**, no solo el `.exe`).
2. Ejecutá **`Iniciar.cmd`** (recomendado). Desbloquea el archivo y abre la app.

Windows suele **bloquear** programas descargados de Internet (*"Este archivo proviene de otro equipo..."*). Si `cursor-usage-tray.exe` no abre al doble clic:

- Usá **`Iniciar.cmd`**, o
- Clic derecho en el `.exe` → **Propiedades** → marcar **Desbloquear** → Aceptar, o
- En PowerShell, dentro de la carpeta: `Get-ChildItem -Recurse | Unblock-File`

Todas las releases: [GitHub Releases](https://github.com/aostapow/cursor-usage-tray/releases).

## Requisitos

- Windows 10+
- Python 3.10+
- **Cursor instalado** con sesión iniciada (el token se lee automáticamente de tu PC)

## Instalación rápida

```powershell
cd cursor-usage-tray
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

O:

```powershell
.\run.ps1
```

## Autenticación

No hay que configurar ni copiar tokens. El token se lee desde `%APPDATA%\Cursor\User\globalStorage\state.vscdb` y **no se guarda** en archivos de configuración.

Config: `%LOCALAPPDATA%\cursor-usage-tray\config.json`

## Uso

- **Monto flotante**: arrastrable en cualquier parte de la pantalla (incluida la barra de tareas)
- **Icono en bandeja**: clic derecho → menú (actualizar, dashboard, configuración, salir)
- **Clic derecho** sobre el monto → mismo menú contextual
- **Clic izquierdo** sobre el monto → dashboard (opcional, deshabilitado por defecto)

## Versión y actualizaciones

La versión actual está en `src/__version__.py`. Al iniciar, la app consulta la última [release en GitHub](https://github.com/aostapow/cursor-usage-tray/releases) y avisa si hay una más nueva. También podés usar **Buscar actualizaciones** en el menú del icono o del monto flotante.

Para publicar una versión nueva: subí el tag `vX.Y.Z` en GitHub y adjuntá el `.zip` de `dist\cursor-usage-tray` como asset de la release.

## Configuración

Clic derecho en el icono de bandeja → **Configuración**

- Intervalo de actualización
- Mostrar/ocultar monto flotante
- Umbrales de color (verde / amarillo / rojo)
- Iniciar con Windows
- Restablecer posición del monto

## Build (.exe)

```powershell
.\build.ps1
```

Salida: `dist\cursor-usage-tray\cursor-usage-tray.exe` (copiar la carpeta completa)

## Diagnóstico

```powershell
.\dist\cursor-usage-tray\cursor-usage-tray.exe --show-config
```
