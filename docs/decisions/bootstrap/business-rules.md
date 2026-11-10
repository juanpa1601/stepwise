# Decisiones y Reglas de Negocio: bootstrap

- **Rama Principal:** `main`
- **Alcance:** el diseño del plugin `stepwise`: el flujo, los agentes, los hooks, el contrato con cada proyecto y la distribución.

---

## 1. Contexto y Objetivo
Este repo es **un solo flujo de desarrollo con Claude Code**, que se instala en cada proyecto. Solo Claude Code: no se escribe nada para otras herramientas de IA.

No hay reglas ni guías por framework. Lo propio de cada proyecto (arquitectura, convenciones, comandos) vive en el `CLAUDE.md` de ese proyecto.

## 2. Criterios de Aceptación (Express)
- [ ] **Escenario 1:** Dado un proyecto con `## Project commands` en su `CLAUDE.md` y el plugin `stepwise` instalado, cuando el equipo hace una feature, entonces recorre `/spec` → (`/implement`, `/check`, `/close`, que corre `/audit self`) por paso sin pasos manuales fuera del flujo.
- [ ] **Escenario 2:** Dado un proyecto sin `## Project commands` o con una clave faltante, cuando una skill o un agente la necesita, entonces se detiene antes de ejecutar nada y propone la línea exacta.
- [ ] **Escenario 3:** Dado cualquier modo de `/audit`, cuando hay algo que publicar en GitHub, entonces no se publica sin aprobación del usuario.

## 3. Reglas de Negocio Clave
1. **Metodología.** Un ADR por feature y N pasos; un fix chico es una feature de un solo paso. Cada paso recorre **implement → check → audit self → close**.

   | Etapa | Skill | Qué hace |
   |---|---|---|
   | a. Planeación | `/spec` | Entrevista al usuario sobre una feature, un bug o un paso nuevo. Investiga con `explore` y escribe el ADR en `Decision docs` (criterios `CA-n` en Dado / Cuando / Entonces y lista de pasos). Con aprobación, crea la rama `<feature>`, hace commit del ADR y abre el PR principal en draft. Nunca escribe código |
   | b. Implementación | `/implement <n>` | Crea `<feature>-step-<n>`. Por cada CA del paso, test primero (en un bug, con la evidencia de que el CA de regresión falla antes del arreglo) y luego el código; corre los tests del paso con `test-runner`. Sin commit |
   | c. Verificación | `/check` | Corre la suite completa, `Migrations check`, `Lint/format` y `Type check`. Si algo falla, arregla lo del paso y vuelve a correr (3 intentos), con `Lint/format` y `Type check` después de cada arreglo; si sigue fallando, se detiene con el diagnóstico. Escribe la sección "Pruebas" del `step-<n>.md` con la huella del paso |
   | Review | `/audit` | Tres modos: `self` (el diff del paso antes de cerrar; lo corre `/close`), `comments [<num>]` (trae los comentarios sin resolver del PR con `gh`, los verifica contra el código, los clasifica y, con aprobación, los convierte en un paso "Atender review" del ADR o en una feature nueva) y `pr <num>` (revisa el PR de otra persona y redacta los comentarios). Nunca publica nada en GitHub sin aprobación |
   | d. Cierre | `/close` | `/audit self` (salvo que la última ronda tenga la misma huella), la suite y los demás chequeos otra vez si la huella cambió desde `/check`, trazabilidad del paso, commit, push, Sub-PR con `--merge` y checklist del PR principal. En el último paso, también la descripción del PR principal: la muestra y pide aprobación antes de aplicarla y antes de sacar el PR de draft |

   **Nombres:** `/plan` es un comando integrado (modo plan), `/verify` una skill incluida y `/review` un alias de `/code-review` en Claude Code. Sin el prefijo `stepwise:` abren la de Claude Code, así que se llaman `/spec`, `/check` y `/audit`. `/implement` y `/close` no chocan. Cualquiera se puede invocar también como `/stepwise:<skill>`.

   **Rama del paso:** `/implement`, `/check`, `/audit` y `/close` interpretan la rama con `^(?P<feature>.+)-step-(?P<n>\d+)$`, tomando la última aparición de `-step-`: `multi-step-form-step-2` es la feature `multi-step-form` y el paso 2. Un nombre de feature que contiene `-step-` es válido.

   **Bugs:** antes del arreglo solo tiene que fallar el CA de regresión. Los demás CA pueden pasar desde el inicio; se registra cuáles pasaban en `## Evidencia de regresión`.

   **Rama al día:** `/spec` e `/implement` comprueban `<feature>` y `Base branch` con `git fetch` y, si falla y el remoto es GitHub, con `gh api`. Si tampoco se puede comprobar, se detienen y preguntan.

   **Hallazgos de `/audit self`:**
   - Corre sobre el diff local del paso, después de `/check` y **antes** del commit y del Sub-PR. Es automático dentro de `/close`. **Nunca se mergea un paso con un bloqueante abierto.**
   - **Bloqueante** (`blocker`: bug, falla de autorización, criterio de aceptación sin test, llamada externa dentro de una transacción…): se arregla en el mismo paso sin preguntar, se vuelven a correr los tests del paso y `code-reviewer` revisa solo esos arreglos, **una vez**. Si el arreglo exige cambiar el diseño, se detiene y vuelve al ADR.
   - **`blocker` nuevo en la pasada sobre los arreglos:** se detiene y le pregunta al usuario qué hacer. No se arregla sin revisión ni hay tercera pasada.
   - **Sugerencia** (`suggestion`): se le pregunta al usuario una sola vez, con selección múltiple, cuáles se arreglan ahora; el resto queda como deuda.
   - **Pregunta** (`question`): se le hace al usuario; si la respuesta cambia el ADR, se actualiza en el mismo paso.
   - **Registro:** la sección "Code review" del `step-<n>.md` lista lo encontrado, lo arreglado y la deuda con su motivo. No se publican comentarios en el Sub-PR. Si `## Code review` ya existe, se agrega `### Ronda <k> (<fecha>)` al final y se conservan las anteriores.
   - La revisión humana y la de herramientas como Copilot siguen ocurriendo sobre el PR principal; `/audit comments` atiende lo que dejen.

   **`/audit comments`:** ignora los hilos resueltos y no da por buena ninguna premisa: verifica cada comentario contra el código y lo clasifica en `válido`, `no aplica` o `requiere decisión`. Con el PR abierto, los válidos se vuelven un paso "Atender review" del ADR con un `CA-n` cada uno, y se sigue con `/implement <n>`. Con el PR mergeado, se propone `/spec` con una feature nueva. Las respuestas se publican y los hilos se resuelven solo con aprobación explícita y después del merge del arreglo, con el enlace al commit. Para saber si un comentario ya se atendió en otra feature, busca el ancla de su URL (`discussion_r<databaseId>`, `issuecomment-<id>`, `pullrequestreview-<id>`) en todos los ADR bajo `Decision docs`; si aparece en varios, pregunta.

   **`/audit pr <num>`:** el veredicto (`COMMENT`, `REQUEST_CHANGES` o `APPROVE`) lo elige el usuario; la skill nunca lo elige sola. El checkout local no existe para este modo: el único archivo local que se lee es el `CLAUDE.md` del proyecto, y los archivos del head se ubican con `gh api .../git/trees/<sha>?recursive=1` y se leen con `gh api repos/{owner}/{repo}/contents/{path}?ref=<sha> -H "Accept: application/vnd.github.raw"`. Nunca `fetch` ni `checkout`.

   **Publicar cualquier texto:** `/audit` nunca pasa un cuerpo por la línea de comandos. Escribe el JSON con Write en un archivo temporal fuera del repo y publica con `gh api -X POST ... --input <archivo>`, también las reviews. La respuesta en un hilo va a `pulls/{pr}/comments/{comment_id}/replies` con el `databaseId` (REST) del comentario raíz; un comentario general o una review se contestan en `issues/{pr}/comments`; resolver un hilo usa su `id` de GraphQL.

2. **Agentes.** Los subagentes no hablan con el usuario: lo interactivo va en skills y lo aislado o verboso, en agentes.

   | Agente | Modelo | Herramientas | Para qué |
   |---|---|---|---|
   | `explore` | Sonnet | Read, Grep, Glob | Investigar el código; conclusiones con `ruta:línea` |
   | `test-runner` | Haiku | Bash | Tests del paso o suite completa con `scripts/run_tests.py`; resumen de los fallos |
   | `code-reviewer` | Opus | Read, Grep, Glob, Bash (`git`, `gh`, solo lectura) | Revisa un diff con contexto limpio contra el ADR: bugs, tests que faltan, seguridad y convenciones. Hallazgos clasificados en bloqueante, sugerencia o pregunta. No edita |

   - **Limitación:** el campo `tools` de un subagente no restringe Bash por patrón: `Bash(git diff:*)` da Bash completo. El "solo lectura" de `code-reviewer` está en sus instrucciones; el freno real son los permisos de la sesión, que también aplican a subagentes. Por eso cada proyecto declara en su `.claude/settings.json` (versionado) al menos estas reglas `ask`:
     ```json
     { "permissions": { "ask": ["Bash(git push:*)", "Bash(git commit:*)", "Bash(gh pr comment:*)", "Bash(gh pr review:*)", "Bash(gh pr merge:*)", "Bash(gh pr edit:*)", "Bash(gh pr ready:*)", "Bash(gh api -X *)", "Bash(gh api * -X *)", "Bash(gh api * --method *)", "Bash(gh api * --input *)"] } }
     ```
     Las reglas de `gh api` existen porque `/audit` publica respuestas y reviews con `gh api -X POST` y resuelve hilos con `gh api graphql`, que esquivan `gh pr comment` y `gh pr review`. El freno principal es el hook `ask_gh_api_writes` (§3.3), que analiza los argumentos; las reglas quedan como respaldo de texto y cubren `-X`, `--method` e `--input` antes o después de la ruta. Un `-f` sin `-X` o una mutación de graphql solo los detecta el hook. Al revés, las reglas de `-X` y `--method` también preguntan en una lectura explícita (`gh api -X GET ... -f per_page=100`), que el hook deja pasar: es el costo del respaldo por texto. La fuente única de la lista es `plugins/stepwise/references/ask-rules.json`, y un test (`hooks/tests/test_ask_gh_api_writes.py`) comprueba que esa lista, la de este bloque y la de `.claude/settings.json` sean iguales.
     Se usa `ask` y no `deny`: `deny` bloquea sin preguntar, incluso en la sesión principal, y `/close` necesita hacer commit, push y merge. Con `ask` cada uno pide aprobación: si un subagente lo intenta, el usuario ve la petición y la niega.

3. **Hooks:**
   - `block_inplace_edits` (`Bash|PowerShell`): niega ediciones de archivos desde la shell y pide Edit o Write. Deja correr un `.py` dentro del proyecto que git lista (con seguimiento, o sin seguimiento y no ignorado), porque está en el diff, donde se revisa.
   - `block_env_access` (`Read|Grep|Glob|Edit|MultiEdit|Write|Bash|PowerShell`): niega `.env` y `.env.*`, salvo plantillas (`.example`, `.sample`, `.template`, `.dist`). En la shell niega cualquier comando que nombre uno, con o sin comillas y en cualquier ruta. También niega `cp .env.example .env`, igual que Write niega crear `.env`: esa copia la hace el usuario. Cubre los comodines (`.env*`), `@.env` y `.env:/ruta`.
   - **Falsos positivos aceptados:** como lee el texto completo, niega también un comando que solo menciona el nombre (`git commit -m "... .env ..."`, un `--title` de `gh pr create`, `grep '\.env'`). Mensajes, títulos y cuerpos van por archivo (`git commit -F`, `--body-file`) o sin el nombre literal. `/close` usa siempre `git commit -F <archivo>` y `--body-file`, con el archivo temporal fuera del repo.
   - `ask_gh_api_writes` (`Bash|PowerShell`): responde `ask` ante un `gh api` que escribe, con el método y la ruta en el motivo. No ve un `gh api` armado en tiempo de ejecución ni dentro de `sh -c`. En modo `dontAsk`, un `ask` se deniega.
   - **Límite:** es una barrera contra errores, no un límite de seguridad. Un script que lee `.env` por dentro (`python manage.py runserver`, `docker compose up`) no se detecta, ni un nombre armado en tiempo de ejecución, y `Grep` sobre una carpeta busca en un `.env` que git no ignore. Si el riesgo importa, los secretos reales no viven en el árbol del proyecto.

4. **Contrato con cada proyecto.** El `CLAUDE.md` del proyecto declara esta sección, con título exacto y claves fijas en inglés; la que no aplica lleva `none`. No hay otro archivo de instrucciones.
   ```markdown
   ## Project commands
   - Tests (step): ...
   - Tests (full): ...
   - Lint/format: ...
   - Type check: ...
   - Migrations check: ...
   - Base branch: ...
   - Decision docs: ...
   - Traceability: ...
   ```
   Con una clave faltante, la pieza se detiene, dice cuál falta y propone la línea; no la escribe sin aprobación y no adivina. En `Decision docs` y `Traceability`, `<feature>` y `<n>` se reemplazan. La clave opcional `Docs paths` se describe en el [README del plugin](../../../plugins/stepwise/README.md).

   **Tests fuera de la suite principal:** `Tests (full)` es todo lo que `/check` y `/close` corren. Si el proyecto tiene tests aparte (por ejemplo los de `.claude/hooks/`), el valor los encadena: `cmd1 && cmd2`. `test-runner` corre el valor una vez, tal cual, y reporta los totales de cada comando; los que no corrieron porque uno anterior falló salen como `not run`.

   **Proyectos sin tests automáticos:** `Tests (step): none` cambia "test primero" por una verificación manual por CA en `## Pruebas` (pasos, esperado, obtenido), y en un bug la reproducción manual antes (falla) y después (pasa) del arreglo. `Tests (full): none` hace que `/check` salte la suite y lo anote. Para `code-reviewer`, un CA con verificación manual registrada cuenta como cubierto. `/close` no mergea con una verificación `pendiente` salvo que el usuario lo diga. Una marcada `después del merge` no frena el merge del paso: va como casilla al PR principal.

5. **Plantillas.** Cada skill lleva las suyas en `references/`: `/spec` lleva la del ADR, y `/close` la del paso y la del PR principal.

6. **Ramas y merges.** `<feature>` sale de `Base branch`; cada paso es `<feature>-step-<n>` con un Sub-PR a `<feature>`, mergeado con `--merge`. Nunca `--squash`, `--rebase`, `--force` ni borrado de ramas.

## 4. Restricciones y Alcance Negativo
- No hay reglas, guías, plantillas de reglas ni plugins por framework.
- No se escriben scripts, carpetas ni comprobaciones para herramientas distintas de Claude Code.
- Nada de un proyecto concreto (rutas, nombres, comandos) entra en este repo: va en el `CLAUDE.md` del proyecto.
- Los subagentes no preguntan al usuario ni publican en GitHub.

## 5. Posibles Soluciones y Trade-offs
- **Opción seleccionada:** un solo plugin de flujo (`stepwise`) y el contexto del proyecto en su `CLAUDE.md`.
- **Alternativa descartada:** una biblioteca por capas, con plugins y reglas por framework y soporte a otras herramientas. Costaba mantener plantillas sincronizadas y copias por herramienta.
- **Trade-off aceptado:** cada proyecto escribe más en su `CLAUDE.md` a cambio de un repo chico, sin sincronización de reglas.

### 5.1 Estructura del repo
```
.claude-plugin/marketplace.json   # el marketplace stepwise
.github/CODEOWNERS
CLAUDE.md                         # ## Project commands de este repo
README.md
plugins/stepwise/{agents,skills,hooks,scripts,references}
docs/decisions/bootstrap/         # este documento
docs/migration-template.md        # plantilla para adoptar el plugin en un proyecto
tests/                            # tests del repo (rutas, bloques compartidos, versión)
```

### 5.2 Distribución
- `main` es lo publicado. Si algo se rompe, `git revert` del merge en `main`, por PR.
- **Instalación:** `/plugin marketplace add juanpa1601/stepwise` y `/plugin install stepwise@stepwise` (ver el `README.md`).
- **Antes de publicar un cambio del plugin:** instalarlo desde su rama (`/plugin marketplace add <owner>/stepwise#<rama>`) en un proyecto desechable con remoto en GitHub y correr un paso chico con el flujo. La plantilla del PR principal de `/close` (`close/references/main-pr-template.md`) trae una sección "Verificación de instalación", que `/close` solo exige cuando el repo publica plugins (`.claude-plugin/marketplace.json`).
- **Advertencias aceptadas de `claude plugin validate`:** `stepwise` no tiene icono, que solo sirve para el directorio público de plugins.

### 5.3 Hallazgos que siguen vigentes
- **Hooks:** solo biblioteca estándar y Python 3.10 o superior, invocados con `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py"` (el único nombre que corre en Windows y existe por defecto en macOS y Linux); en Windows `python3` puede ser otra instalación o el stub de la Microsoft Store.
- **Windows:** Claude Code debe usar Git Bash; ahí corren los hooks y `${CLAUDE_PLUGIN_ROOT}` llega con barras normales. PowerShell sin Git Bash no se probó; macOS tampoco.
- **Versión:** `stepwise` tiene `version` en su `plugin.json`, y Claude Code solo entrega un cambio cuando esa `version` cambia, también con `autoUpdate: true`. Todo cambio publicado sube la versión y `tests/test_plugin_version.py` lo exige.
- **Rama que lee el marketplace:** una fuente `github` lee la rama o tag de `ref` y, sin `ref`, la rama por defecto. Cada proyecto declara `"ref": "main"`. La fijación por commit solo existe por plugin (`sha` en `marketplace.json`); no se diseña.
- **`.claude/` es ruta sensible para Write:** Claude Code pide permiso en cada escritura, incluso en `acceptEdits`; con `-p` la niega y una regla `allow` no la levanta.
- **Skills con `paths:` desde un plugin no se cargan por ruta.**
- **Acceso al repo:** para clonar por HTTPS, `gh auth login` + `gh auth setup-git`; con SSH, una clave sin passphrase. Sin eso, el auto-update falla en silencio.
- **Este repo usa su propio flujo:** no hay forma declarativa portable de cargarlo desde el checkout: `extraKnownMarketplaces` acepta `directory` con `path`, pero la documentación solo muestra rutas absolutas, y declarado en `.claude/settings.json` no se instala en una sesión `-p`. Cada colaborador corre una vez `/plugin marketplace add ./ --scope local` y `/plugin install stepwise@stepwise --scope local` (`.` sin barra se rechaza). Para probar cambios sin commit: `claude --plugin-dir <ruta absoluta>/plugins/stepwise`.
- **Skills que solo invoca el usuario:** frontmatter con `description`, `argument-hint` y `disable-model-invocation: true`. Sin `allowed-tools`, porque daría permiso sin preguntar a `git commit`, `git push` y `gh`, que deben seguir pidiendo aprobación. Desde un plugin se invocan como `/stepwise:<skill>`, o sin el prefijo si ningún comando usa ese nombre. Con `claude -p`, solo se carga la primera skill del prompt y el resto de la línea son sus argumentos.
- **`AskUserQuestion` no existe en una sesión `-p`.** Las skills preguntan en texto plano y terminan el turno; la respuesta llega en el turno siguiente (`claude -p -c`).
- **Probar skills desde Git Bash:** `claude -p '/spec ...'` puede llegar como `C:/Program Files/Git/spec ...`, porque MSYS convierte el argumento en ruta y la skill no se carga. Se corre con `MSYS_NO_PATHCONV=1`. Con esa variable, MSYS tampoco convierte `--plugin-dir /c/...`: la ruta va en forma Windows, `--plugin-dir 'C:/.../plugins/stepwise'`.

**Riesgos:** el hook `ask_gh_api_writes` analiza texto con `shlex` y puede no ver un `gh api` armado en tiempo de ejecución o dentro de `sh -c` anidado; las reglas `ask` siguen como respaldo. Sin huella, `/close` vuelve a correr todo. `block_inplace_edits` deja correr un `.py` sin seguimiento y no ignorado dentro del proyecto sin comprobar que se escribió con Write o Edit (`cp /tmp/w.py tests/w.py && python tests/w.py` pasa); el freno es la revisión del diff.

## 6. Decisiones abiertas
Ninguna.
