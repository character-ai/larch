### FINDING_10: [OUT_OF_SCOPE] Stale `.stderr-tail` sidecar on success path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Success path in `scripts/run-external-agent.sh` (~325) does not remove stale `.stderr-tail` until next pre-launch rm; long-lived output basename could retain sidecar until relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Optionally rm .stderr-tail on exit 0


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] Implement launchers lack stderr-tail surfacing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/launch-codex-*.sh` / `scripts/launch-cursor-*.sh` implement launchers lack sidecar choke point per plan SIMPLE out-of-scope note; `/implement` codex/cursor failures may still lack chat tails despite #3202 for review/design paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Follow-up stderr-source hook for implement launchers (already planned out of scope).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] design-log-publish `.stderr-tail` copy untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: stderr-tail publishability documented but not covered by `test-design-log-publish.sh`; regressions could drop `.stderr-tail` from larch-logs without a targeted test failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Extend design-log-publish or larch-log write-round harness to assert .stderr-tail copies when present.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_24: [OUT_OF_SCOPE] Anti-read-poll hook scope vs #3202 stderr work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Heuristic Bash/Read task-output poll detection on branch is unrelated to stderr tails; possible false positives/negatives on complex shell.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Separate hook-focused review if incidents appear.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_28: [OUT_OF_SCOPE] Generic Read poll state keyed by cwd only across sessions
- **Reviewer(s)**: dyn-hook-parser-fidelity-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: generic Read polling keys state with `state-${cwd_hash}.tsv` only, while task-output polling adds `session_hash`; unrelated sessions sharing cwd can share counters and trigger reminders on the third read across sessions.
- **Suggested revisions (informational for voters; coder decides)**:


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


