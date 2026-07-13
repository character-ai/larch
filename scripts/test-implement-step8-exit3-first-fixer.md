# test-implement-step8-exit3-first-fixer.sh

Pins the Step 8+ ci-fix contract after issue #7192. The autonomous CI-fix path is now a ci-fixer subagent round loop authored inline in `skills/implement/SKILL.md` (spawn `larch:ci-fixer`, continue via `SendMessage`, parse the three `FIXER_*` lines), with the agent contract in `agents/ci-fixer.md`. `ship-pr-exit-matrix.md` keeps the `ci-fix` bullet routing only and carries the new `CI_ERRORS_FILE` / `CI_ERRORS_DISTILL_CLASS` handoff keys and the `ci-fix-no-progress`, `ci-evidence-unavailable`, and `ci-fix-exhausted` bail reasons.
