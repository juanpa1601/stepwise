# [release-2.0.0] Paso 3: documentación y sesión real

- **Rama:** `release-2.0.0-step-3`
- **Rama Destino (Sub-PR):** `release-2.0.0`
- **PR Principal:** `release-2.0.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.0.0/business-rules.md`

---

## 1. Resumen del Paso
La documentación describe el flujo de `2.0.0`: `/check` y `/close` corren los tests del paso, y `/regression` corre la suite completa en segundo plano sobre la rama de la feature y es lo único que saca el PR principal de draft. El README del plugin suma la entrada de `skills/regression/` y deja al día las de `implement`, `check`, `close` y `audit`, el timeout, los bloques compartidos, los proyectos sin tests y el Versionado. El README raíz suma la etapa "Regression", `plugin.json` la nombra y el CHANGELOG cierra `[Unreleased]`. La plantilla de migración deja de frenar con una suite larga y cierra la migración con `/stepwise:regression`. Cubre CA-17, CA-18, CA-20 y CA-21; CA-19 (sesión real) queda pendiente del usuario.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/README.md`: entradas de `implement`, `check`, `audit self` y `close`; la entrada nueva de `regression`; huella de código, timeout y límite de 570 s, tests encadenados, rama del paso, bloques compartidos, proyectos sin tests, lista de tests, versión `2.0.0` y el recordatorio de la versión.
- `README.md`: el flujo con `regression`, las filas "Implement", "Verify" y "Close", la fila nueva "Regression" y `Docs paths`.
- `plugins/stepwise/.claude-plugin/plugin.json`: la `description` nombra `regression`.
- `CHANGELOG.md`: la viñeta "Major" dice qué pasa con una feature en curso al actualizar.
- `docs/migration-template.md`: P1 (suite de más de 570 s), las reglas de la sesión, R3 (`/regression` en el `CLAUDE.md` del proyecto) y R4 (cierre con `/stepwise:regression`, con su aclaración).
- `docs/decisions/release-2.0.0/business-rules.md`: CA-18 incluye R3 y R4 de la plantilla.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| El README del plugin sigue el texto de la versión de origen, sin sus referencias a ADR ni casos de proyectos. | Regla 1 (saneamiento). Se suman los arreglos de las revisiones de los pasos 2 y 3. |
| CA-18 se amplía con R3 y R4 de la plantilla. | Decisión del usuario en `/audit self`: un proyecto migrado necesita `/regression` para sacar el PR principal de draft. |
| El ítem 4 de R4 de la plantilla se aclara como etapa, no como CA. | Decisión del usuario: como verificación `después del merge`, trabaría el ready de `/regression`. |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 plugins/stepwise/scripts/run_tests.py full`: 164 total, 0 failed, 0 errors, 1 skipped, en 135.966s.
  - `python3 -m unittest discover plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped in 53.285s
  - `python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped in 35.998s
  - `python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped in 4.086s
  - `python3 -m unittest discover plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped in 32.828s
  - `python3 -m unittest discover tests`: 41 total, 0 failed, 0 errors, 0 skipped in 9.769s
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 4 CA, 4 ok (CA-19 confirmado por el usuario), 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R1 a R6).
- **Huella:** sha256:f202804cf0db79fa7089ad87a3240eae74fe543f3f5a5c182b7afec4a3ce0865

### Tests del paso
ninguno

El paso solo toca documentación y la descripción de `plugin.json`. `/implement` corrió además, como chequeo, `tests/test_plugin_version.py`, `tests/test_path_lengths.py` y `tests/test_full_suite_owner.py` (27 total, 0 failed), sin modificarlos.

### Verificación manual
- **CA-17:** el README del plugin, el README raíz, `plugin.json` y el CHANGELOG describen el flujo nuevo.
  - Pasos: 1. Leer `plugins/stepwise/README.md:16-27`, `:40`, `:51`, `:66`, `:69`, `:78`, `:81`, `:91`. 2. Leer `README.md:8-20` y `:73`. 3. Leer la `description` de `plugins/stepwise/.claude-plugin/plugin.json`. 4. Leer `[Unreleased]` de `CHANGELOG.md`.
  - Esperado: el texto de CA-17.
  - Obtenido: `implement` (`:16`) anota `### Tests del paso`; `check` (`:17`) corre solo esa lista y la arma si falta; `close` (`:23`) vuelve a correr los tests del paso y deja el PR en draft con `next: /regression`; la entrada nueva `skills/regression/` (`:24-27`) describe la corrida en segundo plano, el verde y el rojo; `:40` deja los 570 s para `test-runner` y la suite para `/regression`; "Hoy" (`:51`) dice `step-tests` (check, close) y `regression` en `project-commands`, `git-rules` y `push-https`; `:66` y `:69` cubren `Tests (full): none` y las verificaciones después del merge; `:81` dice `2.0.0`. Tras la revisión: `:19` agrega a la lista los tests de los arreglos de `/audit self` (R5), `:23` acepta la `Suite completa` de un `/check` anterior y no exige la subsección con `Tests (step): none` (R6), `:40` deja el límite de 570 s solo para los tests del paso (R2) y "El test" de Versionado dice que el recordatorio de la versión llega en `/regression`, o en `/check` si el paso lista `tests/test_plugin_version.py` (R1). `README.md` trae el flujo con `regression` (`:8-11`), "Verify" con los tests del paso y la fila "Regression" (`:20`). La `description` nombra `regression`. `[Unreleased]` tiene `### Added` (`/regression`) y `### Changed` ("Major", con lo que pasa con una feature en curso).
  - Ejecutó: Claude
- **CA-18:** la plantilla de migración ya no frena con una suite de más de 570 s y nombra `/stepwise:regression` en las reglas de la sesión.
  - Pasos: 1. Leer `docs/migration-template.md:37`, `:67`, `:70`, `:117` y `:124`.
  - Esperado: el texto de CA-18.
  - Obtenido: `:37` dice que una suite completa de más de 570 s no frena (la corre `/stepwise:regression` en segundo plano con `--timeout 3600`) y deja la pregunta para los tests de un paso; `:67` agrega `/stepwise:regression` a la cadena de comandos; `:70` dice que solo `/stepwise:regression` saca el PR principal de draft; `:117` pide `/regression` en el `CLAUDE.md` del proyecto (R3) y `:124` cierra la migración con `/stepwise:regression` (R4), que `:126` aclara que no es un CA del paso 4 ni una verificación `después del merge`.
  - Ejecutó: Claude
- **CA-19:** en una sesión real con el plugin de esta rama, `/check` y `/close` corren solo los tests de cada paso, el último `/close` deja el PR en draft y `/regression` corre la suite en segundo plano más allá de 600 s, recibe el aviso, escribe `regression.md` y saca el PR de draft con aprobación; en `claude -p` queda registrado qué pasa con la espera del aviso.
  - Pasos:
    1. Crear un repo desechable en GitHub con `main` y un `CLAUDE.md` con `## Project commands`: `Tests (step): python3 -m unittest`, `Tests (full): python3 -m unittest discover tests`, `Lint/format`, `Type check` y `Migrations check` en `none`, `Base branch: main`, `Decision docs: docs/decisions/<feature>/business-rules.md`, `Traceability: docs/pull-requests/<feature>/step-<n>.md`. Agregar `tests/test_slow.py` con `time.sleep(660)`, para que la suite completa pase de 600 s.
    2. Con este repo en la rama `release-2.0.0-step-3`, abrir en el repo desechable una sesión interactiva con `claude --plugin-dir <ruta a este repo>/plugins/stepwise`.
    3. Correr `/stepwise:spec` con una feature chica de dos pasos y, para cada paso, `/stepwise:implement <n>`, `/stepwise:check` y `/stepwise:close`. Comprobar que `/check` y `/close` delegan `test-runner step <lista>` y nunca `full`, y que el último `/close` deja el PR en draft y termina con `next: /regression`.
    4. En `<feature>`, correr `/stepwise:regression`. Comprobar que lanza `run_tests.py full --timeout 3600` en segundo plano desde la sesión principal, que la suite pasa de 600 s sin cortarse, que recibe el aviso, que escribe `regression.md` con su commit y que pregunta antes de editar el cuerpo y antes de `gh pr ready`.
    5. Repetir el paso 4 con `claude -p "/stepwise:regression" --plugin-dir <ruta a este repo>/plugins/stepwise` (por ejemplo, después de un commit vacío en `<feature>` que exija una corrida nueva) y anotar si la sesión espera el aviso o termina antes; si termina antes, comprobar que el respaldo manual da el comando de `Tests (full)`.
  - Esperado: el texto de CA-19.
  - Obtenido: ok, confirmado por el usuario el 2026-11-18 (sin más detalle en la confirmación).
  - Ejecutó: usuario
- **CA-21:** el diff del paso no trae ningún término de la lista de saneamiento.
  - Pasos: 1. Buscar los términos de la regla 1 (sin distinguir mayúsculas, también rutas locales con `/`) en las líneas agregadas de `git diff release-2.0.0`.
  - Esperado: ninguna coincidencia, salvo texto genérico que ya está en `main` (CA-21).
  - Obtenido: sin coincidencias.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **1 bloqueante y 5 sugerencias.** El usuario eligió arreglar las 5 sugerencias y ampliar CA-18 para R3 y R4.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | "El test" de Versionado decía que el `/check` de la primera feature falla hasta subir la versión; desde `2.0.0`, `/check` solo corre los tests del paso. | Arreglado sin preguntar: el recordatorio llega en `/regression`, o en `/check` si el paso lista `tests/test_plugin_version.py`. |
| R2 | suggestion | El "Límite" de 570 s contradecía la frase de `2.0.0`, y "lo pasan los tests" era ambiguo. | Arreglado: el límite es de los tests del paso en `test-runner`, y `--timeout` lo pasan los tests de `run_tests.py` y `/regression`. |
| R3 | suggestion | R3 de la plantilla de migración no pedía `/regression` en el `CLAUDE.md` del proyecto. | Arreglado, con CA-18 ampliado. |
| R4 | suggestion | R4 de la plantilla cerraba la migración con `/close`, sin `/regression`. | Arreglado en dos vueltas: el ítem 4 nuevo podía volverse un CA `después del merge` que trababa el ready; con la decisión del usuario, `:126` aclara que es la etapa que sigue al último `/close`. |
| R5 | suggestion | La entrada de `audit self` no decía que los tests de sus arreglos entran en la lista. | Arreglado. |
| R6 | suggestion | La entrada de `close` no decía que acepta la `Suite completa` de un `/check` anterior ni la excepción de `Tests (step): none`. | Arreglado. |

- **Pasada sobre los arreglos:** R1, R2, R3, R5 y R6 `fixed`; R4 incompleto (el bloqueo con las verificaciones después del merge). El usuario eligió aclararlo en la plantilla, y una revisión solo de ese arreglo lo dio `fixed`, sin bloqueantes nuevos. La pasada encontró además R7: los "Pasos" de CA-17 no listan `plugins/stepwise/README.md:91`, que su "Obtenido" cita.
- **Deuda:** R7 (sugerencia nueva de la segunda pasada; no se arregla sin revisión). Resuelta después de la publicación de `2.0.0` (2026-11-18, a pedido del usuario): los "Pasos" de CA-17 listan `plugins/stepwise/README.md:91`.
- **Huella:** sha256:f202804cf0db79fa7089ad87a3240eae74fe543f3f5a5c182b7afec4a3ce0865

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`. — La lista es `ninguno` (solo documentación); CA-19 confirmado por el usuario.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.0.0/step-3.md`.
