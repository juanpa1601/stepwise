# [release-2.1.0] Regresión

- **Fecha:** 2026-11-21
- **Rama:** `release-2.1.0`
- **Commit probado:** `638cf66ea5f24dd769d7bf5adf303cdc18d2191f`
- **Comando:** `python3 -m unittest discover plugins/stepwise/hooks/tests && python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/worktree/scripts/tests && python3 -m unittest discover plugins/stepwise/scripts/tests && python3 -m unittest discover tests`
- **Totales:**
  - `python3 -m unittest discover plugins/stepwise/hooks/tests`: 30 total, 0 failed, 0 errors, 0 skipped in 29.725s
  - `python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests`: 26 total, 0 failed, 0 errors, 1 skipped in 21.365s
  - `python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests`: 16 total, 0 failed, 0 errors, 0 skipped in 2.504s
  - `python3 -m unittest discover plugins/stepwise/skills/worktree/scripts/tests`: 56 total, 0 failed, 0 errors, 0 skipped in 33.697s
  - `python3 -m unittest discover plugins/stepwise/scripts/tests`: 51 total, 0 failed, 0 errors, 0 skipped in 20.421s
  - `python3 -m unittest discover tests`: 41 total, 0 failed, 0 errors, 0 skipped in 5.086s
- **Ejecutó:** segundo plano (`run_tests.py full --timeout 3600`)
- **Fallos preexistentes que se dejaron:** ninguno
- **Verificaciones después del merge:** 1 sin marcar: paso 3, CA-12 (sesión real sin Docker de `/stepwise:worktree new` y `remove`)
