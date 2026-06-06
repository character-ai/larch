### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:153-156; skills/shared/scripts/oos-serialize.sh:55-62; skills/review/scripts/review-core.sh:928-932
- **Concern**: Production path rewrites oos-accepted-review.md after tally via oos-serialize, bypassing the proposed tally header normalization. Scenario: tally-code-votes.sh writes accepted OOS (including scope-drift reclassifications) to oos-accepted-review.md, but review-core always runs emit-tally.sh next, which calls oos-serialize.sh on oos.md and overwrites that file; oos-serialize only emits ### FINDING_N: blocks tagged [OUT_OF_SCOPE]/[OOS], so scope-drift accepted OOS (bare ### FINDING_N:) are dropped and legacy headers survive for tagged blocks — tally-only harness tests never exercise this chain
- **Proposed resolution**: Make emit-tally preserve tally output when OOS_ACCEPTED_COUNT>0 (skip oos-serialize), or apply the same normalize_oos_block_header logic inside oos-serialize and include scope-drift blocks; add a review-core/emit-tally integration assertion for scope-drift and [OUT_OF_SCOPE] accepted paths

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/tally-code-votes.sh:583-587
- **Concern**: Plan says to pipe normalized output into both accepted-OOS sinks without restating the existing equality guard. Scenario: When SESSION_ENV_PATH is unset, OOS_ACCEPTED_OUT equals OOS_ACCEPTED_FILE (lines 111-115). Writing normalized output to both unconditionally duplicates every accepted block, inflates awk/Python non_security counts, and can false-fail the disposition gate (two blocks needing coverage for one accepted finding)
- **Proposed resolution**: Preserve the current branch: append normalized output once to OOS_ACCEPTED_FILE, then append to OOS_ACCEPTED_OUT only when OOS_ACCEPTED_OUT != OOS_ACCEPTED_FILE; optionally assert awk count == 1 in single-OOS harness cases to catch regressions

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:153-156; skills/shared/scripts/oos-serialize.sh:55-62; skills/review/scripts/review-core.sh:928-932
- **Concern**: Plan fixes tally output only; emit-tally still overwrites oos-accepted-review.md via oos-serialize. Scenario: On /implement, tally-code-votes.sh would write canonical ### OOS_ headers, then emit-tally.sh always runs oos-serialize.sh on oos.md and overwrites oos-accepted-review.md. oos-serialize keeps only ### FINDING_N: lines tagged [OUT_OF_SCOPE]/[OOS] (no header rewrite) and drops scope-drift accepted OOS (bare ### FINDING_N:). review-core then copy_to_parent propagates the overwrite. tally-only harness tests never hit this chain, so acceptance criterion 1 still fails in production
- **Proposed resolution**: Add emit-tally.sh and/or oos-serialize.sh to the plan: skip oos-serialize when tally already wrote accepted OOS (e.g. OOS_ACCEPTED_COUNT>0), or apply the same normalize_oos_block_header logic inside oos-serialize and include scope-drift accepted blocks; add a review-core/emit-tally integration assertion for [OUT_OF_SCOPE] and scope-drift accepted paths

### OOS_1:
- **Description**: Proposed `_OOS_HEADER_RE` is not semantically equivalent to the awk FINDING branch for tag-after-title headers. Scenario: Awk uses `index($0,"[OUT_OF_SCOPE]")` anywhere on the line after `^###[[:space:]]+FINDING_[0-9]+:`; Python `FINDING_\d+:\s*\[OUT_OF_SCOPE\]` requires the tag immediately after the colon (whitespace only). Headers like `### FINDING_1: Some Title [OUT_OF_SCOPE]` count in awk but not in Python, so bash and Python gates can disagree on defense-in-depth inputs even though the plan claims lockstep parity
- **Reviewer**: Cursor-dyn-awk-python-regex-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/oos.py:32-33
- **Phase**: design
