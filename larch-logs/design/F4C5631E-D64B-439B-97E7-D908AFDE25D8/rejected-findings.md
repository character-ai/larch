### [Plan Review] FINDING_4

### FINDING_4: Make the per-step adapter lock blocking
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan requires lock serialization but does not specify blocking behavior. A non-blocking lock can make concurrent callers fail instead of waiting, and may permit duplicate daemon starts before the registry row becomes visible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Use blocking `fcntl.flock(..., LOCK_EX)` for the per-run-and-step lock (same posture as `python/larch/report/progress_file.py:413`). Hold it through the final result check and launch decision, then release before `start_daemon` via fork-safe close or `FD_CLOEXEC`. Document blocking semantics in `adapt.py` and keep the concurrent second-caller test.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: [SCOPE-REDUCTION] Plan contradicts itself on child argv: Approach accepts the command after `--`, but adapt.py mandates injecting adapter-owned flags and merge-env into child argv. Scenario: Step adapters pass different child argv shapes. step-5-review.sh:12-16 exits 2 on unknown args, so injecting `--merge-result-env` breaks that script on conversion. step-6-entry.sh already passes merge flags in the caller argv. Daemon-side merge already comes from JobSpec.merge_result_env.
- **Proposed resolution**: Limit adapt to passing the caller argv after `--` unchanged into JobSpec.command. Own only derived merge-result-env for JobSpec/daemon publication. Drop mandatory child-argv flag injection from adapt.py and tests unless a future conversion explicitly needs it.


### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/bgjob/adapt.py
- **Concern**: [SCOPE-REDUCTION] Fresh-launch merge-env init must be create-if-absent, not unconditional truncate. Scenario: The plan says to initialize merge env atomically before every fresh launch. Live adapters already write identity or seed KVs into the derived bgjob merge path before `bgjob start` (for example `skills/implement/scripts/step-6-entry.sh:327-337` and `skills/implement/scripts/run-step-checks.sh:378-386`). `bgjob start` never truncates that file today. If `adapt` always reinitializes on launch, later conversions lose preseeded merge rows and daemon result merge omits required KVs.
- **Proposed resolution**: Only create the derived merge file when it is missing: validate path safety, then atomic empty write with mode 0o600. If a regular file already exists at the derived path, leave its contents intact. Restrict re-attach paths from touching merge env. State this explicitly in Approach and `adapt.py`, and add a test that preseeds merge KVs then calls `adapt` and asserts the file is unchanged.

