### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:562-575
- **Concern**: Step 0 awk still exits 10/13 on direct bootstrap/resume-plan-tail counts. Scenario: Implementer updates grep pins but leaves END rules requiring exactly one `--up-to-phase coder` and one `--resume-plan-tail` in Step 0 bash; post-refactor blocks have zero such literals → `make test-implement-structure` fails despite correct SKILL.md
- **Proposed resolution**: Replace exit 10/13 with counts for `implement-bootstrap-invoke.sh --mode initial` and `--mode resume` as the plan’s awk retarget prose describes

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:514-518
- **Concern**: Proposed pins require set +e fences at ≥3 wrapper call sites but SKILL.md only has two executable invoke sites today (Step 0 initial block and dirty-tree recovery fence; no separate Step 0 resume bash). Scenario: Structure harness fails or implementer adds a fake third fence to satisfy the pin
- **Proposed resolution**: Retarget pins to ≥2 sites matching implement-bootstrap-invoke.sh --mode initial and --mode resume only; drop the ≥3 requirement

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:550-574
- **Concern**: Step 0 awk still requires exactly one --resume-plan-tail mention inside step:0 bash while the plan moves resume to implement-bootstrap-invoke.sh --mode resume with zero --resume-plan-tail literals in SKILL bash. Scenario: make test-implement-structure exits 13 even when the wrapper migration is otherwise correct
- **Proposed resolution**: Replace exit 13 logic with pins for zero --resume-plan-tail / zero direct implement-bootstrap.sh in step:0 bash plus at least one --mode resume wrapper call

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-stdio-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:52 (plan) / skills/implement/SKILL.md:37-48 (plan)
- **Concern**: Structural pins require ≥3 `set +e`/`_inv_rc` wrapper fences but the proposed SKILL edit only defines two executable invoke sites (`--mode initial` in Step 0 + `--mode resume` in the dirty-tree fence). Scenario: `make test-implement-structure` fails after a faithful implementation, or the implementer adds a phantom third call site for CI only
- **Proposed resolution**: Align pins and prose to two sites: initial Step 0 + dirty-tree `--mode resume`; change `≥3` to `≥2` (or drop the third-site requirement) and replace “all three call sites” with “both wrapper call sites”

### OOS_1:
- **Description**: Redundant bootstrap-routing.env plus file-first parse duplicates the stdout routing envelope (~720 added lines per plan estimate). Scenario: Extra write/parse surface and harness cases without fixing a failure the current _ib_out KV parse already handles
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/implement-bootstrap-invoke.sh:1-1
- **Phase**: design

### OOS_2:
- **Description**: codex-manifest-schema When to load rider is unrelated to Step 0 bootstrap extraction (#3298). Scenario: Unnecessary review surface and doc churn on a SIMPLE refactor
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/references/codex-manifest-schema.md:7-7
- **Phase**: design
