### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Complete-path quota gate weaker than `classify_launch_failure()` dual-source probe
- **Reviewer(s)**: dyn-dyn-quota-gate
- **Severity**: major
- **Concern**: Even on the Codex path, quota classification on the complete path is weaker than the existing launch-failure classifier. `classify_launch_failure()` treats quota as present when either the sidecar or the output/events file matches `_QUOTA_RE`; the new complete-path gate checks only `st.sidecar_log`. If `_mirror_codex_quota_from_events` fails to append (sidecar write error, truncated sidecar, etc.) while the events stream still contains quota markers, dispatch will still accept `status: "complete"` and commit partial work whenever `disposition_required` is false, or emit disposition KVs when it is true.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-quota-gate: Reuse the same dual-source probe as `classify_launch_failure()` by also checking `st.transcript_path` and, for Codex, the events sidecar path before `git add`/`git commit`.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0
