### FINDING_1: Makefile missing `test-lib-scope-anchor-handoff` harness registration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: New `test-lib-scope-anchor-handoff` target is not registered in any `test-harnesses-N` shard. Central relay gating in `lib-scope-anchor-handoff.sh` can regress without CI ever running its harness; shard-coverage should also fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `test-lib-scope-anchor-handoff` to an appropriate `test-harnesses-N` prerequisite list.

### FINDING_2: Assessor renderer hardens all plan files beyond authorized scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `render-assessor-prompt.sh` wraps all three plan files in `larch_emit_untrusted_file_block` despite the plan limiting hardening to `FEATURE_FILE` and preserving plan fences. Item 6 only authorized feature-file hardening; migrating `plan_original` / `plan_prev` / `plan_current` to literal-redacted XML blocks changes assessor prompt format/semantics beyond acceptance criteria and `SECURITY.md` claims for the assessor scope-anchor path, altering downstream parsing assumptions without plan approval.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep fenced markdown for `plan_original`/`plan_prev`/`plan_current`; apply literal-redacted untrusted blocks only to the feature file.
  - From cursor-specialist-plan-fidelity-output.txt: Revert plan blocks to markdown fences and keep only feature-file untrusted rendering, or explicitly expand the plan/acceptance criteria to cover plan-block migration.

### FINDING_3: Plan-review feature validation duplicates `lib-scope-anchor-handoff`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Feature-file validation in `render-plan-review-prompt.sh` duplicates `lib-scope-anchor-handoff` instead of reusing it. The voter path uses `larch_scope_anchor_validate_*` but the reviewer path keeps parallel CR/LF/size/root checks that can drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source `lib-scope-anchor-handoff.sh` and delegate `--feature-file` validation to `larch_scope_anchor_validate_design`.

### FINDING_4: `emit_untrusted_dynamic_body` duplicates `larch_untrusted_redact_stream`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-review-panel.sh` `emit_untrusted_dynamic_body` duplicates `larch_untrusted_redact_stream` logic inline. Dynamic archetype prompts may miss a future redaction/escaping fix applied only to `lib-untrusted-block` consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source `lib-untrusted-block.sh` and call `larch_untrusted_redact_stream` for dynamic body emission.

### FINDING_5: `lib-untrusted-block.md` misnames helper and overstates responsibilities
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: Contract doc uses wrong function name (`emit_untrusted_file_block` vs `larch_emit_untrusted_file_block`) and states the helper “renders … with untrusted framing prose,” but `larch_emit_untrusted_file_block` only emits the opening `encoding="literal-redacted"` tag, redacted/escaped body, and closing tag; framing is caller-owned. Maintainers may call a nonexistent API or skip required framing, re-opening delimiter-injection / instruction-smuggling on that surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Update doc to `larch_emit_untrusted_file_block` and note framing is caller-owned.
  - From dyn-untrusted-framing-output.txt: Fix the contract to name `larch_emit_untrusted_file_block`, explicitly state that untrusted framing prose is a caller requirement immediately before (or, for subprocess context blocks, immediately after the opening tag and before) the redacted body, and cite the existing callers as canonical patterns.

### FINDING_6: [OUT_OF_SCOPE] Parallel untrusted-block helpers remain in specialist renderer
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Parallel untrusted-block helpers remain in `render-specialist-prompt.sh` after `lib-untrusted-block.sh` landed. Future security fixes may need duplicate edits across specialist and plan-review renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate `render-specialist-prompt` onto `lib-untrusted-block.sh` in a follow-up.

### FINDING_7: [OUT_OF_SCOPE] Branch bundles large unrelated changes outside scope-anchor plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Unrelated changes (Python ship driver, implement skill, review aggregation, and other surfaces outside the #3547 plan) ride on the same branch/PR. Large orthogonal diff complicates review, revert of scope-anchor work, and plan-fidelity certification for #3547-focused reviewers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Prefer splitting or documenting explicit dependency if bundling is intentional.
  - From cursor-specialist-plan-fidelity-output.txt: Split or clearly label non-#3547 commits in the PR description so reviewers can separate scope-anchor work from other landed features.

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

### FINDING_10: [OUT_OF_SCOPE] `resolve_feature_file()` falls through to missing design feature path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `assess-plan-round.sh` `resolve_feature_file()` falls through to a possibly missing design feature path. Degraded session without feature files gets a non-existent path passed downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Return empty or fail closed when no readable feature file exists.

### FINDING_11: [OUT_OF_SCOPE] `recover_main_agent_scope_anchor()` degrades to panel-failed on recovery failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run-step3-review.sh` `recover_main_agent_scope_anchor()` degrades `main-agent-vote-required` to `panel-failed` on recovery failure. Missing handoff KV with no recoverable staged anchor skips MainAgent voting entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document as fail-closed or add loop-side fallback so recovery rarely triggers on happy path.

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

### FINDING_16: `larch_emit_untrusted_file_block` does not validate XML tag names
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `larch_emit_untrusted_file_block` does not validate XML tag names. A future caller passing a user-influenced tag containing `>` or spaces could break out of the literal-redacted block framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict tags to a safe identifier regex or escape tag names inside the helper.

### FINDING_17: Plan-file validation returns non-canonical path unlike feature-file arm
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-plan-review-prompt.sh` plan-file validation returns non-canonical path unlike the feature-file arm. Reviewer could follow a non-canonical `PLAN_FILE` path diverging from the validated inode under TOCTOU or `..`-segment ambiguity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Return `canonical_path` for `--plan-file` and optionally require resolution under `DESIGN_TMPDIR`.

### FINDING_18: [OUT_OF_SCOPE] `plan-review-feature-context.txt` written without redaction and unused
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `plan-review-feature-context.txt` is written without `redact-secrets` and has no production consumer. Future wiring could inline raw brainstorm text into prompts without additional hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Redact/escape at write time or enforce `emit_untrusted_file_block` at any future reader.

### FINDING_19: [OUT_OF_SCOPE] Documented Python-default ship driver parity gaps remain open
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Open parity gaps documented for default `python/ship.py` driver (`#3446`, `#3449`). Default-path `/implement` runs inherit documented ship-driver exposure unrelated to scope-anchor fixes. `python/README.md` does not mention these gaps, so operators reading only the Python README may underestimate residual ship-path risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track/close #3446 and #3449 or keep `LARCH_SHIP_PR_IMPL=bash` until parity is proven.
  - From dyn-python-default-flip-output.txt: `SECURITY.md:96` documents open #3446/#3449 parity gaps as live default-path exposure and documents `LARCH_SHIP_PR_IMPL=bash` rollback accurately; that acknowledgment is not silently closed by this branch. `python/README.md` describes the default flip and bash opt-out but does not mention #3446/#3449, so operators who read only the Python README may underestimate residual ship-path risk.

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

### FINDING_23: [OUT_OF_SCOPE] `--read-tools` subprocess path lacks literal-redacted context embedding
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-untrusted-framing-output.txt, dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: `launch-claude-subprocess.sh` `--read-tools` path still `cat`s the base prompt and does not inline or redact `--context-files`; staged files are read raw via Claude `Read` under `staged-context/`. Pre-existing boundary documented in `SECURITY.md:148`, outside embedded `<context_file_N>` hardening added on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Migrate read-tools path or document as accepted residual risk.
  - From dyn-untrusted-framing-output.txt: The `--read-tools` path still `cat`s the base prompt and does not inline or redact `--context-files`; staged files are read raw via Claude `Read` under `staged-context/`. That predates this branch and is documented separately in `SECURITY.md:148`; it is outside the embedded `<context_file_N>` hardening added here.
  - From dyn-python-default-flip-output.txt: The `--read-tools` branch still embeds only the prompt file and relies on filesystem reads under `--add-dir`; context-body hardening in this branch applies to the legacy `--context-files` embed path. Pre-existing split boundary, not a regression from the scope-anchor work.

### FINDING_24: [OUT_OF_SCOPE] `assessor_path_valid` requires `DESIGN_TMPDIR` for outputs only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `assessor_path_valid` requires `DESIGN_TMPDIR` for outputs only. Pre-existing; unrelated to staged-anchor preference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: No change required for this issue.

### FINDING_25: Scope-reduction marker detector changed `startswith` to `re.match`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Marker consolidation in `check-scope-reduction-marker.sh` changed startswith-based detection to `re.match` despite the plan requiring byte-identical detector logic below the input-read head. A future marker-shape edge case could diverge between pre-merge behavior and consolidated behavior without a deliberate contract decision.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore `startswith` in the unified detector or document and test the intentional semantic change.

### FINDING_26: [OUT_OF_SCOPE] Brief `LOOP_STATUS=complete` window before `tally-error` rewrite
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: Inside `_run_plan_review_round`, `LOOP_STATUS` is set to `complete` before the caller rewrites it to `tally-error`. Relay emission is still safe because `larch_scope_anchor_relay_allowed` keys off `TALLY_PLAN_REVIEW_STATUS` first, but the brief `complete`+`tally-error` window is easy to misread when extending the round function.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] Unit harness lacks direct pins for full `lib-scope-anchor-handoff` relay API
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: `test-lib-scope-anchor-handoff.sh` exercises only `larch_scope_anchor_retally_handoff_value`; it does not directly test `larch_scope_anchor_relay_allowed` or `larch_scope_anchor_design_handoff_value` (parsed-vs-fallback priority, `panel-failed` / `skipped-empty-findings` terminals). Integration coverage largely compensates for loop/Step 3, but the shared library’s dual-gate API lacks direct regression pins.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] Re-tally scope-anchor behavior enforced via grep prose pins only
- **Reviewer(s)**: dyn-scope-anchor-relay-output.txt
- **Severity**: latent
- **Concern**: Re-tally scope-anchor behavior is enforced via `grep -Fq` prose pins in `SKILL.md` / `approval-gates.md`, not via a script-level re-tally env refresh harness; this matches the plan’s SKILL-only delta but leaves the highest-risk handoff boundary on prompt discipline rather than executable contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-anchor-relay-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Aggregator still raw-cats reviewer findings into prompt
- **Reviewer(s)**: dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: `aggregate-findings.sh` still raw-catts reviewer findings into the aggregator prompt; `SECURITY.md:89` already treats findings as a separate untrusted surface from scope-anchor inline renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-untrusted-framing-output.txt: Address the concern above.

### FINDING_30: [OUT_OF_SCOPE] Trusted base `--prompt-file` still raw-catted before context blocks
- **Reviewer(s)**: dyn-untrusted-framing-output.txt
- **Severity**: latent
- **Concern**: The trusted base `--prompt-file` body is still raw-catted before context blocks; hardening applies to `--context-files` payloads only (pre-existing boundary).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-untrusted-framing-output.txt: Address the concern above.

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

### FINDING_33: [OUT_OF_SCOPE] README omits Python-default driver, 3.12 floor, and bash rollback
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Top-level `README.md` feature matrix does not mention the Python-default Step 8+ driver, the 3.12 floor, or `LARCH_SHIP_PR_IMPL=bash` rollback, while `docs/installation-and-setup.md`, `docs/configuration-and-permissions.md`, and `AGENTS.md` do. Minor doc-surface inconsistency for operators who start from README only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Scope-reduction marker `re.match` vs `startswith` subtle drift risk
- **Reviewer(s)**: dyn-python-default-flip-output.txt
- **Severity**: latent
- **Concern**: Marker detection changed from `norm(cand).startswith("[SCOPE-REDUCTION]")` to `re.match(r"^\[SCOPE-REDUCTION\]", norm(cand))` during consolidation; behavior should be equivalent for normalized candidates, and stdin/file parity is now covered by `test-check-scope-reduction-marker.sh`, but any subtle normalization drift would affect dedup parity in `plan-review-loop.sh` as well. Worth watching, not a confirmed regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-python-default-flip-output.txt: Address the concern above.
