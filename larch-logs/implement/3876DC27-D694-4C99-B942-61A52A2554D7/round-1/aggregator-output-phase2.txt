### FINDING_1: Loop writer gates `SCOPE_ANCHOR_FILE` on tally only, not `LOOP_STATUS`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: `_scope_anchor_handoff_value()` in `plan-review-loop.sh` emits/persists `SCOPE_ANCHOR_FILE` when `TALLY_PLAN_REVIEW_STATUS` is `ok` or `main-agent-vote-required` without consulting `LOOP_STATUS`. After a successful tally, later loop failures (e.g. `panel-failed` from snapshot-failed) can leave `TALLY_PLAN_REVIEW_STATUS=ok` while `LOOP_STATUS` is an error terminal, so `write_step3_result_env()` / `emit_loop_kvs()` still relay the anchor—contradicting the omit-on-error contract in FINDING_6, `run-step3-review.md`, and `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Gate on both TALLY and LOOP_STATUS allowlists before emitting or persisting SCOPE_ANCHOR_FILE
  - From cursor-specialist-correctness-output.txt: Add LOOP_STATUS deny-list or require LOOP_STATUS in {complete,main-agent-vote-required} before emit/persist
  - From cursor-specialist-edge-cases-output.txt: Conjunctive allowlist: require TALLY in {ok, main-agent-vote-required} AND LOOP in {complete, main-agent-vote-required}; add mismatched LOOP/TALLY harness case.
  - From dyn-scope-handoff-output.txt: Gate `_scope_anchor_handoff_value()` on both tally terminal and loop terminal — emit only when `TALLY_PLAN_REVIEW_STATUS` is `ok|main-agent-vote-required` **and** `LOOP_STATUS` is not in an explicit denylist (`panel-failed`, `tally-error`, `cap-reached`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `emit-plan-failed`, etc.), or invert to a positive allowlist of loop terminals that may carry the handoff (`complete`, `main-agent-vote-required`, and any others intentionally documented).
  - From dyn-ship-driver-output.txt: Mirror the loop gate exactly — require `TALLY_PLAN_REVIEW_STATUS` ∈ `{ok, main-agent-vote-required}` and reject relay when `LOOP_STATUS` is in the Gate-B-bypass / error set (`tally-error`, `panel-failed`, etc.), with a stale-seed harness case in `test-run-step3-review.sh`.

### FINDING_2: Outer relay `scope_anchor_relay_allowed()` ignores incompatible `LOOP_STATUS`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: `scope_anchor_relay_allowed()` in `run-step3-review.sh` permits `SCOPE_ANCHOR_FILE` relay when `TALLY_PLAN_REVIEW_STATUS=ok` (or `LOOP_STATUS=main-agent-vote-required`) without requiring a compatible success-shaped `LOOP_STATUS`. Desynced inner output (`LOOP_STATUS=panel-failed` or `tally-error` with `TALLY_PLAN_REVIEW_STATUS=ok`) can still be forwarded to stdout and `.step3-review-result.env`, widening stale-handoff exposure at the Step 3 outer boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Align relay gate with loop writer using paired LOOP_STATUS and TALLY_PLAN_REVIEW_STATUS checks plus harness cases
  - From cursor-specialist-correctness-output.txt: Gate on LOOP_STATUS success terminals or explicitly deny panel-failed/tally-error/cap-reached regardless of tally KV
  - From cursor-specialist-testing-output.txt: Align gating with loop terminal semantics; add harness for mismatched terminal pairs.
  - From cursor-specialist-edge-cases-output.txt: Conjunctive allowlist: require TALLY in {ok, main-agent-vote-required} AND LOOP in {complete, main-agent-vote-required}; add mismatched LOOP/TALLY harness case.
  - From dyn-scope-handoff-output.txt: Mirror the loop-side terminal matrix here — require `TALLY_PLAN_REVIEW_STATUS` in `ok|main-agent-vote-required` **and** `LOOP_STATUS` not in the same denylist (or only in the documented allowlist), then clear `SCOPE_ANCHOR_FILE` before emit/write when the pair is incompatible.
  - From dyn-ship-driver-output.txt: Mirror the loop gate exactly — require `TALLY_PLAN_REVIEW_STATUS` ∈ `{ok, main-agent-vote-required}` and reject relay when `LOOP_STATUS` is in the Gate-B-bypass / error set (`tally-error`, `panel-failed`, etc.), with a stale-seed harness case in `test-run-step3-review.sh`.

### FINDING_3: Loop parsed tally path lacks `DESIGN_TMPDIR` containment before persist
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `_scope_anchor_handoff_value()` prefers parsed tally `SCOPE_ANCHOR_FILE` over `_LOOP_SCOPE_ANCHOR_IN` with only CR/LF rejection and no `DESIGN_TMPDIR` containment check inside the loop. Malformed or corrupt tally KV on an ok path can write an out-of-tmpdir path into `.step3-plan-review-result.env` before outer `validate_scope_anchor_handoff` clears it, widening the window for mis-parsed consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Validate/canonicalize parsed path under DESIGN_TMPDIR before preferring it; fall back to _LOOP_SCOPE_ANCHOR_IN on failure.
  - From cursor-specialist-security-output.txt: Reject or canonicalize paths outside DESIGN_TMPDIR in _scope_anchor_handoff_value before persist, matching run-step3 validate_scope_anchor_handoff.

### FINDING_4: Missing loop harness: stale exported `SCOPE_ANCHOR_FILE` on error terminals
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `test-plan-review-loop.sh` lacks a deterministic stale-seed case per plan FINDING_7/12. Exported stale `SCOPE_ANCHOR_FILE` could leak via env if relay gates regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add export SCOPE_ANCHOR_FILE stale seed with tally-error stub omitting KV and assert stdout and result env omit key

### FINDING_5: Missing outer relay harness: `panel-failed` + `TALLY=ok` omits `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-scope-handoff-output.txt
- **Severity**: important
- **Concern**: Plan/acceptance requires asserting `SCOPE_ANCHOR_FILE` omission on `panel-failed` paths, including the desync shape `LOOP_STATUS=panel-failed` with `TALLY_PLAN_REVIEW_STATUS=ok`. Existing `test-run-step3-review.sh` stubs use matching `TALLY_PLAN_REVIEW_STATUS=panel-failed`, so terminal-gating regressions on the mismatch case would not be caught. `test-plan-review-loop.sh` panel-failed coverage omits absence assertions on stdout/result env.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add grep negatives for SCOPE_ANCHOR_FILE on stdout and .step3-plan-review-result.env in panel-failed case
  - From cursor-specialist-testing-output.txt: Extend D5 with a stub that emits SCOPE_ANCHOR_FILE plus panel-failed terminals; assert stdout and .step3-review-result.env omit the key.
  - From cursor-specialist-edge-cases-output.txt: Add inner stub emitting SCOPE_ANCHOR_FILE on panel-failed; assert stdout and result env omit it.
  - From dyn-scope-handoff-output.txt: Add a harness where the loop stub (or real loop snapshot-failed fixture) returns `LOOP_STATUS=panel-failed` with `TALLY_PLAN_REVIEW_STATUS=ok` and optionally seeds a stale anchor path; assert both normalized stdout and `.step3-review-result.env` omit `SCOPE_ANCHOR_FILE=`.

### FINDING_6: Missing outer relay harness: stale-seed `SCOPE_ANCHOR_FILE` on `tally-error`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-run-step3-review.sh` lacks plan-requested stale-seed cases where a pre-exported `SCOPE_ANCHOR_FILE` is present and the inner stub omits the KV on `tally-error`. Stale inner result env or prior anchor could persist through tally-error relay without detection; loop harness has stronger coverage than the outer driver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add tally-error stub test with pre-exported SCOPE_ANCHOR_FILE asserting stdout and result env omit key
  - From cursor-specialist-correctness-output.txt: Add export SCOPE_ANCHOR_FILE=/tmp/stale with inner stub omitting KV; assert omission
  - From cursor-specialist-testing-output.txt: Add tally-error cases with pre-seeded SCOPE_ANCHOR_FILE; assert outer relay omits it on stdout and result env.

### FINDING_7: Missing harness: parsed tally `SCOPE_ANCHOR_FILE` KV wins over materialized fallback
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test verifies that parsed tally `SCOPE_ANCHOR_FILE` KV wins over the materialized fallback when paths differ. Fallback-only tests would not catch regressions that ignore tally stdout KV on ok terminals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add tally stub emitting alternate SCOPE_ANCHOR_FILE on ok; assert parsed path is persisted.

### FINDING_8: Aggregator scope-anchor append uses weak escaping (redact-only, raw inline)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, dyn-prompt-boundary-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: New `--scope-anchor-file` path in `aggregate-findings.sh` pipes anchor content through `redact-secrets.sh` only and appends raw markdown without `<>&` escaping, `encoding="literal-redacted"` wrapper, or untrusted framing prose—unlike sibling consumers (`render-voter-prompt.sh`, `render-main-agent-scope-anchor.sh`, `revise-plan-with-waterfall.sh`, `launch-claude-subprocess.sh`). Issue-body text with delimiter-like or instruction-like prose can weaken the aggregator LLM prompt boundary during merge/dedupe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Render via emit_untrusted_file_block (or shared helper), add untrusted framing, validate path under DESIGN_TMPDIR with size cap, and add escaping regression tests.
  - From dyn-prompt-boundary-output.txt: Reuse the hardened pattern from `skills/design/scripts/render-main-agent-scope-anchor.sh:43-51` or `skills/shared/scripts/render-voter-prompt.sh:21-25`—validate the path, emit untrusted framing prose, then render via `emit_untrusted_file_block plan_review_scope_anchor` (or delegate to `render-main-agent-scope-anchor.sh`). Add a harness case in `skills/review/scripts/test-aggregate-findings.sh` that asserts escaped delimiter bytes and framing when `--scope-anchor-file` is set.
  - From dyn-ship-driver-output.txt: Reuse `emit_untrusted_file_block` (or the same redact + `&lt;`/`&gt;`/`&amp;` pipeline) for the aggregator scope section, and add a harness assertion in `skills/review/scripts/test-aggregate-findings.sh` mirroring the voter delimiter cases.

### FINDING_9: `render-plan-review-prompt.sh` `--feature-file` lacks `DESIGN_TMPDIR` containment
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: `validate_design_prompt_file()` checks symlink rejection and 64KiB cap but does not require the canonical path to resolve under `DESIGN_TMPDIR`. A miswired or same-UID-swapped `--feature-file` can pull arbitrary readable host content into external scout/reviewer prompts despite downstream redact/escape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: After `canon="$(canonical_path "$path")"`, require `canon` under `$(cd "$DESIGN_TMPDIR" && pwd -P)/` for `--feature-file`, mirroring `render-main-agent-scope-anchor.sh:33-40` and the new containment checks in `revise-plan-with-waterfall.sh`.

### FINDING_10: `render-voter-prompt.sh` rejects normal cache-backed scope-anchor paths
- **Reviewer(s)**: dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: `validate_scope_anchor_file()` only accepts paths under `$REPO_ROOT`, `/tmp`, or `/var/folders`, but `/design` materializes `plan-review-scope-anchor.txt` under `$XDG_CACHE_HOME/larch/sessions/…`. `dispatch-plan-voters.sh` forwards that staged path into `render-voter-prompt.sh`, so the normal cache-backed session layout fails closed with exit 2 and plan-review voter prompts never render (harnesses pass because they use `mktemp` under `/tmp`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ship-driver-output.txt: Align containment with `render-main-agent-scope-anchor.sh:33-40` — accept `--design-tmpdir` (or derive it from the caller) and require the canonical anchor path to resolve under that tmpdir; alternatively extend the allowlist to the `session_cache_root` pattern from `session-setup.sh`.

### FINDING_11: `SECURITY.md` overstates aggregator scope-anchor hardening
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: important
- **Concern**: The new "Plan-review scope-anchor pipeline" section claims all inline consumers render staged anchor material as literal-redacted escaped evidence with untrusted framing, but the branch adds aggregator consumption without meeting that contract and does not list the aggregator among inline consumers—creating false assurance about delimiter safety.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: Either harden `aggregate-findings.sh` to match the documented contract and explicitly list the aggregator under inline consumers, or qualify `SECURITY.md` to state that the aggregator is a legacy/raw inline surface until migrated.

### FINDING_12: Scope-reduction `norm()` widening breaks plan-fidelity byte-identical detector contract
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Item 4 required byte-identical detector logic after input-read consolidation, but `norm()` in `check-scope-reduction-marker.sh` now strips any leading bracket tag until `[SCOPE-REDUCTION]` instead of only `important`/`nit`/`latent`. A finding like `[custom] [SCOPE-REDUCTION] …` may flip from absent to detected versus pre-branch behavior, breaking the acceptance criterion that detector semantics stay unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore the original norm() stripping rules in the shared detector, or treat the widening as intentional with updated fixtures and acceptance text.

### FINDING_13: Scope-reduction final tag detection is case-sensitive
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: `norm()` stops generic bracket stripping when `re.match(r'^\[SCOPE-REDUCTION\]', s, re.I)` matches, but the final tag test is `norm(cand).startswith("[SCOPE-REDUCTION]")`, which is case-sensitive. A reviewer-written `[scope-reduction]` (or other casing) is not tagged, so plan-review dedup and aggregate split can treat it as ordinary in-scope text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Make the final detection case-insensitive as well (e.g. `re.match(r'^\[SCOPE-REDUCTION\]', norm_cand, re.I)`), mirror the same rule in `plan-review-loop.sh` `problem_text()` at `skills/design/scripts/plan-review-loop.sh:1317-1322`, and add a harness case for lowercase/alternate casing.

### FINDING_14: Post-dedup parity `prob()` extractor is stale vs updated dedup `problem_text()`
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: Embedded dedup `problem_text()` / `comparison_text()` were updated to match the canonical helper (plain `Concern:`, `what:`, generic bracket stripping), but the post-dedup parity gate still uses the old `prob()` extractor (bold-only `- **Concern**:`, severity-only prefix removal, heading-only fallback). After dedup reshapes tagged blocks, parity can false-fail and force restore of `findings-in-scope.pre-dedup.md`, disabling dedup while still proceeding to aggregation/voting on duplicates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Reuse the same candidate-line + `norm()` logic from dedup `problem_text()` inside parity `prob()` (or call the helper per block for tagged detection and derive comparison tokens from `comparison_text()`), and add a `test-plan-review-loop.sh` case with plain-`Concern` / `what:` scope-reduction findings that must survive dedup without parity fallback.

### FINDING_15: Aggregate recombine parity `problem_text()` prefix normalization lags canonical helper
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: important
- **Concern**: Recombine parity `problem_text()` was partially updated but still strips only `[important|nit|latent]` at the start of the joined string, while `check-scope-reduction-marker.sh` strips arbitrary leading `[tag]` prefixes. For findings like `- **Concern**: [regression] [SCOPE-REDUCTION] …`, helper split correctly withholds the block, yet parity scoring tokenizes the unrevised `[regression]` prefix and can false-fail tagged-block matching, rolling back a valid merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Port the same generic-bracket `while` loop used in dedup `comparison_text()` (`skills/design/scripts/plan-review-loop.sh:1337-1340`) into aggregate recombine `problem_text()` before tokenization, and extend `test-aggregate-findings.sh` with a multi-prefix scope-reduction fixture.

### FINDING_16: MainAgent re-tally scope-anchor refresh is prose-only, not script-enforced
- **Reviewer(s)**: dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: important
- **Concern**: Re-tally `SCOPE_ANCHOR_FILE` refresh (`_RETALLY_SCOPE_ANCHOR_IN` / `_RETALLY_PARSED_SCOPE_ANCHOR_FILE`, omit on `tally-error`, dual env rewrite) is enforced only through orchestrator prose and `test-step3-orchestrator-fence.sh` grep pins, unlike loop and `run-step3-review.sh` paths with script-level terminal gating. A prompt-side miss can leave a stale anchor in result env files despite stated stale-leak mitigations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-scope-handoff-output.txt: Extract re-tally scope-anchor parse/persist into a small helper (parallel to `_scope_anchor_handoff_value()` / `scope_anchor_relay_allowed()`) invoked from the re-tally Bash fence, or add a behavioral harness that simulates re-tally stdout/env refresh rather than only checking documentation strings.
  - From dyn-ship-driver-output.txt: Extract re-tally parse/persist into a small sourced helper (parallel to `_scope_anchor_handoff_value`) invoked from a thin SKILL.md Bash fence, and add an offline harness that seeds stale exported `SCOPE_ANCHOR_FILE`, omits the KV on `tally-error`, and asserts both refreshed env files stay clean.

### FINDING_17: `scope_anchor_relay_allowed()` predicate mismatches loop handoff contract
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: important
- **Concern**: `scope_anchor_relay_allowed()` gates on `LOOP_STATUS==main-agent-vote-required || TALLY_PLAN_REVIEW_STATUS==ok`, but `plan-review-loop.sh` gates on `TALLY_PLAN_REVIEW_STATUS` in `ok|main-agent-vote-required` only. The predicates are not equivalent: `LOOP_STATUS=complete` + `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` would clear a valid anchor at the outer layer even though the loop would emit it, and the inverse would relay when the loop would not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Mirror the loop contract—e.g. `case "${TALLY_PLAN_REVIEW_STATUS:-}" in ok|main-agent-vote-required)` (and optionally require matching `LOOP_STATUS` for `main-agent-vote-required`)—so both layers share one terminal gate.

### FINDING_18: Missing harness: `--scope-anchor-file` append in `aggregate-findings.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: New `--scope-anchor-file` prompt append has no harness coverage. Aggregator prompt could omit, mis-render, or over-include anchor content without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add plan-mode aggregate-findings tests for scope-anchor append and negative code-mode control.

### FINDING_19: Missing harness: context-body hardening in `launch-claude-subprocess.sh`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Context-body hardening in `launch-claude-subprocess.sh` lacks regression tests despite `SECURITY.md` claims. Only path-attribute escaping may be tested; future removal of redact/escape/framing for context bodies would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add capture-prompt tests for secrets, delimiters, framing, and literal-redacted encoding.
  - From cursor-specialist-edge-cases-output.txt: Add fixture with secret-like token, <tag>, & in context body; assert framing, escaping, and no raw leakage.

### FINDING_20: `_scope_anchor_handoff_value()` reads global tally status, not `emit_loop_kvs` parameter
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: `emit_loop_kvs()` accepts `tally_status` as a parameter but `_scope_anchor_handoff_value()` reads global `TALLY_PLAN_REVIEW_STATUS` instead of `$tally_status`. A future refactor passing a different `tally_status` while leaving the global stale could emit mismatched tally KV and `SCOPE_ANCHOR_FILE` lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Pass `tally_status` into `_scope_anchor_handoff_value` (or read only the parameter inside `emit_loop_kvs`) so the relay gate and emitted tally KV share one value.

### FINDING_21: `_PARSED_SCOPE_ANCHOR_FILE` not cleared on tally failure
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: On tally failure the script forces `TALLY_PLAN_REVIEW_STATUS=tally-error` but leaves `_PARSED_SCOPE_ANCHOR_FILE` populated from the raw tally stream; safety depends entirely on `_scope_anchor_handoff_value()` re-checking tally status, which is fragile if a later edit writes from the parsed variable before the gate runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Unset `_PARSED_SCOPE_ANCHOR_FILE` (or clear it in the `tally-error` branch) when `_tally_rc -ne 0`, matching the input/output separation the plan describes.

### FINDING_22: Pre-parse reset omits `SCOPE_ANCHOR_FILE`
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: The pre-parse reset in `run-step3-review.sh` clears `TALLY_PLAN_REVIEW_STATUS`, `VOTING_TALLY_FILE`, etc., but not `SCOPE_ANCHOR_FILE`, relying on line-146 initialization. Any future early path setting `SCOPE_ANCHOR_FILE` before loop invocation could leak into parse/fallback because stdout fallback only fills empty keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: Add `SCOPE_ANCHOR_FILE=""` to the same reset block as the other handoff fields.

### FINDING_23: `render-assessor-prompt.sh` duplicates escape pipeline locally
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Local `emit_untrusted_feature_block` duplicates existing redact/escape helpers; a fifth copy of the escape pipeline increases drift risk versus voter/revise renderers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Reuse shared emit_untrusted_file_block helper with feature_file tag

### FINDING_24: `launch-claude-subprocess.sh` inlines escape/redact instead of shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Context hardening inlines escape/redact instead of a shared block helper; subprocess context contract can drift from plan-review untrusted block emitters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor or source shared untrusted block and attribute escape helpers

### FINDING_25: `SCOPE_ANCHOR_FILE` removed from blanket normalized result-env key assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `SCOPE_ANCHOR_FILE` was removed from blanket normalized result-env key assertion in `test-run-step3-review.sh`. Weird-status fixtures no longer guard against accidental loss of the relay key on success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Restore key assertion for success terminals or add explicit ok-path relay assertion.

### OOS_1: [OUT_OF_SCOPE] `norm()` generic bracket stripping predates consolidation / changes detector semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-shell-hygiene-output.txt
- **Severity**: latent
- **Concern**: `norm()` while-loop bracket stripping predates consolidation; multi-bracket headings may match differently than the original single-severity strip. Consolidation also broadened `norm()` from stripping only `[important|nit|latent]` to stripping any `[A-Za-z0-9_-]+` prefix before `[SCOPE-REDUCTION]` detection—detector semantics changed beyond deduplication-only consolidation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Track separately if parity harness needs expansion

### OOS_2: [OUT_OF_SCOPE] Pre-existing duplicated `redact_untrusted_stream` across renderers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Ongoing maintenance burden when escape contract changes; multiple render scripts carry duplicate redact/escape logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Centralize untrusted block helpers in a shared library script

### OOS_3: [OUT_OF_SCOPE] Branch bundles unrelated Python ship-driver default (#3462) and run artifacts
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: Branch includes large unrelated #3462 Python ship-pr default migration, `python/test_ship.py`, and `larch-logs/` run artifacts beyond #3547 scope-anchor surface. Broader CI failures or regressions can block or obscure scope-anchor fixes; `SECURITY.md` documents open review gaps on the default path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split or document unrelated scope in PR
  - From cursor-specialist-testing-output.txt: Split unrelated ship work into a separate PR or ensure isolated test ownership.
  - From cursor-specialist-security-output.txt: Address via tracked issues #3446/#3404/#3405/#3449; operators can set LARCH_SHIP_PR_IMPL=bash to opt out.
  - From dyn-ship-driver-output.txt: The branch bundles the scope-anchor follow-up (`ed2320447`) with the Python ship-driver default flip (`4de108c0a` / #3462) plus a large `larch-logs/` run artifact (`c0999699d`). That widens review and rollback blast radius beyond issue #3547’s stated dependency surface.

### OOS_4: [OUT_OF_SCOPE] `round-summary.env` writes `SCOPE_ANCHOR_FILE` without terminal gate
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-scope-handoff-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: `_write_round_summary()` always records `SCOPE_ANCHOR_FILE` from the materialized anchor variable while durable handoff is terminal-gated in `_scope_anchor_handoff_value()` / `write_step3_result_env()` / `emit_loop_kvs()`. Forensic round artifacts can contradict the normalized handoff contract on `panel-failed` and `tally-error` exits if any consumer treats `round-summary.env` as authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Optional: gate round-summary SCOPE_ANCHOR_FILE the same way as emit_loop_kvs for consistency.
  - From dyn-scope-handoff-output.txt: `_write_round_summary()` always writes `SCOPE_ANCHOR_FILE=${SCOPE_ANCHOR_FILE:-}` from the materialized anchor variable, without the terminal gate used by `write_step3_result_env()`. This predates the branch diff and is documented in `plan-review-loop.md`, but it remains a secondary path-only surface if any consumer ever treats `round-summary.env` as authoritative for Step 3 handoff rather than forensics.
  - From dyn-ship-driver-output.txt: Route `round-summary.env` through `_scope_anchor_handoff_value()` (or omit the key when tally terminal is not `ok` / `main-agent-vote-required`), and document the gate in `plan-review-loop.md` so passive-summary readers do not treat error-round summaries as authoritative handoff state.

### OOS_5: [OUT_OF_SCOPE] 64KiB scope-anchor size cap has no harness on all consumers
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: 64KiB scope-anchor size cap added in several paths has no harness case on loop materialization or `render-main-agent-scope-anchor.sh`. Oversize anchors might fail opaquely in production without a pinned regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness expecting materialization/loop failure when anchor exceeds cap.
  - From dyn-ship-driver-output.txt: `skills/design/scripts/render-main-agent-scope-anchor.sh:46-50` still lacks the 64 KiB cap added elsewhere (`render-voter-prompt.sh:40-45`, `plan-review-loop.sh:178-184`, `render-plan-review-prompt.sh:122-125`); pre-existing asymmetry, not introduced by the loop handoff work.

### OOS_6: [OUT_OF_SCOPE] Assessor plan snapshot blocks remain raw fenced markdown
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prompt-boundary-output.txt, dyn-ship-driver-output.txt
- **Severity**: latent
- **Concern**: Assessor hardens `FEATURE_FILE` only; `PLAN_ORIGINAL`, `PLAN_PREV`, and `PLAN_CURRENT` remain raw `cat` inside markdown fences. Plan content with delimiter-like text or closing fence lines could break fence structure or inject instructions into external assessor models. `SECURITY.md` claims assessor staged-anchor coverage without symmetric plan-body treatment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Wrap plan sections in the same literal-redacted escaped untrusted block contract or document the gap explicitly in SECURITY.md until migrated.
  - From cursor-specialist-edge-cases-output.txt: Pre-existing; address in a dedicated assessor plan-hardening follow-up if desired.
  - From dyn-prompt-boundary-output.txt: The branch hardens the assessor feature block, but `PLAN_ORIGINAL`, `PLAN_PREV`, and `PLAN_CURRENT` are still raw `cat` inside markdown fences with no `<>&` escaping or breakout hardening; that predates this diff and was not regressed here.
  - From dyn-ship-driver-output.txt: `skills/shared/scripts/render-assessor-prompt.sh:66-78` still inlines plan snapshots as raw markdown fences while only the feature file uses the literal-redacted block; the plan explicitly deferred plan-fence hardening, but `SECURITY.md` now claims assessor staged-anchor coverage without the same symmetric treatment for plan bodies.

### OOS_7: [OUT_OF_SCOPE] Aggregator still raw-inlines reviewer findings bodies
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-testing-output.txt, dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: Pre-existing raw `cat` of reviewer findings into aggregator prompt without delimiter escaping; same prompt-injection class as scope-anchor hardening gap, not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track separately; apply the same untrusted-block renderer to findings input when hardening the aggregator surface.
  - From cursor-specialist-testing-output.txt: Scope-anchor inline append uses redact-only, not literal-redacted escaping. Delimiter-like anchor text could perturb aggregator prompt structure. Migrate append through emit_untrusted_file_block or equivalent escaping helper.
  - From dyn-prompt-boundary-output.txt: Raw reviewer findings are still inlined with plain `cat` before the new scope-anchor block; that behavior predates this branch and remains a separate prompt-boundary gap.

### OOS_8: [OUT_OF_SCOPE] `read-tools` context path not inline-hardened
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `read-tools` path in `launch-claude-subprocess.sh` does not inline-harden context bodies. Context reachable via `--add-dir` remains less bounded than embedded `--context-files` hardening; pre-existing and out of scope for this branch's context-files work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pre-existing; out of scope for this branch’s --context-files hardening.

### OOS_9: [OUT_OF_SCOPE] `test-check-scope-reduction-marker` registered in two Makefile harness shards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-marker-flow-output.txt
- **Severity**: nit
- **Concern**: `test-check-scope-reduction-marker` runs in both harness shards 7 and 18, duplicating CI wall time without added coverage signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Keep a single shard registration.
  - From cursor-specialist-edge-cases-output.txt: Deduplicate to one shard when convenient.
  - From dyn-marker-flow-output.txt: `test-check-scope-reduction-marker` is registered in both `test-harnesses-7` and `test-harnesses-18`, so CI runs the same harness twice; harmless but redundant.

### OOS_10: [OUT_OF_SCOPE] Voter ballot filesystem path lacks attribute escaping
- **Reviewer(s)**: dyn-prompt-boundary-output.txt
- **Severity**: latent
- **Concern**: Ballot filesystem path is still interpolated into the voter prompt without attribute escaping; unchanged by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-boundary-output.txt: The ballot filesystem path is still interpolated into the voter prompt without attribute escaping; unchanged by this branch.

### OOS_11: [OUT_OF_SCOPE] Empty `SCOPE_MARKER_HELPER` fails open in dedup `is_tagged()`
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: latent
- **Concern**: If `SCOPE_MARKER_HELPER` were ever empty/unset, `is_tagged()` returns `False` instead of failing closed. Production wiring always sets a path and non-0/1 helper exits abort dedup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: If `SCOPE_MARKER_HELPER` were ever empty/unset, `is_tagged()` returns `False` instead of failing closed; production wiring always sets a path and non-0/1 helper exits abort dedup, so this is a latent foot-gun rather than a regression from this diff.

### OOS_12: [OUT_OF_SCOPE] Canonical helper does not scan `- **Description**:` for scope-reduction marker
- **Reviewer(s)**: dyn-marker-flow-output.txt
- **Severity**: latent
- **Concern**: Marker detection in `check-scope-reduction-marker.sh` only scans `### FINDING_*` headings and `Concern:`/`what:` lines; a `[SCOPE-REDUCTION]` marker placed only on `- **Description**:` would not be detected. Dedup `problem_text()` has a Description fallback, but the canonical helper does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-marker-flow-output.txt: Marker detection only scans `### FINDING_*` headings, `Concern:`/`what:` lines; a `[SCOPE-REDUCTION]` marker placed only on `- **Description**:` would not be detected. Dedup `problem_text()` has a Description fallback, but the canonical helper does not; pre-existing contract gap, not introduced here.

### OOS_13: [OUT_OF_SCOPE] Assessor `mktemp` prompt file lacks `EXIT` trap
- **Reviewer(s)**: dyn-shell-hygiene-output.txt
- **Severity**: nit
- **Concern**: The `mktemp` prompt file in `render-assessor-prompt.sh` has no `EXIT` trap; a mid-write failure under `set -e` can leave `.assessor-prompt.*` debris. Pre-existing pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-hygiene-output.txt: The `mktemp` prompt file still has no `EXIT` trap; a mid-write failure under `set -e` can leave `.assessor-prompt.*` debris. Pre-existing pattern, not introduced by the scope-anchor delta.
