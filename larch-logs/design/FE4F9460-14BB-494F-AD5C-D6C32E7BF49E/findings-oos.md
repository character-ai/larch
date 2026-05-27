### OOS_1:
- **Description**: [OUT_OF_SCOPE] Existing artifact-name collisions are not guarded by _cand_canon. Scenario: Passing --findings-file as $REVIEW_TMPDIR/aggregator-prompt.md truncates the ballot while building the prompt; passing aggregator-output.txt can make validation compare output to itself, and the post-dispatch candidate containment check still passes because the path is under tmpdir
- **Reviewer**: Cursor-dyn-containment-asymmetry
- **Severity**: latent
- **Focus area**: security
- **Location**: skills/review/scripts/aggregate-findings.sh:159-167,682-685,720-745,646-679
- **Phase**: design

