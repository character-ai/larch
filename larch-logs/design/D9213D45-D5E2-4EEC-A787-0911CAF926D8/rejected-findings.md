### [Plan Review] FINDING_15

### FINDING_15:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:319-342
- **Concern**: Plan assumes sync can fix a MAV writer race, but mav-apply does not write the probed env artifact. Scenario: If the missing file is tied to the MAV apply handoff, retrying stat after sync cannot create round-N/review-and-fix.env, so the root handoff remains uncontracted
- **Proposed resolution**: Make the writer contract explicit: have mav-apply write or preserve a minimal resume sentinel/env file, or probe an artifact that mav-apply actually writes such as coder.env plus a completion marker


### [Plan Review] FINDING_24

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:11,51,63; skills/review-and-fix/scripts/review-implement-step5-loop.sh:82-85
- **Concern**: sync retry is not a semantic visibility or cache-invalidation barrier. Scenario: If the first [[ -f ]] misses because the writer is still in flight, a negative lookup is cached, or the path is wrong, sync does not force the writer to close, does not validate the pathname, and does not guarantee VFS/name-cache invalidation before the second stat; on local APFS a closed directory entry should already be visible, so this does not defeat Hypothesis A as claimed
- **Proposed resolution**: Reframe sync as best-effort only, or replace it with a deterministic contract: write the env atomically before the producing command returns and verify the artifact after child completion; if retry remains, use bounded wait/backoff and do not claim it proves cache invalidation


### [Plan Review] FINDING_25

### FINDING_25:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-implement-round-cap.sh:28-38; skills/review-and-fix/scripts/review-and-fix.sh:1330-1343; <TMPDIR>/plan.txt:9,64
- **Concern**: Hoisted degraded-round counting can undercount a partially written env before the artifact probe. Scenario: review-and-fix.env is written with > and then appended; a concurrent reader can observe an empty or incomplete file, and count_prior_degraded_rounds treats missing or malformed DEGRADED_ROUND as false. The proposed entry-time cap check can then emit mav-resume-past-cap before the within-loop recomputation has a chance to see the completed file
- **Proposed resolution**: Make review-and-fix.env writes atomic via temp file plus mv, or require a complete marker before count_prior_degraded_rounds contributes a file to cap math; alternatively move the stability check ahead of hoisted cap math for the prior artifact set


### [Plan Review] FINDING_26

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-shell-retry-semantics
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:9; scripts/run-step5-review.sh:207-211; scripts/lib-implement-round-cap.sh:38
- **Concern**: entry_prior_deg is not validated before 10# arithmetic. Scenario: Bash arithmetic with an empty entry_prior_deg in $((10#$base_cap + 10#$entry_prior_deg)) silently treats the degraded count as 0, while an unset variable under nounset aborts. The single-round launcher already validates DEGRADED_ROUNDS before arithmetic, but the plan does not add the same guard for the hoisted loop path
- **Proposed resolution**: Add a case validation for entry_prior_deg after count_prior_degraded_rounds and before entry_effective_cap arithmetic; emit a tool-failure diagnostic if it is empty or non-numeric


