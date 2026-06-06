# Contexto del proyecto (conversación previa)

Este workspace nació en una conversación en **Full Modulos** sobre mostrar el consumo en **dólares ($)** de Cursor en Windows.

## Objetivo

Aplicación liviana que:

1. Obtiene el consumo de Cursor vía `WorkosCursorSessionToken`
2. Se integra en la **bandeja del sistema (system tray)** de Windows
3. Refresca periódicamente sin abrir el navegador

## Decisiones tomadas

| Tema | Decisión |
|------|----------|
| Workspace | **Nuevo**, separado de `Full Modulos` (dominio COBIS/TFS) |
| UI Windows | **Texto junto al reloj** en la taskbar (overlay anclado); icono de bandeja opcional |
| Stack MVP | **Python** + `pystray` + `requests` |
| API | Endpoints **no oficiales** del dashboard (`/api/usage-summary`) |
| Auth | Solo lectura en runtime desde `state.vscdb` de Cursor (por usuario/PC) |
| Config | `%LOCALAPPDATA%\cursor-usage-tray\config.json` (preferencias, **sin token**) |

## API utilizada (no oficial)

Documentación comunitaria: [gist dmwyatt](https://gist.github.com/dmwyatt/1e9359b1862e7cbfe1e754fe4c8db764)

```http
GET https://cursor.com/api/usage-summary
Cookie: WorkosCursorSessionToken=<token>
```

Montos on-demand suelen venir en **centavos** → dividir por 100 para USD.

Para eventos detallados (opcional futuro):

```http
POST https://cursor.com/api/dashboard/get-filtered-usage-events
Origin: https://cursor.com
```

## Autenticación (distribución multi-usuario)

- Cada persona ejecuta el mismo binario/script en su PC con Cursor logueado.
- En cada refresh se lee `cursorAuth/accessToken` (o equivalentes) de `state.vscdb`.
- No hay `--set-token`, ni token en código, ni token en `config.json`.

## Limitaciones conocidas

- API no documentada: puede romperse sin aviso
- El token expira (JWT); hay que renovarlo
- El token es sensible (equivale a sesión web)
- Planes distintos (Pro / Team / Enterprise) exponen campos diferentes

## Referencias útiles

- [cursor-usage CLI](https://github.com/dmwyatt/cursor-usage)
- [cursor-usage-monitor (extensión IDE)](https://github.com/lixwen/cursor-usage-monitor)
- [cursor-costs-raycast (macOS menu bar)](https://github.com/shadeov/cursor-costs-raycast)
- [Admin API oficial (teams)](https://docs.cursor.com/account/teams/admin-api)

## Próximos pasos sugeridos

- [ ] Auto-start con Windows (Task Scheduler o registro Run)
- [x] Empaquetar con PyInstaller (`.\build.ps1` → `dist\cursor-usage-tray.exe`)
- [ ] Fallback Windows Credential Manager (`cursor-access-token` del CLI)
- [ ] Desglose por modelo (`get-filtered-usage-events`)
- [ ] Notificación al superar umbral de gasto
