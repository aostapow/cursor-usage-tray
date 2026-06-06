# Contexto del proyecto (conversación previa)

Este workspace nació en una conversación en **Full Modulos** sobre mostrar el consumo en **dólares ($)** de Cursor en Windows.

## Objetivo

Aplicación liviana que:

1. Obtiene el consumo de Cursor vía `WorkosCursorSessionToken`
2. Muestra un **monto flotante** en pantalla y un **icono en la bandeja**
3. Refresca periódicamente sin abrir el navegador

## Arquitectura v1.1 (dos procesos)

| Proceso | Ejecutable | Rol |
|---------|------------|-----|
| Tray supervisor | `cursor-usage-tray.exe` | Icono bandeja, lanza/supervisa float, updates |
| Float worker | `cursor-usage-float.exe` | Monto flotante, API, configuración, alternancia |

Comunicación vía `config.json` y `state.json` en `%LOCALAPPDATA%\cursor-usage-tray\`.

Instalación recomendada: `%LOCALAPPDATA%\cursor-usage-tray\app\` con subcarpeta `float\`.

## Decisiones tomadas

| Tema | Decisión |
|------|----------|
| Workspace | **Nuevo**, separado de `Full Modulos` (dominio COBIS/TFS) |
| UI Windows | **Texto flotante** arrastrable; icono de bandeja (supervisor) |
| Stack MVP | **Python** + `pystray` + `tkinter` + `requests` |
| API | Endpoints **no oficiales** del dashboard |
| Auth | Solo lectura en runtime desde `state.vscdb` de Cursor |
| Config | `%LOCALAPPDATA%\cursor-usage-tray\config.json` (sin token) |
| Updates | Tray puede reemplazar `float/` sin cerrarse (opt-in en config) |

## API utilizada (no oficial)

Documentación comunitaria: [gist dmwyatt](https://gist.github.com/dmwyatt/1e9359b1862e7cbfe1e754fe4c8db764)

```http
GET https://cursor.com/api/usage-summary
Cookie: WorkosCursorSessionToken=<token>
```

Montos on-demand suelen venir en **centavos** → dividir por 100 para USD.

Tokens del ciclo de facturación:

```http
POST https://cursor.com/api/dashboard/get-filtered-usage-events
Origin: https://cursor.com
Content-Type: application/json

{
  "startDate": "<billing_cycle_start_ms>",
  "endDate": "<billing_cycle_end_ms>",
  "page": 1,
  "pageSize": 100
}
```

Se suman `inputTokens`, `outputTokens`, `cacheWriteTokens` y `cacheReadTokens` de cada evento en `tokenUsage`.

## Autenticación (distribución multi-usuario)

- Cada persona ejecuta el mismo binario/script en su PC con Cursor logueado.
- En cada refresh se lee el token de `state.vscdb`.
- No hay token en código ni en `config.json`.

## Limitaciones conocidas

- API no documentada: puede romperse sin aviso
- El token expira (JWT); hay que renovarlo
- Actualizar el **tray** requiere reiniciar el supervisor (el float se actualiza en caliente)

## Referencias útiles

- [cursor-usage CLI](https://github.com/dmwyatt/cursor-usage)
- [cursor-usage-monitor (extensión IDE)](https://github.com/lixwen/cursor-usage-monitor)
