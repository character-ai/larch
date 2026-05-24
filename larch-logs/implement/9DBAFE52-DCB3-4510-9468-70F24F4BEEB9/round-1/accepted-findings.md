### FINDING_1: Smoke-only `test-plan-review-loop.sh` vs promised stubbed harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The harness is effectively smoke-only (`bash -n` plus minimal argv coverage) while acceptance / structural pins implied broader PATH-stubbed scenarios for `plan-review-loop.sh`. CI and local runs do not exercise ballot build, dedup, aggregation handoff, voter wiring, or KV contracts, so regressions in the driver can ship undetected unless acceptance is revised or scenarios are implemented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: Dedup `what_text()` regex assumes a fixed “Scenario:” suffix shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Dedup keys on `what_text()` logic that assumes a `. Scenario:` suffix in rendered markdown; if concern text lacks that exact shape, `what_text` falls back to the whole block and Jaccard dedup can misfire across unrelated findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: [Security] Collector failure log path interpolates unsanitized slot name under `DESIGN_TMPDIR`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Collector failure log paths interpolate raw slot/archetype names from the manifest into `DESIGN_TMPDIR`-relative filenames without sanitization, so a malicious or buggy manifest could use sequences like `../` and resolve writes outside the session tmpdir when combined with path canonicalization assumptions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_15: `set -e` abort from `tally-plan-review.sh` before deterministic `emit_loop_kvs` / recovery KVs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: With `set -e`, if `tally-plan-review.sh` exits non-zero (e.g. rc 2 for malformed ballot / unreadable voter file) before `emit_loop_kvs`, the run can abort with partial artifacts while SKILL.md parses empty `LOOP_STATUS` with non-zero rc, losing structured recovery fields.
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


### FINDING_9: Panel-failed early exit omits `ballot.txt` while other paths create or clear it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The panel-failed path can exit without `ballot.txt` even though sibling docs list it among session-root artifacts, so tooling or recovery that assumes `ballot.txt` exists after Step 3 can hit `ENOENT` on collapsed panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


