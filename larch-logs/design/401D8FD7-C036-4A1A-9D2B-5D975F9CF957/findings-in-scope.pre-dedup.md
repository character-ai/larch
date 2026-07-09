### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_INVARIANTS.md
- **Concern**: Mechanical-backing instructions conflate the #6633 bgjob cure with DIFF_FINGERPRINT/HEAD_SHA consumer validation. Scenario: The plan tells the author to keep issue wording that says bgjob re-entry should mirror note_consumable/_staged_fingerprint_valid, but #6633 was fixed by unlinking stale bgjob result envs in python/larch/review/plan_review_loop.py::_step3_clear_downstream_sentinels (design-step3-review.result.env and design-step4-tail.result.env), not by storing or validating fingerprints inside those envs. If the committed Mechanical backing paragraph implies fingerprint-in-env validation already covers bgjob re-entry, future stale-rejoin fixes may skip the proven clear-before-rejoin path.
- **Proposed resolution**: Split Mechanical backing into two repo-observed patterns: (1) DIFF_FINGERPRINT/HEAD_SHA checks via note_consumable and _staged_fingerprint_valid for staged or durable assessments (#5337 family); (2) bgjob re-entry clears stale result envs before rejoin (#6633 via _step3_clear_downstream_sentinels). Keep the normative rule input-keyed or fail loud; do not claim bgjob envs already carry consumer-side fingerprint validation.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:9-10
- **Concern**: Plan keeps paragraph prose that `architectural-invariants read` strips.. Scenario: The issue’s stated acceptance path still cannot surface I-Stale-1’s normative body, so the feature remains unverifiable on its canonical reader surface.
- **Proposed resolution**: Reformat I-Stale-1 into `- Why:` bullets so the reader emits the full body, or widen this PR to update `parse_invariant_entries` and its tests.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_INVARIANTS.md
- **Concern**: Mechanical-backing drafting still risks misstating the #6633 bgjob cure. Scenario: The plan tells the author to keep body close to the issue text and preserve mechanical pattern references, while the issue mechanical-backing sentence claims input fingerprints in persisted result envs plus consumer-side validation. Repo evidence for #6633 is stale-env deletion in `_step3_clear_downstream_sentinels()` (`bgjob/design-step3-review.result.env`, `bgjob/design-step4-tail.result.env`), not fingerprint fields inside those envs. `DIFF_FINGERPRINT`/`HEAD_SHA` validation via `note_consumable` and `_staged_fingerprint_valid` applies to assessment sidecars, not bgjob result envs. Verbatim issue wording would fail the feature acceptance criterion that mechanical backing cite only real verified patterns.
- **Proposed resolution**: Add explicit drafting guidance in the plan Files/Approach section: describe observed backing as assessment-sidecar `DIFF_FINGERPRINT`/`HEAD_SHA` checks in `python/larch/core/architectural_guidelines.py`; describe the #6633 bgjob cure as re-entry stale result-env clearing; state normatively that remaining bgjob consumers should adopt fingerprint validation. Drop or rewrite the issue sentence about fingerprints already living in persisted result envs.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_INVARIANTS.md
- **Concern**: Mechanical-backing drafting still allows issue wording that overstates deployed bgjob validation. Scenario: The Files section says keep the body close to the issue text and preserve mechanical references, while Approach 5 requires repo-observed backing. Issue text says input fingerprints in persisted result envs; today bgjob re-entry hygiene is stale result-env clearing on fresh launch (design-step3-review.sh rm of design-step3-review.result.env), and DIFF_FINGERPRINT/HEAD_SHA consumer checks live in architectural_guidelines.py for staged/durable assessments only. Copying issue mechanical backing verbatim would misattribute #6633 and claim env-resident fingerprints the repo does not enforce broadly.
- **Proposed resolution**: Resolve the conflict in Files: normative rule may follow issue prose, but the Mechanical backing paragraph must name note_consumable and _staged_fingerprint_valid as the deployed pattern, describe bgjob re-entry as stale-result-env clearing today, and state fingerprint-at-consumption as the extension target without claiming universal env-resident fingerprints. Add a matching failure-mode bullet so implementers do not treat edge-case no mechanical coverage for all bgjob as PR-scope-only while still shipping overstated prose.



### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:287-310
- **Concern**: Prior full-body read finding is still incomplete: the plan changes verification to `git diff` and forbids the parser or format change needed for `architectural-invariants read` to include the new invariant body. Scenario: The binding acceptance criterion requires `python3 python/cli.py architectural-invariants read` to include `I-Stale-1` with its full body, but the planned paragraph-style entry will be emitted as a heading only because `parse_invariant_entries` preserves headings and `- Why:` bullets
- **Proposed resolution**: Revise the plan so the read command emits the full `I-Stale-1` body, either by updating `parse_invariant_entries` with focused tests or by formatting the invariant in the reader-supported shape while preserving the required normative content



### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9-67
- **Concern**: Prior accepted fix is incomplete: the plan relaxes the required `architectural-invariants read` full-body acceptance check instead of meeting it. Scenario: The binding acceptance criterion requires `python3 python/cli.py architectural-invariants read` to include `I-Stale-1` with its full body, but the firm plan keeps paragraph prose that the current reader strips and verifies only the heading, so the PR can land while failing the stated acceptance criterion
- **Proposed resolution**: Make the firm plan satisfy full-body read output: either format the new invariant body using reader-preserved `- Why:` lines, or add firm parser and targeted test updates that preserve invariant prose in `architectural-invariants read`



