### OOS_1: [OUT_OF_SCOPE] risk-integration — stale parent `oos-dropped-before-vote.md` across no-drop rounds
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-oos-routing-output.txt
- **Severity**: latent
- **Concern**: `_copy_gate_audit_to_parent` in `python/review_pipeline.py` (~1933–1943) returns early when `gate.dropped_count <= 0` and never overwrites or clears the parent `oos-dropped-before-vote.md`. A later no-drop round can therefore leave stale parent audit bytes from an earlier round. Pre-existing behavior; this PR does not change that helper (plan explicitly forbids changing it).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-dyn-oos-routing-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] security / correctness — non-atomic dual audit writes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-oos-routing-output.txt
- **Severity**: latent
- **Concern**: Public and local audit writes in `python/review_pipeline.py` (~2145–2157) use sequential, non-atomic `larch_io.write_text` rather than the module's `atomic_write`. A crash or failure after the public write can leave partial on-disk state that panel-failed paths may flush. After partitioning, the public file should contain only non-security blocks, so this is a robustness concern rather than the original leak path; not newly introduced at the same severity as the fixed bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-dyn-oos-routing-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] code-quality — duplicate security classifiers may drift
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: OOS filing in `python/oos_filer.py` (~86–88) still uses a separate `_is_security_block` helper instead of `voting.is_security_block_text`, so the two classifiers can drift. Not modified by this diff; unifying them would be a separate refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] risk-integration — zero-drop pre-vote gate path untested for empty security sidecar
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The zero-drop pre-vote gate path lacks a unit test for empty security sidecar write. Stale `oos-dropped-security-local.md` from a prior round could persist undetected if a future edit skips the empty write on `STATUS=skipped`. Add `test_pre_vote_oos_gate_writes_empty_sidecars_when_no_oos` with in-scope-only findings asserting both audit files are empty and `STATUS=skipped`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] risk-integration — no test guards allowlisting of `oos-dropped-security-local.md`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No test guards against allowlisting `oos-dropped-security-local.md` in `python/run_logs.py` (~2999–3008). A future PR could add the basename to `_ROUND_ARTIFACT_ALLOW` and commit security OOS to public `larch-logs/` without test failure. Assert `oos-dropped-security-local.md` not in `_ROUND_ARTIFACT_ALLOW` in `test_run_logs.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] risk-integration — `is_security_block_text` lacks heading-only `[OUT_OF_SCOPE] [security]` coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `is_security_block_text` in `python/test_voting.py` (~84–100) lacks heading-only `[OUT_OF_SCOPE] [security]` coverage. Explicit-header routing could regress while focus-area tests still pass; security blocks could leak to public audit via title-only tags. Add parametrized case: `### FINDING_1: [OUT_OF_SCOPE] [security] Title` with no focus-area field.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] security — classifier boundary for unmarked dropped OOS blocks
- **Reviewer(s)**: dyn-dyn-oos-routing-output.txt
- **Severity**: latent
- **Concern**: Security routing for pre-vote drops in `python/voting.py` (~1173–1195) still depends on `is_security_block_text` tags (`focus-area`, opening `[security]` heading, unfenced `focus-area=security` prose). Dropped OOS blocks with sensitive body text but no routing markers still land in the public audit. Pre-existing classifier boundary; unchanged by the extraction refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-oos-routing-output.txt: Address the concern above.

---

**Merge notes (brief):**
- **FINDING_1** and **FINDING_8** (input) merged into aggregator **FINDING_1** (same `_copy_gate_audit_to_parent` stale-parent behavior).
- **FINDING_2** and **FINDING_10** (input) merged into aggregator **FINDING_2** (same non-atomic dual-write robustness at ~2145).
- Input **FINDING_7** kept as in-scope aggregator **FINDING_7** (deny-glob gap); kept separate from OOS allowlist/deny test gaps (**FINDING_5**, **FINDING_4**) because they target different enforcement mechanisms and test surfaces.
- Input **FINDING_9** kept separate from **FINDING_7** (classifier tagging vs publication deny-list boundary).

