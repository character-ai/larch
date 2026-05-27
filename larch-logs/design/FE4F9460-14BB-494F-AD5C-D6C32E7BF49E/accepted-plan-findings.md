### FINDING_1: Unsupported equals-form escape-hatch syntax
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity, Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry
- **Severity**: important
- **Concern**: The planned hint/docs advertise `--allow-findings-outside-tmpdir=true`, but the parser only accepts the split argv form `--allow-findings-outside-tmpdir true`, so callers copying the hint would hit `unknown option` instead of enabling the opt-in.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Either add a parser case for --allow-findings-outside-tmpdir=true|false and cover it in the harness, or change the hint to the accepted space-separated form and assert that exact hint.
  - From Cursor-Edge, Codex-Edge: Use the space-separated spelling everywhere and update assertions, or add parser support for --allow-findings-outside-tmpdir=true
  - From Codex-Innovation: Either change the hint to --allow-findings-outside-tmpdir true or add a --allow-findings-outside-tmpdir=* parser arm and document both forms
  - From Cursor-Pragmatic, Codex-Pragmatic: Either change the hint/docs/tests to --allow-findings-outside-tmpdir true or add parser support for --allow-findings-outside-tmpdir=true and test both forms
  - From Cursor-Requirements, Codex-Requirements: Either change the hint/docs/tests to the accepted space form --allow-findings-outside-tmpdir true or add parser support and regression coverage for --allow-findings-outside-tmpdir=true
  - From Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity: Use the split form in the hint/docs/tests, e.g. --allow-findings-outside-tmpdir true, or add an explicit --allow-findings-outside-tmpdir=* case with shift 1 and tests for both spellings
  - From Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry: Change the hint/docs to the space-separated form or add parser support and tests for --allow-findings-outside-tmpdir=true


### FINDING_2: New flag is consumed before validation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence, Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity, Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry
- **Severity**: important
- **Concern**: The planned validation order allows containment logic to read `ALLOW_FINDINGS_OUTSIDE_TMPDIR` before the new boolean value is validated, so invalid values like `maybe` can produce containment errors instead of the promised `must be true or false` diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Validate ALLOW_FINDINGS_OUTSIDE_TMPDIR immediately after argv parsing and before path containment, or move the whole boolean validation block before filesystem checks and update the plan/tests to lock that order.
  - From Cursor-Edge, Codex-Edge: Move all bool/mode/input-mode validation, including the new flag, immediately after required-arg checks and before any flag-dependent path checks; add invalid flag plus outside-path coverage
  - From Codex-Innovation: Add and validate ALLOW_FINDINGS_OUTSIDE_TMPDIR before the containment case, then add an invalid-value outside-path regression
  - From Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements: Validate ALLOW_FINDINGS_OUTSIDE_TMPDIR before the containment case and add a regression for invalid value with an outside findings path
  - From Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Validate ALLOW_FINDINGS_OUTSIDE_TMPDIR immediately after argv parsing and before containment, or make the containment branch reject non-true/non-false values before testing for true
  - From Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity: Validate ALLOW_FINDINGS_OUTSIDE_TMPDIR before the flag-gated containment case, and add an invalid-value regression using an outside-tmpdir findings file
  - From Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry: Move ALLOW_FINDINGS_OUTSIDE_TMPDIR validation before the containment case, or make the containment branch run only after an explicit true false validation


### FINDING_3: SECURITY.md omits containment relaxation
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence, Codex-Innovation, Cursor-Requirements, Codex-Requirements, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity, Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry
- **Severity**: important
- **Concern**: The plan skips `SECURITY.md` even though the opt-in relaxes the findings-file containment boundary and can rewrite an outside regular file in place, leaving the documented trust model stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add a concise SECURITY.md trust-model note for aggregate-findings: default false, input-only opt-in, symlink rejection still enforced, output artifacts still confined, success rewrites the outside ballot, and residual same-UID TOCTOU/shared-file risks.
  - From Cursor-Edge, Codex-Edge, Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Add a SECURITY.md residual-risk note for the opt-in read/rewrite surface and emit a low-noise breadcrumb or execution issue when flag=true and the canonical input is outside review tmpdir
  - From Codex-Innovation, Cursor-Requirements, Codex-Requirements: Update the Pre-vote findings aggregation paragraph to document the opt-in, unchanged symlink/output containment, in-place clobber semantics, and the no-audit/no-execution-issues decision
  - From Cursor-Pragmatic, Codex-Pragmatic: Bound the escape hatch to an explicit canonical allow-root such as the parent round/session dir, keep symlink checks, and update SECURITY.md with the new trust boundary and residual overwrite risk
  - From Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity: Add a concise SECURITY.md trust-model note covering the opt-in flag, non-symlink regular-file requirement, input-only relaxation, strict output containment, and in-place rewrite residual risk
  - From Cursor-dyn-containment-asymmetry, Codex-dyn-containment-asymmetry: Revise the plan to update SECURITY.md with the input-only escape hatch, symlink limits, outside overwrite behavior, and same-UID/operator trust assumptions


### FINDING_4: No regression for strict output containment with outside input allowed
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed tests cover outside input acceptance but do not prove that aggregator-produced candidate output remains confined under `--review-tmpdir` when the new input flag is true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Codex-Arch: Add a regression using --allow-findings-outside-tmpdir true with an outside findings file and a stubbed candidate path outside --review-tmpdir; assert REASON=dispatch-failed, the output-containment warning, and unchanged findings.
  - From Cursor-Edge, Codex-Edge: Add a flag=true test where ALL_OUTPUT_FILES or ALL_OUTPUT_FILES_PATH resolves to an outside candidate and assert dispatch-failed, unchanged input, and the existing output-containment warning
  - From Cursor-Innovation: Add a third case: outside ballot + flag true + stub candidate path outside `--review-tmpdir`; assert `AGGREGATED=false`, `REASON=dispatch-failed`, outside ballot byte-unchanged


### FINDING_5: Allowed-outside fixture may not match merge stub reviewers
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned outside-input test can use a two-reviewer fixture while reusing a merge stub that emits `cursor-a`, `cursor-b`, and `cursor-c`, causing validator failures before the test proves containment relaxation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge: Duplicate or move the existing 3-reviewer in3 fixture before these tests, or add a stub merge kind whose reviewer list matches the 2-block outside fixture
  - From Codex-Innovation: Specify the fixture to include exactly cursor-a/cursor-b/cursor-c across the two blocks, reuse a three-block in3-style fixture, or add a dedicated two-reviewer stub kind
  - From Cursor-Pragmatic, Codex-Pragmatic: Specify the outside test fixture must include all three reviewer labels emitted by the stub, or add a dedicated two-reviewer merge stub variant
  - From Cursor-Requirements, Codex-Requirements: Specify the outside fixture to include cursor-a-output.txt, cursor-b-output.txt, and cursor-c-output.txt across its two FINDING blocks, or add a dedicated two-reviewer stub merge


### FINDING_6: Outside temp directory is not cleaned up
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-Innovation, Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence, Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity
- **Severity**: nit
- **Concern**: The planned sibling `TMP_OUTSIDE` directory is not covered by the existing cleanup trap, so harness runs can leak temporary directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements: Create the outside fixture under a parent covered by the trap, or extend the trap to rm -rf both "$TMP" and "$TMP_OUTSIDE"
  - From Cursor-Innovation: Create `TMP_OUTSIDE` under `$TMP/outside-parent` or extend `trap` to remove sibling dirs
  - From Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Add TMP_OUTSIDE='' and trap 'rm -rf "$TMP" "${TMP_OUTSIDE:-}"' EXIT, or otherwise include the outside fixture in cleanup
  - From Cursor-dyn-flag-grammar-parity, Codex-dyn-flag-grammar-parity: Update the trap to remove ${TMP_OUTSIDE:-} as well, or create and register the sibling temp dir with an explicit cleanup before the new tests run


### FINDING_8: Plan contradicts itself on validation order
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The approach says to validate booleans before `REVIEW_TMPDIR_CANON`, while later edit steps keep containment before sibling boolean validation and put the new flag validation after it, creating conflicting implementation guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align step 8 with steps 1-7 (containment before sibling boolean validation; new flag validated with codex/cursor/mode/input-mode) or explicitly mark step 8 as non-normative


### FINDING_10: [OUT_OF_SCOPE] Disabled mode still enforces input containment
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Concern**: `LARCH_AGGREGATOR_DISABLED=1` still performs input containment before returning `REASON=disabled`, which may surprise operators expecting no-op mode to avoid outside-path rejection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: [OUT_OF_SCOPE] Document in `aggregate-findings.md` Escape hatch, or move disabled fast-path before containment (behavior change beyond #2868)


### FINDING_12: Grep assertion for leading dash pattern needs option terminator
- **Reviewer(s)**: Codex-Innovation, Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence
- **Severity**: important
- **Concern**: A planned `grep -Fq '--allow-findings-outside-tmpdir=true'` assertion treats the pattern as an option because it begins with `--`, causing the test to fail for the wrong reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Use grep -Fq -- '--allow-findings-outside-tmpdir=true' "$err" or grep -Fq -e '--allow-findings-outside-tmpdir=true' "$err"
  - From Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Specify grep -Fq -- '--allow-findings-outside-tmpdir=true' "$TMP/out-outside-reject.err"


### FINDING_13: Final outside rewrite failure can violate non-fatal aggregator contract
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: With an outside findings file, the final `mv -f` may fail due to permissions or parent directory state after dispatch has succeeded, letting `set -e` make the script exit nonzero instead of reporting a non-fatal aggregation failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Plan preflight or guarded handling for final rewrite failures, set MERGE_PIPELINE_RC=2 with a warning, preserve input, and add a read-only outside-destination regression


### FINDING_14: Negative-exit test invocation is underspecified under set -e
- **Reviewer(s)**: Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence
- **Severity**: important
- **Concern**: The harness uses `set -euo pipefail`, so directly invoking a command expected to exit 2 would abort before stderr and byte-unchanged assertions run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Spell out an if/set +e block that captures rc, asserts rc=2, then checks stderr and cmp


### FINDING_15: Allowed outside-input test has weak persistence assertion
- **Reviewer(s)**: Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence
- **Severity**: latent
- **Concern**: The proposed allowed-outside test only checks that the outside file contains a `FINDING` block, which would also be true before merging and therefore does not prove the intended one-block rewrite occurred.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-evidence, Codex-dyn-harness-evidence: Match the existing merge-success assertion by checking exactly one ^### FINDING_ block, and preferably cmp that outside-work.md differs from the original copy### OOS_1:
- **Description**: [OUT_OF_SCOPE] Existing artifact-name collisions are not guarded by _cand_canon. Scenario: Passing --findings-file as $REVIEW_TMPDIR/aggregator-prompt.md truncates the ballot while building the prompt; passing aggregator-output.txt can make validation compare output to itself, and the post-dispatch candidate containment check still passes because the path is under tmpdir
- **Reviewer**: Cursor-dyn-containment-asymmetry
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/review/scripts/aggregate-findings.sh:159-167,682-685,720-745,646-679
- **Phase**: design


