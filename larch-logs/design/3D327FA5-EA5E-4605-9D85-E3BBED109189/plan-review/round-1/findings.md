### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:10-35
- **Concern**: A1 timing-pin scanner omits step2-implement.sh. Scenario: That script already calls timing-ledger.sh mark Step 2 with LARCH_TIMING_SKILL=implement; dropping the pin later would not fail CI
- **Proposed resolution**: Add skills/implement/scripts/step2-implement.sh to the A1 scanned set (and keep the existing per-mark pins additive)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:13-24
- **Concern**: A1 claims a general implement timing-pin scanner, but the scanned set omits existing implement-owned timing emitters such as skills/implement/scripts/step2-implement.sh:206 and scripts/run-step5-review.sh:240.. Scenario: A future edit can drop LARCH_TIMING_SKILL=implement from Step 2 or Step 5 timing marks and still pass the new guard, despite A1 promising that dropped pins fail CI.
- **Proposed resolution**: Either narrow A1's stated contract to the listed surfaces, or add the omitted implement timing emitters to the scanner with explicit exclusions for shared lanes.

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:13-22
- **Concern**: A1 timing-pin scanner file set omits two production `mark` emitters. Scenario: The plan’s enumerated scan list covers nine scripts but `skills/implement/scripts/step2-implement.sh:206` and `scripts/run-step5-review.sh:240` also invoke `timing-ledger.sh mark` with `LARCH_TIMING_SKILL=implement`; an unpinned or dropped pin in either file would not fail the new scanner, undermining the “additive guard catches new or dropped pins” contract
- **Proposed resolution**: Add `skills/implement/scripts/step2-implement.sh` and `scripts/run-step5-review.sh` to the A1 scanned set (or an equivalent single glob over implement production emitters)

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:436-475; skills/implement/scripts/step2-implement.sh:206; scripts/run-step5-review.sh:240; scripts/run-relevant-checks-captured.sh:118-122; scripts/launch-codex-ci.sh:247; scripts/launch-cursor-ci.sh:230; scripts/launch-claude-ci.sh:192
- **Concern**: Proposed A1 scanner file set omits current /implement timing emitters, including three CI-fix vendor launchers that are still unpinned. Scenario: The new invariant can pass while polluted ambient LARCH_TIMING_SKILL=design still mis-tags CI-fix vendor rows, and future pin drops in Step 2, Step 5, or checks helpers stay invisible
- **Proposed resolution**: Add the omitted implement timing emitters to the scanner; apply the same DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix to the CI launchers, or explicitly narrow the invariant so it no longer claims every implement timing call is covered

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:13-22
- **Concern**: A1 scanned-set omits three implement production scripts that already invoke timing-ledger.sh. Scenario: marks in skills/implement/scripts/step2-implement.sh scripts/run-step5-review.sh and scripts/run-relevant-checks-captured.sh are outside the enumerated scanner set and have no literal grep pins in test-implement-structure.sh so an unpinned LARCH_TIMING_SKILL regression there would pass CI
- **Proposed resolution**: Add those three paths to the A1 file list (or bound discovery over skills/implement/scripts and implement-owned scripts/*.sh excluding test-*)

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:27-35
- **Concern**: A3 workflow_path stale-key assertion has no bounded production path set. Scenario: A repo-wide or python/-wide grep -Fq workflow_path false-fails on python/test_run_logs.py fixtures and other harness text while a too-narrow grep misses future reads outside the Step 2 pair
- **Proposed resolution**: Pin an explicit allowlist (e.g. skills/implement/scripts/run-step2-dispatch.sh skills/implement/scripts/step2-implement.sh scripts/implement-bootstrap.sh scripts/ship-pr.sh python/ship.py python/run_logs.py) with test-* and python/test_* excluded

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:442-474; skills/implement/scripts/step2-implement.sh:206; scripts/run-step5-review.sh:240; scripts/run-relevant-checks-captured.sh:118-122
- **Concern**: A1 scanner file set omits active implement timing emitters. Scenario: The proposed general timing-pin guard can pass while Step 2, Step 5, or relevant-check timing calls lose LARCH_TIMING_SKILL=implement and inherit a polluted design skill value
- **Proposed resolution**: Extend the A1 scanned set to include these already-pinned implement timing emitters, or narrow the invariant text and keep separate literal pins for them.

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-timing-env
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:10-35
- **Concern**: A1 timing-pin scanner file list omits three implement shell scripts that already emit timing-ledger marks. Scenario: `skills/implement/scripts/step2-implement.sh` (Step 2 mark at :206), `scripts/run-step5-review.sh` (Step 5 mark at :240), and `scripts/run-relevant-checks-captured.sh` (Step 3/6 marks at :118,:122) have no per-mark `grep -qF` pins in `test-implement-structure.sh`; if the A1 scanner skips them, dropping `LARCH_TIMING_SKILL=implement` on any of those lines would pass CI despite the stated general invariant
- **Proposed resolution**: Add those three paths to the A1 scanned set (same awk/index() same-line rule as the other production scripts)

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh:442-474
- **Concern**: A1 is described as a general timing-pin invariant, but the proposed explicit scanned set omits live implement timing call sites such as skills/implement/scripts/step2-implement.sh:206, scripts/run-step5-review.sh:240, and scripts/run-relevant-checks-captured.sh:118-122.. Scenario: If one of the omitted runtime paths later drops or adds an unpinned timing call, the new guard still passes, giving false confidence that all implement timing rows are protected from polluted ambient timing env.
- **Proposed resolution**: Keep the SIMPLE scope honest: either narrow A1 to focused assertions for the two A2 launcher record-vendor-task lines, or make the scanned file list complete for the implement timing surface and only add pins where the current contract requires them.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:17-22
- **Concern**: A1 scanned-file list omits skills/implement/scripts/step2-implement.sh even though it emits a production timing-ledger mark (Step 2 — implementation). Scenario: step2-implement.sh is outside the new general pin scanner so a dropped or unpinned LARCH_TIMING_SKILL=implement on that mark would not fail test-implement-structure.sh; A1’s “enumerate implement production scripts that emit timing calls” goal is incomplete
- **Proposed resolution**: Add skills/implement/scripts/step2-implement.sh to the A1 scanned set alongside the other implement timing emitters

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:436-475
- **Concern**: A1 promises a general scanner over implement production scripts that emit timing calls, but the proposed scanned set omits existing implement timing emitters: skills/implement/scripts/step2-implement.sh:206, scripts/run-step5-review.sh:240, and scripts/run-relevant-checks-captured.sh:118-122.. Scenario: If one of those Step 2/Step 5/checks timing calls later drops LARCH_TIMING_SKILL=implement, the new invariant still passes, so A1's acceptance criterion that every implement timing invocation is pinned is not covered.
- **Proposed resolution**: Add those three files to the A1 scanner's explicit file set, or derive the scanner input from a grep of implement production timing callers while keeping the intentional scripts/launch-review.sh exclusion.

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-timing-env
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-implement-structure.sh:436-475; skills/implement/scripts/step2-implement.sh:206; scripts/run-step5-review.sh:239-240; scripts/run-relevant-checks-captured.sh:115-123
- **Concern**: FINDING_1: The proposed A1 scanner set omits existing production implement timing marks in Step 2, Step 5 re-entry, and captured Step 3/6 checks.. Scenario: The plan claims the scanner enumerates implement production scripts that emit timing calls, but a future unpinned mark in these production paths would not fail CI.
- **Proposed resolution**: Add these three files to the explicit scanner set, or narrow the invariant text so it no longer claims every production mark is covered.

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-timing-env
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/launch-codex-implement.sh:225-238; scripts/launch-cursor-implement.sh:164-177; scripts/timing-ledger.sh:55-85
- **Concern**: FINDING_2: The proposed scanner enforces only same-line LARCH_TIMING_SKILL=implement for record-vendor-task, not the full same-line DESIGN_TMPDIR='' LARCH_TIMING_SKILL=implement prefix A2 requires.. Scenario: If DESIGN_TMPDIR='' is later dropped but the skill pin remains, the scanner passes while timing-ledger.sh can still fall back to an ambient DESIGN_TMPDIR when no implement ledger root is available.
- **Proposed resolution**: For record-vendor-task and timing-report lines, assert the same command line contains both DESIGN_TMPDIR='' and LARCH_TIMING_SKILL=implement; keep mark lines at the skill-only requirement if broader clearing would be scope creep.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-ci-outcomes
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ci_monitor.py:409-424
- **Concern**: Plan B candidate decide(status=error)→bail duplicates parity table and is not monitor-reachable. Scenario: parity row at python/test_ci_monitor.py:160 already pins action bail; poll_ci coerces gather_status error to pending before decide so monitor never exercises decide error→bail without monkeypatch
- **Proposed resolution**: Drop this candidate; if a status-gather bail is needed at monitor level use the three-consecutive-failure poll path (poll_ci:411-417 → monitor bail→STALLED at ci_monitor.py:1555-1561) already covered at poll_ci in test_ci_monitor.py:330-351

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-ci-outcomes
- **Severity**: important
- **Focus area**: code-quality
- **Location**: python/test_ci_monitor.py:149-188,284-300,1863-1873; python/ci_monitor.py:409-418,436-443,1564-1568
- **Concern**: Plan B still names decide-level error/unknown cases even though status="error" is already in the parity table and wait decisions are consumed inside poll_ci or collapse to existing timeout coverage. Scenario: Implementer may add a direct decide row or monkeypatched wait test that duplicates parity/budget tests instead of new terminal MonitorResult evidence
- **Proposed resolution**: Revise B to require only genuinely monitor-level tests: runner-backed gh pr view/status-error through monitor asserts Outcome.STALLED and merged PR through monitor asserts Outcome.OK; drop unknown-status fallthrough unless a real monitor-reachable branch is identified

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-run-log-posture
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/larch-log.md:33-39
- **Concern**: Approach requires sibling contract sync when D2/D4 reword dynamic-Codex retention rationale, and this block restates that rationale, but `### UPDATED:` omits `scripts/larch-log.md`. Scenario: D2 removes the overstated catch-all framing in `larch-log.sh` while `larch-log.md` still claims an explicit narrow allow with no catch-all suffix glob and no mention of the broad `*-output*` backstop; implementers following only the file list leave primary write-round contract stale
- **Proposed resolution**: Add `### UPDATED: scripts/larch-log.md` (comment/prose only): align lines 33-39 with the D2 wording — known `dyn-*-codex-output*` shapes are explicitly pinned; other shapes may fall through to the broad `*-output*` allow; frame retained families under the same pattern-based redaction posture cross-referenced in SECURITY.md

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-run-log-posture
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/README.md:10
- **Concern**: D3 documents append-only quiet logs in `logging_util.py`, but `python/README.md` still says `quiet_init()` mirrors `scripts/lib-quiet.sh`. Scenario: Operators and reviewers infer bash/Python parity; bash truncates per init (`lib-quiet.sh:71` `: >`) while Python appends (`logging_util.py:76-80` `O_APPEND`), so the README misstates behavior the D3 contract-drift pass is meant to clarify
- **Proposed resolution**: Add a one-line `python/README.md` clarification beside the `logging_util.py` bullet: routing mirrors lib-quiet, but log open uses append-for-forensics (per D3 comment), not bash truncate-per-run

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-run-log-posture
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/larch-log.md:30-38
- **Concern**: Dynamic Codex contract doc already restates the rationale D2 changes, but the plan leaves its update conditional and outside the UPDATED file list. Scenario: The implementation can update only scripts/larch-log.sh and SECURITY.md, leaving scripts/larch-log.md saying dynamic Codex retention does not use catch-all behavior while the new code comment says future shapes fall through to broad output allows
- **Proposed resolution**: Add scripts/larch-log.md as an explicit UPDATED file and revise lines 30-38 to match the new known-shapes plus broad-fallback rationale

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-run-log-posture
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/README.md:10
- **Concern**: Python quiet logging docs still say quiet_init mirrors scripts/lib-quiet.sh while D3 intentionally preserves append behavior that diverges from bash truncate-per-run behavior. Scenario: Operators and maintainers may expect Python quiet logs to truncate like bash quiet logs, but crash or retry forensics can persist in the same quiet log path
- **Proposed resolution**: Add a minimal python/README.md wording update noting that Python mirrors quiet stream routing but intentionally appends quiet logs for crash/retry forensics

### OOS_1:
- **Description**: Fixed-path A1 scanner will drift when new implement timing call sites land outside the list. Scenario: The next timing-ledger.sh or timing-report.sh added under implement without updating the scanner array silently evades the general pin guard
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-implement-structure.sh:13-22
- **Phase**: design
