# Decisiones y Reglas de Negocio: release-2.1.0

- **Fecha:** 2026-11-21
- **Tipo:** feature
- **Rama Principal:** `release-2.1.0`
- **Fuente / Documento:** [prompt de `/spec`](../../prompts/release-2.1.0/2026-11-21-spec.md) y las respuestas de la entrevista (2026-11-21).

---

## 1. Contexto y Objetivo
Una copia de trabajo lleva una feature a la vez: `/implement`, `/check`, `/close` y `/regression` trabajan sobre la rama de la carpeta de la sesión. Para llevar varias features en paralelo hace falta un `git worktree` por feature, y hoy stepwise no lo documenta ni lo automatiza. Además, el README del plugin (`plugins/stepwise/README.md`) sigue en español, mientras el README raíz y el `CHANGELOG.md` ya están en inglés.

El objetivo es publicar `2.1.0`:
- una skill nueva, `/stepwise:worktree`, solo invocable por el usuario: `new <carpeta>` crea el worktree y mete la sesión en él; `remove <carpeta>`, con el PR principal mergeado, baja el compose de tests y lo quita sin borrar la rama;
- su script de solo lectura `skills/worktree/scripts/worktree_check.py`, con tests;
- la guía `docs/worktrees.md`;
- el README del plugin en inglés.

## 2. Criterios de Aceptación
**Paso 1: script `worktree_check.py`** (solo lectura, sin red, biblioteca estándar, Python 3.10+)
- **CA-1:** Dada una copia principal con `## Project commands` y una `<carpeta>` válida y nueva, cuando se corre `worktree_check.py new <carpeta>` desde su raíz, entonces sale con 0 e imprime `ok`, `Carpeta:` (ruta absoluta de `../<carpeta>`), `Proyecto:` (el nombre normalizado como lo hace Compose), `venv:`, `compose:`, `Proyecto fijo:` (lo que fija un mismo proyecto para todos los worktrees: `-p`, `--project-directory`, `name:` o la carpeta de un compose fuera de la raíz) y `Entorno:`.
- **CA-2:** Dada una `<carpeta>` inválida, cuando se corre `new`, entonces sale con 1, `error: <motivo>` en stderr, y nada cambia. Inválida es:
  - fuera de `^[a-z0-9][a-z0-9_-]*$`, o `../<carpeta>` ya existe;
  - su nombre de proyecto normalizado es el de otro worktree (la copia principal incluida);
  - con compose: es un `-p`/`--project-name` o `--project-directory` de los comandos, un `name:` de primer nivel o la carpeta de un compose fuera de la raíz; o un compose no se puede leer como UTF-8, o su `name:` tiene una variable `$`.
- **CA-3:** Dado `Lint/format`, cuando menciona `.venv`, entonces `venv: yes (<python>)` con el primero que exista de `.venv/Scripts/python.exe`, `.venv/Scripts/python` y `.venv/bin/python`; sin ninguno, `venv: yes (aviso: la copia principal no tiene .venv)`; si no lo menciona o vale `none`, `venv: no`.
- **CA-4:** Dados `Tests (step)`, `Tests (full)` y `Migrations check`, cuando contienen `docker compose` o `docker-compose` con `-f`/`--file` globales, entonces `compose:` lista cada archivo una vez, en orden y sin `./`; sin ninguno, `compose: none`.
- **CA-5:** Dados el compose de tests y los archivos ignorados, cuando se corre `new`, entonces `Entorno:` lista, sin abrirlos:
  - los `env_file:` con ruta relativa que caen dentro de la copia principal y que git no versiona, con ` (sin ignorar)` si git no los ignora;
  - los ignorados llamados `.env` o `.env.*`, sin bajar a carpetas ignoradas enteras y sin `.env.example`, `.env.sample`, `.env.template` ni `.env.dist`;
  - `ninguno` si no hay.
- **CA-6:** Dado `remove <carpeta>`, cuando `../<carpeta>` es un worktree registrado, no la copia principal y con rama, entonces sale con 0 e imprime `Carpeta:`, `Rama:`, `Feature:` (la rama, o `<feature>` de `<feature>-step-<n>`), `Proyecto:`, `compose:` (del `CLAUDE.md` del worktree) y `Llamadas compose:` (los `-f` de cada llamada, juntos y entre comillas de shell). Sale con 1 si no está registrado, su carpeta ya no existe, es la copia principal, tiene HEAD separado o, con compose, por los mismos rechazos de proyecto de CA-2 (también un nombre que normalizado queda vacío).
- **CA-7:** Dada una corrida fuera de la raíz de la copia principal, cuando se corre cualquiera de los modos, entonces sale con 1. Un uso incorrecto, un `CLAUDE.md` sin `## Project commands` o un fallo de git salen con 2.
- **CA-8:** Dado el paso 1 hecho, cuando corre `Tests (full)`, entonces pasa con el `discover` de `plugins/stepwise/skills/worktree/scripts/tests` en `CLAUDE.md:3`, `2.1.0` en `plugin.json` y en `tests/test_plugin_version.py:257`, y la viñeta `Added` del script en `[Unreleased]`.

**Paso 2: README del plugin en inglés**
- **CA-9 (manual: documentación):** Dado `plugins/stepwise/README.md`, cuando se lee contra la versión de `main`, entonces:
  - está en inglés y dice lo mismo: ninguna regla, paso ni ejemplo agregado o quitado;
  - los textos que escriben o buscan las skills quedan literales y entre backticks (`## Pruebas`, `### Tests del paso`, `### Verificación manual`, `después del merge`, `(manual: <motivo>)`, `sin tests del paso`, `Huella de código`, `Ejecutó`, `Verificación Global`…);
  - `## Versionado` pasa a `## Versioning` y `CHANGELOG.md:3` enlaza `#versioning`; ningún otro archivo enlaza un ancla que cambie;
  - `[Unreleased]` trae la viñeta `Changed`.

**Paso 3: skill, guía y publicación**
- **CA-10 (manual: texto de skill):** Dada `skills/worktree/SKILL.md`, cuando se lee, entonces tiene `disable-model-invocation: true`, `argument-hint: new <folder> | remove <folder>`, los bloques `project-commands` y `git-rules`, y en `new`:
  1. corre el script y se detiene con su exit 1 o 2;
  2. `git fetch origin <Base branch>` (si falla, no crea nada) y `git worktree add --detach "<Carpeta>" "origin/<Base branch>"`;
  3. con `venv: yes (<python>)`, crea el `.venv` con ese python e instala su `pip freeze` sin las líneas de rutas locales, en segundo plano;
  4. da el `cp` de `Entorno:` para que lo corra el usuario, sin correrlo, y avisa de `(sin ignorar)`;
  5. entra con `EnterWorktree` `path`, o da `cd "<Carpeta>" && claude`.
- **CA-11 (manual: texto de skill):** Dada la misma `SKILL.md`, cuando se lee `remove`, entonces:
  - dentro del worktree que quita, sale con `ExitWorktree` `keep` si entró en esta sesión; si no, se detiene;
  - exige el PR principal mergeado (`gh pr list --state merged`; sin GitHub, `git merge-base --is-ancestor`) y `git -C "<Carpeta>" status --short` vacío antes de bajar nada;
  - se detiene si un contenedor del proyecto tiene un `working_dir` fuera del worktree;
  - quita los one-off con `docker rm -f -v` y corre `rm -s -v -f` y `down --rmi local` con `-p "<Proyecto>"` desde la carpeta del worktree, nunca `down -v` ni `docker compose config`;
  - borra solo los volúmenes con la etiqueta del proyecto y el prefijo `<Proyecto>_`, después del sí del usuario;
  - `git worktree remove` y `git worktree prune` desde la copia principal, sin `--force` y sin borrar la rama.
- **CA-12 (manual: sesión real sin Docker con `claude --plugin-dir`, solo la corre el usuario):** Dado un repo desechable en GitHub sin compose de tests, cuando el usuario corre `/stepwise:worktree new <carpeta>` desde la copia principal, entonces el worktree queda en `../<carpeta>` con HEAD separado en `origin/<Base branch>`, la sesión entra y `/stepwise:spec` llega al resumen de aprobación. Con `remove` antes del merge del PR principal, se detiene sin quitar nada. Después del merge, salta el compose (`Llamadas compose: none`), `git worktree list` ya no muestra la carpeta y la rama sigue local y remota. La trazabilidad anota qué pasó con `EnterWorktree`.
- **CA-13 (manual: documentación):** Dada `docs/worktrees.md`, cuando se lee, entonces:
  - está en inglés, con las secciones 1 a 9 (qué es un worktree, paso a paso, qué nace vacío, Docker en paralelo, rendimiento, integración, limpieza, checklist con problemas comunes y lo no verificado);
  - ofrece `/stepwise:worktree` en las secciones 2, 7 y 8 y conserva los comandos a mano;
  - los recuadros **In this repo** hablan de stepwise (instalación `local`, `README.md:87-88`, y `--plugin-dir`; versión, test de versión y `CHANGELOG`);
  - cada `ruta:línea` que cita apunta a stepwise y es correcta.
- **CA-14 (manual: documentación):** Dados `plugins/stepwise/README.md`, `README.md`, `plugin.json`, `.claude-plugin/marketplace.json` y `CHANGELOG.md`, cuando se leen, entonces:
  - el README del plugin tiene la entrada de `skills/worktree/` (`new`, `remove`, script), `worktree` en "Today" de `project-commands` y `git-rules`, el `discover` del script en los tests y la versión `2.1.0`;
  - el README raíz tiene la fila de worktrees en la tabla y el enlace a `docs/worktrees.md`;
  - las descripciones de `plugin.json` y de `marketplace.json:4` y `:9` nombran las siete skills;
  - `[Unreleased]` trae la viñeta `Added` de la skill.

**Todos los pasos**
- **CA-15:** Dado cada paso hecho, cuando corre `Tests (full)`, entonces pasa, con `test_shared_blocks.py`, `test_full_suite_owner.py` y `test_path_lengths.py` sobre los archivos nuevos.
- **CA-16 (manual: revisión del diff):** Dado el diff de cada paso, cuando se busca con la lista de términos de la regla 1 (también rutas locales con `/`), entonces no aparece ninguno. Un hallazgo es un `blocker`. No cuenta el texto genérico que ya está en `main` y no viene del origen.

## 3. Reglas de Negocio Clave
1. **Saneamiento** (usuario, no negociable): igual que en `release-2.0.0`. Nada nombra el repo de origen, su organización, sus proyectos, su sandbox, sus PR, sus commits, sus ADR ni sus CA, rutas locales ni personas, tampoco en docstrings ni tests. Los docstrings de los tests citan los CA de este ADR. Las fuentes y los términos están en la memoria privada de Claude, fuera del repo.
2. **Mismo comportamiento que el origen:** el script y la skill se traen con los nombres de stepwise (`/stepwise:worktree`, `plugins/stepwise/`). Las líneas que imprime el script (`Carpeta:`, `Proyecto fijo:`, `Entorno: ninguno`, `(sin ignorar)`…) quedan en español, como los demás marcadores del plugin. Tres cambios elegidos en la revisión del paso 1 (usuario):
   - `Proyecto fijo:` también lista `carpeta de <compose>` por cada compose fuera de la raíz;
   - `remove` de un worktree registrado cuya carpeta ya no existe sale con 1 y sugiere `git worktree prune`;
   - los rechazos citan la guía con su URL de GitHub (regla 3).
3. **Enlace a la guía:** la skill corre en otros proyectos, así que enlaza `docs/worktrees.md` con su URL de GitHub en `juanpa1601/stepwise`, y sus explicaciones no citan reglas de un ADR.
4. **Archivos de entorno:** la skill nunca los lee ni los nombra en un comando suyo; solo imprime el `cp` para el usuario. Los hooks no cambian (`block_env_access` niega cualquier comando que los nombre).
5. **Texto prohibido:** la `SKILL.md` nueva no contiene `gh pr ready`, ni `run_tests.py` con `full`, ni `test-runner` con `"full"` (`tests/test_full_suite_owner.py`), tampoco en prosa.
6. **Guía genérica con hechos** (usuario): los hechos verificados en el origen quedan como afirmaciones sin proyecto, cifras, hashes, fechas ni PR; se conservan las marcas **unverified** y la sección 9.
7. **Traducción** (pedido): solo `plugins/stepwise/README.md`. `docs/migration-template.md`, `docs/prompts/README.md`, los ADR y las trazabilidades siguen en español. Las citas `README.md:<línea>` de ADR y trazabilidades anteriores no se actualizan: son históricas.
8. **Versión `2.1.0`, menor:** agrega una skill y no cambia ningún comportamiento existente. Se sube una vez, en el paso 1, porque `tests/test_plugin_version.py` lo exige apenas cambia `plugins/stepwise/`.
9. **CHANGELOG:** en inglés y con el formato de `[2.0.0]`. Cada paso agrega su viñeta en `[Unreleased]`, que se renombra al publicar.
10. **Marketplace** (usuario): sus dos descripciones se alinean con la de `plugin.json` en el paso 3.

## 4. Fuera de Alcance
- Que `/regression` exija `git merge-base --is-ancestor origin/<Base branch> <feature>`.
- Que la skill cree un worktree de una feature que ya existe (la guía da el comando a mano).
- Copiar `.claude/settings.local.json` o pasar `--plugin-dir` desde la skill.
- Una clave nueva en `## Project commands` para el compose de tests.
- Cambiar los hooks, `run_tests.py` o los agentes.
- Traducir otros documentos.
- La prueba real con Docker (usuario): la cubren los tests del script y la revisión del texto.
- El tag `stepwise--v2.1.0`: se crea a mano después del merge del PR principal.

## 5. Solución y Trade-offs
- **Opción seleccionada:** traer la skill, el script, sus tests y la guía con los nombres de stepwise y saneados, en 3 pasos (usuario): script, traducción sola y skill con guía, para que el diff de la traducción se revise sin cambios de contenido.
- **Alternativa descartada:** el orden del origen (la skill antes de la traducción), que escribe la entrada en español para traducirla después.
- **Trade-off aceptado:** `Tests (full)` suma un `discover`, y el compose solo se detecta si los comandos usan `-f`/`--file`.

## 6. Riesgos
- **La traducción cambia el sentido:** el paso 2 no agrega contenido, y CA-9 se revisa contra `main`.
- **Fuga al repo público:** la guía del origen trae mucha evidencia privada; CA-16 en cada paso.
- **`EnterWorktree`:** la sesión conserva el plugin y la configuración con que se abrió; CA-12 lo mide.
- **Docker sin sesión real** (usuario): un error en `remove` con compose se vería en un proyecto real.
- **`pip freeze`:** puede traer líneas `-e` o rutas locales; la skill las quita y las lista.
- **Esta misma feature:** si el plugin instalado es anterior a `2.1.0`, `/stepwise:worktree` no existe en la sesión; CA-12 usa `--plugin-dir`.

## 7. Pasos de Implementación
1. **Paso 1: script `worktree_check.py`** (CA-1 a CA-8, CA-15, CA-16): `plugins/stepwise/skills/worktree/scripts/worktree_check.py` y `scripts/tests/test_worktree_check.py`, el `discover` en `CLAUDE.md:3`, `plugin.json` en `2.1.0`, `tests/test_plugin_version.py:257` y `CHANGELOG.md`.
2. **Paso 2: README del plugin en inglés** (CA-9, CA-15, CA-16): `plugins/stepwise/README.md`, el ancla en `CHANGELOG.md:3` y su viñeta `Changed`.
3. **Paso 3: skill, guía y publicación** (CA-10 a CA-16): `skills/worktree/SKILL.md`, `docs/worktrees.md`, `plugins/stepwise/README.md`, `README.md`, la descripción de `plugin.json`, `.claude-plugin/marketplace.json`, `CHANGELOG.md` y la sesión de CA-12.

## 8. Decisiones Abiertas
Ninguna.
