# Prompts

Aquí `/spec` guarda el pedido exacto con el que se inició cada feature, porque este repo declara `- Prompts: docs/prompts/<feature>/` en su `CLAUDE.md`. La clave está descrita en el [README del plugin](../../plugins/stepwise/README.md).

- **Nombre:** `docs/prompts/<feature>/<AAAA-MM-DD>-spec.md` para una feature o un bug, y `<AAAA-MM-DD>-spec-step-<n>.md` para un paso nuevo, con `<n>` el primer paso que agrega.
- **Contenido:** un encabezado corto (fecha, tipo, rama y enlace al ADR) y, debajo, el pedido tal cual. Entra en el mismo commit del ADR, y "Fuente / Documento" lo enlaza.
- **No se pisan:** `/spec` no sobrescribe un archivo que ya existe: pregunta si lo sobrescribe, usa otro nombre o no lo guarda.
- **Rutas largas:** ninguna ruta del repo pasa de 72 caracteres (`tests/test_path_lengths.py`). `docs/prompts/<feature>/2026-11-10-spec-step-12.md` son 40 caracteres más la feature, así que una feature de más de 32 caracteres no cabe. `/spec` no mira el largo, y el test lo detecta en el `/check` siguiente. Por eso aquí el nombre de la feature se elige corto.
- **Repo público:** el pedido queda en el historial tal cual. Antes de aprobar, se revisa que no traiga datos privados (otros repos, clientes, personas, rutas locales, secretos). Si los trae, se reescribe el pedido sin esos datos antes de invocar `/spec`. `/spec` no ofrece "no guardarlo" al aprobar (solo cuando el archivo ya existe): pedírselo depende de que el modelo lo respete, así que se revisa el commit antes del push.
- **Lo anterior:** los ADR anteriores a la clave (`bootstrap` y `release-1.1.0`) no tienen prompt guardado, y no se agrega.
