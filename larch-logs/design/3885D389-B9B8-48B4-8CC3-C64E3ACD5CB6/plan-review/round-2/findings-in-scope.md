### FINDING_1: Incomplete `test-implement-structure.sh` migration vs remaining `_ib_*` pins
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The plan’s `test-implement-structure.sh` rewrite list does not cover all pins that still target removed `_ib_*` symbols. Gaps include `_ib_target_issue` (507–510), the exit-2 guard still keyed on `_ib_rc` (511–515; SKILL moves to `_inv_rc` at two sites), the bootstrap stdout parse loop (517–518), and the BRANCH_NAME/BRANCH_ACTION/PLAN_FILE/coder `_ib_kv_scan` case arms (519–526). An implementer can follow the plan, drop `_ib_kv_scan` from SKILL.md, and still leave or miss pins so `make test-implement-structure` fails, or drop routing-key coverage on the wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Extend the plan’s `test-implement-structure.sh` bullet to invert/retarget 507-526: assert `_ib_target_issue` absent; require `_inv_rc` exit-2 guard(s) on wrapper calls (≥2); move BRANCH_NAME/PLAN_FILE/coder parse coverage to `scripts/implement-bootstrap-invoke.sh` (or invert); retarget the stdout-parse pin to the shared routing-env block (or drop if harness-owned).

### FINDING_2: Duplicated Step 0 exit-2 operator messaging (wrapper vs SKILL)
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Exit-2 handling splits operator messaging between the wrapper and SKILL call sites. The wrapper is specified to run `_ib_handle_bootstrap_exit2` (formatted operator strings to stdout) then `exit 2`, while SKILL initial/resume/dirty-tree sites also do `print "$_inv_out"` when `_inv_rc -eq 2`. Command substitution captures wrapper stdout, so operators can see duplicated Step 0 failure text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make one owner: either wrapper prints handler output and SKILL only `exit 2` (no second print), or wrapper returns rc 2 with raw bootstrap stdout and a single handler site prints once; align `test-implement-bootstrap-invoke.sh` exit-2 cases with the chosen contract
