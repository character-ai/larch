## Acceptance

- For a design run where `ARCHITECTURAL_GUIDELINES.md` is present and valid, the committed run log `larch-logs/design/<RUN_ID>/architectural-guideline-assessment.md` contains the clean note (`CLEAN_PRESENTATION_NOTE`) or the orchestrator-authored deviation text, written only from Gate C.
- When guidelines are `absent` or `invalid`, no `architectural-guideline-assessment.md` is committed; a stale artifact from a prior present visit is unlinked, and an unlink failure exits non-zero so Gate C halts.
- `python/cli.py architectural-guidelines persist-design-assessment` fails closed: `present` guidelines with neither or both of `--assessment clean` / `--assessment-file` exits non-zero; an unvalidated or symlinked `--design-tmpdir` or `--assessment-file` is rejected; the artifact is written atomically.
- The new verb is registered in the `python/cli.py` dispatch table and `_MACHINE_STDOUT_KEYS`; `python/test_design_cli_ports.py` asserts both.
- `audit-runs scan-run --skill design` emits the `guideline-assessment` scan: `pass` with `assessment_kind` (`clean`/`deviation`) when the file is present and non-empty, `informational` when missing, `fail` when empty or non-regular.
- `/fluff-analysis` emits a `## Guideline assessment coverage` section from manifest-enumerated design runs, including assessment-only runs with zero finding records, independent of `findings-classification.tsv`.
- `make py-test`, `make py-lint`, `make lint`, and `make test-fluff-analysis` pass.
