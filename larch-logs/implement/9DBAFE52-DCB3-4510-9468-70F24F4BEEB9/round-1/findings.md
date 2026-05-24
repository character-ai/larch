Here is the normalized structured finding list. In-scope items are merged by behavioral risk; out-of-scope items are `### OOS_*` blocks. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (this merge is non-empty).

---

### FINDING_1: Smoke-only `test-plan-review-loop.sh` vs promised stubbed harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The harness is effectively smoke-only (`bash -n` plus minimal argv coverage) while acceptance / structural pins implied broader PATH-stubbed scenarios for `plan-review-loop.sh`. CI and local runs do not exercise ballot build, dedup, aggregation handoff, voter wiring, or KV contracts, so regressions in the driver can ship undetected unless acceptance is revised or scenarios are implemented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Reviewer slot labels bound by collector order vs manifest (mis-attribution risk)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Collector records are aligned to manifest slots by parallel index (and manifest rows with empty `jq .slot` are skipped), so reorder, missing blocks, dispatch bugs, or partially edited `plan-review-slots.ndjson` can stamp findings with the wrong reviewer slot while remaining schema-valid, misleading tally, Gate B, and forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Jaccard dedup merges distinct findings when token sets are empty
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Jaccard dedup treats two empty “what” texts as identical (empty vs empty merges), so multiple distinct sparse findings could collapse into one block and change votes downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Zero-findings path emits tally success semantics without running `tally-plan-review.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The zero-finding short-circuit writes tally-related artifacts / `TALLY_PLAN_REVIEW_STATUS=ok` without invoking `tally-plan-review.sh`, so consumers that treat non-empty tally KVs as proof that tally ran can mis-handle the skipped-voting path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Use a dedicated sentinel or empty tally KVs and document the contract.
  - From cursor-specialist-testing-output.txt: Use a distinct tally status when tally is skipped or align SKILL consumers and document contract
  - From cursor-specialist-edge-cases-output.txt: Use a distinct skipped sentinel or invoke tally on an explicit empty ballot so KVs remain truthful.
  - From cursor-specialist-plan-fidelity-output.txt: Use a skipped-specific tally status or omit the KV when tally is not executed.

### FINDING_5: Missing TSV / prose fallback when TSV is unusable (silent loss of reviewer signal)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: When TSV is missing or unusable, behavior does not match the documented plan edge-case: reviewer signal can drop silently (beyond WARN), under-collecting the ballot and skewing voting outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Non-OK collect statuses skip TSV and prose fallback before discarding reviewer output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Non-OK collect statuses (e.g. NOT_SUBSTANTIVE, EMPTY_OUTPUT) never run TSV or prose fallback extraction, so readable narrative findings can be logged as collector failures yet contribute zero ballot blocks, silently shrinking the review surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Embedded TSV parser Python uses confusing / dead `fi`/`oi` assignments
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Module-level or pre-`main()` assignments use names resembling Bash `fi` and look like dead numbering, which risks mis-read control flow and wrong mental model around dedup renumbering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_8: Branch mixes driver, harness, logs, version/changelog (review / bisect coupling)
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The branch merges the #2676 driver with harness work, version/changelog bumps, and `larch-logs` flushes, making bisect and failure attribution harder because failures may not map cleanly to plan-review changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Panel-failed early exit omits `ballot.txt` while other paths create or clear it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The panel-failed path can exit without `ballot.txt` even though sibling docs list it among session-root artifacts, so tooling or recovery that assumes `ballot.txt` exists after Step 3 can hit `ENOENT` on collapsed panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Dedup `what_text()` regex assumes a fixed “Scenario:” suffix shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Dedup keys on `what_text()` logic that assumes a `. Scenario:` suffix in rendered markdown; if concern text lacks that exact shape, `what_text` falls back to the whole block and Jaccard dedup can misfire across unrelated findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Original issue prose vs revised landed scope (launcher / subprocess / trust boundary)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Original issue text promised no behavior change and no Voter1 launcher change while the branch follows a revised plan (subprocess voter, aggregator mode), so operators trusting the original issue may underestimate runtime deltas and ballot shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: `test-plan-review-loop.md` implies fuller harness than smoke tests deliver
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Documentation admits smoke-only coverage but structural pins can still imply deep loop coverage to casual readers; clarify that the scenario harness is follow-up (or align pins/messages).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [Security] Collector failure log path interpolates unsanitized slot name under `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Collector failure log paths interpolate raw slot/archetype names from the manifest into `DESIGN_TMPDIR`-relative filenames without sanitization, so a malicious or buggy manifest could use sequences like `../` and resolve writes outside the session tmpdir when combined with path canonicalization assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Plan input mode in `aggregate-findings.sh` skips merged-output severity validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Plan input mode skips merged-output severity validation that code mode still enforces, weakening automatic detection of malformed aggregator merges for `/design` (e.g. missing severity on merged blocks can pass where code mode fails closed).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: `set -e` abort from `tally-plan-review.sh` before deterministic `emit_loop_kvs` / recovery KVs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: With `set -e`, if `tally-plan-review.sh` exits non-zero (e.g. rc 2 for malformed ballot / unreadable voter file) before `emit_loop_kvs`, the run can abort with partial artifacts while SKILL.md parses empty `LOOP_STATUS` with non-zero rc, losing structured recovery fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: `emit_loop_kvs` overloads aggregator/tally KVs with synthetic values when subsystems did not run
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Synthetic `AGGREGATOR_STATUS` / `TALLY_PLAN_REVIEW_STATUS` values when neither subsystem ran can mislead telemetry or future consumers that assume tally KVs always reflect `tally-plan-review.sh` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Python dedup failure silently copies raw tmp without WARN / degraded panel
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On dedup failure, the flow can fall back to copying the raw tmp file without WARN or `DEGRADED_PANEL`, silently losing dedup and in-scope-wins-OOS guarantees while continuing as if dedup succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Stale normative prose in `plan-review.md` (dispatch ownership vs `plan-review-loop.sh`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `plan-review.md` still claims static reviewer launches are inline in `SKILL.md` after Step 3 moved into `plan-review-loop.sh`, misleading operators/agents about ownership and where to debug failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: `plan-review-loop.md` overstates harness and ballot invariants vs code / panel-failed path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The sibling spec overstates offline stub harness and invariant ballot presence relative to the actual test script and panel-failed behavior, risking incorrect “edit-in-sync” guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: `design-driver.md` lacks explicit backward-compat note for `ACTION=TALLY`
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Missing explicit note that `ACTION=TALLY` remains for backward-compatible older callers, so out-of-tree or legacy SKILL snapshots lose rationale for keeping the TALLY arm.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

### OOS_1: [OUT_OF_SCOPE] Large committed `larch-logs/**` diffs (policy / review noise, not feature logic)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Large run-log directories dominate diff size and review signal, but logs are shipped by design per repo policy; not treated as a defect of plan-review-loop correctness for this scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Extra harness for `test-read-design-review-budget-invoke.sh` (#2715) on same branch
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness expansion tied to #2715 is present on the branch but is not part of the supplied #2676 implementation plan; track under #2715 / release hygiene rather than #2676 fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge notes (for humans, not machine validation):**  
- Input `FINDING_8` / `19` / `29` were merged into **OOS_1** (all `[OUT_OF_SCOPE]` + `larch-logs/**`).  
- Zero-tally KV concerns (`FINDING_4`, `11`, `18`, `28`, `37`) merged into **FINDING_4** with five distinct non-identical suggested-revision strings preserved.  
- Slot mis-attribution (`FINDING_2`, `9`, `17`, `22`, `34`) merged into **FINDING_2**.  
- Panel missing `ballot.txt` (`FINDING_10`, `25`, `32`) merged into **FINDING_9**.  
- TSV-missing-only narrative (`FINDING_5`, `35`) merged into **FINDING_5**; non-OK collect path (`FINDING_23`) kept as **FINDING_6** (different code path / fix).  
- `FINDING_26` kept separate from **FINDING_4** (synthetic KV overload across subsystems vs “ok without tally” specifically).
