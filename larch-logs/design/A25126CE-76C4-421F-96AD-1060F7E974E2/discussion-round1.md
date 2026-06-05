## Decision 1: Cutover scope (LARCH_SHIP_PR_IMPL)
- **Question**: Should this work flip the default finalize path to Python, or stay parity-only?
- **Resolution**: Parity-only. Keep bash (ship-pr.sh / implement-finalize.sh) as the shipped default; Python stays dev/CI-only. Do NOT flip LARCH_SHIP_PR_IMPL (defaults to bash per python/config.py:56 and scripts/test-implement-structure.sh). The cutover flip is a separate future step.
- **Source**: user

## Decision 2: Parity depth
- **Question**: Port only the enumerated divergences, or do a full behavioral audit?
- **Resolution**: Full behavioral audit — audit every branch of scripts/implement-finalize.sh and scripts/local-cleanup.sh and match it in python/finalize.py, beyond the enumerated divergences.
- **Source**: user

## Decision 3: Cross-file divergence scope
- **Question**: Include the enumerated divergences whose code lives outside the issue's Files list (_postmerge_should_flush in ship.py, stage_and_push in ci_monitor.py)?
- **Resolution**: Yes — include python/ship.py and python/ci_monitor.py. Total 6 implementation/test files (finalize.py, run_logs.py, ship.py, ci_monitor.py + their tests).
- **Source**: user

## Decision 4: Fail-closed parity gate surface
- **Question**: Create a new `make test-merge-parity` Makefile target, or wire fail-closed into existing py-test?
- **Resolution**: Wire fail-closed into existing `make py-test` — add an in-module guard so bash-present runs cannot all-skip (fail rather than skip when bash is present). No new Makefile target. The Makefile change is limited to correcting the stale shard-balance comment that claims test-ship-pr was removed; docs/linting.md refresh corrects existing rows (test-merge-pr race-gate mention) and documents the parity gate behavior under py-test.
- **Source**: user

## Decision 5: Bash reference is untouched (hard constraint)
- **Question**: Is this a one-directional port (Python matches bash; bash unchanged)?
- **Resolution**: Yes. scripts/implement-finalize.sh, scripts/local-cleanup.sh, scripts/merge-pr.sh remain the reference and must NOT change behavior. Python is brought to parity with them. Bash stays the shipped default; behavioral parity is asserted Python-vs-bash via real subprocess parity tests.
- **Source**: codebase + Decision 1
