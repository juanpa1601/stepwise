# [release-2.1.0] Paso 2: README del plugin en inglés

- **Rama:** `release-2.1.0-step-2`
- **Rama Destino (Sub-PR):** `release-2.1.0`
- **PR Principal:** `release-2.1.0` $\rightarrow$ `main`
- **Documento de Decisiones:** `docs/decisions/release-2.1.0/business-rules.md`

---

## 1. Resumen del Paso
Traduce al inglés `plugins/stepwise/README.md`, como ya estaban el README raíz y el `CHANGELOG.md`, sin agregar ni quitar contenido: los textos que escriben o buscan las skills quedan literales entre backticks, y un párrafo inicial explica por qué. `## Versionado` pasa a `## Versioning`, y el enlace del `CHANGELOG.md` apunta a `#versioning`. Cubre CA-9, CA-15 y CA-16.

## 2. Qué se hizo (Detalle de Cambios)
- `plugins/stepwise/README.md`: la traducción, sección por sección, desde el texto de stepwise.
- `CHANGELOG.md`: el ancla `#versioning` en `:3` y la viñeta del README en `### Changed` de `[Unreleased]`.

## 3. Decisiones Específicas del Paso
| Decisión | Justificación / Por qué |
|---|---|
| Se agrega un párrafo que explica que los marcadores de las skills quedan en español. | Es una nota de traducción, no una regla nueva; el usuario la eligió en la revisión (R5). |
| Los marcadores de posición (`<ruta>`, `<modo>`, `ruta:línea`…) se traducen; los textos que escriben las skills (`(manual: <motivo>)`, `Ejecutó: usuario`…) no. | Los primeros son solo para quien lee; los segundos los escriben o buscan las skills (CA-9). |
| La versión del README sigue en `2.0.0`. | El paso 2 no cambia contenido; el paso 3 la sube a `2.1.0` (CA-14). |

## Pruebas
- **Tests del paso (`Tests (step)`):** `python3 -m unittest tests/test_plugin_version.py tests/test_shared_blocks.py tests/test_path_lengths.py tests/test_full_suite_owner.py`: 41 total, 0 failed, 0 errors, 0 skipped, en 4.393s.
- **Migrations check:** `none`.
- **Lint/format:** `none`.
- **Type check:** `none`.
- **Alineación del plugin:** Plugin: no habilitado; Marketplace: no declarado.
- **Intentos:** 0.
- **Arreglos:** ninguno.
- **Fallos preexistentes que se dejaron:** ninguno.
- **Verificación manual:** 2 CA, 2 ok, 0 pendientes de confirmar por el usuario, 0 después del merge (ver abajo).
- **Corrida en `/close`:** la huella cambió (arreglos de la revisión R2 a R4).
- **Huella:** sha256:cab7cab2ea840292a232ad1fa4ad264093bcb86544af6beeb0df8b989983800f

### Tests del paso
- `tests/test_plugin_version.py`
- `tests/test_shared_blocks.py`
- `tests/test_path_lengths.py`
- `tests/test_full_suite_owner.py`

### Verificación manual
- **CA-9:** `plugins/stepwise/README.md` está en inglés, dice lo mismo que en `main`, conserva literales los textos de las skills, `## Versioning` reemplaza a `## Versionado` y `[Unreleased]` trae la viñeta `Changed`.
  - Pasos: 1. Comparar sección por sección `git show release-2.1.0:plugins/stepwise/README.md` con el archivo nuevo. 2. Extraer los spans entre backticks y los enlaces de las dos versiones (fuera de los bloques de código) y comparar los conjuntos. 3. `grep -rn 'stepwise/README.md#'` en el repo para los enlaces con ancla. 4. Leer `CHANGELOG.md:3` y `[Unreleased]`.
  - Esperado: el texto de CA-9.
  - Obtenido: mismas secciones, entradas y ejemplos; la única línea nueva es el párrafo inicial que explica que los marcadores de las skills quedan en español, y "La introducción en inglés" pasa a "The introduction". Los enlaces son los mismos. Los spans que cambian son solo marcadores de posición traducidos (`<ruta>` → `<path>`, `<modo>` → `<mode>`, `<AAAA-MM-DD>` → `<YYYY-MM-DD>`, `<navegador>` → `<browser>`, `<versión>` → `<version>`, `<archivo>` → `<file>`, `ruta:línea` → `path:line`, `<descripción>` → `<description>`); los nuevos son marcadores citados (`## Pruebas`, `### Tests del paso`, `ninguno`, `pendiente`, `después del merge`, `Faltan`). `(manual: <motivo>)`, `Ejecutó: usuario`, `sin tests del paso`, `Huella de código`, `Verificación Global`, `pendiente de /regression`, `Paso de corrección`, `válido`, `no aplica` y `requiere decisión` siguen literales. El único enlace con ancla al README era `CHANGELOG.md:3`, que ahora apunta a `#versioning`. `[Unreleased]` tiene `### Changed`. La versión del README sigue en `2.0.0`: el paso 3 la sube (CA-14). Después de los arreglos R2 a R4 de la revisión (solo redacción en inglés de `README.md:10`, `:12` y `:107`), se repitió la comparación de spans y enlaces: sin cambios en lo anterior.
  - Ejecutó: Claude
- **CA-16:** el diff del paso no trae ninguno de los términos de la regla 1 (también rutas locales con `/`).
  - Pasos: 1. Desde la raíz, `git diff release-2.1.0` y sus líneas agregadas. 2. Buscar sin distinguir mayúsculas la lista de términos de la regla 1 (en la memoria privada de Claude), más las referencias a ADR del origen y a sus secciones propias.
  - Esperado: ningún término; un hallazgo es un `blocker`.
  - Obtenido: `grep` sin coincidencias (exit 1), también después de los arreglos de la revisión (el diff y esta trazabilidad). El texto se tradujo del README de stepwise, no se copió el del origen.
  - Ejecutó: Claude

## Code review
`stepwise:code-reviewer` sobre el diff local del paso: **0 bloqueantes, 4 sugerencias y 1 pregunta.** El usuario eligió arreglar las cuatro sugerencias.

| id | Tipo | Hallazgo | Resultado |
|---|---|---|---|
| R1 | suggestion | La verificación de CA-16 citaba el título de una sección del README del origen. | Arreglado: se quitó el literal. |
| R2 | suggestion | `README.md:10` calcaba el orden del español ("in `claude -p`, no"). | Arreglado: "after 180 s in interactive, VS Code or CLI sessions; not in `claude -p`". |
| R3 | suggestion | `README.md:12`: "The "read-only" of Bash is in its instructions" era poco claro. | Arreglado: "Bash is read-only only through its instructions". |
| R4 | suggestion | `README.md:107`: "project scope" no es lo que explica el README raíz. | Arreglado: "project setup". |
| R5 | question | ¿El párrafo nuevo de `README.md:7` encaja en "dice lo mismo" de CA-9? | El usuario eligió dejarlo: es una nota de traducción. |

- **Pasada sobre los arreglos:** R1 a R5 `fixed`; sin bloqueantes nuevos.
- **Deuda:** ninguna.
- **Huella:** sha256:cab7cab2ea840292a232ad1fa4ad264093bcb86544af6beeb0df8b989983800f

## Checklist del Paso
- [x] Código implementado según los CA del paso en el ADR.
- [x] Tests del paso creados, listados en "Tests del paso" y en verde (o fallos preexistentes registrados con la decisión del usuario). La suite completa la corre `/regression`.
- [x] Code review sin `blocker` abierto.
- [x] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [x] Trazabilidad registrada en `docs/pull-requests/release-2.1.0/step-2.md`.
