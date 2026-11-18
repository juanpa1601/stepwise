# [release-2.0.0] Paso 2: skill /regression

- **Rama:** `release-2.0.0-step-2`
- **Rama Destino (Sub-PR):** `release-2.0.0`
- **PR Principal:** `release-2.0.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.0.0/business-rules.md`

---

## 1. Resumen del Paso
Skill nueva `/regression`: corre `Tests (full)` una vez sobre `<feature>` con todos los pasos mergeados, en segundo plano desde la sesión principal (`run_tests.py full --timeout 3600`, con respaldo manual), y es la única que saca el PR principal de draft. En verde escribe `regression.md`, hace commit y push, y pregunta antes de editar el PR y antes de `gh pr ready`; en rojo no arregla nada y da la línea `/stepwise:spec` de un paso de corrección. La plantilla del PR principal toma su corrida, y el test de CA-7 comprueba la skill nueva. Cubre CA-9 a CA-16, CA-20 y CA-21.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/skills/regression/SKILL.md` (nuevo): la skill, con los bloques compartidos `project-commands`, `git-rules` y `push-https`.
- `plugins/stepwise/skills/close/references/main-pr-template.md`: "Verificación Global" con la corrida de `/regression` y su enlace, y el ítem de la suite en "Checklist de Entrega".
- `tests/test_full_suite_owner.py`: `owner_problems` y sus casos, y el test del repo de CA-15.
- `CHANGELOG.md`: la viñeta de `/regression` en `### Added` de `[Unreleased]`.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| La skill es el texto de la versión de origen, con los nombres de stepwise, más los arreglos de la revisión (R1, R3 y R4). | El ADR elige traer el cambio sin reescribirlo (§5); los arreglos cubren huecos que la revisión encontró contra CA-11, CA-12 y CA-16. |
| El ejemplo de ruta con `/` de §1.4 queda tal cual. | Es el mismo texto de `agents/test-runner.md:32` en `main`: texto genérico que CA-21 excluye. |
| Antes de escribir `regression.md`, la skill comprueba que `origin/<feature>` sigue en el commit probado. | Decisión del usuario en R4: evita un commit local que haría detenerse a la corrida siguiente. |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 plugins/stepwise/scripts/run_tests.py full`: 164 total, 0 failed, 0 errors, 1 skipped, en 95.622s.
  - `python3 -m unittest discover plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped in 40.490s
  - `python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped in 26.439s
  - `python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped in 2.545s
  - `python3 -m unittest discover plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped in 20.810s
  - `python3 -m unittest discover tests`: 41 total, 0 failed, 0 errors, 0 skipped in 5.338s
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 8 CA, 8 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R1 a R5).
- **Huella:** sha256:03f8c7dd758e35d57356630811058544c5162f21ffe9772bacd1a02ac8fe1e18

### Tests del paso
- `tests/test_full_suite_owner.py`

`/implement` corrió además `tests/test_shared_blocks.py` (la skill nueva copia tres bloques compartidos) y `tests/test_path_lengths.py` (la ruta nueva), sin modificarlos: no son tests del paso (regla 2 del ADR), y la suite completa los cubre.

### Verificación manual
- **CA-9:** `/regression` se detiene sin correr nada si la rama no es `<feature>`, el árbol tiene cambios, `<feature>` no está al día o falta un paso mergeado.
  - Pasos: 1. Leer `plugins/stepwise/skills/regression/SKILL.md:26-34` (§0.2 a §0.7).
  - Esperado: el texto de CA-9.
  - Obtenido: `:26` exige `<feature>` y en una rama `-step-<n>` se detiene y pide correrla en `<feature>`; `:27` se detiene con cambios en archivos con seguimiento; `:28` compara con `origin/<feature>` (con `gh api` de respaldo) y se detiene si difieren o no se puede confirmar; `:31-34` exige cada paso marcado en el PR principal o, sin GitHub, cada `<feature>-step-<k>` ancestro de `<feature>`, y lista los que faltan.
  - Ejecutó: Claude
- **CA-10:** la sesión principal lanza `run_tests.py full --timeout 3600` con `run_in_background` una vez, espera el aviso sin `sleep` ni polling y lee el reporte con `tail -n 20`.
  - Pasos: 1. Leer `regression/SKILL.md:40-45`.
  - Esperado: el texto de CA-10.
  - Obtenido: `:40` "Do not delegate it to `stepwise:test-runner`", con `run_in_background: true`, "exactly once", y el comando `python3 "<this skill's directory>/../../scripts/run_tests.py" full --timeout 3600` (desde `skills/regression/` llega a `plugins/stepwise/scripts/`); `:45` espera el aviso sin segunda copia, `sleep`, polling ni otro trabajo, y lee con `tail -n 20`.
  - Ejecutó: Claude
- **CA-11:** en verde escribe `regression.md`, hace commit solo de ese archivo y push, propone "Verificación Global" y pregunta antes de `gh pr edit`, y pregunta antes de `gh pr ready` solo con el mismo commit.
  - Pasos: 1. Leer `regression/SKILL.md:38`, `:63-88`.
  - Esperado: el texto de CA-11.
  - Obtenido: `:38` toma el commit probado antes de todo (desde R3, también con `Tests (full): none`); `:63` (R4) comprueba que `origin/<feature>` sigue en el commit probado antes de escribir nada, y si avanzó se detiene sin escribir ni hacer commit; `:64-75` es la plantilla de `regression.md` (fecha, commit probado, comando, totales, `Ejecutó`); `:76` hace `git add` solo de ese archivo y `docs(<feature>): add regression run`; `:77` el push con el respaldo HTTPS, y `:81` (R4), si el push se rechaza igual, se detiene sin `pull` ni edición del PR y da `git reset --keep HEAD~1` para descartar el commit local; `:83` llena "Verificación Global" y pregunta antes de `gh pr edit`; `:84-88` pregunta antes de `gh pr ready` y exige que `origin/<feature>` sea el commit de `regression.md`.
  - Ejecutó: Claude
- **CA-12:** con una verificación después del merge sin marcar, o una "Verificación de instalación" con placeholders, no ofrece ready; solo con una decisión explícita, registrada en `regression.md`.
  - Pasos: 1. Leer `regression/SKILL.md:62`, `:84-89`.
  - Esperado: el texto de CA-12.
  - Obtenido: `:62` lista las casillas sin marcar; `:86-87` exige que no quede ninguna y que no haya placeholders en la sección de instalación; `:89` (desde R1, para los dos casos) deja el PR en draft y, solo con la decisión explícita del usuario, la anota en `regression.md` (`Ready sin confirmar`, con qué quedó sin confirmar), hace commit, push y vuelve a preguntar.
  - Ejecutó: Claude
- **CA-13:** con `timeout after 3600 s`, o sin segundo plano o sin aviso, da el comando de `Tests (full)`, termina el turno y registra `Ejecutó: usuario`.
  - Pasos: 1. Leer `regression/SKILL.md:46`.
  - Esperado: el texto de CA-13.
  - Obtenido: `:46` "Manual fallback (not a failure, costs nothing)" en los tres casos: da el comando exacto, pide los totales y fallos, "end the turn", y lo registra con `Ejecutó: usuario`.
  - Ejecutó: Claude
- **CA-14:** en rojo no edita, no hace commit ni ready; reporta en 10 líneas los fallos, la causa y el paso, con la línea `/stepwise:spec`; pregunta por los fallos que parecen de `Base branch`.
  - Pasos: 1. Leer `regression/SKILL.md:49-58`.
  - Esperado: el texto de CA-14.
  - Obtenido: `:51` no cambia nada; `:52` busca el paso con `git log`; `:53` pregunta por un fallo preexistente y solo sigue en verde si el usuario vio todos (`failed + errors`); `:54-58` reporta en 10 líneas como máximo con la línea `/stepwise:spec <feature> Paso de corrección: ...`.
  - Ejecutó: Claude
- **CA-16:** las plantillas de PR nombran a `/regression`.
  - Pasos: 1. Leer `plugins/stepwise/skills/close/references/main-pr-template.md:22-25`, `:34` y `step-pr-template.md:33`.
  - Esperado: el texto de CA-16.
  - Obtenido: "Verificación Global" trae comando, totales, `Ejecutó` y `Registro:` con un enlace Markdown a `regression.md` en la rama de la feature (R2), con el comentario de `pendiente de /regression`; "Checklist de Entrega" dice `Suite completa en verde (/regression, ...)`; `step-pr-template.md:33` dice "La suite completa la corre `/regression`" (desde el paso 1).
  - Ejecutó: Claude
- **CA-21:** el diff del paso no trae ningún término de la lista de saneamiento.
  - Pasos: 1. Buscar los términos de la regla 1 (sin distinguir mayúsculas, también rutas locales con `/`) en las líneas agregadas de `git diff release-2.0.0` y en los archivos nuevos.
  - Esperado: ninguna coincidencia, salvo texto genérico que ya está en `main` (CA-21).
  - Obtenido: sin coincidencias. Las dos que salen son texto genérico de `main`: el ejemplo de ruta con `/` de `regression/SKILL.md:45`, igual al de `agents/test-runner.md:32`, y la frase del directorio temporal de la sesión de `:76`, igual a la de `audit` y `close`.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **1 bloqueante y 4 sugerencias.** El usuario eligió arreglar las 4 sugerencias.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | blocker | `/regression` §3.7 no trataba la sección de instalación con placeholders: CA-12 pide que solo una decisión explícita, registrada en `regression.md`, saque el PR de draft también en ese caso. | Arreglado sin preguntar: §3.7 cubre los dos casos y registra `Ready sin confirmar` con lo que quedó sin confirmar. |
| R2 | suggestion | `Registro:` de la plantilla del PR principal era una ruta, no un enlace (CA-16). | Arreglado: enlace Markdown a `regression.md` en la rama de la feature. |
| R3 | suggestion | Con `Tests (full): none`, §1 saltaba a §3 sin tomar el commit probado que pide la plantilla. | Arreglado: §1.1 toma el commit antes del caso `none`. |
| R4 | suggestion | Si el push de `regression.md` se rechaza porque `origin/<feature>` avanzó durante la corrida, la skill no decía qué hacer. | Arreglado en dos vueltas: la primera dejaba un commit local que hacía que la siguiente corrida se detuviera en §0.4; con la decisión del usuario, §3.2 comprueba antes de escribir y §3.4 da `git reset --keep HEAD~1` si el push se rechaza igual. |
| R5 | suggestion | `### Tests del paso` listaba dos tests que el paso no modifica (regla 2). | Arreglado: queda `tests/test_full_suite_owner.py`, con una nota sobre los otros dos. |

- **Pasada sobre los arreglos:** R1, R2, R3 y R5 `fixed`; R4 `incomplete` (el bucle con §0.4). El usuario eligió comprobar antes de escribir, y una revisión solo de ese arreglo lo dio `fixed`, sin bloqueantes nuevos.
- **Deuda:** ninguna.
- **Huella:** sha256:03f8c7dd758e35d57356630811058544c5162f21ffe9772bacd1a02ac8fe1e18

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.0.0/step-2.md`.
