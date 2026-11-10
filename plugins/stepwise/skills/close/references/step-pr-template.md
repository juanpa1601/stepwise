# [{{FEATURE_NAME}}] Paso {{STEP_NUM}}: {{DESCRIPCION_BREVE}}

- **Rama:** `{{FEATURE_BRANCH}}-step-{{STEP_NUM}}`
- **Rama Destino (Sub-PR):** `{{FEATURE_BRANCH}}`
- **PR Principal:** `{{FEATURE_BRANCH}}` $\rightarrow$ `{{BASE_BRANCH}}`
- **Documento de Decisiones:** `{{DECISION_DOC}}`

---

## 1. Resumen del Paso
<!-- 3 a 5 líneas: qué se implementó, por qué y qué CA cubre. -->

## 2. Qué se hizo (Detalle de Cambios)
- `ruta/archivo`: descripción del cambio

## 3. Decisiones Específicas del Paso
<!-- Decisiones puntuales del paso que complementan el ADR. Si no hay, una fila con "Ninguna". -->
| Decisión | Justificación / Por qué |
|---|---|
| | |

## Evidencia de regresión
<!-- Solo en un bug. La escribe /implement; /close la conserva tal cual. Si no aplica, borra la sección. -->

## Pruebas
<!-- La escribe /check, con la huella del paso; /close la conserva tal cual y solo la actualiza si la huella cambió. -->

## Code review
<!-- La escribe /audit self; /close la conserva tal cual. -->

## Checklist del Paso
- [ ] Código implementado según los CA del paso en el ADR.
- [ ] Tests del paso creados y suite completa en verde (o fallos preexistentes registrados con la decisión del usuario).
- [ ] Code review sin `blocker` abierto.
- [ ] Verificaciones `después del merge` agregadas al checklist del PR principal (o ninguna).
- [ ] Trazabilidad registrada en `{{TRACEABILITY_FILE}}`.
