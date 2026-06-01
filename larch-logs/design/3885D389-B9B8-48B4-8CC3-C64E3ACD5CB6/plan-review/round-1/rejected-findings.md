### [Plan Review] FINDING_4

### FINDING_4: Plan omits post-refactor awk expectations in `test-implement-structure.sh`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The plan says to retarget the Step 0 awk guard in `scripts/test-implement-structure.sh` (~550–575) but does not specify new expected counts after bootstrap moves out of `<!-- step:0` bash blocks. An implementer may leave `bootstrap_calls==1` / `resume_mentions==1` on `implement-bootstrap.sh` literals and get a false pass or a confusing failure after SKILL.md correctly drops direct bootstrap calls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Spell out the post-refactor awk expectations (e.g. zero direct `implement-bootstrap.sh` calls in Step 0 bash, exactly one `implement-bootstrap-invoke.sh --mode initial`, exactly one `--mode resume`, `--up-to-phase coder` asserted only in `scripts/implement-bootstrap-invoke.sh`)

**Merge notes (for voters, not machine output):** Input FINDING_2–3, 6, and 9 → aggregator FINDING_2; input FINDING_1, 4, and 7 → aggregator FINDING_1. No `[OUT_OF_SCOPE]` tags in the supplied input.

