# Review Round 2

- Mode: `diff`
- 8 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Relocated legacy scripts use wrong PLUGIN_ROOT/REPO_ROOT and MARKER_HELPER paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-review-cli-parity-output.txt, dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: After relocation from `skills/review/scripts/` to `python/legacy_review_shell/`, eight legacy scripts still compute `PLUGIN_ROOT`/`REPO_ROOT` with `SCRIPT_DIR/../../..` (one directory too high). `compose-review-findings.sh` correctly uses `../..`, so the relocation fix is partial. `aggregate-findings.sh:82` also keeps a stale `MARKER_HELPER` fallback at `$SCRIPT_DIR/../../../python/cli.py`. When `CLAUDE_PLUGIN_ROOT` is unset or empty, direct bash invocation or CLI calls without a valid plugin root fail to source `scripts/lib-quiet.sh`, resolve helper paths outside the repo, and break aggregate scope-marker fallbacks. `run_legacy()` masks missing `CLAUDE_PLUGIN_ROOT` via `setdefault` but not empty string; production paths that export `CLAUDE_PLUGIN_ROOT` or invoke `review-core.sh` directly via `REVIEW_AND_FIX_REVIEW_CORE_SH` can still hit the wrong `scripts/` tree and break MAV `emit-tally` handoff, parent artifact copies, and round log flush paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-review-cli-parity-output.txt: Change all `legacy_review_shell` fallbacks to `../..` (and `../../python/cli.py` for the marker helper); in `run_legacy`, set `CLAUDE_PLUGIN_ROOT` when it is missing **or empty** (`if not env.get("CLAUDE_PLUGIN_ROOT"): env["CLAUDE_PLUGIN_ROOT"] = ...`).
  - From dyn-review-and-fix-handoff-output.txt: Change the fallback to `SCRIPT_DIR/../..` across relocated shells (matching `compose-review-findings.sh`), or require `review-and-fix.sh` to export `CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"` on every `REVIEW_CORE_CMD` invocation so the override path cannot run without a correct plugin root.


### FINDING_10: `test-review-structure.md` contract doc misstates current harness enforcement
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The sibling harness contract still says Assertion 1 expects nine `/review` bash scripts, each with a sibling `.md` and harness, but this branch rewrote `scripts/test-review-structure.sh` to pin `python/cli.py` `review` verb registry entries instead. The contract doc now misstates what the harness enforces and still names retired script surfaces such as `review-core`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Rewrite the Assertion 1 paragraph to describe the current checks: registered `review` CLI verbs in `python/cli.py`, retained bash dependencies under `python/legacy_review_shell/`, and the pytest-backed harness mapping.


### FINDING_11: `review-and-fix.sh` hardcodes `$PLUGIN_ROOT/python/cli.py` outside `REVIEW_AND_FIX_PY_CLI` override
- **Reviewer(s)**: dyn-review-and-fix-handoff-output.txt
- **Severity**: important
- **Concern**: The cutover correctly uses argv arrays for `REVIEW_CORE_CMD` and `COMPOSE_CMD` with `REVIEW_AND_FIX_PY_CLI`, but auxiliary Step 5 surfaces still hardcode `$PLUGIN_ROOT/python/cli.py` for submodule scrub (`_scrub_submodule_paths`), run-log (`_larch_log`), session key reads, and `oos normalize-header`. A harness or fork that pins `REVIEW_AND_FIX_PY_CLI` gets Python review core/compose on one path and a different CLI on the other, which breaks the nested implement handoff contract for log flush and OOS normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-review-and-fix-handoff-output.txt: Route every Python CLI call in `review-and-fix.sh` through the same `$PY_CLI` variable (or a single `_py_cli()` helper), keeping executable-path overrides limited to `REVIEW_CORE_CMD` / `COMPOSE_CMD` only.


### FINDING_2: C1b Python port ships as `run_legacy()` bash delegation, not importable Python implementations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The plan-required Python port is a thin `run_legacy` shell wrapper, not implemented pipeline logic. `review_pipeline`, `review_aggregate`, `review_tally`, and `compose_review` all invoke `bash python/legacy_review_shell/*.sh`. C1b acceptance ("absorbed bash deleted", importable Python functions) is unmet; behavior and security changes still require editing relocated shell. Operators and docs treat `python/cli.py review` as the owner, but the absorbed bash pipeline remains in the shipped runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-generic-output.txt: Replace the legacy-shell delegations with real Python implementations for the review pipeline verbs, and delete `python/legacy_review_shell` once parity tests pass.


### FINDING_3: Deleted bash harness coverage replaced by minimal pytest; critical contracts untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-review-cli-parity-output.txt
- **Severity**: important
- **Concern**: The branch deletes multi-hundred-line bash harnesses (`test-aggregate-findings.sh`, `test-tally-code-votes.sh`, `test-compose-review-findings.sh`, `test-gather-context.sh`, `test-collect-findings.sh`, `test-review-core.sh`) but replaces them with only ~12 focused pytest cases. Makefile targets may run pytest, but coverage is a tiny fraction of deleted behavior. Missing pins include: diff-mode `gather-context` delegation plus trailing `SCOPE_FILES_COUNT=0`/`MODE=diff` KVs; collect-findings `.done` sentinel wait/timeout; post-threshold `panel-failed` gates; OOS snapshot/restore on zero-findings/prune-skipped; MAV emit-tally handoff; `aggregator-validation-exhausted` exhaust-side tally/emit; tally scope-fit/`OUT_OF_SCOPE_DRIFT_COUNT`; security-tagged compose holdback; aggregation merge, validation-exhausted, scope-reduction, plan-review mode, scope-anchor, and dispatch override cases. `test_review_pipeline.py` mostly exercises stubbed `REVIEW_CORE_*` overrides, so regressions in real legacy-shell paths can ship unnoticed. Regressions in scope-fit, security OOS, MAV paths, aggregation, tally scope-drift normalization, plan scope-reduction, compose redaction, and panel-failed gates may merge with green CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Port deleted harness scenarios into `python/test_review_{pipeline,aggregate,tally}.py` and `python/test_compose_review.py` before (or instead of) deleting bash harnesses.
  - From dyn-review-cli-parity-output.txt: Port the highest-risk harness scenarios from the deleted scripts into the four pytest modules, especially contracts called out in the C1b plan edge-case list and any path-resolution fallbacks not covered by `run_legacy` setdefault.


### FINDING_5: Focus-area enum CI guard targets legacy shell, not live Python prompt surface
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The focus-area enum CI guard still targets `python/legacy_review_shell/dispatch-panel.sh` (via `python/voting.py` and `.github/workflows/ci.yaml`) rather than the actual specialist prompt owner `python/rendering.py`. `skills/review/SKILL.md` is guarded, but enum regressions in rendered prompt text may not fail CI after future edits. The hidden legacy-shell pin will break again when `legacy_review_shell/` is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-retired-reference-sweep-output.txt: Point `UNQUOTED_FILES` / `UNQUOTED_FOCUS_FILES` and `scripts/test-prompt-template-invariants.sh` at `python/rendering.py` (or a rendered fixture) for specialist prompt enum coverage; keep or replace the legacy-shell pin only while that private shell remains the prompt owner for dynamic dispatch.


### FINDING_8: `run_legacy()` stderr relay may hide diagnostics under quiet mode
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `run_legacy()` calls `logging_util.quiet_init()`, captures child stderr, then writes it back to `sys.stderr`, which quiet mode has already redirected to the quiet log. A failed review command can return a non-zero status while hiding the legacy script's user-visible diagnostic from the caller.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Relay captured stderr through the saved diagnostic stream, for example `logging_util.diagnostic()` per line or fd 4, or avoid capturing stderr when quiet routing needs to preserve terminal diagnostics.


### FINDING_9: `plan-review-loop.md` cross-link points at deleted `aggregate-findings.md`
- **Reviewer(s)**: dyn-retired-reference-sweep-output.txt
- **Severity**: important
- **Concern**: The Cross-links section still points operators at deleted `aggregate-findings.md` for the `--allow-findings-outside-tmpdir true` contract, but C1b removed `skills/review/scripts/aggregate-findings.md` and moved aggregation to `python/cli.py review aggregate-findings`. Anyone following this cross-link will look for a file that no longer exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retired-reference-sweep-output.txt: Retarget the bullet to the live contract surface, for example `python/review_aggregate.py` or an explicit `python/cli.py review aggregate-findings` note, and document `--allow-findings-outside-tmpdir true` there.


