# [release-1.1.0] Paso 3: compactación, perfil Angular y `Prompts` en este repo

- **Rama:** `release-1.1.0-step-3`
- **Rama Destino (Sub-PR):** `release-1.1.0`
- **PR Principal:** `release-1.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-1.1.0/business-rules.md`

---

## 1. Resumen del Paso
Este paso solo toca documentación y configuración, nada en `plugins/`:
- **Ventana de compactación:** la recomendación de `CLAUDE_CODE_AUTO_COMPACT_WINDOW` en `500000` va en el `README.md` y en la plantilla de migración, y este repo la declara en su `.claude/settings.json`.
- **Perfil Angular:** la plantilla trae el perfil Angular con Karma verificado (P1 y Anexos A, B y C), sin nombrar el proyecto medido.
- **`Prompts`:** este repo declara la clave en su `CLAUDE.md`, `docs/prompts/README.md` documenta la convención, y las tres líneas que nombran las claves opcionales ya incluyen `Prompts`.

Cubre CA-21 a CA-26.

## 2. Qué se hizo (Detalle de Cambios)
- `.claude/settings.json`: `env.CLAUDE_CODE_AUTO_COMPACT_WINDOW` en `"500000"`; `permissions.ask` sin cambios.
- `CLAUDE.md`: `- Prompts: docs/prompts/<feature>/`.
- `README.md`: **Optional keys** con `Prompts` (`:71`) y **Compaction window (recommended)** junto a **Permissions** (`:73`).
- `docs/migration-template.md`:
  - la viñeta "Anexos" (`:9`), con el Anexo C;
  - Referencias (`:15`), con `Prompts`;
  - P1, con la versión del SDK;
  - R2, con la variable en el `env`;
  - el Anexo A, con la columna Angular verificada y sus notas;
  - el Anexo B, con los casos 1, 3 y 5 confirmados;
  - el Anexo C nuevo, con el contrato del script.
- `docs/decisions/bootstrap/business-rules.md:86`: §3.4 nombra las claves opcionales `Docs paths` y `Prompts`.
- `docs/prompts/README.md`: nuevo, con la convención de `/spec`, el límite de 72 caracteres y el aviso de repo público.
- `docs/pull-requests/release-1.1.0/step-3.md`: esta trazabilidad.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| CA-22 se comprobó con `printenv` y no con `echo "$VAR"`, también con la variable quitada y con otro valor heredado | `claude -p` bloquea la expansión de variables en Bash, y el entorno de Windows de esta máquina ya trae la variable en `500000` |
| Los tiempos y conteos medidos del perfil Angular entran, sin nombre ni rutas del proyecto | La regla 9 pide "lo medido"; nada de eso identifica el proyecto |
| El Anexo C da solo el contrato, sin el texto de ningún script | Regla 1: no se copia código de proyectos |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 -m unittest discover plugins/stepwise/hooks/tests && python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests && python3 -m unittest discover plugins/stepwise/scripts/tests && python3 -m unittest discover tests`:
  - `plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped, en 20.427s;
  - `plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped, en 16.323s;
  - `plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped, en 1.688s;
  - `plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped, en 20.195s;
  - `tests`: 25 total, 0 failed, 0 errors, 0 skipped, en 5.618s. Incluye `test_path_lengths.py`, con `docs/prompts/README.md` y esta trazabilidad ya en el índice.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 5 CA, 5 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos del code review: R2 en `docs/prompts/README.md` y R3 en `README.md`; R1 pidió correrla con los archivos nuevos en el índice).
- **Huella:** sha256:f55822785c7e4bbcb8a3a9336944463edf4b13427e13dc03b1a132bb8584cddc

### Verificación manual
- **CA-21:** la ventana de compactación está en el `README.md`, en la plantilla y en el `.claude/settings.json` de este repo.
  - Pasos: 1. Leer `README.md:72-73`. 2. Leer el bloque R2 de `docs/migration-template.md` (`:95-108`). 3. Cargar `.claude/settings.json` con `json.load` y comparar `permissions.ask` con las 11 reglas de `main`, en orden.
  - Esperado: el README trae, junto a "Permissions", la recomendación de la regla 8 (valor, texto sin sufijo, por qué 500000, por qué en el proyecto y que el valor del proyecto le gana al de usuario); la plantilla pide la variable (se agrega si falta y se cambia si tiene otro valor, sin tocar el resto del `env`); el settings tiene el `env` y las mismas 11 reglas `ask` en el mismo orden.
  - Obtenido:
    - `README.md:73`, **Compaction window (recommended)**, justo después de **Permissions** (`:72`): `"CLAUDE_CODE_AUTO_COMPACT_WINDOW": "500000"` (a string, no suffix), 200K contra 1M, por qué el plugin no puede fijarla y que el valor del proyecto le gana al de usuario;
    - `docs/migration-template.md:108`: la viñeta de R2, con "se agrega si falta y se cambia si tiene otro valor, sin tocar el resto del `env`";
    - el settings da `{'CLAUDE_CODE_AUTO_COMPACT_WINDOW': '500000'}`, y `permissions.ask` tiene 11 reglas, iguales y en el mismo orden (`True`).
  - Ejecutó: Claude
- **CA-22:** una sesión nueva en la raíz de este repo ve la variable en `500000`.
  - Pasos: 1. En la raíz, correr `claude -p --allowedTools "Bash(printenv:*)" -- 'Run exactly this Bash command and reply with only its raw output, nothing else: printenv CLAUDE_CODE_AUTO_COMPACT_WINDOW'`. 2. Repetirlo con la variable quitada del entorno (`env -u CLAUDE_CODE_AUTO_COMPACT_WINDOW claude -p …`) y con otro valor heredado (`CLAUDE_CODE_AUTO_COMPACT_WINDOW=200000 claude -p …`).
  - Esperado: imprime `500000`.
  - Obtenido: `500000` en las tres corridas. La segunda y la tercera hacen falta porque el entorno de Windows de esta máquina ya trae la variable en `500000`: sin ellas no se sabría si el valor sale del proyecto. Con la variable quitada o en `200000`, sale `500000`, el valor del `.claude/settings.json` del proyecto. `echo "$CLAUDE_CODE_AUTO_COMPACT_WINDOW"`, el comando del CA, no sirvió en `claude -p`: el permiso de Bash lo bloquea porque expande una variable. `printenv` lee la misma variable sin expandir nada.
  - Ejecutó: Claude
- **CA-23:** la plantilla trae el perfil Angular de la regla 9.
  - Pasos: leer `docs/migration-template.md`: la viñeta "Anexos" (`:9`), P1 (`:41-42`), el Anexo A (`:141-176`), el Anexo B (`:178-208`) y el Anexo C (`:210-218`).
  - Esperado: P1 comprueba la versión del SDK y se detiene si no es compatible; el Anexo A tiene la columna verificada con `Tests (step)` por script, `Tests (full)` con `--progress=false`, `Type check` con `ngc` más `tsc` del tsconfig de specs (y por qué `tsc` solo no alcanza) y `Lint/format` con `ng lint`; el Anexo B tiene los casos 1, 3 y 5 confirmados (el 1, lleno desde `1.1.0`) y los casos 2 y 4 sin probar; el Anexo C da solo el contrato; nada nombra el proyecto ni sus rutas.
  - Obtenido:
    - `:9` nombra el Anexo C;
    - `:42` es la viñeta **Versión del SDK** (`npx ng version`, `flutter doctor`, se detiene, y el caso de Node 25.2.1 con Angular 18);
    - el Anexo A tiene la columna "Angular con Karma en el host (verificado en un proyecto Angular 18 con Karma, Windows con Git Bash)", con los cuatro valores y sus tiempos. La nota de `Type check` explica que `tsc` no revisa las plantillas (`TS2339` solo con `ngc`), y ya no sugiere el glob entre comillas ni una llamada por ruta;
    - el Anexo B confirma los casos 1 ("Desde `1.1.0`" y "hasta `1.0.0`"), 3 y 5, y la introducción dice que los casos 2 y 4 siguen sin probar en Angular;
    - el Anexo C tiene el contrato de 5 viñetas de la regla 9 (`createRequire` y `process.execPath` sin shell, un `--include` por argumento, 2 para un argumento con `-` o sin rutas, y el código de salida) y no trae el texto de ningún script.
  - Ejecutó: Claude
- **CA-24:** `Prompts` en `CLAUDE.md`, en `docs/prompts/README.md` y en las tres líneas que nombran las claves opcionales.
  - Pasos: leer `CLAUDE.md`, `docs/prompts/README.md`, `README.md:71`, `docs/decisions/bootstrap/business-rules.md:86` y `docs/migration-template.md:15`.
  - Esperado: `CLAUDE.md` declara `- Prompts: docs/prompts/<feature>/`; el README de prompts documenta la regla 10 (convención, límite de 72 caracteres y repo público); las otras tres líneas nombran `Docs paths` y `Prompts`.
  - Obtenido:
    - `CLAUDE.md:10` declara `- Prompts: docs/prompts/<feature>/`;
    - `docs/prompts/README.md` da el nombre, el contenido, que no se pisan, las rutas largas (40 caracteres más la feature, así que una feature de más de 32 no cabe) y el aviso de repo público;
    - `README.md:71` (**Optional keys**), `bootstrap:86` y `migration-template.md:15` nombran las dos claves.
  - Después del code review (R2 y R3), se leyó otra vez: el aviso de repo público de `docs/prompts/README.md` deja como vía reescribir el pedido antes de `/spec`, y aclara que `/spec` no ofrece "no guardarlo" al aprobar; `README.md:71` dice "in that folder, in the same commit as the ADR, which links it".
  - Ejecutó: Claude
- **CA-26:** el diff del paso no trae ningún término de la fuente.
  - Pasos: 1. Pasar las líneas agregadas de `git diff HEAD` (archivos con seguimiento) por el grep de la lista de términos de la regla 1, sin distinguir mayúsculas, que incluye las carpetas temporales locales. 2. Pasar el contenido completo de cada archivo sin seguimiento (`git ls-files --others --exclude-standard`: `docs/prompts/README.md` y esta trazabilidad) por el mismo grep.
  - Esperado: ninguna coincidencia.
  - Obtenido: 0 coincidencias en las líneas agregadas y 0 en `docs/prompts/README.md`. En la plantilla, el perfil Angular nombra solo "un proyecto Angular 18 con Karma", y la nota de lint usa "una sola carpeta de `src/app/`" en lugar de la ruta del proyecto medido.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **0 bloqueantes, 3 sugerencias y 0 preguntas.** El usuario eligió arreglar las tres.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | suggestion | CA-25: `test_path_lengths.py` solo mira `git ls-files`, y la suite de `/check` corrió con `docs/prompts/README.md` sin seguimiento | Arreglado: los dos archivos nuevos del paso quedan en el índice, y `/close` vuelve a correr la suite con ellos (ver "Pruebas") |
| R2 | suggestion | `docs/prompts/README.md` proponía pedirle a `/spec` que no guarde el prompt al aprobar, pero la skill solo ofrece "no guardarlo" cuando el archivo ya existe | Arreglado: la vía es reescribir el pedido antes de `/spec`, y lo otro queda dicho como algo que depende del modelo |
| R3 | suggestion | `README.md:71` decía "next to the ADR", pero el prompt va en la carpeta de `Prompts` | Arreglado: "in that folder, in the same commit as the ADR, which links it" |

- **Pasada sobre los arreglos:** R1, R2 y R3 `fixed`. Además encontró R1a (suggestion): los Pasos de CA-26 llaman "sin seguimiento" a `docs/prompts/README.md` y a esta trazabilidad, que desde R1 están en el índice. Así, `git ls-files --others` ya no los devuelve, aunque `git diff HEAD` sí los incluye.
- **Deuda:** R1a, como sugerencia nueva de la segunda pasada, que no se arregla sin revisión. El grep de CA-26 se corrió sobre los dos archivos, también después de indexarlos (0 coincidencias).
- **Huella:** sha256:f55822785c7e4bbcb8a3a9336944463edf4b13427e13dc03b1a132bb8584cddc

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados y suite completa en verde (o fallos preexistentes registrados con la decisión del usuario).
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-1.1.0/step-3.md`.
