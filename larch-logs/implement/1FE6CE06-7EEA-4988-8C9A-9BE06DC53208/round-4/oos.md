### FINDING_14: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-design-structure.sh:413-1131` — Still pins `design-publish.sh` call ordering and subshell capture, but does not grep for registration-gate tokens (`REG_TIMEOUT`, `did not register within`, `headRefOid`, `PUSH_HEAD_SHA`). `design-publish.md` lists `test-design-structure.sh` as a sync target. Pre-existing structural gap, amplified by this change. ### Summary The core #3413 work is in good shape: flush re-enabled in `design-publish.sh`, two-phase head-bound registration in `design-log-publish.sh`, SECURITY/docs updated, and `test-design-log-publish.sh` adds the planned race / never-register / CI-fail / pending-rc / stale-head cases with strong stderr and `GH_STUB_LOG` assertions. Existing happy-path and pause-reuse cases were updated for `TEST_CLONE_ROOT` / `headRefOid`, and `test-design-multi-round-integration.sh` was fixed for the `--json`/`--watch` stub split. Main gaps before merge: assert failed-publish recovery metadata in the rendered summary (not only result env), and confirm the `plan-review-loop.sh` stderr change via `test-plan-review-loop` (not just multi-round integration). I did not execute harnesses in this read-only review; run `make test-design-publish test-design-log-publish test-design-multi-round-integration test-plan-review-loop` (or `bash scripts/relevant-checks.sh`) to confirm green.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] code-quality: skills/design/scripts/design-publish.sh:1699-1701
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] LOG_RECOVERY_BRANCH duplicated in result env KVs. None functional. Deduplicate the second append when touching that helper next.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] **Pre-existing:** `--reason pause` still runs the same post-push PR create + merge gate as final flush (`scripts/design-pause-save.sh`); a successful pause publish can still `--admin` merge log snapshots mid-design. Re-enabling Step 5c does not change that, but it is worth remembering when judging production risk.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **Pre-existing:** `--reason pause` still runs the same post-push PR create + merge gate as final flush (`scripts/design-pause-save.sh`); a successful pause publish can still `--admin` merge log snapshots mid-design. Re-enabling Step 5c does not change that, but it is worth remembering when judging production risk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] **Positive (no issue):** Splitting `gh` stub `--json` vs `--watch` arms, deriving default `headRefOid` from `TEST_MERGE_BRANCH` / `ls-remote`, stale-head knobs, and the updated CI-fail stderr assertions materially reduce the original registration-race + false “CI failed” conflation; the core #3413 fix aligns with the stated acceptance criteria.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **Positive (no issue):** Splitting `gh` stub `--json` vs `--watch` arms, deriving default `headRefOid` from `TEST_MERGE_BRANCH` / `ls-remote`, stale-head knobs, and the updated CI-fail stderr assertions materially reduce the original registration-race + false “CI failed” conflation; the core #3413 fix aligns with the stated acceptance criteria.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_36: [OUT_OF_SCOPE] The two-phase registration gate (`PUSH_HEAD_SHA` + non-empty `--json` checks, then `--watch`) is structurally aligned with the #3413 root cause; harness cases in `scripts/test-design-log-publish.sh` exercise race, never-registered, watch-failure, non-zero JSON rc, and stale-head paths coherently with the stderr/`GH_STUB_LOG` split described in the plan.
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - The two-phase registration gate (`PUSH_HEAD_SHA` + non-empty `--json` checks, then `--watch`) is structurally aligned with the #3413 root cause; harness cases in `scripts/test-design-log-publish.sh` exercise race, never-registered, watch-failure, non-zero JSON rc, and stale-head paths coherently with the stderr/`GH_STUB_LOG` split described in the plan.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_37: [OUT_OF_SCOPE] `design-publish.sh`’s envelope handling (`_publish_rc` vs `PUBLISH_OK=`, `failed-publish` post-render with `DESIGN_LOG_*` exports, pre/post render split) is internally consistent; post-push `design-log-publish.sh` exit `1` with `PUBLISH_OK=false` on stdout is absorbed by the driver without aborting the orchestrator (`design-publish.md:39-42`).
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - `design-publish.sh`’s envelope handling (`_publish_rc` vs `PUBLISH_OK=`, `failed-publish` post-render with `DESIGN_LOG_*` exports, pre/post render split) is internally consistent; post-push `design-log-publish.sh` exit `1` with `PUBLISH_OK=false` on stdout is absorbed by the driver without aborting the orchestrator (`design-publish.md:39-42`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_41: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-multi-round-integration.sh:25-35` — The slimmer integration gh stub branches on `grep -- '--json'` / `grep -- '--watch'` over `"$*"`, while `test-design-log-publish.sh` uses exact-token `has_arg`. Behavior matches today’s argv shape, but the two stubs could diverge if `gh` flag spelling changes; consider sharing one stub or the same `has_arg` helpers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:1016-1032` — Registration `pr view` failures use stub stderr `Could not resolve host: api.github.com`, which production’s `with_transient_retry` treats as transient (up to three attempts per probe). The test still fails closed, but probe-count semantics differ from a single-shot view failure; this is harness realism, not a false pass in the current no-op sleep setup.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

