# Decisiones y Reglas de Negocio: {{FEATURE_NAME}}

- **Fecha:** {{FECHA}}
- **Tipo:** {{TIPO}} <!-- feature | bug -->
- **Rama Principal:** `{{FEATURE_BRANCH}}`
- **Fuente / Documento:** {{DOCUMENTO_O_REQUERIMIENTO_ORIGINAL}}

---

## 1. Contexto y Objetivo
<!-- Qué problema de negocio se resuelve y por qué. En un bug: qué falla, cómo se reproduce y qué se esperaba. -->

## 2. Criterios de Aceptación
<!-- Numerados y verificables con un test. En un bug, CA-1 es el test de regresión que reproduce el error. Un CA sin un test razonable (un paso que solo toca configuración o documentación, o algo que solo puede correr el usuario, como otra skill /stepwise:) lleva la marca "(manual: <motivo>)" y se verifica a mano; la marca la aprueba el usuario con el ADR. -->
- **CA-1:** Dado [estado inicial], cuando [acción], entonces [resultado esperado].
- **CA-2:** Dado [caso borde o error], cuando [evento], entonces [manejo esperado].
- **CA-3 (manual: [motivo]):** Dado [estado inicial], cuando [acción], entonces [resultado que se comprueba a mano].

## 3. Reglas de Negocio Clave
<!-- Invariantes que la lógica debe respetar (permisos, estados, límites). Cita la fuente: el usuario o `ruta:línea`. -->
1. **Regla 1:** ...

## 4. Fuera de Alcance
- ...

## 5. Solución y Trade-offs
- **Opción seleccionada:** ...
- **Alternativa descartada:** ...
- **Trade-off aceptado:** ...

## 6. Riesgos
- ...

## 7. Pasos de Implementación
<!-- Pasos chicos, cada uno con los CA que cubre. Un fix chico es un solo paso. -->
1. **Paso 1: [título]** (CA-1, CA-2): [alcance en una o dos líneas: qué archivos o módulos toca].

## 8. Decisiones Abiertas
<!-- Lo que el usuario dejó sin responder. No se rellena con supuestos. "Ninguna" si no hay. -->
1. ...
