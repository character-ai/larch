### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:48,64,113
- **Concern**: Failure modes cite new structural check as (25) but the Files section defines that check as (27). Scenario: An implementer may extend the existing (25) design_reentry_marker_write ordering assertions in scripts/test-design-structure.sh instead of adding a new (27) publish-gate grep, or skip the gate assertion entirely
- **Proposed resolution**: Change plan.txt Failure modes line 113 to reference (27) consistently with lines 48 and 64; keep (25) reserved for design_reentry_marker_write ordering only

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:113 vs plan.txt:48
- **Concern**: Failure modes cites structural check (25) but Files section reserves (25) for reentry-marker ordering and assigns the publish-gate grep to (27). Scenario: An implementer following Failure modes could add a second (25) publish-gate assertion or weaken the existing (25) reentry-order greps in scripts/test-design-structure.sh:1118-1121
- **Proposed resolution**: Correct plan.txt Failure modes line 113 to reference assertion (27) consistently with the Files section and scripts/test-design-structure.md note

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh (planned assertion (27); plan Failure modes ~line 113)
- **Concern**: Plan Failure modes cites new publish-gate structural check as `(25)` but Files/Testing define it as unused `(27)` while `(25)` already pins `design_reentry_marker_write` ordering in test-design-structure.sh. Scenario: Implementer follows Failure modes and edits the wrong grep id — publish gate absent or `(25)` marker-order assertion broken
- **Proposed resolution**: Align Failure modes mitigation text with `(27)` everywhere (match Files § test-design-structure and test-design-structure.md)

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-publish-state-machine
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/design-pause-save.sh:175-191
- **Concern**: Plan omits FINDING_17 parity for the pause publish path while claiming it is already handled. Scenario: On non-zero design-log-publish.sh exit with PUBLISH_OK=true on stdout, pause-save only fails when PUBLISH_OK is empty; publish_rc!=0 with PUBLISH_OK=true can still reach PAUSE_OK=true and write a resume marker as if logs were published
- **Proposed resolution**: Add a surgical pause-save bullet: any non-zero publish_rc forces publish-failed (before trusting PUBLISH_OK=true), mirroring the proposed design-publish.sh and Step 0b clarify rules; add a small test-design-pause-resume.sh or design-pause-save harness case if one exists

### FINDING_5:
- **Reviewer(s)**: Codex-dyn-publish-state-machine
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.md:22-27,48-52; skills/design/scripts/render-final-summary.md:12-20,29-34; skills/design/scripts/design-publish.sh:257-330,332-352; skills/design/scripts/test-design-publish.sh:251-263
- **Concern**: The plan updates publish docs for new outcomes but leaves stale publish-tail ordering text that says pre-publish render runs and design_reentry_marker_write precedes publish/rename. Scenario: The landed docs would still contradict the driver and harness: current code publishes first, renders post-publish only, then renames and writes the reentry marker only after PUBLISH_OK=true. Operators could infer a marker exists before publish success or that an approved pre-render can be staged into a failed publish PR.
- **Proposed resolution**: Extend the design-publish.md and render-final-summary.md doc edits to state the actual order: plan write, diagram upsert, design-log-publish, post-publish render, [DESIGNED] rename, then reentry marker; no pre-publish render; rename and marker gated on non-empty SESSION_ID and PUBLISH_OK=true.

### FINDING_6:
- **Reviewer(s)**: Codex-dyn-publish-state-machine
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/design-log-publish.sh:14-16
- **Concern**: The plan changes malformed --repo to exit 1 with no PUBLISH_OK envelope but does not update the script header contract saying pre-validation failures exit 0 for stdout parsing. Scenario: After the PR, direct callers and future maintainers reading the script contract would expect PUBLISH_OK=false on all pre-validation failures, contradicting the new invalid-repo fail-closed path.
- **Proposed resolution**: Update the header comment alongside validate_repo to carve out malformed --repo as a structural argv failure: exit 1, no PUBLISH_OK success envelope, before gh/network work.
