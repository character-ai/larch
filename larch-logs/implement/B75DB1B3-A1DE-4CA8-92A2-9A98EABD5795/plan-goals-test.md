## Goal
Implement issue #7534: [IMPLEMENTING] lint-refactor: migrate occurrence baselines to the shared lint engine.

## Implementation Plan
Parent: #7529

## Summary

Move the occurrence-shaped private baselines in four legacy lint modules onto `larch.lint.engine`. The engine must become the only reader, comparator, reason preserver, serializer, atomic writer, and read-back verifier for these baseline files.

This issue covers:

- `python/larch/lint/lint_env_via_config_constant.py`
- `python/larch/lint/lint_lifecycle_prefix_literal.py`
- `python/larch/lint/lint_subprocess_via_runner.py`
- `python/larch/lint/lint_suppression_reason.py`
- focused engine and lint tests under `python/tests/lint/`
- removal of the corresponding rows from `python/lint-engine-adoption-baseline.json`

Keep the PR below 2,000 changed lines. Split this issue before implementation if the measured diff would exceed that cap.

## Required behavior

1. Convert each detector result to `larch.lint.engine.Finding` and run baseline check/write through `run_rule` or `run_rule_cli`.
2. Configure exact occurrence identities:
   - env-via-config-constant: `file + qualified_symbol + env_name + constant + access + occurrence`
   - lifecycle-prefix-literal: `file + qualified_symbol + token + constant + context + occurrence`
   - subprocess-via-runner: `file + qualified_symbol + callee + occurrence`
   - subprocess gh rule: `file + qualified_symbol + occurrence`
   - suppression-reason: `file + suppression_kind + text + occurrence`
3. Add the smallest engine extension needed for occurrence rows whose committed schema omits `qualified_symbol`. Do not synthesize or serialize a shadow `qualified_symbol` for suppression-reason rows.
4. Preserve each existing exemptions and inline-pragma policy. Exemptions remain separate inputs, not baseline rows.
5. Preserve current exit precedence: internal or baseline errors return 2, live unbaselined findings or strict stale rows return 1, and a fully baselined scan returns 0.
6. Preserve current warnings for matching baseline findings where the legacy lint emits them.
7. `lint_subprocess_via_runner.py` owns two committed baselines. Run both rules and combine results without letting one clean result mask the other rule's finding or error.
8. Use engine path validation, trusted reads, atomic writes, byte read-back, structural read-back, duplicate detection, stale detection, and reason preservation. Delete private `*-baseline.json` load/write/serialize/compare code after parity is established.

## Byte-stable baseline contracts

A write with unchanged live findings must leave these payload shapes and field order unchanged:

- `python/env-via-config-constant-baseline.json`
- `python/lifecycle-prefix-literal-baseline.json`
- `python/subprocess-via-runner-baseline.json`
- `python/subprocess-via-runner-gh-baseline.json`
- `python/suppression-reason-baseline.json`

Do not rename files, add fields, remove fields, rewrite reasons, change occurrence numbering, or normalize relative paths. In particular, suppression-reason rows must remain valid without `qualified_symbol`.

## CLI compatibility

Keep the registered commands and accepted flags unchanged:

- `python3 python/cli.py lint env-via-config-constant [--root ROOT] [--write] [--initial-reason TEXT]`
- `python3 python/cli.py lint lifecycle-prefix-literal [--root ROOT] [--write] [--initial-reason TEXT]`
- `python3 python/cli.py lint subprocess-via-runner [--root ROOT] [--write] [--initial-reason TEXT]`
- `python3 python/cli.py lint suppression-reason [--root ROOT] [--write] [--initial-reason TEXT]`

Help remains exit 0. Invalid usage and blank `--initial-reason` remain exit 2.

## Tests and acceptance

Add or update focused tests that prove:

- every legacy baseline payload parses through the engine;
- unchanged write mode is byte-stable for all five files;
- an existing reason survives regeneration;
- a new row without `--initial-reason` fails closed;
- duplicate live identities fail closed;
- missing, malformed, symlinked, and path-escaping baselines follow engine policy;
- strict stale behavior and matching-baseline warnings match each legacy command;
- suppression rows missing `qualified_symbol` round-trip unchanged;
- subprocess and gh baseline results aggregate with error greater than finding greater than clean precedence;
- the four modules no longer perform direct private baseline I/O;
- their baseline-I/O and argparse rows disappear from `python/lint-engine-adoption-baseline.json`;
- targeted pytest, ruff, pyright, pylint, and `python3 python/cli.py lint engine-adoption --root .` pass.

Do not change committed baseline contents merely to make tests pass.

## Test plan
(no test plan section in plan-file)
