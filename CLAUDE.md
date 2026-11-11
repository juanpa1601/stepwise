## Project commands
- Tests (step): python3 -m unittest
- Tests (full): python3 -m unittest discover plugins/stepwise/hooks/tests && python3 -m unittest discover plugins/stepwise/skills/close/scripts/tests && python3 -m unittest discover plugins/stepwise/skills/check/scripts/tests && python3 -m unittest discover plugins/stepwise/scripts/tests && python3 -m unittest discover tests
- Lint/format: none
- Type check: none
- Migrations check: none
- Base branch: main
- Decision docs: docs/decisions/<feature>/business-rules.md
- Traceability: docs/pull-requests/<feature>/step-<n>.md
- Prompts: docs/prompts/<feature>/
