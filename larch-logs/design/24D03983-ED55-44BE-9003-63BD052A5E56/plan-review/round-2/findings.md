### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1024-1040
- **Concern**: Plan flips the default driver but leaves Step 8+ exit-matrix and recovery bullets that still order re-invocation of `ship-pr.sh` or the fenced `Invoke:` block without an `LARCH_SHIP_PR_IMPL=bash` guard. Scenario: After default becomes Python, Exit 0/6 continuations, autonomous CI-fix step 12, conflict handoff Phase 4, and NEVER recovery at :56 can still run `scripts/ship-pr.sh` despite unset env, undermining the selector flip and `--no-logs-commit` argv parity
- **Proposed resolution**: Add one load-bearing sentence to the flipped **Python driver selector** (within the two routing sentences): on the default Python path, any Step 8+ bullet that says re-invoke the fenced `Invoke:` block or `ship-pr.sh` means re-invoke the Python foreground command from the selector; matrix and `Invoke:` apply only when `LARCH_SHIP_PR_IMPL=bash`

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955,971-982,1279-1290
- **Concern**: Proposed Python-default path still leaves bash ship-pr-state seeding plus unchanged Step 18 restore in place. Scenario: With unset LARCH_SHIP_PR_IMPL, the prompt seeds ship-pr-state.sh before running python/ship.py; Step 18 then sees that file and restore-finalize-state.sh can rebuild finalize-state.sh from stale bash seed values, masking Python-written stall or merge state before teardown
- **Proposed resolution**: Make restore-finalize-state.sh invocation bash-path only, or otherwise ensure Python-path teardown ignores the seeded ship-pr-state.sh; if the state file must remain for OOS helpers, do not use it to restore finalize-state on the Python path

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:14
- **Concern**: Anti-halt critical boundary still mandates post-`ship-pr.sh` `ship-pr-state.sh` parse and exit-table re-invoke; plan does not list this line for update. Scenario: The plan flips the Step 8+ default to `python/ship.py` but leaves the load-bearing anti-halt text: after `ship-pr.sh` exits, parse `ship-pr-state.sh` and re-invoke per the bash exit-code table. That boundary outranks the selector for many orchestrators, so the first transient/OOS/loop exit on the new default path can spawn `ship-pr.sh` instead of `python/ship.py`, mixing drivers mid-run
- **Proposed resolution**: Add one minimal sentence to the flipped selector (or edit this critical boundary): on the default Python path, after `python/ship.py` returns, route from JSON stdout + selector exit routing only—do not parse `ship-pr-state.sh` for driver continuation and do not treat the bash exit table as authoritative unless `LARCH_SHIP_PR_IMPL=bash`

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955,971-987,1279-1290
- **Concern**: Python selector omits --state-file while the plan leaves ship-pr-state.sh seeding and Step 18 restore active. Scenario: Default Python runs seed ship-pr-state.sh once, never refresh it, then Step 18 restore-finalize-state.sh can overwrite python/ship.py's finalize-state.sh with stale PR_CLOSED=false or STALL_TRACKING=false values; stalled artifacts can be cleaned up or terminal outcome can be misclassified
- **Proposed resolution**: Add --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to the Python argv list so python/ship.py replaces the seeded state before teardown, or gate ship-pr-state seeding and restore to the bash opt-in path only

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/references/stall-recovery.md:28-30,41
- **Concern**: Stall recovery still hard-codes re-invoking scripts/ship-pr.sh. Scenario: A default-Python run that reaches Step 18a with a recoverable step8-shippr stall switches back to the legacy bash driver despite unset LARCH_SHIP_PR_IMPL, bypassing the new selector and JSON routing
- **Proposed resolution**: Update only the step8-shippr bullet and safety constraint to re-enter Step 8+ through the same selector: Python unless LARCH_SHIP_PR_IMPL=bash; keep the foreground writer_rc routing for the bash opt-in path

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:14
- **Concern**: Global anti-halt boundary still mandates post-`ship-pr.sh` `ship-pr-state.sh` parse and Step 8+ exit-code table after every ship return. Scenario: After the default flips to Python, orchestrators still hit a top-of-file **Critical boundary** that orders `ship-pr-state.sh` routing, contradicting the selector’s JSON-only Python contract and the planned pre-`Invoke:` bash guard
- **Proposed resolution**: Default-path runs can mis-route exits (e.g. read stale/missing `PHASE`/`BAIL_REASON`, re-enter bash matrix) despite a successful `python/ship.py` JSON envelope Add one anti-halt qualifier: unless `LARCH_SHIP_PR_IMPL=bash`, after Step 8+ ship driver return use Python selector JSON + exit routing, not `ship-pr-state.sh` / bash exit table

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955 and skills/implement/SKILL.md:1282-1291
- **Concern**: Python default path leaves a stale seeded ship-pr-state.sh for unchanged Step 18 restore. Scenario: Python writes finalize-state.sh, but Step 18 restore-finalize-state.sh sees the preseeded ship-pr-state.sh and can overwrite terminal booleans such as PR_CLOSED or STALL_TRACKING from stale initial values before teardown
- **Proposed resolution**: Pass --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to python/ship.py in the selector argv, or skip ship-pr-state seeding/restore on the Python path; passing the existing supported flag is the smaller fix

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:56,987,1024,1040
- **Concern**: Timeout/recovery and Exit 6 bullets still mandate re-invoking the fenced bash `Invoke:` / `ship-pr.sh` without a python-path guard. Scenario: After the default flips to Python, a harness timeout (NEVER #13 / long-running recovery at ~987) or Exit 6 handling that follows the bash matrix can re-run `scripts/ship-pr.sh` even when `LARCH_SHIP_PR_IMPL` is unset, switching drivers mid-run and ignoring JSON routing
- **Proposed resolution**: Add one minimum sentence (same pattern as the planned pre-`Invoke:` guard): on the default Python path, re-invoke the selector’s `python3 …/python/ship.py` foreground call; use the fenced `Invoke:` block only when `LARCH_SHIP_PR_IMPL=bash`

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1024-1080
- **Concern**: Finding 1: Python default still falls through to bash-only continuation prose. Scenario: The plan flips the selector but explicitly preserves the Step 8 exit/OOS matrix where OOS, autonomous CI-fix, and transient paths read ship-pr-state.sh and re-invoke ship-pr.sh. A default Python run that returns oos-filing or ci-fix-exhausted can switch drivers mid-run or read missing/stale bash state.
- **Proposed resolution**: Keep the bash matrix, but label it bash-only and add minimal Python-path continuation rules: use JSON fields, re-invoke python/ship.py with the same argv after OOS or main-agent CI fix, and avoid ship-pr-state.sh for Python routing.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1037
- **Concern**: Autonomous CI-fix step 12 still hardcodes re-invoke ship-pr.sh while plan makes Python the default Step 8+ driver. Scenario: After flip, exit-3 autonomous CI-fix (referenced from the Python selector) completes push then step 12 runs the bash Invoke block, switching drivers mid-run and ignoring JSON routing
- **Proposed resolution**: Add one load-bearing override in the flipped Python driver selector: autonomous sub-procedure step 12 re-invokes the active Step 8+ driver (python/ship.py foreground argv unless LARCH_SHIP_PR_IMPL=bash, then fenced Invoke)

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955,1281-1289; python/ship.py:197-199
- **Concern**: Python default invocation is planned without --state-file while Step 8 still seeds ship-pr-state.sh. Scenario: With unset or empty LARCH_SHIP_PR_IMPL, Step 8 creates the initial bash-shaped ship-pr-state.sh, python/ship.py runs without ctx.state_file and cannot refresh it, then Step 18 sees the stale file and restore-finalize-state.sh rebuilds finalize-state.sh from old PHASE/PR fields before teardown, losing PR URL/stall/cleanup state
- **Proposed resolution**: Add --state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh" to the Python selector invocation and pin or validate it, or explicitly skip creating/restoring ship-pr-state.sh on the Python path; keep the bash fenced block byte-stable

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-selector-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1020-1040
- **Concern**: Post-Invoke exit-routing block is still bash-only and ungated after the default flips to Python. Scenario: The plan adds a pre-`Invoke:` guard and inverts the selector (skills/implement/SKILL.md:955) but leaves the block at 1020-1040 unconditional: it tells the orchestrator to read ship-pr-state.sh and re-invoke ship-pr.sh on exits 0/3/4/6. That contradicts the selector (JSON routing, do not read ship-pr-state.sh for Python-path routing; exit 0 → Step 16; exit 3/6 → reinvoke Python). After the flip, unset/empty LARCH_SHIP_PR_IMPL runs Python, yet the next prose still routes through stale seeded ship-pr-state.sh and the fenced ship-pr.sh argv—wrong re-entry, missed OOS/CI loops, or spurious bash invocations.
- **Proposed resolution**: Pre-Invoke routing alone is insufficient. Add one bash-only gate immediately before line 1020 (e.g. apply the following exit matrix only when LARCH_SHIP_PR_IMPL=bash; otherwise follow the Python driver selector JSON exit routing and reinvoke python/ship.py) without rewriting the matrix bullets. Keeps the fenced Invoke: block byte-stable per plan scope.

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-selector-routing
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955-957
- **Concern**: Phantom-probe lead-in still names only ship-pr.sh before the Invoke fence. Scenario: Plan Step 8+ edits cover delegation, selector default, and pre-`Invoke:` routing but not line 957 (Immediately before the first foreground ship-pr.sh invocation below). With Python as default, that line still implies the next foreground call is ship-pr.sh even when the orchestrator should run python3 python/ship.py per the selector.
- **Proposed resolution**: Reword line 957 to a driver-neutral lead-in (before the Step 8+ foreground driver: Python per selector unless LARCH_SHIP_PR_IMPL=bash) in the same SKILL edit hunk; no change to the fenced argv block.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-selector-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:14; skills/shared/subskill-invocation.md:59-68
- **Concern**: The plan leaves load-bearing anti-halt/post-invocation prose that still says Step 8+ always exits from ship-pr.sh and must be routed by ship-pr-state.sh.. Scenario: With LARCH_SHIP_PR_IMPL unset or empty, the new selector tells the orchestrator to run python/ship.py and route by JSON, but the top-level critical boundary can still direct it to parse ship-pr-state.sh and re-invoke ship-pr.sh.
- **Proposed resolution**: Add a minimal selector-neutral rewrite for these specific reminders: after the Step 8+ ship driver exits, use Python JSON routing unless LARCH_SHIP_PR_IMPL=bash; only the bash branch parses ship-pr-state.sh and re-invokes the fenced ship-pr.sh contract.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-selector-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:21-24; skills/implement/references/stall-recovery.md:36-41
- **Concern**: Stall recovery still hard-codes step8-shippr to re-invoke scripts/ship-pr.sh as a foreground Bash call.. Scenario: A Python-default run that stalls and enters Step 18a can recover through step8-shippr, but this reference would switch the recovery attempt back to the legacy bash driver even though only literal LARCH_SHIP_PR_IMPL=bash should preserve that invocation.
- **Proposed resolution**: Extend the plan to update only the step8-shippr bullet and safety constraint: re-enter the Step 8+ driver selector; use python/ship.py plus JSON routing unless LARCH_SHIP_PR_IMPL=bash, and keep the existing writer_rc/ship-pr-state wording scoped to the bash branch.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-stale-reference-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:987
- **Concern**: Long-running recovery prose still mandates re-invoking the fenced bash `Invoke:` block without scoping to `LARCH_SHIP_PR_IMPL=bash`. Scenario: After the default flips to Python, a timeout or unexpected turn end on the default path can still route the orchestrator back through `scripts/ship-pr.sh` instead of the selector’s `python/ship.py` + JSON routing — the same failure mode the plan flags for stale delegation, via a different sentence
- **Proposed resolution**: Add a bash-only qualifier on the recovery bullet (or point recovery at the selector’s Python re-invocation) so default-path recovery never names the fenced `ship-pr.sh` `Invoke:` block as authoritative

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-stale-reference-sweep
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/scrub-log-secrets.md:35-38
- **Concern**: Plan misses stale security-helper prose that still calls the Python ship-pr scrub path in-progress parity. Scenario: The default Python ship driver relies on this scrub path, but the doc still implies it is not live, which can mislead security review of run-log secret scrubbing
- **Proposed resolution**: Add scripts/scrub-log-secrets.md to the update list and reword this sentence to describe the default Python ship driver scrub path rather than in-progress parity

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-operator-upgrade
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:30-44
- **Concern**: The planned upgrade notice says operators who never set LARCH_SHIP_PR_IMPL switch drivers on the next plugin upgrade, but the driver default lives in cached SKILL.md and only changes after the upgraded plugin is loaded.. Scenario: After /upgrade-larch without restart, or before the cache refresh described at docs/installation-and-setup.md:77-82, /implement can still follow the old bash-default SKILL while the notice implies the flip already happened.
- **Proposed resolution**: Tie the notice to the existing restart rule at docs/installation-and-setup.md:38 and the cached-plugin note at docs/installation-and-setup.md:77-82 (e.g. the Python default applies on the first /implement after the upgraded plugin is loaded; set LARCH_SHIP_PR_IMPL=bash before starting Claude Code to pin legacy behavior during rollout).
