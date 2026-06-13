# Review Round 1

- Mode: `diff`
- 8 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Wrapper-routed allowlist bypasses probe checks on compound commands
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-hook-enforcement-output.txt
- **Severity**: important
- **Concern**: `bash_is_wrapper_routed` substring-matches the entire Bash command and exits allowed before probe detection. A compound command that merely contains `design-run-*.sh` plus a step wrapper name (e.g. `design-step3-review.sh`) can append `ls "$DESIGN_TMPDIR"`, `&&`/`;`-separated probes, or background watchers and bypass the live-marker deny guard, recreating the polling shape the incident targeted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Only allow wrapper-routed commands when the whole command matches the expected launcher invocation, or continue scanning for probe verbs after stripping the allowed launcher segment.
  - From codex-specialist-edge-cases-output.txt: Allow only a whole-command launcher invocation, or run probe detection first and deny compound commands with extra probes.
  - From codex-specialist-testing-output.txt: Anchor the wrapper allow to a single launcher command or run probe detection first; add an appended-probe denial test.
  - From dyn-hook-enforcement-output.txt: Parse the first synchronous segment (split on unquoted `&&`, `||`, `;`), allow only when that segment alone matches a strict wrapper pattern, and still evaluate probe rules on trailing segments.


### FINDING_12: SKILL post-notification fallback uses unbound `ROUND_NUM`
- **Reviewer(s)**: dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: The post-notification fallback uses `plan-review/round-${ROUND_NUM}/reviewer-status.tsv`, but `ROUND_NUM` is not bound at that step boundary. Step 3 result env exposes `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, and `ROUNDS_COMPLETED`. If `latest-reviewer-status.tsv` is missing, the fallback can point at the wrong round or a nonexistent path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-wait-contract-output.txt: Change the fallback to `round-${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-${ROUNDS_COMPLETED:-1}}}` and require parsing `.step3-review-result.env` before rendering the post-notification table.


### FINDING_14: Over-broad probe matching causes cross-session false denies
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-hook-enforcement-output.txt
- **Severity**: important
- **Concern**: The hook scans all live markers globally and uses broad heuristics (`plan-review` substring anywhere in the command, relative target tokens without tmpdir anchor). Markers record `CLAUDE_PID` but the hook does not compare it to the current session. A live `/design` wait in one session can deny unrelated consumer-repo work in another tab (`grep -r plan-review docs/`, shell edits referencing `plan-review-loop.sh`, etc.) that never targets the live `$DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Bind markers to the current session or only treat relative probe tokens as matches when cwd is the live marker dir; add a cross-session false-deny test.
  - From dyn-hook-enforcement-output.txt: Require a tmpdir anchor (`$DESIGN_TMPDIR`, `${DESIGN_TMPDIR}`, canonical live `dir`, or `path_under_dir` on an absolute path) for Bash denies; drop the bare `*plan-review*` heuristic or gate it on cwd equals the live design tmpdir.
  - From dyn-hook-enforcement-output.txt: Thread session identity from the PreToolUse JSON into marker matching (e.g. only honor markers whose `CLAUDE_PID` matches the current session's Claude PID when known), or narrow deny paths to the single live tmpdir tied to the current session env symlink.


### FINDING_2: Probe-verb detection omits common read utilities
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-hook-enforcement-output.txt
- **Severity**: important
- **Concern**: `bash_has_probe_verb` whitelists only `ls|cat|wc|stat|find|head|tail|test|grep`. Shapes seen in the #4102 incident and in `hook-anti-read-poll.sh` (`rg`/`ripgrep`, `awk`, `sed`, `python`/`python3`, `jq`, `dd`, `cmp`, etc.) are not denied during a live Step 3 background wait, so orchestrator polling via those tools can still pass the PreToolUse guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add rg (and optionally awk/sed/python -c) to probe detection, or deny any Bash referencing live-tmpdir probe targets without verb whitelist.
  - From cursor-specialist-edge-cases-output.txt: Extend banned probe shapes or document as accepted residual risk with telemetry.
  - From dyn-hook-enforcement-output.txt: Extend verbs to match the intent rule in `orchestrator-never.md` (or share a small probe-classifier with `hook-anti-read-poll.sh`), and add harness cases for `awk`/`rg` against `$DESIGN_TMPDIR` and `*-output.txt`.


### FINDING_5: Missing `DESIGN_TMPDIR` validation before marker write in Step 3 and final-summary wrappers
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: `design-step3-review.sh` and `design-step-final-summary.sh` write `.bg-wait-active` immediately after optional session sourcing with no non-empty `DESIGN_TMPDIR` guard (unlike `design-step5c.sh`). Empty `DESIGN_TMPDIR` can yield marker path `/.bg-wait-active` or a marker outside allowed session parents; the hook may fail open while the orchestrator believes the wait is protected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-design-wait-contract-output.txt: Mirror the Step 5c precondition: abort (or skip marker creation) when `DESIGN_TMPDIR` is empty or not a directory under the allowed session root.


### FINDING_6: `deny_if_needed` allows probes when telemetry write fails
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-hook-enforcement-output.txt, dyn-design-wait-contract-output.txt
- **Severity**: important
- **Concern**: `deny_if_needed` calls `increment_denial_count "$dir" || exit 0` before emitting deny JSON. If the counter write fails (read-only tmpdir, permissions, disk full), the hook exits 0 with no deny JSON and the probe is allowed, inverting the contract that telemetry failure must not prevent denial. A secondary variant: increment succeeds but `json_deny`/`jq` fails, inflating `bg-poll-guard-denials.count` while allowing the probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Emit the deny JSON regardless of telemetry write success, and treat the count increment as best-effort only.
  - From cursor-specialist-testing-output.txt: Call json_deny before or regardless of increment_denial_count; add harness case with unwritable count file asserting deny JSON still emitted
  - From dyn-hook-enforcement-output.txt: Emit `json_deny` unconditionally once a probe is classified; increment the counter in parallel or after deny, and never treat telemetry failure as allow.
  - From dyn-design-wait-contract-output.txt: Always emit `json_deny` on a matched probe; call `increment_denial_count` best-effort afterward (or ignore its return) so denial does not depend on counter writes.
  - From cursor-specialist-correctness-output.txt: Increment only after successful json_deny output, or treat jq failure as fail-closed deny.


### FINDING_7: Pure file-test sleep loops not detected by watcher-loop logic
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `bash_is_watcher_loop` and related detectors require probe verbs like `ls`/`grep` inside the loop body. A shape such as `while [ ! -f .step3-review-result.env ]; do sleep 5; done` observes progress during a live wait but is allowed because `[ ... ]` / `[[ ... ]]` file tests against live wait targets are not denied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Detect [ ... ] and [[ ... ]] tests against live wait targets, and deny while/until/for plus sleep loops that reference those targets.


### FINDING_8: Step 3 marker creation is fatal under `set -e` instead of best-effort
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Marker write/`mv` failure under `set -e` aborts `design-step3-review.sh` entirely. `/design` loses the review driver, not just the poll guard, when `DESIGN_TMPDIR` is unwritable.
- **Suggested revisions (informational for voters; coder decides)**:


