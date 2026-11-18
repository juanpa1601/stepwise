# Decisiones y Reglas de Negocio: release-2.0.0

- **Fecha:** 2026-11-17
- **Tipo:** feature
- **Rama Principal:** `release-2.0.0`
- **Fuente / Documento:** [prompt de `/spec`](../../prompts/release-2.0.0/2026-11-17-spec.md).

---

## 1. Contexto y Objetivo
En `stepwise` `1.1.0`, `/check` corre siempre `Tests (full)` (`plugins/stepwise/skills/check/SKILL.md:29`), y `/close` la vuelve a correr si la huella cambió después de `/check` (`plugins/stepwise/skills/close/SKILL.md:55`). Eso pasa a menudo, porque `/audit self` aplica arreglos antes del commit. Con una suite de 20 o 30 minutos son hasta dos corridas completas por paso. Además, una suite así no cabe en los 570 s de `run_tests.py` en primer plano (`plugins/stepwise/README.md:36`).

El objetivo es publicar `2.0.0`:
- `/check` y `/close` corren solo los tests del paso.
- Una skill nueva, `/regression`, corre la suite completa una vez, en segundo plano, sobre `<feature>` con todos los pasos mergeados. Es la única que saca el PR principal de draft.

## 2. Criterios de Aceptación
Los CA de texto de skill se comprueban leyendo la `SKILL.md` contra el CA. El comportamiento real de punta a punta lo cubre CA-19.

**Paso 1: tests del paso en `/implement`, `/check`, `/close` y `/audit`**
- **CA-1 (manual: texto de skill):** Dado un paso con CA cubiertos por tests, cuando `/implement` termina, entonces la trazabilidad tiene `## Pruebas` → `### Tests del paso`, antes de `### Verificación manual`, con las rutas o ids que pasó a `test-runner step`, uno por línea. Si no hay ninguno, dice `ninguno`. El reporte trae `Step tests: <N> in "Tests del paso" of <archivo> | ninguno`.
- **CA-2 (manual: texto de skill):** Dado `### Tests del paso` con rutas, cuando corre `/check`, entonces delega `stepwise:test-runner step <esas rutas>`, nunca `full`, y escribe `- **Tests del paso (\`Tests (step)\`):**` con el comando y los totales. Un arreglo de `/check` que crea o modifica un test lo agrega a la lista antes de volver a correr.
- **CA-3 (manual: texto de skill):** Dado `ninguno`, cuando corre `/check`, entonces no llama a `test-runner`, anota `sin tests del paso` y corre igual `Migrations check`, `Lint/format` y `Type check`.
- **CA-4 (manual: texto de skill):** Dada una trazabilidad sin `### Tests del paso` (un paso de una versión anterior), cuando corre `/check`, entonces arma la lista con los archivos de test entre los cambios del paso, la muestra, pide confirmación antes de correr nada y la escribe. Si la lista existe y le falta un archivo de test del paso, avisa y pregunta.
- **CA-5 (manual: texto de skill):** Dado un paso cuya huella cambió después de `/check`, cuando corre `/close`, entonces agrega a la lista los tests que crearon o modificaron los arreglos de la revisión y vuelve a correr `test-runner step` con la lista (no `full`). El merge exige esos tests en verde, o `sin tests del paso`, o `Tests (step): none`. `/close` deja de pedir la clave `Tests (full)`. Exige la línea `Tests del paso` de `/check` (o la `Suite completa` de un `/check` anterior) y `### Tests del paso`.
- **CA-6 (manual: texto de skill):** Dado el último paso del ADR, cuando corre `/close`, entonces escribe la descripción del PR principal, con "Verificación Global" en `pendiente de /regression`, y pregunta antes de aplicarla. No corre ni ofrece `gh pr ready`, aunque se lo pidan, y el reporte termina con `next: /regression`.
- **CA-7:** Dados los `plugins/stepwise/skills/*/SKILL.md`, cuando corre la suite, entonces un test nuevo en `tests/` falla, con `ruta:línea`, si una `SKILL.md` distinta de `skills/regression/SKILL.md` delega `"full"` a `test-runner` (con comillas dobles, simples o backticks), invoca `run_tests.py` con `full` o contiene `gh pr ready`.
- **CA-8:** Dado el paso 1 hecho, cuando corre `Tests (full)`, entonces pasa con `step-tests` entre los ids exigidos de `tests/test_shared_blocks.py`, en `check` y `close`, y con `2.0.0` en `plugin.json` y en `tests/test_plugin_version.py:257`.

**Paso 2: skill `/regression`**
- **CA-9 (manual: texto de skill):** Dada cualquiera de estas situaciones, cuando corre `/regression`, entonces se detiene sin correr nada y dice qué falta:
  - la rama no es `<feature>` (por ejemplo, una `-step-<n>`);
  - hay cambios en archivos con seguimiento;
  - `<feature>` no está al día con `origin/<feature>` (con el `gh api` de respaldo);
  - un paso del ADR no está marcado en el PR principal (sin GitHub: una `<feature>-step-<k>` que no es ancestro de `<feature>`).
- **CA-10 (manual: texto de skill):** Dadas las precondiciones cumplidas, cuando corre `/regression`, entonces la sesión principal, no `test-runner`, lanza `python3 "<plugin>/scripts/run_tests.py" full --timeout 3600` con `run_in_background`, una sola vez. Espera el aviso sin `sleep`, polling ni otro trabajo, y lee el reporte con `tail -n 20`.
- **CA-11 (manual: texto de skill):** Dada la suite en verde, cuando corre `/regression`, entonces escribe `regression.md` en la carpeta de `Traceability` con la fecha, el commit probado, el comando, los totales y `Ejecutó`. Hace el commit `docs(<feature>): add regression run`, solo con ese archivo, y el push. Propone "Verificación Global" y pregunta antes de `gh pr edit`. Pregunta de nuevo antes de `gh pr ready`, solo si `origin/<feature>` es el commit de `regression.md`.
- **CA-12 (manual: texto de skill):** Dado un `- [ ] Verificación después del merge (...)` sin marcar o una "Verificación de instalación" con placeholders, cuando `/regression` termina en verde, entonces no ofrece `gh pr ready` y deja el PR en draft. Solo con una decisión explícita del usuario lo marca ready, y la decisión queda en `regression.md`.
- **CA-13 (manual: texto de skill):** Dado `timeout after 3600 s`, o un segundo plano que no se puede lanzar o no avisa, cuando corre `/regression`, entonces no es un fallo: da el comando exacto de `Tests (full)`, termina el turno y registra lo que pegue el usuario con `Ejecutó: usuario`.
- **CA-14 (manual: texto de skill):** Dada la suite en rojo, cuando corre `/regression`, entonces no edita nada, no hace commit y no marca ready. Reporta en 10 líneas como máximo los fallos, la causa probable y el paso que la introdujo (por `git log`), y da la línea `/stepwise:spec <feature> Paso de corrección: ...`. Si un fallo parece de `Base branch`, pregunta si se deja, y solo sigue en verde si el usuario vio todos los fallos.
- **CA-15:** Dado `skills/regression/SKILL.md`, cuando corre la suite, entonces el test de CA-7 también falla en cualquiera de estos casos:
  - la skill no existe;
  - no invoca `run_tests.py" full --timeout 3600`;
  - no menciona `run_in_background`;
  - no contiene `gh pr ready`;
  - delega `"full"` a `test-runner`.
- **CA-16 (manual: plantilla):** Dada `close/references/main-pr-template.md`, cuando se lee, entonces "Verificación Global" trae el comando, los totales, `Ejecutó` y el enlace a `regression.md`, y "Checklist de Entrega" dice `Suite completa en verde (/regression, ...)`. `step-pr-template.md` dice que la suite completa la corre `/regression`.

**Paso 3: documentación y sesión real**
- **CA-17 (manual: documentación):** Dados `plugins/stepwise/README.md`, `README.md`, `plugin.json` y `CHANGELOG.md`, cuando se leen, entonces:
  - describen el flujo nuevo, con la entrada de `skills/regression/`;
  - "Hoy" de bloques compartidos dice `step-tests` (check, close), y `project-commands`, `git-rules` y `push-https` con `regression`;
  - `README.md` tiene la etapa de regresión en la tabla y "Verify" corre los tests del paso;
  - la descripción de `plugin.json` nombra `regression`;
  - `[Unreleased]` trae `Added` y `Changed` (mayor), con lo que pasa con una feature en curso.
- **CA-18 (manual: documentación):** Dada `docs/migration-template.md`, cuando se lee, entonces P1 ya no dice que una suite de más de 570 s frena (`:36`): la corre `/regression` en segundo plano. Las reglas de la sesión (`:68-70`) nombran `/stepwise:regression` como la etapa que saca el PR principal de draft.
- **CA-19 (manual: sesión real con `claude --plugin-dir`, solo la corre el usuario):** Dado un repo desechable en GitHub con una feature de dos pasos y una suite de más de 600 s (un test con `sleep`), cuando se corre el flujo completo con el plugin de la rama, entonces:
  - `/check` y `/close` corren solo los tests de cada paso;
  - el último `/close` deja el PR en draft;
  - `/regression` corre la suite en segundo plano sin el corte de 600 s, recibe el aviso, escribe `regression.md` y saca el PR de draft con aprobación.
  La trazabilidad anota qué hace `claude -p` con la espera.

**Todos los pasos**
- **CA-20:** Dado cada paso hecho, cuando corre `Tests (full)`, entonces pasa.
- **CA-21 (manual: revisión del diff):** Dado el diff de cada paso, cuando se busca con la lista de términos de la regla 1, entonces no aparece ninguno. Un hallazgo es un `blocker`.

## 3. Reglas de Negocio Clave
1. **Saneamiento** (usuario, no negociable): igual que en `release-1.1.0`. Nada nombra el repo de origen, su organización, sus proyectos, sus PR, sus ADR, rutas locales ni personas, tampoco en docstrings ni tests. Las fuentes y los términos están en la memoria privada de Claude, fuera del repo.
2. **Tests del paso:** los creados o modificados en el paso.
   - **Quién escribe la lista:** `/implement`. `/check` la arma si falta y la amplía con sus arreglos; `/audit self` y `/close`, con los de la revisión.
   - **Qué reemplaza `/check`:** solo la lista de `## Pruebas`. Conserva `### Tests del paso` y `### Verificación manual`.
   - **El texto:** la instrucción de correrla es un bloque compartido nuevo, `step-tests`, en `check` y `close`.
3. **`Tests (full)` y `gh pr ready` solo en `/regression`:** `/check` y `/close` dejan de pedir `Tests (full)`. El ejemplo de alineación de `check` deja de nombrar `gh pr ready`, porque el test de CA-7 lo rechaza.
4. **Ready:** solo desde `/regression`, con la suite en verde (o con fallos preexistentes que el usuario decidió dejar, o con `Tests (full): none`), sin verificaciones "después del merge" sin marcar y con el mismo commit. Pregunta antes de cada `gh pr edit` y de `gh pr ready`.
5. **Nunca se corrige en `<feature>`:** un fallo termina en un paso de corrección con `/spec`.
6. **Segundo plano:**
   - **Desde la sesión principal**, con un `--timeout 3600` fijo, sin clave nueva.
   - **No pasa por `test-runner`:** a un subagente no le llega el aviso de un proceso en segundo plano.
   - **`run_tests.py` no cambia:** ya acepta cualquier `--timeout`.
   - **Respaldo manual:** solo con un timeout o cuando no hay segundo plano.
7. **Registro:** `<carpeta de Traceability>/regression.md`, con un commit directo en `<feature>`. Cada corrida en verde lo reemplaza; una en rojo no lo escribe.
8. **Bloques de `/regression`:** copia `project-commands`, `git-rules` y `push-https`, no `test-runner-foreground`.
9. **Versión `2.0.0`, mayor:** `/check` deja de correr la suite y `/close` deja de marcar ready, y los dos comportamientos son API pública (`plugins/stepwise/README.md:79-85`). La versión se sube una vez, en el paso 1, porque `tests/test_plugin_version.py` lo exige apenas cambia `plugins/stepwise/`.
10. **CHANGELOG:** en inglés y con el formato de `[1.1.0]`. Cada paso agrega su viñeta en `[Unreleased]`, que se renombra al publicar.
11. **Alcance de la documentación** (usuario): `README.md` y `docs/migration-template.md` se actualizan. El ADR `bootstrap` no se toca: es histórico.

## 4. Fuera de Alcance
- Cambiar `run_tests.py`, su timeout por defecto o los agentes.
- Elegir tests "afectados" por análisis de dependencias.
- Una clave para elegir entre el flujo viejo y el nuevo, o para configurar el timeout.
- CI.
- Reescribir los ADR y las trazabilidades de `bootstrap` y `release-1.1.0`.
- El tag `stepwise--v2.0.0`: se crea a mano después del merge del PR principal.

## 5. Solución y Trade-offs
- **Opción seleccionada:** traer el cambio con los nombres de stepwise y saneado, en 3 pasos, con las fuentes en la memoria privada.
- **Alternativa descartada:** correr la suite completa en un paso sin tests, o en la rama del último paso antes de su `/close`. Devuelve el costo, o no prueba el estado mergeado.
- **Trade-off aceptado:** una regresión que mete un paso intermedio se descubre al final, y arreglarla cuesta un paso nuevo con su ciclo completo.

## 6. Riesgos
- **Regresiones tardías:** `/regression` señala el paso probable con `git log`.
- **Lista incompleta:** `/check` compara la lista con los archivos de test del paso y avisa.
- **Segundo plano sin comprobar:** puede haber otro tope, y puede que `claude -p` no espere el aviso. CA-19 lo mide, y CA-13 cubre el caso.
- **Recursos del stack:** un `docker compose run` cortado deja su contenedor vivo, como hoy.
- **Features en curso al actualizar:** CA-4 cubre los pasos sin lista, y el último `/close` pide `/regression`.
- **Esta misma feature:** si el plugin instalado es anterior a `2.0.0`, `/stepwise:regression` no existe en la sesión, y se sigue a mano la `SKILL.md` de la rama.
- **Fuga al repo público:** CA-21 en cada paso.

## 7. Pasos de Implementación
1. **Paso 1: tests del paso** (CA-1 a CA-8, CA-20, CA-21):
   - `skills/implement/SKILL.md`, `skills/check/SKILL.md` y `skills/close/SKILL.md` (claves, §0.3, §2, merge, último paso y reporte);
   - `skills/audit/SKILL.md:43`, `close/references/step-pr-template.md` y el bloque `step-tests`;
   - `tests/test_full_suite_owner.py` (CA-7), `tests/test_shared_blocks.py`, `plugin.json` en `2.0.0`, `tests/test_plugin_version.py:257` y `CHANGELOG.md`.
2. **Paso 2: skill `/regression`** (CA-9 a CA-16, CA-20, CA-21): `skills/regression/SKILL.md`, `close/references/main-pr-template.md`, la parte de CA-15 del test y `CHANGELOG.md`.
3. **Paso 3: documentación y sesión real** (CA-17 a CA-21): `plugins/stepwise/README.md`, `README.md`, la descripción de `plugin.json`, `CHANGELOG.md`, `docs/migration-template.md` y la sesión de CA-19.

## 8. Decisiones Abiertas
Ninguna.
