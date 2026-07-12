# Discussion Round 1 — #7066 fixer-rounds poisoning

## Decision 1: Work item 4 (prompt hardening) is deferred
- **Question**: Include the optional `complexity-baseline` ratchet example in `_ci_launcher.py:208` (work item 4), or defer it?
- **Resolution**: Defer. Rely on the generic regen guidance already present at `_ci_launcher.py:208`.
- **Source**: user

## Decision 2: Crashed-lane tier behavior — advance, not relaunch
- **Question**: When a fixer lane crashes (`BGJOB_RC != 0`), does tier selection record the crashed tier and advance, or relaunch the same tier once?
- **Resolution**: Advance. Record the crashed tier as attempted in `lineage-$LINEAGE_KEY.tsv`, emit `RESULT=retry-next-tool` while untried tiers remain, and `operator-bail` only when tiers are exhausted. Matches the issue's acceptance criteria.
- **Source**: user (confirming acceptance criteria)

## Decision 3: Crash diagnostics land in execution-issues.md
- **Question**: Where should the bounded redacted crash diagnostic (work item 3) be preserved so it survives `implement-finalize teardown`?
- **Resolution**: Append a bounded (~4 KiB), redacted entry to `$IMPLEMENT_TMPDIR/execution-issues.md`. The existing `run-log flush` / `run-log refresh` path copies it into the committed run log. This matches NEVER #20 ("durable diagnostics are bounded execution-issues.md warnings only"). Written from the Python finalize path, never via orchestrator reads of lane transcripts.
- **Source**: user

## Hard constraints (must preserve)

- **Integrity intent stays fail-closed**: after the work-item-1 fix, same-run-id duplicate attempts and malformed `fixer-rounds.tsv` rows still raise `LaneClosedError`. Only foreign (different-run-id) rows become non-fatal history.
- **Fix the input contract, not a reason string**: the ledger is cross-lineage history that the guard wrongly treats as single-lineage state. Do not add a `closed-failure` reason-string exception filter (per repo anti-pattern: root-cause over symptom).
- **`main()` recovery persist must succeed** in the cross-lineage scenario: the exception path that re-persists an `operator-bail` result must not trip the foreign-identity guard a second time.
- **Single-wait-owner rule intact**: the Step 8 prompt remains the sole bgjob wait owner; only `step-8-ci-fixer.sh --finalize` may validate envelopes and emit routing KVs.
- **No-evidence-reads rule intact**: the main agent must not read default-path CI evidence, merge envelopes, `fixer-status.env`, lane transcripts, or failure digests. Work items 2 and 3 happen inside the Python/bash finalize path, not in orchestrator reads.
- **Daemon is not at fault**: `python/larch/bgjob/daemon.py` and `model.py` are context only; do not change bgjob reap/result-env behavior.

## Non-goals

- Work item 4 (complexity-baseline prompt example) — deferred.
- No change to bgjob daemon reap/result-env semantics.
- No change to the complexity-baseline ratchet itself or to `checks_run_relevant.py` CI-delegation scoping.

## Open implementation decision (deferred to Step 2b + review)

- Work item 1 offers two shapes: (a) filter foreign rows in `_read_rounds` and scope duplicate-attempt rejection to the same run id, vs (b) scope the ledger per lineage (`fixer-rounds-<key>.tsv`). Minimum-change preference is (a); (b) is the considered alternative for reviewers to challenge.
