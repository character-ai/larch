## Final Design Plan

## Plan

Create the first production rule built on `larch.lint.engine`. Scan tracked Python files under `python/larch/` for:

- `pylint: skip-file`
- Module-level `pylint: disable=R0801`
- Module-level `pylint: disable=duplicate-code`

Ignore strings, local or block-level disables, and narrow `disable-next` directives. Use a strict, reason-bearing baseline for existing debt. Do not allow inline rule metadata to suppress this gate.

### UPDATED: python/larch/lint/engine.py

- Let a `LintRule` opt out of inline suppression handling.
- Preserve current suppression behavior for existing and future rules that select it.
- Keep validation, discovery, baseline comparison, and exit codes unchanged.
- Use the unsuppressible mode for the new gate so a runtime module cannot disarm it with another pragma.

### UPDATED: python/tests/lint/test_lint_engine.py

- Prove unsuppressible rules retain findings even when the source adds a matching, reason-bearing lint pragma.
- Confirm ordinary rules still honor their existing suppression contract.
- Cover invalid rule configuration if the new option changes validation.

### NEW: python/larch/lint/lint_pylint_skip_file.py

- Define one `LintRule` and execute it through `run_rule` with `ProcRunner`.
- Scope discovery to tracked files under `python/larch/`.
- Tokenize comments so directive-like strings and docstrings do not match.
- Parse Pylint directive names and comma-separated values without relying on fragile substring matching.
- Report stable findings for `skip-file` and module-level `R0801` or `duplicate-code` disables.
- Run against `python/pylint-skip-file-baseline.json` with strict stale-row detection.
- Support guarded baseline regeneration through `--write` and `--initial-reason`.
- Return the engine’s `0`, `1`, and `2` outcomes unchanged.

### NEW: python/tests/lint/test_lint_pylint_skip_file.py

- Cover canonical and spacing variants of `skip-file`.
- Cover `R0801` and `duplicate-code` alone and inside comma-separated module-level disable lists.
- Confirm strings, docstrings, unrelated Pylint directives, `disable-next`, and indented local disables are ignored.
- Confirm tracked files outside `python/larch/`, including `python/tests/`, are excluded.
- Verify new findings, including malformed Python handled fail-closed by the rule, exit `1`; unreadable tracked files retain the engine’s `ScanError` behavior and exit `2`; invalid baseline state exits `2`; and fully baselined findings exit `0`.
- Verify stale rows fail and regeneration preserves existing reasons while refusing new rows without a reason.
- Pin deterministic finding text and baseline identities.
- Prove the rule cannot be bypassed with its own inline suppression pragma.

### NEW: python/pylint-skip-file-baseline.json

- Add rows for the 16 remaining tracked `python/larch/` modules that currently use `# pylint: skip-file`.
- Give every row a non-empty reason that identifies the deferred module debt.
- Do not baseline `_oos.py` or add rows for broad R0801 disables.
- Keep rows in the engine’s deterministic generic-baseline order.

### UPDATED: python/larch/issue/_oos.py

- Remove `# pylint: skip-file`.
- Run `make py-lint-duplicate-code` to expose the resulting R0801 clusters.
- Eliminate those clusters with the smallest behavior-preserving local helper extraction or reuse.
- Keep OOS parsing, stable-ID matching, rollup expansion, and fate scoring behavior unchanged.
- Use a narrow, reason-bearing block suppression only if extraction would add more complexity than it removes. Do not add a file-level suppression or baseline row.

### UPDATED: python/suppression-reason-baseline.json

- Regenerate the suppression-reason baseline after removing `_oos.py`’s `pylint: skip-file` pragma.
- Remove the stale `larch/issue/_oos.py` / `pylint-skip-file` identity while preserving valid existing rows and their reasons.

### UPDATED: python/larch/cli.py

- Register `python3 python/cli.py lint pylint-skip-file` with the new module’s `main`.

### UPDATED: Makefile

- Add lint, focused-test, and baseline-regeneration targets to `.PHONY`.
- Add `pylint-skip-file` to `py-lint-checks-fast`.
- Regenerate an existing baseline without replacing reasons.
- Require `--initial-reason` only when bootstrapping a missing baseline.

### UPDATED: .pre-commit-config.yaml

- Add an always-run local hook for the new CLI command.
- Trigger it for changes to runtime Python modules or `python/pylint-skip-file-baseline.json`.
- Keep `pass_filenames: false` because the engine owns tracked-file discovery and baseline comparison.

## Edge cases

- Match Pylint symbolic and numeric duplicate-code names without matching similar identifiers.
- Treat a module-level disable list containing R0801 as blanket even when it also lists other checks.
- Do not confuse comments inside functions with module-wide directives.
- Fail closed on malformed Python with a finding and exit `1`; unreadable tracked files retain the engine’s `ScanError` behavior and exit `2` without a stdout finding.
- Fail with validation errors for invalid baseline rows, duplicate identities, and stale rows.
- Preserve the separate `lint_suppression_reason` baseline and behavior.

## Failure modes

- If removing `_oos.py` from Pylint’s skip path reveals duplicate clusters, the change is incomplete until the full duplicate-code command passes.
- If `_oos.py`’s removed pragma leaves its suppression-reason baseline row behind, `make py-lint-checks-fast` will fail.
- If the new baseline gains `_oos.py`, a new violation, or an empty reason, fail validation.
- If rule wiring exists in only the CLI, Makefile, or pre-commit surface, the gate may not run consistently. Update all three together.
- If inline suppression remains enabled for this rule, the replacement gate recreates the bypass it is meant to close.

## Testing strategy

Run:

- `python3 -m pytest python/tests/lint/test_lint_engine.py python/tests/lint/test_lint_pylint_skip_file.py -q`
- `python3 -m pytest python/tests/issue/test_oos.py -q`
- `python3 python/cli.py lint pylint-skip-file`
- `python3 python/cli.py lint suppression-reason`
- `make py-lint-duplicate-code`
- `make py-lint-checks-fast`

Confirm `_oos.py` is scanned by duplicate-code, its stale suppression-reason baseline identity is removed, the 16 baseline warnings remain documented, unreadable tracked files produce the engine’s exit-`2` scan error, and no unbaselined skip-file or blanket R0801 disable passes.

difficulty: MODERATE
oversize_override: operator
diff_lines: 520
