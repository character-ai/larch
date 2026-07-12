## Pieces

### Piece 1: Dispatch extension and Bash adapter rewrites
- Scope: Extend all four Python verbs (`step5_review_main`, `step5_resume_main`, `step6_entry_main`, `run_step_checks_main`) in `dispatch_commit_route.py` with parent/child modes. Rewrite `step-5-review.sh`, `step-5-resume.sh`, `step-6-entry.sh`, `run-step-checks.sh` to thin wrappers. Update their Python unit tests and `test-step-5-review.sh`, `test-step-5-review.md`, `test-implement-timing-rehydration.sh`.
- Firm-headings: python/larch/implement/dispatch_commit_route.py, skills/implement/scripts/step-5-review.sh, skills/implement/scripts/step-5-resume.sh, skills/implement/scripts/step-6-entry.sh, skills/implement/scripts/run-step-checks.sh, skills/implement/scripts/test-step-5-review.sh, skills/implement/scripts/test-step-5-review.md, python/tests/implement/test_step_6_entry.py, python/tests/implement/test_run_step_checks.py, python/tests/implement/test_implement_dispatch.py, python/tests/review/test_review_and_fix.py, scripts/test-implement-timing-rehydration.sh
- Acceptance: `make test-step-5-review`, `make test-implement-anti-halt`, `make test-implement-relevant-checks-anti-halt`, Python unit tests green.
- Dependencies: none
- Size estimate: ~1600 lines

### Piece 2: CI-fixer adapter and harness/SKILL.md updates
- Scope: New `ci_fixer_adapter.py` porting step-8-ci-fixer.sh logic to Python. Register new verb in `cli.py`. Rewrite `step-8-ci-fixer.sh`. Update `test-step-8-ci-fixer.sh`. Update shared harnesses `test-implement-structure.sh`, `test-implement-fence-shape.sh`. Update `skills/implement/SKILL.md` prose.
- Firm-headings: python/larch/implement/ci_fixer_adapter.py, python/larch/cli.py, skills/implement/scripts/step-8-ci-fixer.sh, skills/implement/scripts/test-step-8-ci-fixer.sh, scripts/test-implement-structure.sh, scripts/test-implement-fence-shape.sh, skills/implement/SKILL.md
- Acceptance: `make test-implement-fence-shape`, `make test-implement-structure`, `make lint`, `make py-test` green.
- Dependencies: blocked-by Piece 1
- Size estimate: ~1800 lines
