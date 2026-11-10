# [FEATURE] {{FEATURE_NAME}}: {{DESCRIPCION_GENERAL}}

- **Rama:** `{{FEATURE_BRANCH}}`
- **Rama Destino:** `{{BASE_BRANCH}}`
- **Documento de Decisiones:** `{{DECISION_DOC}}`

---

## Resumen de la Funcionalidad
<!-- Descripción ejecutiva de la feature completa para el equipo. -->

## Pasos
<!-- El checklist que /spec creó y /close fue marcando: se conserva tal cual, con el número de cada Sub-PR y su trazabilidad. -->
- [x] **Paso 1:** resumen (CA-1, CA-2) — #<sub-pr> · `<traceability file>`
- [ ] Verificación después del merge (paso 1, CA-2): <pasos>
<!-- Una por cada verificación manual marcada `después del merge`; se marcan al confirmarlas. Sin ninguna, borra el ejemplo. -->

## Reglas de Negocio Implementadas
<!-- Síntesis de las reglas principales del ADR. -->
- Regla 1

## Verificación Global
<!-- Del `## Pruebas` del último paso. -->
- **Suite completa (`Tests (full)`):** `<command>`: <N> total, <N> failed, en <time>.
- **Lint/format, Type check, Migrations check:** <resultado o `none`>.

## Verificación de instalación desde `develop`
<!-- Obligatoria si el PR va hacia `main` y el repo publica plugins (tiene `.claude-plugin/marketplace.json` en la raíz). En cualquier otro PR, borra la sección y su ítem del checklist. Sin ella, ese PR a `main` no está listo para revisión. -->
- **Proyecto:** <repo y rama de prueba que no se mergea, o proyecto desechable con remoto en GitHub>.
- **Instalación:** `<comandos exactos, p. ej. /plugin marketplace add <owner>/<repo>#develop y /plugin install <plugin>@<marketplace>>`, con la versión de Claude Code y el commit instalado (`gitCommitSha` de `installed_plugins.json`).
- **Paso chico corrido con el flujo:** `/spec` → `/implement 1` → `/check` → `/close`, con el resultado de cada uno y cualquier fallo.

## Checklist de Entrega
- [ ] Todos los pasos mergeados en `{{FEATURE_BRANCH}}`.
- [ ] Suite completa en verde.
- [ ] Verificaciones después del merge confirmadas (o ninguna).
- [ ] ADR y trazabilidad de cada paso completos.
- [ ] Instalación verificada desde `develop` (sección anterior; solo en un PR a `main` de un repo que publica plugins).
