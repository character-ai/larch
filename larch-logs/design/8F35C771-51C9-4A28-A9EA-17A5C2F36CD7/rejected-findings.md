### [Plan Review] FINDING_13

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/breadcrumb-monitor.sh:163-168; scripts/ci-wait.sh:277-282
- **Concern**: Timeout signaling only targets the top-level PID. Scenario: Family B scripts often block in child commands such as sleep, gh, or external launchers; killing only the shell PID can still leave the actual long-running child orphaned after monitor timeout
- **Proposed resolution**: Use a supervisor/process-group or per-script TERM trap strategy that terminates tracked child PIDs, and add a test where the paired PID is a shell currently waiting on a child process


### [Plan Review] FINDING_14

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-foreground-markers.sh:337-388
- **Concern**: New PID-file lint checks are fence-global rather than launch-specific. Scenario: A single LARCH_PAIRED_PID_FILE token and one --paired-pid-file monitor invocation can satisfy every Family B anchor in a multi-launch fence, leaving another launch effectively unpaired while lint passes
- **Proposed resolution**: Make the linter associate allocation/export and monitor argv with each denylisted anchor, or reject multiple Family B anchors per fence unless each has its own paired PID-file block; add a negative multi-anchor fixture


### [Plan Review] FINDING_28

### FINDING_28:
- **Reviewer(s)**: Codex-dyn-signal-lifecycle
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/breadcrumb-monitor.sh:163-168
- **Concern**: Kill-loop timing is underspecified for the exact five-iteration grace period. Scenario: The plan says poll for up to 5 seconds but does not pin the loop shape or require a test that SIGKILL happens only after five one-second sleeps, leaving room for off-by-one escalation
- **Proposed resolution**: Add the exact Bash 3.2 loop body to the plan and test elapsed time or a poll counter: send TERM, run five kill -0 checks separated by sleep 1, then send KILL only if still alive


### [Plan Review] FINDING_31

### FINDING_31:
- **Reviewer(s)**: Cursor-dyn-linter-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lint-foreground-markers.sh:100-623
- **Concern**: Plan adds four new fixtures but does not require updating existing PASS cases. Scenario: After has_pid_alloc/has_pid_flag land, cases 1/4/9-13c/15/17/20-21b/28 (and similar) lack LARCH_PAIRED_PID_FILE and --paired-pid-file; make test-lint-foreground-markers fails even when product fences are converted
- **Proposed resolution**: Extend plan: refresh every assert_case_clean Family B fixture and test-lint-foreground-markers.md case list in the same change; gate CI on harness green


### [Plan Review] FINDING_32

### FINDING_32:
- **Reviewer(s)**: Codex-dyn-linter-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:75-82, BASH_AUTHORING.md:66-73
- **Concern**: The proposed has_pid_alloc check is fence-wide and accepts bare export LARCH_PAIRED_PID_FILE, so it does not prove a fresh pid file is allocated before the Family B launch.. Scenario: A fence can put export LARCH_PAIRED_PID_FILE after the background script, or inherit/re-export a stale value, and still pass lint while the launched script never writes the pid file the monitor will later signal.
- **Proposed resolution**: Define the check as a pre-anchor rule: require an assignment/export line before the denylisted launch, preferably within the same five-line per-anchor window, matching an actual mktemp allocation such as export LARCH_PAIRED_PID_FILE="$(mktemp ...)" or LARCH_PAIRED_PID_FILE=...mktemp followed by export before the anchor; do not count bare export alone.


### [Plan Review] FINDING_33

### FINDING_33:
- **Reviewer(s)**: Codex-dyn-linter-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:81-82, scripts/test-lint-foreground-markers.sh:100-112, scripts/test-lint-foreground-markers.sh:250-262, scripts/test-lint-foreground-markers.sh:397-409
- **Concern**: The plan adds four new fixture categories but does not say to update the existing positive Family B fixtures that currently lack both LARCH_PAIRED_PID_FILE allocation and --paired-pid-file.. Scenario: After the linter starts requiring the new tokens, existing clean fixtures such as collect-agent-results.sh, ship-pr.sh, and dispatch-plan-voters.sh will fail even before the new fixtures exercise the intended negative cases.
- **Proposed resolution**: Update every existing positive Family B fixture to include a fresh LARCH_PAIRED_PID_FILE mktemp allocation/export before the anchor and pass --paired-pid-file "$LARCH_PAIRED_PID_FILE" on the monitor invocation, then add the four new fixtures.


### [Plan Review] FINDING_34

### FINDING_34:
- **Reviewer(s)**: Codex-dyn-linter-invariant
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:81-82, scripts/test-lint-foreground-markers.sh:205-224, scripts/test-lint-foreground-markers.md:9-10
- **Concern**: The four proposed fixture categories are not sufficient to catch off-by-one errors in the five-line look-back rule because they do not pin boundary placement.. Scenario: A buggy linter that checks four previous lines could reject valid fences, or one that checks six previous lines could accept invalid fences, while missing-allocation, allocation-without-flag, both-present-pass, and step-7a-pass all still pass if the new tokens are adjacent to the anchor.
- **Proposed resolution**: Add boundary fixtures: pid allocation/comment exactly five in-fence lines before the anchor must pass, six lines before must fail, and allocation after the anchor must fail; keep the existing comment-window failure as the too-far negative.


### [Plan Review] FINDING_35

### FINDING_35:
- **Reviewer(s)**: Codex-dyn-linter-invariant
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:78-79, scripts/lint-foreground-markers.md:5-13, scripts/lint-foreground-markers.sh:345-386
- **Concern**: The plan asks to document the new pid checks but does not explicitly repair the existing lint contract text, which still describes a foreground-required rule for all denylisted scripts.. Scenario: The updated md could end up documenting the new tokens alongside stale foreground banner/comment wording, leaving the contract contradictory to the actual background branch and the step-7a carve-out.
- **Proposed resolution**: Rewrite scripts/lint-foreground-markers.md around the current two-branch model: nine Family B scripts require background banner/comment, run_in_background, breadcrumb-monitor --stream, pid allocation, and --paired-pid-file; step-7a.sh alone requires the foreground banner/comment and forbids run_in_background; include the exact emitted error strings for each branch.


### [Plan Review] FINDING_8

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/dispatch-with-waterfall.sh:177-221
- **Concern**: Timeout signaling only targets the top-level paired PID, but several Family B scripts spawn child launchers and wait on them. Scenario: Monitor timeout can terminate dispatch-with-waterfall.sh while its launch-review or launch-claude-review children continue running orphaned; the same pattern exists in collector retry paths and synchronous child launchers
- **Proposed resolution**: Extend the contract to terminate the process tree or process group, or add TERM traps in child-spawning Family B scripts that kill/wait their tracked child PIDs before exiting; add a regression test with a child that survives parent TERM


