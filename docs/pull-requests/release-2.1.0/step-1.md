# [release-2.1.0] Paso 1: script worktree_check.py

- **Rama:** `release-2.1.0-step-1`
- **Rama Destino (Sub-PR):** `release-2.1.0`
- **PR Principal:** `release-2.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.1.0/business-rules.md`

---

## 1. Resumen del Paso
Agrega el script de solo lectura `skills/worktree/scripts/worktree_check.py`, que la skill `/worktree` del paso 3 usa para validar la carpeta y detectar el `.venv`, los compose de tests, los archivos de entorno y la feature, con sus tests sobre repos git temporales. Suma su `discover` a `Tests (full)` y sube la versión a `2.1.0`. Es el script del origen con los nombres de stepwise, más tres cambios que el usuario eligió en la revisión (regla 2). Cubre CA-1 a CA-8, CA-15 y CA-16.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/skills/worktree/scripts/worktree_check.py` (nuevo): los modos `new` y `remove`, con las salidas `Carpeta:`, `Proyecto:`, `venv:`, `compose:`, `Proyecto fijo:`, `Entorno:`, `Rama:`, `Feature:` y `Llamadas compose:`, y los códigos 0, 1 y 2.
- `plugins/stepwise/skills/worktree/scripts/tests/test_worktree_check.py` (nuevo): 56 tests de CA-1 a CA-7.
- `CLAUDE.md`: el `discover` de `plugins/stepwise/skills/worktree/scripts/tests` en `Tests (full)`.
- `plugins/stepwise/.claude-plugin/plugin.json` y `tests/test_plugin_version.py`: versión `2.1.0`.
- `CHANGELOG.md`: la viñeta del script en `### Added` de `[Unreleased]`.
- `docs/decisions/release-2.1.0/business-rules.md`: la regla 2 con los tres cambios de la revisión, `Proyecto fijo:` en CA-1 y la carpeta que ya no existe en CA-6.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| Los docstrings de las clases de test citan CA-1 a CA-7 de este ADR, y se quitaron las referencias a rondas de revisión. | Regla 1: no se nombran los ADR, CA ni revisiones del origen. |
| `Proyecto fijo:` lista también `carpeta de <compose>`; `remove` de una carpeta borrada sugiere `git worktree prune`; los rechazos citan la URL de la guía. | Elección del usuario en la revisión (R3, R7, R4); quedan en la regla 2 del ADR. |
| La descripción de `plugin.json` no cambia todavía. | El ADR la deja para el paso 3, cuando existe la skill. |
| Los archivos nuevos se registraron con `git add -N` antes de volver a correr los tests. | `tests/test_path_lengths.py` solo ve los archivos de `git ls-files` (R8). |

## Pruebas
- **Tests del paso (`Tests (step)`):** `python3 -m unittest plugins/stepwise/skills/worktree/scripts/tests/test_worktree_check.py tests/test_plugin_version.py tests/test_shared_blocks.py tests/test_path_lengths.py tests/test_full_suite_owner.py`: 97 total, 0 failed, 0 errors, 0 skipped, en 40.439s.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 1 CA, 1 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R1 a R8).
- **Huella:** sha256:1b0f75225098545d6e0c8e154fffc839d8211b12e4ec12f157ee21d8d78fcd12

### Tests del paso
- `plugins/stepwise/skills/worktree/scripts/tests/test_worktree_check.py`
- `tests/test_plugin_version.py`
- `tests/test_shared_blocks.py`
- `tests/test_path_lengths.py`
- `tests/test_full_suite_owner.py`

### Verificación manual
- **CA-16:** el diff del paso no trae ninguno de los términos de la regla 1 (también rutas locales con `/`).
  - Pasos: 1. Desde la raíz, juntar `git diff release-2.1.0` y el contenido de los archivos sin seguimiento (`git ls-files --others --exclude-standard`). 2. Buscar sin distinguir mayúsculas la lista de términos de la regla 1 (en la memoria privada de Claude), más las referencias a rondas de revisión del origen (`round <n>`, `R<n> of`, `rule <n>`). 3. Comparar `worktree_check.py` y su test con los del origen: el código es igual salvo los cambios de la regla 2, y el resto de las diferencias son docstrings y comentarios.
  - Esperado: ningún término; un hallazgo es un `blocker`.
  - Obtenido: `grep` sin coincidencias (exit 1), también después de los arreglos de la revisión (`/close`, con los archivos nuevos registrados con `git add -N`). La comparación con el origen muestra docstrings y comentarios sin el ADR, las rondas ni las reglas del origen, y, en el código, solo los tres cambios de la regla 2 (R3, R4 y R7 de la revisión). Los docstrings de las clases de test citan CA-1 a CA-7 de este ADR.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **2 bloqueantes, 6 sugerencias y 0 preguntas.** El usuario eligió arreglar las seis sugerencias.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | La verificación de CA-16 listaba un patrón con el número de una regla de un ADR del origen. | Arreglado sin preguntar: el patrón genérico `rule <n>`. |
| R2 | blocker | Ningún test cubría el exit 2 de CA-7 cuando git falla. | Arreglado sin preguntar: `UsageTests.test_git_failure`, fuera de todo repo con `GIT_CEILING_DIRECTORIES`. |
| R3 | suggestion | `Proyecto fijo:` no informaba la carpeta de un compose fuera de la raíz, que `taken_projects` sí trata como compartida. | Arreglado: `_outside_root`, `carpeta de <compose>` en `fixed_projects` y su test; regla 2 y CA-1 del ADR. |
| R4 | suggestion | Los rechazos citaban `docs/worktrees.md` relativo, que no existe en otros proyectos. | Arreglado: la constante `GUIDE` con la URL de GitHub en los tres mensajes, y su test. |
| R5 | suggestion | `new` no probaba los rechazos por `-p`, `--project-directory`, `name:` y `name:` con `$`. | Arreglado: `NewInvalidTests.test_project_taken_by_the_commands_or_the_compose`. |
| R6 | suggestion | No había test del orden de búsqueda del python del `.venv`. | Arreglado: `VenvTests.test_python_search_order`. |
| R7 | suggestion | Un worktree registrado sin carpeta salía con 2 y "falta la sección". | Arreglado: sale con 1 y sugiere `git worktree prune`, con su test; regla 2 y CA-6 del ADR. |
| R8 | suggestion | `test_path_lengths.py` no veía los archivos nuevos sin seguimiento. | Arreglado: registrados con `git add -N` y los tests corridos de nuevo (97 en verde). |

- **Pasada sobre los arreglos:** R1 a R8 y los cambios del ADR `fixed`; sin bloqueantes nuevos. Los totales de `## Pruebas` los reescribió la corrida de `/close`.
- **Deuda:** ninguna.
- **Huella:** sha256:1b0f75225098545d6e0c8e154fffc839d8211b12e4ec12f157ee21d8d78fcd12

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.1.0/step-1.md`.
