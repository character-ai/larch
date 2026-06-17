# Round 1 — Scope and Constraints (issue #4630)

sh-to-py G1: port the `review_pipeline.py` `run_legacy` bodies in-process.

## Decision 1: Port faithfulness
- **Question**: How faithful should the bash to Python port be?
- **Resolution**: Port plus opportunistic cleanup. Simplifying awkward bash logic is allowed during the port; not a strict 1:1 transcription.
- **Source**: user

## Decision 2: Slice granularity
- **Question**: One plan/PR for all 6 bodies, or allow splitting?
- **Resolution**: Keep all 6 bodies in one plan/PR. The slice is already decomposed from umbrella #3692; the bodies share `review_pipeline.py` state and the `run_legacy` removal is atomic.
- **Source**: user

## Decision 3: Test coverage
- **Question**: Replicate the deleted bash harnesses, or baseline coverage?
- **Resolution**: Baseline new-function coverage. Focused pytest over the new Python functions; do not 1:1 replicate every old harness case.
- **Source**: user

## Decision 4: Orphaned private helpers
- **Question**: How to treat private helpers (e.g. `scripts/lib-prune-decision.sh`) that the in-scope bodies source but the 6-body list omits?
- **Resolution**: Absorb helpers whose only live bash consumers are the ported bodies. Port `lib-prune-decision.sh` logic into the Python module and delete it plus its harness. Keep genuinely shared infra (`lib-quiet.sh`, and any helper still sourced by out-of-scope bash) as bash and call it from Python.
- **Source**: user

## Decision 5: Output-contract stability under cleanup
- **Question**: Must KV/FD-3 output contracts stay byte-stable during cleanup?
- **Resolution**: Contract changes are allowed, but every in-repo consumer must be updated in the same PR. This includes out-of-scope façade bash (`aggregate-findings.sh`, `tally-code-votes.sh`), skill `.md` parsers, and tests. Prefer byte-stable contracts where cleanup gains nothing; change a contract only when the consumer update stays contained.
- **Source**: user

## In-scope bodies (port to `python/review_pipeline.py`)
- `python/legacy_review_shell/review-core.sh` (orchestrator)
- `python/legacy_review_shell/dispatch-panel.sh`
- `python/legacy_review_shell/collect-findings.sh`
- `python/legacy_review_shell/gather-context.sh`
- `python/legacy_review_shell/check-reviewer-failure-threshold.sh`
- `scripts/reviewer-prune.sh`
- `scripts/lib-prune-decision.sh` (absorbed per Decision 4)

## Out of scope (stay bash; invoked from the Python port)
- `aggregate-findings.sh`, `compose-review-findings.sh` — `review_aggregate.py` / `compose_review.py` façades (C1b #3677).
- `tally-code-votes.sh`, `emit-tally.sh`, `log-phase.sh` — `review_tally.py` façade.
- `skills/review/scripts/prune-nit-findings.sh` — separate review-skill helper.
- `scripts/lib-quiet.sh` — shared FD-3 infra; Python uses native `quiet_init` / `emit_kv` / `BreadcrumbWriter`.
- `scripts/lib-failed-agent-stderr-tail.sh` — keep bash if still sourced by out-of-scope bash; otherwise reassess.

## Consumers to cut (hard cutover, same PR)
- Skills: `skills/review/SKILL.md`, `skills/review/references/heavy-worker.md`, `skills/review/scripts/prune-nit-findings.md`, `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, `skills/shared/voting-protocol.md`.
- Python: `python/review_pipeline.py` (remove `run_legacy`), `python/review_and_fix.py` (cut its `reviewer-prune.sh` subprocess call). `python/run_logs.py` references only batch/data filenames; no cut needed.
- Docs: `docs/external-reviewers.md`, `docs/linting.md`, `docs/run-logs.md`, `docs/python-migration.md`.

## Hard constraints (must not break)
- `review-core.py` keeps invoking the out-of-scope façades (`aggregate-findings.sh`, `tally-code-votes.sh`, `emit-tally.sh`) via their `cli.py review …` verbs or equivalent boundary calls; those bodies remain bash.
- `reviewer-prune` port must serve BOTH `/review` (review-core, dispatch-panel) AND `/design` plan-review consumers.
- Stdlib-only, Python ≥ 3.11; subprocess through `proc.py`; flat `python/` layout; no `LARCH_*_IMPL` selectors; no shims.
- DoD: append deleted paths to `python/migrated-scripts.tsv`; `make lint && make py-lint && make py-test` green; `make lint-retired-scripts` clean.
