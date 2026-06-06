## Proposed Design Outline

### Goals
- File accepted `[OUT_OF_SCOPE]` review findings instead of silently dropping them (NEVER #14).
- Make the OOS counter (bash awk + Python port) and ship-driver disposition gate recognize legacy-header accepted OOS.
- Add regression coverage in both the bash and Python gate harnesses.

### Non-goals
- No change to the design plan-review OOS path — `tally-plan-review.sh` already emits only `### OOS_` headers.
- No change to vote-tally/classification logic, gate disposition math, or the `/issue` filing schema.
- No change to security-OOS routing — security findings stay local and are never filed.

### Approach sketch
- Producer normalization (primary fix): in `tally-code-votes.sh`, rewrite any non-`OOS_` header (`### FINDING_N:`, both the `[OUT_OF_SCOPE]` tag and the scope-drift case) to `### OOS_<k>:` with a collision-free fresh index before writing the accepted-OOS output; preserve the title text after the id.
- Reader backstop (defense-in-depth): extend `oos-non-security-block-count.awk` and `python/oos.py` `_OOS_HEADER_RE` to also match the `### FINDING_N: [OUT_OF_SCOPE]` header (tagged only — bare `### FINDING_N:` stays an in-scope finding); keep the security-exclusion sub-rule intact.
- Keep the awk counter and its Python port semantically in lockstep.

### Surfaces in scope
- `skills/review/scripts/tally-code-votes.sh` (producer)
- `skills/implement/scripts/oos-non-security-block-count.awk` (bash counter)
- `python/oos.py` (Python counter)
- `skills/implement/scripts/test-oos-disposition-gate.sh`, `python/test_oos.py` (regression)

### Open questions
- None.
