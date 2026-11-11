# Decisiones y Reglas de Negocio: release-1.1.0

- **Fecha:** 2026-11-10
- **Tipo:** feature
- **Rama Principal:** `release-1.1.0`
- **Fuente / Documento:** pedido del usuario en `/stepwise:spec` (2026-11-10). El prompt no se guarda: el repo todavía no declara `Prompts`, y el pedido trae datos que no pueden entrar a un repo público (regla 1).

---

## 1. Contexto y Objetivo
`stepwise` `1.0.0` deja cuatro huecos:
- `/spec` no guarda el pedido con el que se inició: solo escribe el ADR y solo hace commit del ADR (`plugins/stepwise/skills/spec/SKILL.md:12`, `:98`, `:105`).
- `run_tests.py` solo lee pytest y unittest (`plugins/stepwise/scripts/run_tests.py:14-18`, `:365-409`). Con Karma cae en el modo genérico (`:502-506`), y las líneas salen con los códigos ANSI que Karma usa para reescribir su progreso.
- Nada dice cómo fijar la ventana de compactación automática de un proyecto.
- El perfil Angular de la plantilla de migración está sin verificar (`docs/migration-template.md:139-181`).

El objetivo es publicar `1.1.0` con la clave opcional `Prompts`, Karma y ANSI en `run_tests.py`, la ventana de compactación como recomendación y el perfil Angular con Karma verificado.

## 2. Criterios de Aceptación
Los CA de `/spec` se comprueban con sesiones reales `claude -p --plugin-dir plugins/stepwise` en un repo desechable con un `origin` local `--bare`. Ningún test lee `SKILL.md`.

**Paso 1: `/spec` guarda el prompt**
- **CA-1 (manual: texto de skill, sesión `claude -p`):** Dado un proyecto con `- Prompts: docs/prompts/<feature>/`, cuando `/stepwise:spec <texto de varias líneas>` escribe un ADR de feature y el usuario lo aprueba, entonces existe `docs/prompts/<feature>/<AAAA-MM-DD>-spec.md`, con el encabezado de la regla 4 y debajo `$ARGUMENTS` igual carácter por carácter. Además, `git show --name-only` del commit `docs(<feature>): add ADR` lista exactamente el ADR y ese archivo.
- **CA-2 (manual: texto de skill, sesión `claude -p`):** Dado el mismo proyecto, cuando el resumen de aprobación sale y el usuario no aprueba, entonces no existe ningún archivo en `docs/prompts/<feature>/`, y el resumen nombra la ruta del prompt.
- **CA-3 (manual: texto de skill, sesión `claude -p`):** Dado un proyecto sin `Prompts`, cuando `/spec` termina un ADR aprobado, entonces no escribe ningún prompt y el commit trae solo el ADR. El resumen trae la línea literal `Prompt: no se guarda (sin la clave opcional Prompts)`, y el reporte, de 6 líneas como máximo, `Prompt: no guardado (sin la clave opcional Prompts)`.
- **CA-4 (manual: texto de skill, sesión `claude -p`):** Dado `<feature>` con un ADR de 2 pasos y `Prompts`, cuando `/spec` agrega un paso y el usuario lo aprueba, entonces existe `<AAAA-MM-DD>-spec-step-3.md`, y el commit `docs(<feature>): add step 3 to ADR` lista exactamente el ADR y ese archivo.
- **CA-5 (manual: texto de skill, sesión `claude -p`):** Dado que el archivo del prompt ya existe, cuando `/spec` va a escribirlo después de la aprobación, entonces no lo sobrescribe: se detiene antes del commit, muestra la ruta y pregunta si sobrescribe, usa otro nombre o no lo guarda. Hasta la respuesta no hay commit y el archivo no cambia.
- **CA-6 (manual: texto de skill, sesión `claude -p`):** Dado `Prompts`, cuando `/spec` escribe el ADR de una feature, entonces "Fuente / Documento" enlaza al prompt con su ruta final. En un paso nuevo, agrega el enlace sin quitar lo que el campo ya tenía.
- **CA-7:** Dado el paso 1 hecho, cuando corre `Tests (full)`, entonces `tests/test_plugin_version.py` pasa con `1.1.0` en `plugin.json` y en `tests/test_plugin_version.py:257`, y `tests/test_shared_blocks.py` sigue en verde.
- **CA-8 (manual: documentación):** Dado el paso 1 hecho, cuando se leen los archivos, entonces `plugins/stepwise/README.md` describe la clave en `skills/spec/` (regla 2) y dice "Versión actual: `1.1.0`" (`:73`), y `[Unreleased]` de `CHANGELOG.md` trae la línea de `Prompts` (regla 7).

**Paso 2: ANSI y Karma en `run_tests.py`**
- **CA-9:** Dado un runner no reconocido cuya salida trae `ESC[32m`, `ESC[39m`, `ESC[1A` y `ESC[2K`, cuando corre `run_tests.py`, entonces el modo genérico sigue igual (`Totals: not available (exit N)` y la nota), y ninguna línea reportada trae `ESC`.
- **CA-10:** Dados `pytest_color_pass.txt` y `pytest_color_fail.txt` (`--color=yes`), cuando corre `run_tests.py`, entonces se leen como pytest, con los mismos `Totals:` y `Failures:` que sus pares `_plain` (salvo el tiempo de cada captura) y sin `ESC`.
- **CA-11:** Dado el paso 2 hecho, cuando corren los tests de `run_tests.py`, entonces los casos de pytest, unittest y `&&` que ya existen siguen en verde, sin cambiar sus fixtures.
- **CA-12:** Dado `karma_ok.txt` con salida 0, cuando corre `run_tests.py full`, entonces sale con 0, `Totals: 2 total, 0 failed, 0 errors, 0 skipped in 0.011s` y `Failures: none`.
- **CA-13:** Dado `karma_fail.txt` con salida 1, cuando corre `run_tests.py full`, entonces sale con 1, `Totals: 2 total, 1 failed, 0 errors, 0 skipped in 0.008s`, y el fallo es `- tmp failing check fails on purpose — <spec>:7: Expected 1 to be 2.`: el nombre sin el navegador y la primera ubicación del proyecto fuera de `node_modules/`. Si no queda ninguna ubicación del proyecto fuera de `node_modules/` (por ejemplo, sin la línea del spec), el fallo sale sin ubicación: `- tmp failing check fails on purpose — Expected 1 to be 2.`
- **CA-14:** Dado `karma_skip.txt`, cuando corre `run_tests.py full`, entonces da `Totals: 2 total, 0 failed, 0 errors, 1 skipped in 0.008s`.
- **CA-15:** Dado `Tests (full)` = `<Karma> && <unittest>`, los dos verdes, cuando corre `run_tests.py full`, entonces `Totals:` trae una fila por comando.
- **CA-16:** Dado un Karma cortado sin la línea `TOTAL:`, cuando corre `run_tests.py`, entonces cae en el modo genérico, sin `ESC`.
- **CA-17:** Dada una línea parecida que no cumple el formato (`TOTAL: 3 tests`, `Grand TOTAL: 3 SUCCESS`), cuando corre `run_tests.py`, entonces no se lee como Karma.
- **CA-18:** Dada una línea `Executed` con `<m> min(s) <s> sec(s)` (también `1 sec`) o con `(<k> FAILED) (skipped <s>)`, cuando corre `run_tests.py`, entonces el tiempo sale en segundos (`1 min 5.5 secs` da `65.5s`) y los fallados y saltados salen los dos.
- **CA-19 (manual: documentación):** Dado el paso 2 hecho, cuando se leen los archivos, entonces el docstring de `run_tests.py` nombra Karma y el quitado de ANSI; `plugins/stepwise/README.md` dice que el script lee Karma y quita ANSI, "Modo genérico" (`:34`) ya no nombra Karma y `:70` nombra los fixtures de Karma y de color; y `[Unreleased]` trae la línea de Karma (regla 7).
- **CA-20:** Dado el paso 2 hecho, cuando corre `Tests (full)`, entonces pasa, con la versión todavía en `1.1.0` (`test_plugin_version.py` compara con `origin/main`, en `1.0.0`).

**Paso 3: documentación**
- **CA-21 (manual: documentación y configuración):** Dado el paso 3 hecho, cuando se leen los archivos, entonces:
  - `README.md` trae, junto a "Permissions" (`:72`), la recomendación de la regla 8;
  - el bloque de `.claude/settings.json` de `docs/migration-template.md` (`:96-106`) pide la variable: se agrega si falta y se cambia si tiene otro valor, sin tocar el resto del `env`;
  - el `.claude/settings.json` de este repo tiene `"env": {"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000"}`, y `permissions.ask` sigue con las mismas 11 reglas en el mismo orden.
- **CA-22 (manual: solo se comprueba en una sesión nueva):** Dada una sesión nueva en la raíz de este repo, cuando se corre `echo "$CLAUDE_CODE_AUTO_COMPACT_WINDOW"`, entonces imprime `500000`.
- **CA-23 (manual: documentación):** Dada `docs/migration-template.md`, cuando se lee, entonces trae el perfil Angular de la regla 9 (P1, Anexo A con sus notas, Anexo B, Anexo C y la viñeta "Anexos" de `:9`).
- **CA-24 (manual: documentación):** Dado el paso 3 hecho, cuando se leen los archivos, entonces:
  - `CLAUDE.md` declara `- Prompts: docs/prompts/<feature>/`;
  - `docs/prompts/README.md` documenta la regla 10;
  - `README.md:71`, el ADR `bootstrap` §3.4 (`:86`) y la línea de Referencias de `docs/migration-template.md` (`:15`) nombran las claves opcionales `Docs paths` y `Prompts`.
- **CA-25:** Dado el paso 3 hecho, cuando corre `Tests (full)`, entonces pasa, con `tests/test_path_lengths.py` incluido `docs/prompts/README.md`.

**Todos los pasos**
- **CA-26 (manual: revisión del diff):** Dado el diff de cada paso, cuando se busca con la lista de términos de la regla 1, entonces no aparece ninguno. Un hallazgo es un `blocker`.

## 3. Reglas de Negocio Clave
1. **Saneamiento** (usuario, no negociable): stepwise es público (MIT). Nada de lo que entra nombra el repo del que vienen los cambios, su organización, sus proyectos, sus PR, sus ADR, rutas locales ni personas. Tampoco cita sus ADR ni sus CA en docstrings, comentarios o tests, como ya se hizo en `run_tests.py:1`. No se copia código de proyectos: el script de Angular entra solo como contrato. Las fuentes y la lista de términos de CA-26 están en la memoria privada de Claude de este proyecto, fuera del repo (decisión del usuario).
2. **Clave opcional `Prompts`:** `- Prompts: <carpeta>`, con `<feature>` reemplazado. Solo la lee `/spec`, y el bloque compartido `project-commands` no cambia.
   - **Después de la aprobación**, `/spec` escribe con Write `$ARGUMENTS` literal (sin resumen, traducción, bloque de código ni recorte, y sin las respuestas de la entrevista) en `<carpeta>/<AAAA-MM-DD>-spec.md`. En un paso nuevo usa `-spec-step-<n>.md`, con `<n>` el primer paso que agrega.
   - **Sin aprobación**, no lo escribe.
   - **Archivo que ya existe:** lo comprueba con Glob justo antes del Write. Si existe, no lo sobrescribe: pregunta (CA-5).
   - **Largo de la ruta:** no lo mira.
   - **Enlace en "Fuente / Documento":** sigue la ruta final. Si el usuario elige no guardar el prompt, se quita.
3. **Commit:** el prompt entra en el mismo commit del ADR, sin cambiar el mensaje.
4. **Encabezado del prompt**, en español: `# Prompt de /spec: <feature>`, y luego `Fecha`, `Tipo` (`feature | bug | paso nuevo (paso <n>)`), `Rama` y `ADR` (enlace relativo desde el prompt), en viñetas `- **<campo>:**`, y `---`.
5. **Sin la clave**, todo sigue igual. El resumen y el reporte dicen las líneas literales de CA-3, en español como las plantillas (`README.md:73`). El reporte pasa de 5 a 6 líneas.
6. **Versión:** los pasos 1 y 2 son menores del mismo ciclo. La versión sube de `1.0.0` a `1.1.0` una sola vez, en el paso 1 (`plugins/stepwise/README.md:79-82`). El paso 3 no toca `plugins/`.
7. **CHANGELOG:** una viñeta por cambio en `### Added` de `[Unreleased]`, en inglés y con el formato de `[1.0.0]` (`CHANGELOG.md:10-20`). `[Unreleased]` se renombra al publicar.
8. **Ventana de compactación** (recomendación, no requisito): `"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000"` en el `env` del `.claude/settings.json` del proyecto, como texto y sin sufijo.
   - **Por qué 500000:** con 200K, un paso largo con `/close` compacta a la mitad; con 1M casi nunca compacta, pero cada turno cuesta más.
   - **Por qué en el proyecto:** el plugin no puede fijarla, porque el `settings.json` de un plugin descarta `env`. Además, el valor del proyecto le gana al de usuario.
9. **Perfil Angular** (en un proyecto Angular 18 con Karma, Windows con Git Bash):
   - **P1:** antes de medir, se comprueba que la versión del SDK es compatible con la del framework (`npx ng version`, `flutter doctor`), y la sesión se detiene si no lo es.
   - **Anexo A**, columna "verificado en un proyecto Angular 18 con Karma (Windows con Git Bash)":
     - `Tests (step)`: el script local del Anexo C;
     - `Tests (full)`: con `--progress=false`;
     - `Type check`: `npx ngc -p tsconfig.app.json --noEmit && npx tsc --noEmit -p tsconfig.spec.json`, porque `tsc` no revisa las plantillas;
     - `Lint/format`: `npx ng lint` con `angular-eslint`, y Prettier solo si el proyecto lo usa.
     Las notas dejan de sugerir el glob y una llamada a `test-runner` por ruta.
   - **Anexo B:** los casos 1, 3 y 5 confirmados (el caso 1, con `Totals:` lleno desde `1.1.0`); los casos 2 y 4, sin probar.
   - **Anexo C, solo el contrato del script:** resuelve `@angular/cli/bin/ng.js` con `createRequire` y lo lanza con `process.execPath`, sin shell; agrega un `--include <ruta>` por argumento; rechaza un argumento que empieza con `-`; propaga el código de salida; y termina con 2 si no recibe rutas.
   - Lo medido entra sin el nombre ni las rutas del proyecto.
10. **`docs/prompts/README.md`:**
    - **Convención:** `docs/prompts/<feature>/<AAAA-MM-DD>-spec[-step-<n>].md`.
    - **Límite de 72 caracteres** (`tests/test_path_lengths.py`): una feature de más de 32 caracteres no cabe con `-spec-step-<n>.md`, así que aquí el nombre es corto.
    - **Repo público:** antes de aprobar, se revisa que el pedido no traiga datos privados. Si los trae, se elige no guardarlo.

## 4. Fuera de Alcance
- El tag `stepwise--v1.1.0`: se crea a mano después del merge del PR principal.
- Jest, Flutter y otros runners; Karma con varios navegadores u otros reporters.
- Otras piezas o documentos de la fuente, y renombrar los prompts o los ADR que ya existen.
- Una sección de estado (verificado/experimental) en `README.md`: hoy no existe.
- Que el plugin compruebe el largo de las rutas, o que otras skills lean o escriban prompts.

## 5. Solución y Trade-offs
- **Opción seleccionada:** traer los cambios con los nombres de stepwise y saneados, en 3 pasos, con las fuentes en la memoria privada de Claude.
- **Alternativa descartada:** un ADR autosuficiente que no necesite la fuente: pasaba de 150 líneas y arriesgaba diferencias con el código original.
- **Trade-off aceptado:** el prompt literal lo copia el modelo, no un script. Es una instrucción, no un control. Además, un parser de Karma va contra "el plugin no depende del stack", pero Karma ya está medido.

## 6. Riesgos
- **Fuga al repo público:** un docstring, un fixture o una nota con un nombre de la fuente. CA-26 en cada paso, y los fixtures ya se revisaron con un grep (sin coincidencias).
- **`Prompts` publica el pedido literal:** en este repo, un pedido con datos privados quedaría en el historial. La regla 10 lo advierte.
- **Prompt alterado:** el modelo puede resumir o recortar un `$ARGUMENTS` largo. CA-1 lo mide con un texto de varias líneas.
- **Otra versión de Karma:** puede cambiar el formato. Si pasa, cae en el modo genérico, que sigue funcionando.
- **Fixtures de Windows:** las capturas salen de un solo entorno (Windows, Chrome 157).
- **`origin/main` se mueve:** si avanza con un cambio en `plugins/` antes del merge, CA-20 puede fallar.
- **Enlaces del CHANGELOG** (`:24-25`): apuntan a `stepwise--v1.0.0`, un tag que no existe en el remoto.

## 7. Pasos de Implementación
1. **Paso 1: la clave `Prompts` en `/spec`** (CA-1 a CA-8, CA-26):
   - `plugins/stepwise/skills/spec/SKILL.md`: frontmatter, regla de archivos, §0, §4, §5, §6 y §7;
   - `plugins/stepwise/README.md`: `skills/spec/` y `:73`;
   - `plugin.json` en `1.1.0` y `tests/test_plugin_version.py:257`;
   - `CHANGELOG.md`.
2. **Paso 2: ANSI y Karma en `run_tests.py`** (CA-9 a CA-20, CA-26):
   - `run_tests.py` (regex, `output_lines`, `karma_failures`, `summaries()`, modo genérico y docstring);
   - `test_run_tests.py` (el `{ESC}` de `emit.py`, y las clases de ANSI y de Karma);
   - los 7 fixtures;
   - `plugins/stepwise/README.md:34`, `:70`;
   - `CHANGELOG.md`.
3. **Paso 3: documentación** (CA-21 a CA-26):
   - `README.md` (`:71-72`);
   - `docs/migration-template.md` (`:9`, `:15`, P1, R2, Anexos A, B y C);
   - `.claude/settings.json` y `CLAUDE.md`;
   - `docs/prompts/README.md`;
   - `docs/decisions/bootstrap/business-rules.md:86`.

## 8. Decisiones Abiertas
Ninguna.
