# [release-2.0.0] Paso 1: tests del paso en /implement, /check, /close y /audit

- **Rama:** `release-2.0.0-step-1`
- **Rama Destino (Sub-PR):** `release-2.0.0`
- **PR Principal:** `release-2.0.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.0.0/business-rules.md`

---

## 1. Resumen del Paso
`/check` y `/close` corren ahora solo los tests del paso: la lista que `/implement` anota en `## Pruebas` → `### Tests del paso`, con un bloque compartido nuevo, `step-tests`. Ya no corren `Tests (full)`. Si la lista falta, `/check` la arma y pide confirmación, y `/audit self`, `/check` y `/close` le agregan los tests que tocan sus arreglos. El último `/close` deja el PR principal en draft y pide `/regression`. Un test nuevo impide que otra skill corra la suite completa o use `gh pr ready`, y la versión pasa a `2.0.0`. Cubre CA-1 a CA-8, CA-20 y CA-21.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/skills/implement/SKILL.md`: la descripción, la lista `### Tests del paso` al terminar los CA, la línea `Step tests:` del reporte, y `/regression` mantiene el PR en draft por las verificaciones después del merge.
- `plugins/stepwise/skills/check/SKILL.md`: la descripción, la clave `Tests (step)` en lugar de `Tests (full)`, §0.4 (lista que falta o incompleta), el bloque `step-tests`, los tests de los arreglos en la lista, la línea `Tests del paso` de `## Pruebas` y el ejemplo de alineación sin `gh pr ready`.
- `plugins/stepwise/skills/close/SKILL.md`: la descripción, las claves sin `Tests (full)`, la precondición de `/check`, §2 ("Step tests after changes") con el bloque `step-tests`, el merge con los tests del paso, el último paso en draft con `pendiente de /regression` y el reporte con `next: /regression`.
- `plugins/stepwise/skills/audit/SKILL.md`: los totales de los tests del paso y los tests de los arreglos en la lista.
- `plugins/stepwise/skills/close/references/step-pr-template.md`: el ítem de tests del checklist.
- `tests/test_full_suite_owner.py` (nuevo): ninguna `SKILL.md` fuera de `regression` delega `full`, invoca `run_tests.py full` ni contiene `gh pr ready`.
- `tests/test_shared_blocks.py`: `step-tests` entre los ids exigidos, y sus copias solo en `check` y `close`.
- `plugins/stepwise/.claude-plugin/plugin.json` y `tests/test_plugin_version.py`: versión `2.0.0`.
- `CHANGELOG.md`: la viñeta "Major" en `### Changed` de `[Unreleased]`.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| El texto de las skills es el de la versión de origen, con los nombres de stepwise. | El ADR elige traer el cambio sin reescribirlo (§5). Las diferencias son solo las de stepwise de antes (nombre del marketplace, plegado de la descripción) y los arreglos R3 y R4. |
| `implement` ya dice que `/regression` mantiene el PR en draft. | Es el comportamiento que deja este paso; esperar al paso 3 dejaba el texto viejo en una rama donde `/close` ya no marca ready. |
| La descripción de `plugin.json` no cambia todavía. | El ADR la deja para el paso 3, cuando existe `regression`. |
| Los docstrings del test nuevo citan el ADR `release-2.0.0`. | Es el ADR de stepwise; la regla 1 prohíbe solo los de la fuente. |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 plugins/stepwise/scripts/run_tests.py full`: 158 total, 0 failed, 0 errors, 1 skipped, en 68.045s.
  - `python3 -m unittest discover plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped in 23.941s
  - `python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped in 17.250s
  - `python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped in 3.773s
  - `python3 -m unittest discover plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped in 19.060s
  - `python3 -m unittest discover tests`: 35 total, 0 failed, 0 errors, 0 skipped in 4.021s
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 7 CA, 7 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R1 a R5).
- **Huella:** sha256:ef9f7ea230cb68d1302a60119cb6a0bfc567c3f4a3833ace7751f866722c45c8

### Tests del paso
- `tests/test_full_suite_owner.py`
- `tests/test_shared_blocks.py`
- `tests/test_plugin_version.py`

### Verificación manual
- **CA-1:** `/implement` escribe `### Tests del paso` (o `ninguno`) antes de `### Verificación manual` y lo reporta.
  - Pasos: 1. Leer `plugins/stepwise/skills/implement/SKILL.md:87` ("Step tests list") y `:107` (línea `Step tests:` del reporte). 2. Comprobar la ubicación de la subsección, el formato ``- `<ruta>` `` y `ninguno`.
  - Esperado: el texto de CA-1.
  - Obtenido: `:87` pide escribir, después del último CA, las rutas pasadas a `test-runner step`, una por línea, antes de `### Verificación manual`, o `ninguno`; `:107` agrega `Step tests: <N> in "Tests del paso" of <archivo> | ninguno` al reporte.
  - Ejecutó: Claude
- **CA-2:** `/check` corre `test-runner step <lista>`, nunca `full`, escribe la línea `Tests del paso` y agrega los tests de sus arreglos.
  - Pasos: 1. Leer `plugins/stepwise/skills/check/SKILL.md:32` (bloque `step-tests`), `:55` ("Tests the fix touched") y la plantilla de `## Pruebas` de la sección 3.
  - Esperado: el texto de CA-2.
  - Obtenido: `:32` delega `"step <every path or id of the list ...>"`, "never the full suite (only `/regression` runs it)"; `:55` agrega el test del arreglo a la lista (reemplaza `ninguno`) antes de volver a correr; la plantilla trae `- **Tests del paso (\`Tests (step)\`):**`. `test_full_suite_owner.py` confirma que ninguna `SKILL.md` fuera de regression delega `full`.
  - Ejecutó: Claude
- **CA-3:** con `ninguno`, `/check` no llama a `test-runner`, anota `sin tests del paso` y corre lo demás.
  - Pasos: 1. Leer `check/SKILL.md:32` y el ítem 3 de la sección 1.
  - Esperado: el texto de CA-3.
  - Obtenido: `:32` dice "If the list says `ninguno`, do not call `test-runner` and record `sin tests del paso`"; el ítem 3 dice que `Lint/format` y `Type check` corren "also when the step's tests ran and passed on the first try, or there were none", y el ítem 2 corre `Migrations check`.
  - Ejecutó: Claude
- **CA-4:** sin lista, `/check` la arma, la muestra y pide confirmación; con lista, avisa de un test del paso que falta.
  - Pasos: 1. Leer `check/SKILL.md:26-28` (§0.4).
  - Esperado: el texto de CA-4.
  - Obtenido: `:27` ("Missing") arma la lista con los archivos de test entre los cambios del paso, la muestra y pide confirmar antes de correr nada, y la escribe (desde R3, como la única escritura de la sección 0, creando el archivo o `## Pruebas` si faltan); `:28` ("Present") avisa y pregunta si un archivo de test del paso no está en la lista.
  - Ejecutó: Claude
- **CA-5:** `/close` exige la línea de `/check` y `### Tests del paso`, agrega los tests de la revisión, vuelve a correr la lista (no `full`) y el merge exige esos tests en verde; no pide `Tests (full)`.
  - Pasos: 1. Leer `plugins/stepwise/skills/close/SKILL.md:16`, `:27`, `:55`, `:77`, y `audit/SKILL.md:43`.
  - Esperado: el texto de CA-5.
  - Obtenido: `:16` ya no lista `Tests (full)`; `:27` exige `Tests del paso` (o `Suite completa` de un `/check` anterior) y `### Tests del paso`; `:55` agrega los tests de los arreglos y corre el bloque `step-tests`; `:77` mergea con los tests del paso en verde, `sin tests del paso` o `Tests (step)` `none`. `audit/SKILL.md:43` agrega a la lista el test que crea o modifica un arreglo.
  - Ejecutó: Claude
- **CA-6:** el último `/close` deja "Verificación Global" en `pendiente de /regression`, pregunta antes de aplicar la descripción, no ofrece `gh pr ready` y termina con `next: /regression`.
  - Pasos: 1. Leer `close/SKILL.md:74`, `:83-85` y `:90`.
  - Esperado: el texto de CA-6.
  - Obtenido: `:83` escribe la descripción con "Verificación Global" en `pendiente de /regression` y pregunta antes del `gh pr edit`; `:84` "Never take it out of draft and do not offer it, even if the user asks"; `:74` y `:90` terminan el reporte con `next: /regression`. No queda ningún `gh pr ready` fuera de regression (`test_full_suite_owner.py`).
  - Ejecutó: Claude
- **CA-21:** el diff del paso no trae ningún término de la lista de saneamiento.
  - Pasos: 1. Buscar los términos de la regla 1 (sin distinguir mayúsculas, también rutas locales con `/`) en las líneas agregadas de `git diff release-2.0.0` y en los archivos nuevos.
  - Esperado: ninguna coincidencia, salvo texto que ya está en `main` (CA-21).
  - Obtenido: sin coincidencias. La única es una frase genérica de `close/SKILL.md:83` que ya estaba en `main` (`audit` y `close`) y no viene de la fuente; el usuario la aceptó en `/audit self` (R6). La ruta local del comando de la suite se quitó en R1.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **1 bloqueante, 4 sugerencias y 1 pregunta.** El usuario eligió arreglar las 4 sugerencias y aceptar la frase de R6.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | El comando de la suite en `## Pruebas` traía una ruta local, que el grep de CA-21 no detectaba (busca solo `\`). | Arreglado sin preguntar: el comando queda relativo al repo y CA-21 busca también rutas con `/`. |
| R2 | suggestion | `test_shared_blocks.py` no comprobaba que `step-tests` estuviera en `check` y en `close` (CA-8). | Arreglado: `test_step_tests_lives_in_check_and_close`. |
| R3 | suggestion | `check` §0.4 escribe la lista aunque la sección 0 dice "change nothing yet". | Arreglado: §0.4 dice que es la única escritura de la sección 0 y que crea el archivo si falta. |
| R4 | suggestion | El título "## 2. Suite after changes" de `close` quedó viejo. | Arreglado: "## 2. Step tests after changes". |
| R5 | suggestion | La regla de `run_tests.py full` solo aceptaba `"` antes de `full`. | Arreglado: acepta `"`, `'` o backtick, con `test_run_tests_full_after_any_quote`. |
| R6 | question | Una línea editada de `close` trae la frase genérica "the session's scratchpad if there is one", ya presente en `main`; CA-21 no preveía excepciones. | El usuario la acepta: CA-21 del ADR excluye el texto genérico que ya está en `main` y no viene de la fuente. |

- **Pasada sobre los arreglos:** R1, R2, R3, R4, R5 y R6 `fixed`, sin bloqueantes nuevos.
- **Deuda:** ninguna.
- **Huella:** sha256:ef9f7ea230cb68d1302a60119cb6a0bfc567c3f4a3833ace7751f866722c45c8

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.0.0/step-1.md`.
