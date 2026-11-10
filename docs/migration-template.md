# Migrar <Proyecto> al plugin `stepwise`

> **Cómo se usa esta plantilla** (se borra este bloque al rellenarla)
> - Es la plantilla para adoptar `stepwise` en un proyecto existente, backend o frontend. El contrato es el mismo para cualquier stack; cambian los valores de las claves y las piezas locales.
> - Se copia a donde quieras guardar el prompt (por ejemplo `docs/prompts/<AAAA-MM-DD>-migration.md` en tu proyecto) y se reemplaza cada `<marcador>`: `<Proyecto>`, `<org>/<repo>`, `<Base branch>`, `<feature de la migración>` (por ejemplo `adopt-stepwise`), `<revisor>`, `<num>`, `<archivo de entorno>`, `<pieza local>`, `<otra copia>`, `<piezas locales que se quedan>`, `<ruta absoluta a este prompt>` y cualquier otro `<...>` de lo propio que quede, salvo `<feature>`, `<n>`, `<motivo>` y `<ruta>`, que se dejan tal cual: `<feature>` y `<n>` los reemplaza el plugin en `Decision docs` y `Traceability` para cada feature (ADR `bootstrap` §3.4), `<motivo>` es la sintaxis de `/spec` y `<ruta>` la de cada comprobación. Los valores de R0 y del bloque de `## Project commands` (`<comando>`, `<pathspecs>`…) los rellena la Preparación.
> - Lo propio del proyecto (rutas, comandos, piezas locales) va en el prompt rellenado o en el `CLAUDE.md` del proyecto, nunca en las skills del plugin.
> - Lo que no aplique se quita, con una línea que diga por qué.
> - El contrato no se copia aquí: se enlaza el ADR `bootstrap` §3.4 y `plugins/stepwise/README.md`, que son los que cambian.
> - **Anexos:** el Anexo A (perfiles por stack) da valores de partida para P1 y P2. En la copia se borra después de escribir R0. El Anexo B (fricción esperada en frontend) se queda en la copia de un proyecto frontend y se borra en uno backend.

**Conversación:** nueva, abierta en el clon de **<Proyecto>** (`<org>/<repo>`), en `<Base branch>` al día y con el árbol limpio.

**Referencias** (en `juanpa1601/stepwise`, solo lectura):
- `docs/decisions/bootstrap/business-rules.md`: §3.2 (reglas `ask`) y §3.4 (contrato `## Project commands`);
- `plugins/stepwise/README.md`: claves opcionales (`Docs paths`), la línea `no files to check`, CA manuales y alineación del plugin;
- `plugins/stepwise/references/ask-rules.json`: la lista vigente de reglas `ask`;
- `docs/migration-template.md`: esta plantilla.

## Precondiciones (la sesión las comprueba antes de cambiar nada)
Si alguna falla, se detiene y lo dice.

1. **`stepwise` instalado en alcance `user` y desde `main`:**
   ```bash
   claude plugin marketplace list   # stepwise, Source: GitHub (...@main o sin @)
   claude plugin list               # stepwise@stepwise, Scope: user
   git -C ~/.claude/plugins/marketplaces/stepwise branch --show-current   # main
   ```
   Con `CLAUDE_CONFIG_DIR`, cambia `~/.claude` por esa carpeta. Si no se cumple, se sigue la Instalación del README de `stepwise` y se reinicia la sesión.
2. **Rama:** `git branch --show-current` es `<Base branch>`, el árbol está limpio y `<Base branch>` está al día con `origin/<Base branch>`.

## Preparación (antes de `/spec`)
`/spec` exige el árbol limpio y lee `Base branch` y `Decision docs`. `/implement 1` exige además `Tests (step)`, `Lint/format`, `Type check` y `Traceability`. Por eso todas las claves llegan a `<Base branch>` en un PR propio, mergeado antes de `/spec`. Así no se edita `CLAUDE.md` con `/spec` en curso ni hay claves que tenga que escribir el paso 1.

### P1. Inventario
La sesión lanza `stepwise:explore` ("very thorough") sobre el clon y arma la tabla del requisito R0. Busca:
- **Comandos reales:** tests de un paso y suite completa, lint/format, type check y chequeo de migraciones, con su fuente (`ruta:línea` de la CI, `Makefile`, `package.json`, `compose`, README). Cada comando **se corre una vez** para medir tiempo y estado:
  - si la suite pasa de 570 s, `stepwise:test-runner` reportará `timeout`: se pregunta antes de seguir;
  - si un lint o un type check fallan hoy sobre todo el repo, se pregunta: arreglar la base en un paso aparte, acotar el comando al diff o `none`.
- **Piezas locales:** agentes (`.claude/agents/`), skills (`.claude/skills/`), comandos (`.claude/commands/`), hooks (`.claude/hooks/` y sus entradas en `.claude/settings.json`), plantillas (`docs/templates/`) y copias para otras IA (`AGENTS.md`, `.agents/`, `GEMINI.md`). De cada una: si el plugin la reemplaza, si se queda o si lo decide `/spec`.
- **Archivos de entorno:** cuáles hay (`.env`, `.env.*`, assets) y qué los carga. Ningún comando de `## Project commands` puede nombrarlos, porque `block_env_access` lo negaría. Se cargan por fuera del comando (`env_file`, `COMPOSE_ENV_FILES`, la configuración del runner).
- **Restricciones del host:** Docker, SDK (Node, Flutter, navegador), Windows y Git Bash (`python3`, rutas largas, librerías que no corren en el host).

Los valores de partida por stack están en el Anexo A. Cada uno se mide igual: un perfil "sin verificar" no se copia sin correrlo.

La sesión muestra la tabla y, **con la aprobación del usuario**, la escribe en la sección R0 de este prompt (`<ruta absoluta a este prompt>`), reemplazando las filas de ejemplo. Es lo que lee `/spec`: sin ella, R0 llega con los marcadores vacíos y se pierde lo medido.

### P2. PR de claves
1. Con R0 escrito, la sesión muestra la sección completa y, **con la aprobación del usuario**, la escribe al final de `CLAUDE.md`. Si `CLAUDE.md` ya tiene `## Project commands`, aunque sea parcial, completa esa sección en su lugar y muestra el diff, sin duplicarla:
   ```markdown
   ## Project commands
   - Tests (step): <comando>
   - Tests (full): <comando>
   - Lint/format: <comando | none>
   - Type check: <comando | none>
   - Migrations check: <comando | none>
   - Base branch: <Base branch>
   - Decision docs: docs/decisions/<feature>/business-rules.md
   - Traceability: docs/pull-requests/<feature>/step-<n>.md
   - Docs paths: <pathspecs | se omite la línea>
   ```
2. La lleva en una rama propia (que no se llame `<feature de la migración>` ni `<feature de la migración>-step-<n>`) con un PR chico a `<Base branch>`. Commit, push y PR, cada uno con aprobación. El PR lo revisa `<revisor>` y se mergea antes de `/spec`.
3. El ADR de la migración cita ese PR en "Fuente / Documento".
4. Después la sesión se detiene y le pide al usuario que actualice `<Base branch>` y escriba el comando de la sección **Comando**.

## Reglas de la sesión
- **El usuario encadena el flujo.** Las skills son "User only · locked": el agente nunca dice "ejecuto `/spec`". Al terminar cada etapa se detiene y le pide al usuario que escriba el siguiente comando (`/stepwise:implement <n>`, `/stepwise:check` o `/stepwise:close`), también después de un "corrige y cierra".
- **Fricción del plugin:** cualquier fricción con una skill, un agente o un hook se anota en la sección "Fricción del plugin" de la trazabilidad del paso. No se arregla aquí: se reporta como issue en `juanpa1601/stepwise`.
- **Ninguna lectura de `<archivo de entorno>`.** Ningún comando, mensaje de commit ni título de PR lo nombra literalmente: `block_env_access` lee el comando entero. Los mensajes van por archivo (`git commit -F`, `--body-file`).
- **El PR principal no sale de draft ni se mergea a `<Base branch>` sin el usuario.** `/spec` pregunta quién lo revisa.

## Comando
Lo escribe el usuario, en una sesión nueva, después de mergear el PR de claves:
```
/stepwise:spec Feature <feature de la migración>: migrar <Proyecto> al plugin stepwise con los requisitos R0 a R5 de <ruta absoluta a este prompt>
```

## Requisitos para `/spec`
Propón los pasos y los CA a partir de estos requisitos, **en este orden**, y entrevista al usuario donde algo no esté claro. Un paso que solo toca configuración o documentación propone sus CA como `(manual: <motivo>)`.

### R0. Inventario
La escribe la Preparación (P1), con una fila por clave del contrato y otra por pieza local.

| Clave o pieza | Valor propuesto o destino | Fuente (`ruta:línea`) | Tiempo y estado |
|---|---|---|---|
| `Tests (step)` | `<comando>` | `<ruta:línea>` | `<s>`, `<ok/falla>` |
| `<pieza local>` | se quita / se queda / decide `/spec` | `<ruta>` | — |

### R1. Paso 1: `CLAUDE.md` como fuente única
- `## Project commands` ya está en `<Base branch>` (P2). Si `/spec` o el inventario corrigen un valor, este paso lo cambia.
- Pasa a `CLAUDE.md` lo que solo esté en las copias para otras herramientas y las borra (`AGENTS.md`, `.agents/`, `<otra copia>`). Antes muestra el diff de lo que se pierde: debe estar vacío o ser aprobado.
- El encabezado de `CLAUDE.md` deja de nombrar otras herramientas, y se quitan sus referencias a las copias.
- Los `CLAUDE.md` y `README.md` por carpeta y `.claude/rules/` se quedan.

### R2. Paso 2: plugin y reglas `ask`, antes de borrar nada local
Va antes de R3 para que la rama nunca quede sin protección: si los hooks locales se borran antes de habilitar el plugin, la rama queda un tiempo sin ninguno.
- En `.claude/settings.json`:
  ```json
  "extraKnownMarketplaces": {
    "stepwise": {
      "source": { "source": "github", "repo": "juanpa1601/stepwise", "ref": "main" },
      "autoUpdate": true
    }
  },
  "enabledPlugins": { "stepwise@stepwise": true }
  ```
  y en `permissions.ask` las reglas de `plugins/stepwise/references/ask-rules.json`, tal cual. Se conservan `env`, `permissions.allow` y los hooks locales (se van en R3). `settings.local.json` no se toca.
- En `claude -p`, un `ask` del proyecto le gana a `--allowedTools`: se documenta en el README.
- **README del proyecto, sección "Flujo con Claude Code":** `python3` en Git Bash (Windows); la instalación (`claude plugin marketplace add juanpa1601/stepwise` y `claude plugin install stepwise@stepwise`), con un enlace al README de `stepwise`; y reiniciar la sesión después de instalar.
- Los cambios de `settings.json` se comprueban en una sesión nueva: no está comprobado que la sesión que lo escribe los recargue.

### R3. Paso 3: quitar las piezas locales que reemplaza `stepwise`
- **Agentes** `<pieza local>` (por ejemplo `explore` y `test-runner`), **skills** (por ejemplo una de cierre de paso) y **plantillas** (`docs/templates/`), si el plugin trae las suyas. Antes de borrar una plantilla se busca con `stepwise:explore` qué más la usa.
- **Hooks** que cubre el plugin (por ejemplo `block_inplace_edits` y `block_env_access`), con sus tests y sus entradas en `.claude/settings.json`. Antes de borrar cada uno se compara con el del plugin; si el local bloquea algo que el del plugin no, se pregunta.
- **Se quedan:** `<piezas locales que se quedan>` (lo decide R5).
- **`CLAUDE.md`:** la descripción del flujo anterior pasa a `/spec`, `/implement`, `/check`, `/close` y `/audit`, una línea por skill con el enlace al README del plugin, para que no se desactualice.
- **Sesión nueva:** si el paso toca `.claude/agents/`, `.claude/skills/` o `.claude/commands/`, `/implement` lo avisa. Se abre una sesión nueva antes de `/stepwise:check`; hasta entonces las piezas viejas siguen cargadas y se confunden con `stepwise:explore` y `stepwise:test-runner`.

### R4. Paso 4: verificación final
1. `/stepwise:audit pr <num>` sobre un PR de <Proyecto> ya mergeado, con el `## Project commands` real. No publica nada: el borrador no se aprueba.
2. El `## Pruebas` que escribe `/stepwise:check` trae `- **Alineación del plugin:** ok`.
3. El último paso se cierra con `/stepwise:close`, de punta a punta.

Los dos primeros solo los puede correr el usuario: van como CA `(manual: <motivo>)`, con el comando exacto.

### R5. Lo que decide el proyecto
`/spec` pregunta, con lo que encontró el inventario:
1. **Lint acotado al diff:** si `Lint/format` revisa solo los archivos del diff. Si es así, cuando no queda ninguno imprime la línea exacta `no files to check` y termina en 0.
2. **`Docs paths`:** qué rutas declara, después de inventariar qué leen sus tests, su lint y sus migraciones. Ninguna ruta que lea un test va ahí.
3. **Hooks locales que se quedan:** cuáles, y por qué el plugin no los cubre.
4. **Protección de la configuración:** si `.claude/settings.json` y `CLAUDE.md` tienen tests propios, o si basta el chequeo de alineación de `/stepwise:check`.

## Entrega
Al final de `/spec`, y otra vez después del último `/close`, la sesión responde con:
- el enlace al PR principal;
- la lista de pasos del ADR;
- toda la "Fricción del plugin" junta, para reportarla en `juanpa1601/stepwise`;
- el siguiente comando que tiene que escribir el usuario.

## Anexo A. Perfiles por stack
Valores sugeridos para cada clave, **sin verificar en tu proyecto**: el inventario los corre una vez y los corrige. El perfil de Django con Docker es el que más se usó.

| Clave | Django con Docker | Angular en el host | Flutter en el host |
|---|---|---|---|
| `Tests (step)` | `docker compose run --rm test pytest` | `npx ng test --watch=false --browsers=ChromeHeadless --include` | `flutter test` |
| `Tests (full)` | `docker compose run --rm test` | `npx ng test --watch=false --browsers=ChromeHeadless` | `flutter test` |
| `Lint/format` | `docker compose run --rm test sh -c "ruff check . && isort --check-only ."`, o un lint en el host sobre los `*.py` del diff, con `no files to check` | `npx eslint . && npx prettier --check .` | `dart format --output=none --set-exit-if-changed . && flutter analyze` |
| `Type check` | `docker compose run --rm test mypy .`, o `none` | `npx tsc --noEmit` | `none`: `flutter analyze` ya lo cubre |
| `Migrations check` | `docker compose run --rm test python manage.py makemigrations --check --dry-run` | `none` | `none` |
| `Base branch` | `<Base branch>` | `<Base branch>` | `<Base branch>` |
| `Decision docs` | `docs/decisions/<feature>/business-rules.md` | igual | igual |
| `Traceability` | `docs/pull-requests/<feature>/step-<n>.md` | igual | igual |
| `Docs paths` | `'*.md' 'docs/**'`, o las carpetas de `docs/` que ningún test lee | lo decide R5.2 | lo decide R5.2 |

Notas por perfil:
- **Django:**
  - Los archivos de entorno los carga `env_file` en el `compose`, nunca el comando.
  - `--build` va cuando la imagen no monta el código, porque si no `test-runner` da un verde falso. Ojo con el tiempo: el build cuenta para el timeout de 570 s.
  - Lo que importa GDAL no corre en el host en Windows: los tests van en Docker.
- **Angular:**
  - `stepwise:test-runner` agrega las rutas al final de `Tests (step)`, separadas por espacios. Por eso termina en `--include`. Con varias rutas, solo la primera queda en `--include` si el flag no acepta varios valores seguidos, y las demás se leerían como argumentos de `ng test` (Anexo B, caso 5). El plugin no parte las rutas: `/implement` hace una sola llamada con todas. Si el flag no los acepta, se anota en la "Fricción del plugin". Mientras tanto, el usuario pide a `/implement` una llamada a `test-runner` por ruta, o un glob entre comillas (o una carpeta).
  - Si el proyecto usa Jest en lugar de Karma, `Tests (step)` es el comando de Jest, que recibe las rutas sin flag.
- **Flutter:**
  - `--output=none` hace que `dart format --set-exit-if-changed .` solo revise. Sin el flag, reescribe los archivos al correr el inventario, `/check` o `/close`, y ensucia el árbol.
  - `flutter test` recibe las rutas al final sin flag.

## Anexo B. Fricción esperada en frontend
El plugin casi no se ha probado en proyectos frontend. El primero confirma cada caso y anota el resultado, confirmado o no, en la "Fricción del plugin" de la trazabilidad del paso en que aparezca.

1. **El `total` de `stepwise:test-runner` con runners que no son pytest ni unittest.** `run_tests.py` no tiene un parser para otros runners: da `Totals: not available (exit N)`, la nota `runner not recognized` y las últimas líneas de la salida. **Qué confirmar:** que el resultado se entiende en `/implement` y en `/check`, con un fallo y sin fallos. Ejemplos de resumen: Karma `Executed 12 of 12 SUCCESS`, Jest `Tests: 1 failed, 11 passed, 12 total`, `flutter test` `+12: All tests passed!`.
2. **`block_env_access` con un `.env` que Flutter carga como asset.** El hook niega `.env` y `.env.*` en Read, Grep, Glob, Edit, Write, Bash y PowerShell, también en un comando que solo los nombra. Permite las plantillas (`.env.example`, `.env.sample`, `.env.template`, `.env.dist`), y no ve lo que `flutter test` o `flutter run` leen por dentro. **Qué confirmar:**
   - si `pubspec.yaml` lo declara como asset y los tests lo necesitan;
   - qué tareas del agente quedan negadas;
   - si basta una plantilla.
   La copia `cp .env.example .env` la hace el usuario.
3. **Chrome headless en Windows.** **Qué confirmar:**
   - que `ng test --browsers=ChromeHeadless` encuentra Chrome desde Git Bash, sin abrir ventana y en menos de 570 s;
   - si hace falta `CHROME_BIN` o un launcher en `karma.conf.js`. Esa configuración va fuera del comando y de los archivos de entorno.
4. **CA de UI sin test automático.** Un CA visual o de interacción sin un test razonable va como `(manual: <motivo>)`. Lo propone `/spec`, lo aprueba el usuario, `/implement` lo registra en `### Verificación manual` y `code-reviewer` no lo marca `blocker`. **Qué confirmar:** que el flujo funciona así en un paso de UI, y si conviene cubrir con tests de widget o e2e lo que hoy queda manual.
5. **Varias rutas en `Tests (step)` de Angular.** `test-runner` agrega las rutas separadas por espacios después de `--include`. **Qué confirmar:**
   - si `ng test --include a b` corre los dos archivos, o si hace falta un glob entre comillas (sin comillas, Git Bash lo expande y vuelven las varias rutas);
   - si no corre los dos, se anota en la "Fricción del plugin", porque el plugin hace una sola llamada con todas las rutas. Mientras tanto, el usuario pide a `/implement` una llamada a `test-runner` por ruta, o un glob entre comillas (o una carpeta).
