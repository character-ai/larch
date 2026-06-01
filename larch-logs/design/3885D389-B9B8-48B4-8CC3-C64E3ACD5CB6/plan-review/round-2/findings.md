### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:41-42; scripts/test-implement-structure.sh:507-526
- **Concern**: The `test-implement-structure.sh` rewrite list is incomplete versus pins that still target removed `_ib_*` symbols.. Scenario: It omits `_ib_target_issue` (507-510), the exit-2 guard still keyed on `_ib_rc` (511-515; SKILL moves to `_inv_rc` at two sites), the bootstrap stdout parse loop (517-518), and the BRANCH_NAME/BRANCH_ACTION/PLAN_FILE/coder `_ib_kv_scan` case arms (519-526). An implementer can follow the plan, drop `_ib_kv_scan` from SKILL.md, and still leave or miss pins so `make test-implement-structure` fails, or drop routing-key coverage on the wrapper.
- **Proposed resolution**: Extend the plan’s `test-implement-structure.sh` bullet to invert/retarget 507-526: assert `_ib_target_issue` absent; require `_inv_rc` exit-2 guard(s) on wrapper calls (≥2); move BRANCH_NAME/PLAN_FILE/coder parse coverage to `scripts/implement-bootstrap-invoke.sh` (or invert); retarget the stdout-parse pin to the shared routing-env block (or drop if harness-owned).

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:12-13,35-38
- **Concern**: Exit-2 handling assigns operator messaging to the wrapper but SKILL call sites still re-print captured stdout on rc 2. Scenario: The wrapper is specified to run `_ib_handle_bootstrap_exit2` (formatted operator strings to stdout) then `exit 2`, while SKILL initial/resume/dirty-tree sites also do `print "$_inv_out"` on `_inv_rc -eq 2`; command substitution captures wrapper stdout, so operators see duplicated Step 0 failure text
- **Proposed resolution**: Make one owner: either wrapper prints handler output and SKILL only `exit 2` (no second print), or wrapper returns rc 2 with raw bootstrap stdout and a single handler site prints once; align `test-implement-bootstrap-invoke.sh` exit-2 cases with the chosen contract
