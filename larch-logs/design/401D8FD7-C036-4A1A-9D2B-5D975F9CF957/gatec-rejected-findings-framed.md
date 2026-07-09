---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Separate bgjob re-entry cure from fingerprint validation
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The mechanical-backing language risks conflating the verified #6633 bgjob re-entry fix with the DIFF_FINGERPRINT/HEAD_SHA consumer-validation pattern, which can overstate what bgjob result envs actually enforce and blur stale-rejoin hygiene versus assessment-sidecar checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Split Mechanical backing into two repo-observed patterns: (1) DIFF_FINGERPRINT/HEAD_SHA checks via note_consumable and _staged_fingerprint_valid for staged or durable assessments (#5337 family); (2) bgjob re-entry clears stale result envs before rejoin (#6633 via _step3_clear_downstream_sentinels). Keep the normative rule input-keyed or fail loud; do not claim bgjob envs already carry consumer-side fingerprint validation."
  - From Cursor-Innovation: "Add explicit drafting guidance in the plan Files/Approach section: describe observed backing as assessment-sidecar `DIFF_FINGERPRINT`/`HEAD_SHA` checks in `python/larch/core/architectural_guidelines.py`; describe the #6633 bgjob cure as re-entry stale result-env clearing; state normatively that remaining bgjob consumers should adopt fingerprint validation. Drop or rewrite the issue sentence about fingerprints already living in persisted result envs."
  - From Cursor-Pragmatic: "Resolve the conflict in Files: normative rule may follow issue prose, but the Mechanical backing paragraph must name note_consumable and _staged_fingerprint_valid as the deployed pattern, describe bgjob re-entry as stale-result-env clearing today, and state fingerprint-at-consumption as the extension target without claiming universal env-resident fingerprints. Add a matching failure-mode bullet so implementers do not treat edge-case no mechanical coverage for all bgjob as PR-scope-only while still shipping overstated prose."


---LARCH-REJECTED-END---
