# [release-2.1.0] Paso 3: skill, guía y publicación

- **Rama:** `release-2.1.0-step-3`
- **Rama Destino (Sub-PR):** `release-2.1.0`
- **PR Principal:** `release-2.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.1.0/business-rules.md`

---

## 1. Resumen del Paso
Agrega la skill `/stepwise:worktree` (`new <folder>` y `remove <folder>`), que usa el script del paso 1, y la guía `docs/worktrees.md` para llevar varias features en paralelo con `git worktree`, en inglés y sin datos del origen. Los README, `plugin.json`, `marketplace.json` y el CHANGELOG nombran la skill, y el README del plugin queda en `2.1.0`. Cubre CA-10 a CA-16; la sesión real de CA-12 queda para después del merge, por decisión del usuario.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/skills/worktree/SKILL.md` (nuevo): la skill, con los bloques `project-commands` y `git-rules` y el enlace a la guía por su URL de GitHub.
- `docs/worktrees.md` (nuevo): la guía, secciones 1 a 9, con los recuadros **In this repo** de stepwise.
- `plugins/stepwise/README.md`: la entrada `skills/worktree/`, `worktree` en "Today", el `discover` del script en los tests y la versión `2.1.0`.
- `README.md`: la fila "Worktrees" y el enlace a la guía.
- `plugins/stepwise/.claude-plugin/plugin.json` y `.claude-plugin/marketplace.json`: las descripciones con las siete skills.
- `CHANGELOG.md`: la skill en `### Added` de `[Unreleased]`.
- `docs/decisions/release-2.1.0/business-rules.md`: CA-13 cita `README.md:90-91` (R6 de la revisión).

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| El aviso de proyecto compartido de `new` sale solo de `Proyecto fijo:`. | Desde el paso 1, `Proyecto fijo:` incluye la carpeta de un compose fuera de la raíz (regla 2), así que cubre el caso que el origen avisaba aparte. |
| La guía suma la regla "the test compose file at the root" en la sección 4. | Refleja el mismo cambio del paso 1. |
| Las referencias de la skill a la guía van como "the guide, section N". | La skill corre en otros proyectos, donde `docs/worktrees.md` no existe; arriba enlaza la URL (regla 3). |
| Los hechos verificados de la guía quedan sin proyecto, cifras, hashes, fechas, PR, servicios ni textos del origen. | Regla 6; R5 y R7 de la revisión. |
| CA-12 se mergea sin correr y queda `después del merge`. | Decisión del usuario en `/close` (2026-11-21); `/regression` mantiene el PR principal en draft hasta confirmarla. |

## Pruebas
- **Tests del paso (`Tests (step)`):** `python3 -m unittest tests/test_shared_blocks.py tests/test_full_suite_owner.py tests/test_path_lengths.py tests/test_plugin_version.py plugins/stepwise/skills/worktree/scripts/tests/test_worktree_check.py`: 97 total, 0 failed, 0 errors, 0 skipped, en 33.719s.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 6 CA, 5 ok, 0 pendientes de confirmar por el usuario, 1 después del merge (ver abajo; CA-12 pasó de `pendiente` a `después del merge` por decisión del usuario en `/close`).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R1 a R7).
- **Huella:** sha256:d8b710be20d1140364aa1452da8b828df9ad09606f22a32bd69d0fda39ae3831

### Tests del paso
- `tests/test_shared_blocks.py`
- `tests/test_full_suite_owner.py`
- `tests/test_path_lengths.py`
- `tests/test_plugin_version.py`
- `plugins/stepwise/skills/worktree/scripts/tests/test_worktree_check.py`

### Verificación manual
- **CA-10:** `skills/worktree/SKILL.md` tiene el frontmatter, los bloques `project-commands` y `git-rules`, y el modo `new` de CA-10.
  - Pasos: 1. Leer el frontmatter (`:1-6`). 2. Leer §0 (`:14-37`) y §1 (`:39-58`) contra los cinco puntos de CA-10. 3. `tests/test_shared_blocks.py` comprueba que los bloques son iguales a sus copias.
  - Esperado: el texto de CA-10.
  - Obtenido: `disable-model-invocation: true` y `argument-hint: new <folder> | remove <folder>`; los dos bloques, en verde en `test_shared_blocks.py`. `new`: corre el script y se detiene con exit 1 o 2 (§0, "The script"); `git fetch origin <Base branch>` y, si falla, no crea nada (§1.2); `git worktree add --detach "<Carpeta>" "origin/<Base branch>"` (§1.3); con `venv: yes (<python>)`, el `.venv` con ese python y el `pip freeze` sin rutas locales, instalado con `run_in_background` (§1.4); el `cp` de `Entorno:` solo impreso, con el aviso de `(sin ignorar)` (§1.5); `EnterWorktree` con `path`, o `cd "<Carpeta>" && claude` (§1.6). El aviso de proyecto compartido sale de `Proyecto fijo:`, que desde el paso 1 incluye la carpeta de un compose fuera de la raíz (regla 2).
  - Ejecutó: Claude
- **CA-11:** el modo `remove` de la misma `SKILL.md` cumple CA-11.
  - Pasos: 1. Leer §2 (`:60-94`) contra los seis puntos de CA-11. 2. Buscar `down -v`, `docker compose config`, `--force` y `gh pr ready` en la skill.
  - Esperado: el texto de CA-11.
  - Obtenido: dentro del worktree, `ExitWorktree` `keep` si entró en esta sesión, si no se detiene (§2.1); el exit 1 del script, con ejemplos que incluyen la carpeta que ya no existe (`git worktree prune`) y el nombre que normalizado queda vacío (§2.2, R4 de la revisión); el PR principal mergeado con `gh pr list --state merged` o `git merge-base --is-ancestor` (§2.3) y `status --short` vacío antes de bajar nada (§2.4); se detiene si un contenedor del proyecto tiene otro `working_dir` (§2.5.1); `docker rm -f -v` de los one-off, `rm -s -v -f` y `down --rmi local` con `-p "<Proyecto>"` desde la carpeta del worktree (§2.5.2-3); los volúmenes con la etiqueta y el prefijo `<Proyecto>_`, con el sí del usuario (§2.5.4); `git worktree remove` y `prune` desde la copia principal, y la rama queda (§2.6-7). `down -v` y `docker compose config` aparecen solo como prohibidos, `--force` solo como "never", y `gh pr ready` no aparece (`test_full_suite_owner.py` en verde).
  - Ejecutó: Claude
- **CA-12:** sesión real sin Docker de `/stepwise:worktree new` y `remove` en un repo desechable de GitHub.
  - Pasos:
    1. Crear un repo desechable en GitHub (por ejemplo `wt-test`), clonarlo y hacer commit y push a `main` de un `CLAUDE.md` con `## Project commands`: `Tests (step)`, `Tests (full)`, `Lint/format`, `Type check` y `Migrations check` en `none`, `Base branch: main`, `Decision docs: docs/decisions/<feature>/business-rules.md` y `Traceability: docs/pull-requests/<feature>/step-<n>.md`.
    2. Desde la raíz de ese clon: `claude --plugin-dir "<ruta absoluta de stepwise>/plugins/stepwise"`, con stepwise en la rama `release-2.1.0-step-3`.
    3. Escribir `/stepwise:worktree new wt-a`. Comprobar que `../wt-a` existe, que `git -C ../wt-a status` dice HEAD separado en `origin/main` y que la sesión entró (o anotar qué pasó con `EnterWorktree`).
    4. En esa sesión, `/stepwise:spec agregar un README de prueba` hasta el resumen de aprobación, y aprobarlo (crea `<feature>` y el PR principal en draft).
    5. Escribir `/stepwise:worktree remove wt-a` sin mergear el PR: debe detenerse sin quitar nada.
    6. Sacar el PR de draft y mergearlo en GitHub con merge commit, y volver a escribir `/stepwise:worktree remove wt-a`.
  - Esperado: en el paso 3, el worktree en `../wt-a` con HEAD separado en `origin/main` y la sesión adentro; en el 4, el resumen de aprobación de `/spec`; en el 5, se detiene por el PR sin mergear; en el 6, salta el compose (`Llamadas compose: none`), `git worktree list` ya no muestra `wt-a` y la rama `<feature>` sigue local y remota.
  - Obtenido: después del merge: el usuario decidió mergear el paso y correr esta sesión después (2026-11-21, en `/close`); queda como casilla en el PR principal, y `/regression` no lo saca de draft hasta que esté confirmada.
  - Ejecutó: después del merge
- **CA-13:** `docs/worktrees.md` cumple CA-13.
  - Pasos: 1. Leer las secciones. 2. Comprobar que la skill aparece en las secciones 2, 7 y 8 con los comandos a mano. 3. Leer los recuadros **In this repo**. 4. Abrir cada `ruta:línea` citada.
  - Esperado: el texto de CA-13.
  - Obtenido: en inglés, con "Why it is needed" y las secciones 1 a 9; `/stepwise:worktree` en 2 (`new`), 7 (`remove`) y 8 (checklist), con los comandos a mano. Los recuadros hablan de la instalación `local` (`README.md:90-91`, después de las líneas que este paso agrega al README raíz; R1 de la revisión, con CA-13 actualizado; y `--plugin-dir`) y de la versión, `tests/test_plugin_version.py:257` y el `CHANGELOG`, sobre `main`. Las citas son correctas en stepwise: `implement/SKILL.md:30-31` y `:32`, `close/SKILL.md:86`, `spec/SKILL.md:109`, `regression/SKILL.md:42` y `:84`, `run_tests.py:41`, `:473-494` y `:627`, `block_env_access.py:40-79` (vueltas a abrir después de los arreglos). Los hechos del origen quedan sin proyecto, cifras, hashes, fechas ni PR (regla 6); después de R5 y R7 de la revisión, tampoco traen el servicio, el puerto ni los textos de las verificaciones del origen, y la regla 3 de la sección 4 (el compose en la raíz) refleja el cambio del paso 1.
  - Ejecutó: Claude
- **CA-14:** los README, `plugin.json`, `marketplace.json` y `CHANGELOG.md` nombran la skill.
  - Pasos: 1. Leer la entrada `skills/worktree/`, "Today", la línea de tests y "Versioning" del README del plugin. 2. Leer la tabla y el enlace del README raíz. 3. Leer las tres descripciones. 4. Leer `[Unreleased]`.
  - Esperado: el texto de CA-14.
  - Obtenido: el README del plugin tiene la entrada (`new`, `remove`, script, con los cambios de la regla 2), `worktree` en "Today" de `project-commands` y `git-rules`, el `discover` del script en la línea de tests y `Current version: 2.1.0`; el README raíz tiene la fila "Worktrees" y el enlace a `docs/worktrees.md`; `plugin.json` y `marketplace.json:4` y `:9` nombran spec, implement, check, audit, close, regression y worktree (JSON válido); `[Unreleased]` → `### Added` trae la skill y su guía.
  - Ejecutó: Claude
- **CA-16:** el diff del paso no trae ninguno de los términos de la regla 1 (también rutas locales con `/`).
  - Pasos: 1. Registrar los archivos nuevos con `git add -N`. 2. Buscar sin distinguir mayúsculas, en las líneas agregadas de `git diff release-2.1.0`, la lista de términos de la regla 1 (en la memoria privada de Claude), más los nombres, hashes, fechas, cifras y PR de las verificaciones del origen.
  - Esperado: ningún término; un hallazgo es un `blocker`.
  - Obtenido (repetido después de los arreglos de la revisión, también buscando `8080`, `test_db` y los textos de la verificación del origen): una sola coincidencia, "the session's scratchpad if there is one" en `SKILL.md:46`, el mismo texto genérico que ya está en `main` en otras skills (`audit/SKILL.md:14`, `close/SKILL.md:68`) (no cuenta, por la decisión del usuario en `release-2.0.0`). Nada más.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **1 bloqueante, 3 sugerencias y 3 preguntas.** El usuario eligió arreglar las tres sugerencias y generalizar los detalles de R5 y R7.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | La guía citaba `README.md:87-88`, que con las líneas nuevas del README raíz ya no es la instalación `local`. | Arreglado sin preguntar: `README.md:90-91`. |
| R2 | suggestion | `run_tests.py:473-496` incluía dos líneas en blanco. | Arreglado: `:473-494`. |
| R3 | suggestion | La fila "Worktrees" del README raíz prometía el `.venv` sin condición. | Arreglado: "if `Lint/format` uses one". |
| R4 | suggestion | "Exit 1 stops here:" de §2.2 se leía como lista completa. | Arreglado: "for example:" y el caso del nombre que normalizado queda vacío. |
| R5 | question | ¿El servicio y el puerto de la verificación del origen cuentan para la regla 6? | El usuario eligió generalizarlos: `<folder-a>-<service>-1`, `<port>:<port>`, "a port the image `EXPOSE`s". |
| R6 | question | CA-13 fijaba `README.md:87-88`. | El usuario eligió actualizar CA-13 a `:90-91`. |
| R7 | question | Los textos del ejemplo de merge salían del repo de prueba del origen. | El usuario eligió un ejemplo inventado. En la segunda pasada salió incompleto (describía un conflicto de texto); con la decisión del usuario se cambió por un ejemplo sin conflicto (un default cambiado y una llamada nueva en otro archivo), sin otra pasada. |

- **Pasada sobre los arreglos:** R1 a R6 `fixed`; R7 incompleto, corregido con la decisión del usuario, como se dice arriba. Sin bloqueantes nuevos.
- **Deuda:** ninguna.
- **Huella:** sha256:d8b710be20d1140364aa1452da8b828df9ad09606f22a32bd69d0fda39ae3831

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.1.0/step-3.md`.
