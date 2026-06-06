# Review Round 4

- Mode: `diff`
- 16 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: Makefile missing `test-lib-scope-anchor-handoff` harness registration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: New `test-lib-scope-anchor-handoff` target is not registered in any `test-harnesses-N` shard. Central relay gating in `lib-scope-anchor-handoff.sh` can regress without CI ever running its harness; shard-coverage should also fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `test-lib-scope-anchor-handoff` to an appropriate `test-harnesses-N` prerequisite list.


### FINDING_12: MainAgent re-tally `SCOPE_ANCHOR_FILE` refresh is prose-only; stale anchor can persist
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scope-anchor-relay-output.txt, dyn-python-default-flip-output.txt
- **Severity**: important
- **Concern**: Loop and Step 3 relay paths are mechanically gated via `lib-scope-anchor-handoff.sh`, but MainAgent re-tally refresh in `SKILL.md` is orchestrator prose only. `larch_scope_anchor_retally_handoff_value` is implemented and unit-tested yet no production script or SKILL bash fence calls it. Post–re-tally dual-env writes (`.step3-plan-review-result.env` and `.step3-review-result.env`) still depend on the orchestrator manually unsetting `_RETALLY_PARSED_SCOPE_ANCHOR_FILE`, omitting the key on `tally-error`, and applying terminal/fallback rules that loop/Step 3 enforce in bash—leaving stale `SCOPE_ANCHOR_FILE` for Gate B / Step 3.6. Integration coverage lacks a stale-seed re-tally case asserting both result envs omit `SCOPE_ANCHOR_FILE` on tally-error; `test-step3-orchestrator-fence.sh` only grep-pins prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add stale-seed re-tally case asserting both `.step3-plan-review-result.env` and `.step3-review-result.env` omit `SCOPE_ANCHOR_FILE` on tally-error.
  - From cursor-specialist-security-output.txt: Wire re-tally persist through `larch_scope_anchor_retally_handoff_value` or a dedicated script that validates design-tmpdir containment before writing env KVs.
  - From cursor-specialist-edge-cases-output.txt: Add a script helper mirroring loop/run-step3 gating and invoke it from the re-tally path.
  - From dyn-scope-anchor-relay-output.txt: Add a small writer helper (or fenced bash block in the MainAgent re-tally section) that sources `lib-scope-anchor-handoff.sh`, parses re-tally stdout into `_RETALLY_PARSED_SCOPE_ANCHOR_FILE`, computes the handoff via `larch_scope_anchor_retally_handoff_value`, and atomically rewrites both result envs only when `TALLY_PLAN_REVIEW_STATUS`/`LOOP_STATUS` permit; keep `test-step3-orchestrator-fence.sh` pins but add an offline harness that simulates re-tally `ok` / `tally-error` stdout and asserts env outcomes.
  - From dyn-python-default-flip-output.txt: Wire re-tally through a small helper (or extend `tally-plan-review.sh` post-processing) that calls `larch_scope_anchor_retally_handoff_value` and rewrites both result env files, and add a stale-seed harness case parallel to the loop/run-step3 tests.


### FINDING_13: Missing render harness for legacy `feature-description.txt` assessor fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No render harness case covers the legacy `feature-description.txt` fallback path. Legacy assessor sessions may render raw `feature-description.txt` without the literal-redacted contract verified in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add render case using `feature-description.txt` with secret/tag/safe-line fixture and same hardening assertions.


### FINDING_14: `test-lib-scope-anchor-handoff.sh` omits `panel-failed` terminal cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Harness omits `panel-failed` `LOOP_STATUS` cases despite doc claiming that terminal. `panel-failed` handoff gating relies on integration tests only; lib-layer regression gap is undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add lib harness cases with `LOOP_STATUS=panel-failed` asserting empty handoff output.


### FINDING_15: `--design-tmpdir` optional allows feature-file containment bypass
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-assessor-prompt.sh` `--design-tmpdir` is optional; without it feature-file validation is only `common_shape_ok`. A future or test caller omitting `--design-tmpdir` could inline arbitrary local file bytes (even redacted) into external assessor prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require `--design-tmpdir` for feature-file containment or fail closed when the path is outside the resolved tmpdir.


### FINDING_17: Plan-file validation returns non-canonical path unlike feature-file arm
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-plan-review-prompt.sh` plan-file validation returns non-canonical path unlike the feature-file arm. Reviewer could follow a non-canonical `PLAN_FILE` path diverging from the validated inode under TOCTOU or `..`-segment ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Return `canonical_path` for `--plan-file` and optionally require resolution under `DESIGN_TMPDIR`.


### FINDING_2: Assessor renderer hardens all plan files beyond authorized scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `render-assessor-prompt.sh` wraps all three plan files in `larch_emit_untrusted_file_block` despite the plan limiting hardening to `FEATURE_FILE` and preserving plan fences. Item 6 only authorized feature-file hardening; migrating `plan_original` / `plan_prev` / `plan_current` to literal-redacted XML blocks changes assessor prompt format/semantics beyond acceptance criteria and `SECURITY.md` claims for the assessor scope-anchor path, altering downstream parsing assumptions without plan approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep fenced markdown for `plan_original`/`plan_prev`/`plan_current`; apply literal-redacted untrusted blocks only to the feature file.
  - From cursor-specialist-plan-fidelity-output.txt: Revert plan blocks to markdown fences and keep only feature-file untrusted rendering, or explicitly expand the plan/acceptance criteria to cover plan-block migration.


### FINDING_20: `emit_loop_kvs` parameter/global terminal status can desync relay gating
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `emit_loop_kvs` gates `SCOPE_ANCHOR_FILE` from global `TALLY`/`LOOP_STATUS` but emits parameter `loop_status`/`tally_status`. A future caller passing argv/globals out of sync could show one terminal on stdout while relay gating used another, leaking or omitting `SCOPE_ANCHOR_FILE` incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Thread terminal statuses through `_scope_anchor_handoff_value`/`larch_scope_anchor_relay_allowed` or sync globals from `emit_loop_kvs` parameters before gating.


### FINDING_21: Legacy feature resolution uses `-f` not `-s`, blocking implement fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `assess-plan-round.sh` legacy feature resolution uses `-f` not `-s`, so zero-byte `feature-description.txt` blocks `IMPLEMENT_TMPDIR` fallback. Degraded session with empty design feature file and valid implement feature: Step 3.6 hits `render-assessor` exit 2 and opens degraded-default-open instead of assessing against real scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use `-s` for design (and implement) feature checks; add harness for empty design + non-empty implement feature.


### FINDING_22: stdout KV fallback is first-wins across multi-round loop output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `run-step3-review.sh` stdout KV fallback is first-wins across multi-round loop output. Symlinked inner result env forces stdout-only parse: an early round's `TALLY_PLAN_REVIEW_STATUS` can mask the final terminal state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use last-wins parsing or isolate the final `emit_loop_kvs` block.


### FINDING_3: Plan-review feature validation duplicates `lib-scope-anchor-handoff`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Feature-file validation in `render-plan-review-prompt.sh` duplicates `lib-scope-anchor-handoff` instead of reusing it. The voter path uses `larch_scope_anchor_validate_*` but the reviewer path keeps parallel CR/LF/size/root checks that can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source `lib-scope-anchor-handoff.sh` and delegate `--feature-file` validation to `larch_scope_anchor_validate_design`.


### FINDING_31: Python 3.12 floor enforced only at Step 8+ ship driver start
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: important
- **Concern**: Python 3.12 floor is enforced only when `ship.py` starts at `/implement` Step 8+, after implementation, review, and commits may already be done. With Python now the default driver, a host whose `python3` is 3.11 or older can complete most of the run and then stall with `outcome=STALLED` and no PR. `session-setup.sh` and `implement-bootstrap.sh` do not probe interpreter version, so there is no early fail-fast with the documented `LARCH_SHIP_PR_IMPL=bash` rollback hint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Add a Step 0 (or session-setup) version probe when the default Python ship path is active; fail loudly before Step 2 with the rollback instructions, mirroring the `ship.py` JSON contract.


### FINDING_32: `make py-test` has no Python 3.12 floor unlike CI and `relevant-checks.sh`
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: important
- **Concern**: CI dropped Python 3.11 from the matrix (3.12 only), but `make py-test` uses `$(PYTHON) -m pytest` with `PYTHON ?= python3` and no version floor. On a machine where `python3` is 3.11, `make py-test` can pass syntax checks or fail opaquely while `pyproject.toml` requires `>=3.12`; this diverges from CI and the new production default. `scripts/relevant-checks.sh` gates `py-test` on 3.12+, but bare `make py-test` does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Have the Makefile target reject `python3` below 3.12 (same probe as `python/ship.py`) or document/require `PYTHON=python3.12` explicitly in `docs/linting.md` with a failing guard in the recipe.


### FINDING_5: `lib-untrusted-block.md` misnames helper and overstates responsibilities
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: Contract doc uses wrong function name (`emit_untrusted_file_block` vs `larch_emit_untrusted_file_block`) and states the helper “renders … with untrusted framing prose,” but `larch_emit_untrusted_file_block` only emits the opening `encoding="literal-redacted"` tag, redacted/escaped body, and closing tag; framing is caller-owned. Maintainers may call a nonexistent API or skip required framing, re-opening delimiter-injection / instruction-smuggling on that surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update doc to `larch_emit_untrusted_file_block` and note framing is caller-owned.
  - From dyn-untrusted-framing-output.txt: Fix the contract to name `larch_emit_untrusted_file_block`, explicitly state that untrusted framing prose is a caller requirement immediately before (or, for subprocess context blocks, immediately after the opening tag and before) the redacted body, and cite the existing callers as canonical patterns.


### FINDING_8: Tagged-block dedup/parity text extraction can drop or mis-merge findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: In `plan-review-loop.sh`, `problem_text()` returns only the first header-derived candidate for scope-reduction-tagged blocks, ignoring Concern bodies used for dedup; two tagged findings with the same `###` header but different Concern bodies can be Jaccard-merged and one scope-reduction finding dropped before voting. Main dedup `problem_text()` and parity `prob()` disagree on tagged-block extraction, forcing pre-dedup fallback with warnings. Tagged scope-reduction dedup now prefers header/candidate lines over Concern regex, so divergent title vs Concern text may dedup differently and change the accepted-finding set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: For `is_tagged` blocks, base `comparison_text` on Concern/Description (or header+Concern), not header alone.
  - From cursor-specialist-correctness-output.txt: Unify tagged-block comparison logic between dedup and parity helpers.
  - From cursor-specialist-edge-cases-output.txt: Pin behavior with a divergent-header fixture; document precedence in `plan-review-loop.md`.


### FINDING_9: Mid-loop round-summary emits empty `LOOP_STATUS` with `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Mid-loop round-summary writes use empty `LOOP_STATUS` while global `LOOP_STATUS` still allows `SCOPE_ANCHOR_FILE` emission. Non-terminal `round-summary.env` shows `LOOP_STATUS=` with `SCOPE_ANCHOR_FILE` set, confusing forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass real round status into `_write_round_summary` or omit anchor from non-terminal summaries.


