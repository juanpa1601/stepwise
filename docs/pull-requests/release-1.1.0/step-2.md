# [release-1.1.0] Paso 2: ANSI y Karma en `run_tests.py`

- **Rama:** `release-1.1.0-step-2`
- **Rama Destino (Sub-PR):** `release-1.1.0`
- **PR Principal:** `release-1.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-1.1.0/business-rules.md`

---

## 1. Resumen del Paso
`run_tests.py` quita los códigos ANSI de cada línea antes de buscar resúmenes y antes de reportar, también en el modo genérico. Además lee el resumen de Karma: la línea `TOTAL:` con `fullmatch`, los totales, los saltados y el tiempo de la última línea `Executed <x> of <y>`, y los fallos `<navegador> <test> FAILED` con su primera ubicación del proyecto. Entran 7 fixtures reales y sus tests. La versión sigue en `1.1.0`. Cubre CA-9 a CA-20 y CA-26.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/scripts/run_tests.py`:
  - las regex `_KARMA_TOTAL`, `_KARMA_EXECUTED`, `_KARMA_FRAME`, `_URL_SCHEME` y `_ANSI`;
  - las funciones `output_lines` y `karma_failures`;
  - la rama de Karma en `summaries()`, y el modo genérico sin ANSI;
  - el docstring.
- `plugins/stepwise/scripts/tests/test_run_tests.py`: `emit.py` cambia `{ESC}` por el byte `0x1b`; clases `AnsiTests` (3 tests) y `KarmaTests` (10 tests); `assert_no_escape` en `ProjectCase`; el docstring nombra las capturas.
- `plugins/stepwise/scripts/tests/fixtures/`: `karma_ok.txt`, `karma_fail.txt`, `karma_skip.txt`, `pytest_color_pass.txt`, `pytest_color_pass_plain.txt`, `pytest_color_fail.txt` y `pytest_color_fail_plain.txt`.
- `plugins/stepwise/README.md`: **Reporte** con Karma y ANSI, **Modo genérico** sin Karma, y la línea de tests con los fixtures nuevos.
- `CHANGELOG.md`: la línea de Karma en `[Unreleased]` → `### Added`.
- `docs/decisions/release-1.1.0/business-rules.md`: la última frase de CA-13 (aprobada por el usuario en `/implement`).
- `docs/pull-requests/release-1.1.0/step-2.md`: esta trazabilidad.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| CA-13: un fallo sale sin ubicación cuando no queda ningún frame del proyecto fuera de `node_modules/` | `project_path` no mira si el archivo existe, así que "si el spec no está en el proyecto" no se podía verificar (aprobado por el usuario) |
| Los frames con esquema de URL (`http:`, `webpack:`) no cuentan como ubicación | Code review R1, elección del usuario: sin source map, Karma imprime el bundle servido, que no es un archivo del proyecto |
| Los fixtures se escribieron con Write y se compararon por sha256 con las capturas | El hook `block_inplace_edits` no deja copiarlos desde el shell; los 7 son idénticos byte a byte |

## Pruebas
- **Suite completa (`Tests (full)`):** `python3 -m unittest discover plugins/stepwise/hooks/tests && python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests && python3 -m unittest discover plugins/stepwise/scripts/tests && python3 -m unittest discover tests`:
  - `plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped, en 24.837s;
  - `plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped, en 18.227s;
  - `plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped, en 1.818s;
  - `plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped, en 18.381s;
  - `tests`: 25 total, 0 failed, 0 errors, 0 skipped, en 4.474s.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 2 CA, 2 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos del code review: R1 en `run_tests.py`, R1 a R3 en `test_run_tests.py`).
- **Huella:** sha256:1ebd660dec22c43dc3a81e1648c6e87eb05b11d91d0e4d85b9a5c8958154d849

### Verificación manual
- **CA-19:** el docstring de `run_tests.py`, el README del plugin y el CHANGELOG dicen que el script lee Karma y quita ANSI.
  - Pasos: 1. Leer el docstring de `plugins/stepwise/scripts/run_tests.py` (`:14-20`). 2. Leer en `plugins/stepwise/README.md` la viñeta **Reporte** (`:37`), **Modo genérico** (`:38`) y la línea de tests (`:74`). 3. Leer `[Unreleased]` de `CHANGELOG.md`.
  - Esperado: el docstring nombra Karma y el quitado de ANSI; el README dice que el script lee Karma y quita ANSI, "Modo genérico" ya no nombra Karma y la línea de tests nombra los fixtures de Karma y de color; `[Unreleased]` trae la línea de Karma.
  - Obtenido:
    - el docstring dice que la salida "loses its ANSI codes (``ESC[`` + parameters + a letter) line by line" y que se lee "for pytest, unittest and Karma", con `TOTAL:` y la última línea `Executed <x> of <y>`;
    - en el README, **Reporte** nombra Karma (`TOTAL:`, `Executed <x> of <y>`, `<navegador> <test> FAILED`) y el quitado de ANSI, también en el modo genérico; **Modo genérico** dice "(Jest, `flutter test`)"; la línea de tests dice "con salidas reales de pytest, unittest y Karma como fixtures, y pares de pytest con y sin `--color=yes`";
    - `[Unreleased]` → `### Added` tiene **Karma in `scripts/run_tests.py`**, debajo de la línea de `Prompts`.
  - Ejecutó: Claude
- **CA-26:** el diff del paso no trae ningún término de la fuente.
  - Pasos: 1. Pasar las líneas agregadas de `git diff HEAD` (archivos con seguimiento) por el grep de la lista de términos de la regla 1, sin distinguir mayúsculas, que incluye las carpetas temporales locales. 2. Pasar el contenido completo de cada archivo sin seguimiento (`git ls-files --others --exclude-standard`: los 7 fixtures y esta trazabilidad) por el mismo grep.
  - Esperado: ninguna coincidencia.
  - Obtenido: 0 coincidencias en las líneas agregadas y 0 en cada uno de los 7 fixtures; lo mismo al repetirlo después de los arreglos R1 a R3 del code review. Además, los 7 fixtures son idénticos byte a byte a las capturas de origen (mismo sha256), y `run_tests.py` y `test_run_tests.py` solo difieren del origen en lo saneado (el nombre del proyecto, las referencias a ADR y CA) y en el ejemplo de minutos de CA-18 (`1 min 5.5 secs` → `65.5s`). Después del code review difieren además por R1 (los frames con esquema de URL no son ubicación), R2 (el caso `1 sec` en el tiempo total) y R3 (`assert_no_escape` en `ProjectCase`).
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **0 bloqueantes, 3 sugerencias y 0 preguntas.** El usuario eligió arreglar las tres.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | suggestion | `karma_failures` tomaba como ubicación del proyecto un frame con URL (`http://localhost:9876/...`, `webpack:///...`), porque `project_path` lo acepta como ruta relativa, también en Windows | Arreglado: `_URL_SCHEME` en `run_tests.py`, y esos frames no cuentan como ubicación; test nuevo `test_location_skips_url_frames` |
| R2 | suggestion | CA-18: el `sec` singular solo se probaba en el tiempo neto, no en el total que da `Totals:` | Arreglado: caso `("1 sec / 0.5 secs", "1s")` en `test_minutes_and_singular_seconds` |
| R3 | suggestion | `assert_no_escape` estaba copiado en `AnsiTests` y en `KarmaTests` | Arreglado: una sola vez, en `ProjectCase` |

- **Pasada sobre los arreglos:** R1, R2 y R3 `fixed`.
- **Deuda:** ninguna.
- **Huella:** sha256:1ebd660dec22c43dc3a81e1648c6e87eb05b11d91d0e4d85b9a5c8958154d849

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados y suite completa en verde (o fallos preexistentes registrados con la decisión del usuario).
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-1.1.0/step-2.md`.
