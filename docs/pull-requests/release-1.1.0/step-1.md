# [release-1.1.0] Paso 1: la clave opcional `Prompts` en `/spec`

- **Rama:** `release-1.1.0-step-1`
- **Rama Destino (Sub-PR):** `release-1.1.0`
- **PR Principal:** `release-1.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-1.1.0/business-rules.md`

---

## 1. Resumen del Paso
`/spec` lee la clave opcional `Prompts` de `## Project commands`. Con ella, después de la aprobación guarda `$ARGUMENTS` literal, con un encabezado corto, en `<carpeta>/<AAAA-MM-DD>-spec.md` (o `-spec-step-<n>.md`), en el mismo commit del ADR, y "Fuente / Documento" lo enlaza. No sobrescribe un archivo que ya existe. Sin la clave, todo sigue igual, con una línea literal en el resumen y otra en el reporte, que pasa a 6 líneas. El plugin pasa a `1.1.0`. Cubre CA-1 a CA-8 y CA-26.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/skills/spec/SKILL.md`: la clave `Prompts` en el frontmatter, la regla de archivos, §0, §4 ("Fuente / Documento"), §5 (línea del prompt y sin escribirlo antes de la aprobación), §6 (el bloque **Prompt file** y los pasos de feature y de paso nuevo) y §7 (6 líneas). El bloque compartido `project-commands` no cambia.
- `plugins/stepwise/README.md`: la viñeta **Prompt del pedido** bajo `skills/spec/` y "Versión actual: `1.1.0`".
- `plugins/stepwise/.claude-plugin/plugin.json`: `version` `1.1.0`.
- `tests/test_plugin_version.py`: el valor fijo de `test_stepwise_manifest_has_semver_version` pasa a `1.1.0`.
- `CHANGELOG.md`: `### Added` en `[Unreleased]`, con la clave `Prompts`.
- `docs/pull-requests/release-1.1.0/step-1.md`: esta trazabilidad.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| La frase de introducción antes del reporte de `/spec` no cuenta como línea del reporte | Decisión del usuario en el code review (R2); `SKILL.md` no cambia |
| Con "otro nombre", `/spec` vuelve a comprobar con Glob la ruta nueva antes del Write | Code review R3, elección del usuario: evita pisar otro archivo que ya existe |
| Los CA manuales se verificaron con sesiones reales `claude -p --plugin-dir`, en repos desechables con `origin` `--bare` | Lo pide el ADR (§2): ningún test lee `SKILL.md` |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 -m unittest discover plugins/stepwise/hooks/tests && python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests && python3 -m unittest discover plugins/stepwise/scripts/tests && python3 -m unittest discover tests`:
  - `plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped, en 26.282s;
  - `plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped, en 20.737s;
  - `plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped, en 2.003s;
  - `plugins/stepwise/scripts/tests`: 38 total, 0 failed, 0 errors, 0 skipped, en 15.318s;
  - `tests`: 25 total, 0 failed, 0 errors, 0 skipped, en 4.892s.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 8 CA, 8 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos del code review: R3 en `spec/SKILL.md`).
- **Huella:** sha256:02b80c8b97ffb01c3abbfa24a0abb86ac6d721b8160e03b7c5014aff96b56660

### Verificación manual
Entorno común de CA-1 a CA-6: dos repos desechables, cada uno con un `origin` local `--bare`. `demo` declara `- Prompts: docs/prompts/<feature>/` y `demo-b` no lo declara; los dos tienen `Tests (step): none` y `Base branch: main`. Cada sesión es `claude -p --plugin-dir <ruta absoluta>/plugins/stepwise --output-format json --permission-mode acceptEdits --allowedTools Read Glob Grep Write Edit Agent "Bash(git:*)" -- "/stepwise:spec <pedido>"`. La aprobación va en un segundo turno: `claude -p --resume <session_id> ... -- "Apruebo."`. Claude Code 2.1.322, 2026-11-10.

- **CA-1:** con `Prompts`, un ADR de feature aprobado deja `<AAAA-MM-DD>-spec.md` con el encabezado y `$ARGUMENTS` literal, en el mismo commit del ADR.
  - Pasos: 1. En `demo`, correr `/stepwise:spec` con un pedido de 8 líneas: un encabezado `##`, una lista, una línea `---`, `*énfasis*`, acentos y `ñ`. 2. Aprobar. 3. Comparar el cuerpo del prompt, después del primer `\n---\n\n`, con el pedido, en Python y con los saltos de línea normalizados. 4. `git show --name-only --format=%s HEAD`.
  - Esperado: el archivo existe con el encabezado de la regla 4 y el pedido igual carácter por carácter, y el commit `docs(<feature>): add ADR` lista exactamente el ADR y el prompt. No cuentan como diferencia el salto de línea que termina el archivo ni los finales de línea CRLF/LF, que en Windows cambia `git` (`core.autocrlf`) y no el modelo.
  - Obtenido: existe `docs/prompts/funcion-despedida/2026-11-10-spec.md`. El encabezado es `# Prompt de /spec: funcion-despedida`, con Fecha, Tipo `feature`, Rama, ADR con enlace relativo y `---`. El cuerpo es igual al pedido, salvo el salto de línea final del archivo. El commit `docs(funcion-despedida): add ADR` lista solo `docs/decisions/funcion-despedida/business-rules.md` y ese prompt.
  - Ejecutó: Claude
- **CA-2:** sin aprobación no se escribe ningún prompt, y el resumen nombra la ruta.
  - Pasos: 1. Después del primer turno de la sesión de CA-1, y antes de aprobar, correr `git status --short --untracked-files=all` y `ls docs/prompts`. 2. Leer el resumen.
  - Esperado: no existe ningún archivo en `docs/prompts/<feature>/`, y el resumen nombra la ruta del prompt.
  - Obtenido: `ls` da `No such file or directory`, y solo aparece el ADR sin seguimiento. El resumen dice `**Prompt:** docs/prompts/funcion-despedida/2026-11-10-spec.md`.
  - Ejecutó: Claude
- **CA-3:** sin `Prompts`, el commit trae solo el ADR y salen las dos líneas literales.
  - Pasos: 1. En `demo-b`, correr `/stepwise:spec` con un pedido de una línea. 2. Leer el resumen. 3. Aprobar y leer el reporte. 4. `git show --name-only --format=%s HEAD` y `ls docs`.
  - Esperado: ningún prompt; el commit trae solo el ADR; el resumen dice `Prompt: no se guarda (sin la clave opcional Prompts)` y el reporte, de 6 líneas como máximo, `Prompt: no guardado (sin la clave opcional Prompts)`. Una frase de introducción antes del reporte no cuenta como línea del reporte (decisión del usuario, code review R2).
  - Obtenido:
    - el resumen trae `**Prompt:** no se guarda (sin la clave opcional Prompts)`;
    - el reporte trae `- Prompt: no guardado (sin la clave opcional Prompts)`;
    - el commit `docs(agregar-despedida): add ADR` lista solo el ADR, y `docs/` solo tiene `decisions/`;
    - el reporte tiene sus 6 líneas (ADR, prompt, rama, commit, PR y siguiente), con una frase de introducción antes ("Listo. Hice commit…").
  - Ejecutó: Claude
- **CA-4:** en un paso nuevo, el commit trae el ADR y `-spec-step-3.md`.
  - Pasos: 1. En `demo`, agregar a mano un paso 2 al ADR de `funcion-despedida`, hacer commit y push. 2. En la rama `funcion-despedida`, correr `/stepwise:spec Paso nuevo de funcion-despedida: …`. 3. Aprobar. 4. `git show --name-only --format=%s HEAD`.
  - Esperado: existe `<AAAA-MM-DD>-spec-step-3.md`, y el commit `docs(<feature>): add step 3 to ADR` lista exactamente el ADR y ese archivo.
  - Obtenido: existe `docs/prompts/funcion-despedida/2026-11-10-spec-step-3.md`, con `Tipo: paso nuevo (paso 3)` y el pedido literal. El commit `docs(funcion-despedida): add step 3 to ADR` lista solo el ADR y ese archivo, y el reporte tiene 6 líneas.
  - Ejecutó: Claude
- **CA-5:** si el prompt ya existe, no se sobrescribe: pregunta y no hace commit.
  - Pasos: 1. En `demo`, después de CA-4, crear a mano `docs/prompts/funcion-despedida/2026-11-10-spec-step-4.md`, sin seguimiento, y anotar su `sha256sum`. 2. Correr `/stepwise:spec` con un paso nuevo, que es el 4. 3. Aprobar sin elegir opción. 4. `git log --oneline -1`, `git status --short` y `sha256sum` otra vez.
  - Esperado: no lo sobrescribe, se detiene antes del commit, muestra la ruta y pregunta (sobrescribir, otro nombre o no guardar); no hay commit y el archivo no cambia.
  - Obtenido: el resumen ya avisa que el archivo existe. Después de aprobar, lo vuelve a revisar, no lo toca y pregunta por las tres opciones. El último commit sigue siendo `adf4bfa` (paso 3), el ADR queda modificado sin commit y el sha256 no cambia (`d74f8c50…`).
  - Segunda corrida, después del arreglo R3 del code review ("otro nombre" también se comprueba):
    - Pasos: 1. Con el ADR de `demo` devuelto a `adf4bfa`, crear además `2026-11-10-spec-step-4-b.md` sin seguimiento. 2. Correr `/stepwise:spec` con un paso nuevo y luego "Apruebo.". 3. Responder "Usa otro nombre: 2026-11-10-spec-step-4-b.md".
    - Obtenido: después de aprobar, se detiene y pregunta. Al elegir el otro nombre, vuelve a comprobarlo, dice que también existe, no lo escribe y pregunta otra vez. Sigue sin commit (`adf4bfa`), y los dos archivos conservan su sha256 (`d74f8c50…` y `0faceb0a…`).
  - Ejecutó: Claude
- **CA-6:** "Fuente / Documento" enlaza el prompt, y en un paso nuevo agrega el enlace sin quitar lo que había.
  - Pasos: leer la línea `Fuente / Documento` del ADR después de la sesión de CA-1 y después de la de CA-4.
  - Esperado: en la feature, el enlace al prompt; en el paso nuevo, el enlace anterior más el del paso.
  - Obtenido: en la feature, `[Prompt de /spec](../../prompts/funcion-despedida/2026-11-10-spec.md)`; después del paso 3, el mismo enlace más `; paso 3: [Prompt de /spec (paso 3)](../../prompts/funcion-despedida/2026-11-10-spec-step-3.md)`.
  - Ejecutó: Claude
- **CA-8:** el README del plugin describe la clave y dice `1.1.0`, y el CHANGELOG trae la línea de `Prompts`.
  - Pasos: leer `plugins/stepwise/README.md` (`skills/spec/` y Versionado) y `[Unreleased]` de `CHANGELOG.md`.
  - Esperado: la clave descrita según la regla 2, "Versión actual: `1.1.0`" y una viñeta en `### Added`, en inglés y con el formato de `[1.0.0]`.
  - Obtenido: `skills/spec/` tiene la viñeta **Prompt del pedido** con sus tres sub-viñetas (archivo existente, largo y sin la clave); Versionado dice `1.1.0`; `[Unreleased]` tiene `### Added` con **The optional `Prompts` key**.
  - Ejecutó: Claude
- **CA-26:** el diff del paso no trae ningún término de la fuente.
  - Pasos: 1. Pasar las líneas agregadas de `git diff HEAD` (archivos con seguimiento) por el grep de la lista de términos de la regla 1, sin distinguir mayúsculas, que incluye las carpetas temporales locales. 2. Pasar el contenido completo de cada archivo sin seguimiento (`git ls-files --others --exclude-standard`: esta trazabilidad) por el mismo grep. 3. Repetirlo después de los arreglos del code review.
  - Esperado: ninguna coincidencia.
  - Obtenido: 0 coincidencias en las líneas agregadas y 0 en `docs/pull-requests/release-1.1.0/step-1.md`, después de los arreglos R1 a R4. La primera corrida solo miraba `git diff`, que no incluye los archivos sin seguimiento (code review R1).
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **1 bloqueante, 2 sugerencias y 1 pregunta.** El usuario eligió arreglar R3 y R4, y respondió R2.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | La verificación de CA-26 pasó el grep solo por `git diff`, que no ve esta trazabilidad sin seguimiento | Arreglado sin preguntar: el grep pasa también por el contenido completo de los archivos sin seguimiento, y se corrió otra vez |
| R2 | question | ¿Cuenta como línea la frase de introducción que antecede al reporte de 6 líneas (CA-3)? | No cuenta (decisión del usuario); queda dicho en el Esperado de CA-3, y `SKILL.md` no cambia |
| R3 | suggestion | Si el usuario elige "otro nombre", la skill no pide comprobar con Glob el nombre nuevo | Arreglado: `spec/SKILL.md`, viñeta "Already exists", "For another name, repeat this check on the new path before writing."; CA-5 se repitió con una sesión real |
| R4 | suggestion | CA-1 pide "carácter por carácter" pero acepta, sin explicarlo, el salto de línea final y la normalización CRLF/LF | Arreglado: el Esperado de CA-1 dice que esas dos diferencias no cuentan |

- **Pasada sobre los arreglos:** R2, R3 y R4 `fixed`. R1 quedó incompleto: los Pasos de CA-26 nombraban dos términos de la lista, y el grep sobre el archivo daba 1 coincidencia, no 0. El usuario eligió sacarlos de los Pasos y pasarlos a la lista privada. Se hizo, y el grep repetido da 0 y 0. Este último arreglo no tuvo tercera pasada del revisor (no la hay).
- **Deuda:** ninguna.
- **Huella:** sha256:02b80c8b97ffb01c3abbfa24a0abb86ac6d721b8160e03b7c5014aff96b56660

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados y suite completa en verde (o fallos preexistentes registrados con la decisión del usuario).
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-1.1.0/step-1.md`.
