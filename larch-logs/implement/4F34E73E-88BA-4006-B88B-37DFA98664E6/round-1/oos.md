### FINDING_3: [OUT_OF_SCOPE] missing active-batch guard when pending files are absent
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-evidence-gate
- **Severity**: minor
- **Concern**: When the triage-pending JSONL file is absent, ingest loses the intended active-batch scope check. That leaves acceptance behavior dependent on call order and weakens batch isolation if `ledger --ingest-triage` runs before the pending batch is created.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-evidence-gate: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_5: [OUT_OF_SCOPE] orchestrator-side token relay still fabricates triage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Prompt-only anti-relay rules do not mechanically prove that the triage agent actually read the bundle. If the orchestrator reads bundle files and relays the token out of band, schema-valid verdicts can still be fabricated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_6: [OUT_OF_SCOPE] bundle path containment is unchecked
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Bundle-path validation does not enforce containment under the run directory, so a hand-edited manifest could point token verification at an attacker-chosen local file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] CI cwd differs from the acceptance pytest cwd
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Repo-root-relative static tests can pass in acceptance but fail under CI because the pytest working directory differs. That makes the fixture brittle unless path resolution is made explicit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Standardize pytest cwd or document repo-root resolution pattern for static fixtures


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] unverified `FIXED_CLEAR` sample exclusion is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The exclusion rule for unverified `FIXED_CLEAR` rows is not directly asserted, so the deep-queue sampling path could regress without a targeted test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add assert that unverified FIXED_CLEAR rows never enter sample-sourced deep queue


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_11: [OUT_OF_SCOPE] unreadable-bundle prompt still asks for rejected JSONL
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: The agent prompt still tells triage to emit a full JSONL row for unreadable bundles even though the ingest path rejects rows without a file-derived token. That leaves the agent encouraged to guess at data it cannot validate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Add prompt language to omit JSONL for unreadable bundles, or state explicitly that ingest will reject rows without a file-derived token so the agent should not guess.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_12: [OUT_OF_SCOPE] deep-ingest preservation of triage verification is untested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: There is no dedicated regression test for the deep-only ingest case that must leave `triage_evidence_verified` untouched, so a future change could regress that invariant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Add a small ingest-deep-on-verified-triage fixture asserting `triage_evidence_verified` stays `true`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_13: Token relay can satisfy evidence verification without a real Read
- **Reviewer(s)**: dyn-dyn-evidence-gate
- **Severity**: major
- **Concern**: The ingest check only proves that the JSONL token matches what disk parsing returns; it does not distinguish a triage agent that actually read the bundle from an orchestrator that supplied the token out of band. With prompt-only anti-relay rules, a non-reading agent can still emit schema-valid, token-matched verdicts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-evidence-gate: Add a mechanical boundary—e.g. require a second agent-bound nonce in triage output, record and reject ingest when orchestrator-side bundle reads are detected, or validate platform tool-use metadata before setting `triage_evidence_verified=True`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] appended verification bits are trusted without revalidation
- **Reviewer(s)**: dyn-dyn-evidence-gate
- **Severity**: minor
- **Concern**: `load_ledger` trusts appended `triage_evidence_verified: true` values without an ingest-time signature or revalidation, so a local writer to the ledger file can mark fabricated triage as verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-evidence-gate: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

