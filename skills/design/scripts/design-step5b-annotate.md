# design-step5b-annotate.sh

## Purpose

Thin launcher-compat wrapper for the `/design` Step 5b annotate block.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- The `.sh` file only derives and exports `CLAUDE_PLUGIN_ROOT`, then execs `python/cli.py design step5b-annotate`.
- `python/cli.py design step5b-annotate` owns the OOS annotate behavior.
- The Python entrypoint binds `env = _rehydrate_wrapper_env(parsed)` before reading session keys.
- The `DESIGN_TMPDIR` guard rejects only an empty value, matching the retired Bash annotate prelude.
- The annotate entrypoint binds `oos_issue_stdout = design_tmpdir / "oos-issue.stdout.txt"` immediately after the tmpdir guard.
- The same `oos_issue_stdout` path is used for `--issue-stdout-file` and `ISSUES_FAILED` detection.
- The annotate entrypoint returns immediately through pause-save when `.pause-requested` exists.
- Annotate failure emits `STEP5B_STATUS=annotate-failed`; `.completed/step-5b` is also written when `oos-issue.stdout.txt` is present and non-empty (partial `/larch:issue` failures and skip-already annotate retries can continue to Step 5b.5). When `oos-issue.stdout.txt` is empty or missing (sequencing error), the sentinel is not written.

## Harness

Covered by `python/test_design_oos.py`, `python/test_design_cli_ports.py`, and `scripts/test-design-structure.sh`.
