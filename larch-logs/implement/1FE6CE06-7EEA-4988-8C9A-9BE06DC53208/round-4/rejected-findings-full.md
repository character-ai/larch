### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/design-publish.sh:301-338
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Three publish-failure branches duplicate append-tool-failure and recovery warn logic. Future exit-code or warn changes may update only one branch and leave inconsistent operator surfaces. Add record_publish_failure() helper and route all three branches through it.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: **latent** `scripts/test-design-log-publish.sh` (harness-wide) — Merge-gate behavior is covered well with stubbed `gh` (`--json` vs `--watch`, head OID alignment, stderr substrings, probe budgets). There is still no test against real `gh pr checks` registration latency or pending rc=8 JSON from GitHub. **Suggested fix:** Treat manual acceptance (one live `/design` flush PR) as required before merge; optional follow-up: a gated integration job with a throwaway repo.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **latent** `scripts/test-design-log-publish.sh` (harness-wide) — Merge-gate behavior is covered well with stubbed `gh` (`--json` vs `--watch`, head OID alignment, stderr substrings, probe budgets). There is still no test against real `gh pr checks` registration latency or pending rc=8 JSON from GitHub. **Suggested fix:** Treat manual acceptance (one live `/design` flush PR) as required before merge; optional follow-up: a gated integration job with a throwaway repo.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **CI still gates merge**: Registration timeout, head mismatch, and watch failure all set `merge_rc≠0`, emit `PUBLISH_OK=false`, and skip `--watch` or merge (see ```790:903:scripts/design-log-publish.sh```).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **CI still gates merge**: Registration timeout, head mismatch, and watch failure all set `merge_rc≠0`, emit `PUBLISH_OK=false`, and skip `--watch` or merge (see ```790:903:scripts/design-log-publish.sh```).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **Stale-check bypass closed**: Binding registration to `PUSH_HEAD_SHA` addresses pause/force-push reuse where green checks on an old head could otherwise satisfy a naive “checks exist” probe.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stale-check bypass closed**: Binding registration to `PUSH_HEAD_SHA` addresses pause/force-push reuse where green checks on an old head could otherwise satisfy a naive “checks exist” probe.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Stdout contract hygiene**: `jq -e` is redirected to `/dev/null`; registration probes use `set +e` so pending-check non-zero `gh` exits do not abort the script or leak booleans onto the KV stream.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stdout contract hygiene**: `jq -e` is redirected to `/dev/null`; registration probes use `set +e` so pending-check non-zero `gh` exits do not abort the script or leak booleans onto the KV stream.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Pre-merge redaction unchanged**: Tmpdir allowlist, symlink guards, plan-review allowlist, and `scrub-log-secrets` fail-closed behavior remain; re-enable restores `SECRET_SCRUB_VIOLATIONS` surfacing in `design-publish.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pre-merge redaction unchanged**: Tmpdir allowlist, symlink guards, plan-review allowlist, and `scrub-log-secrets` fail-closed behavior remain; re-enable restores `SECRET_SCRUB_VIOLATIONS` surfacing in `design-publish.sh`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Inputs bounded**: `--issue` (digits), `--run-id` (`larch_log_slug_is_valid`), `--repo` (`validate_repo` in `design-publish.sh`), `PR_NUM` from `gh` parsing.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Inputs bounded**: `--issue` (digits), `--run-id` (`larch_log_slug_is_valid`), `--repo` (`validate_repo` in `design-publish.sh`), `PR_NUM` from `gh` parsing.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/scripts/render-final-summary.sh:313-328,404-417
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] failed-publish recovery notes duplicated in invoke_render and compose_self_fallback. Fallback summaries can omit PR/recovery lines that the full renderer shows after a wording change. Extract write_failed_publish_notes() used by both code paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **Documentation aligned**: `SECURITY.md` and `design-log-publish.md` now describe registration-before-watch and distinguish `did not register within` vs `did not pass`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Documentation aligned**: `SECURITY.md` and `design-log-publish.md` now describe registration-before-watch and distinguish `did not register within` vs `did not pass`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: **No command-injection surface added**: `gh`/`git` arguments use quoted variables; branch names derive from validated `RUN_ID`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No command-injection surface added**: `gh`/`git` arguments use quoted variables; branch names derive from validated `RUN_ID`. **Residual operational risk (pre-existing, amplified by re-enable)** Re-enabling flush means more automated `--admin` merges and more committed `larch-logs/design/` content on the default branch. That increases impact if a `gh` token with admin-merge scope is compromised or if redaction/scrub fails — but the branch does not remove scrub gates or allowlist controls.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_22: risk-integration: scripts/design-log-publish.sh:825-884
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Registration retries pr view with transient backoff on every probe while checks JSON is non-empty but head OID mismatches, consuming REG_DEADLINE faster than the nominal 31×10s budget. Pause/force-push reuse can show green required checks for an old head while headRefOid lags; the run times out with did not register within even though checks existed, blocking [DESIGNED] rename and leaving a recovery PR. Skip transient retry for head-only probes during registration, or emit an explicit stale-head diagnostic when checks are non-empty but headRefOid != PUSH_HEAD_SHA.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: architecture: scripts/design-log-publish.sh:882-884
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-registration gh pr checks --watch has no local timeout. A required check or gh watch can stall indefinitely after up to 300s registration; operator must kill /design manually. Document operational handling; consider a bounded watch in a follow-up change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_27: correctness: skills/design/scripts/design-publish.md:24-28
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract doc omits failed-publish outcome and DESIGN_LOG_* recovery exports that implementation and tests now rely on. Operators troubleshooting a stuck flush PR read design-publish.md and do not see how failed publish is rendered or which recovery fields exist. Document failed-publish, DESIGN_LOG_* exports, and post-publish render behavior on publish failure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: architecture: skills/design/SKILL.md:538
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] SKILL.md lists failed-publish on the orchestrator Final summary block enum but Gate C uses design-publish.sh internal render. Orchestrator authors may export SUMMARY_OUTCOME=failed-publish on a path that never sets DESIGN_LOG_* recovery metadata. Clarify failed-publish is design-publish.sh-only or wire orchestrator paths if truly needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-design-log-publish.sh:53-74,182-216 and scripts/test-design-multi-round-integration.sh:38-56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate gh stub registration/headRefOid logic across harnesses. Already required a separate integration-test fix when stub arms split; next gate change risks drift again. Share one stub fragment or template for pr checks/view behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **risk-integration** `scripts/design-log-publish.sh:882-888` — After registration succeeds, any non-zero `gh pr checks --watch --fail-fast` is reported only as `required CI checks did not pass`, with no branch for the pre-fix `no checks reported` failure mode. If `gh` ever returns that message on `--watch` after a successful `--json` probe (API inconsistency or check-suite reset between phases), operators are steered toward “CI failed” rather than “registration/watch gap,” weakening the diagnostic split this branch introduces. Harnesses assert substring separation for the never-registered path but not for this watch-after-register edge. **Suggested fix:** When `ci_rc -ne 0`, if `ci_wait_out` matches the known `no checks reported` pattern, emit a third diagnostic (e.g. `checks not available for watch after registration`) or re-enter a short registration backoff before failing closed; keep `did not pass` only when watch output reflects an actual failing/pending required check.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:882-888` — After registration succeeds, any non-zero `gh pr checks --watch --fail-fast` is reported only as `required CI checks did not pass`, with no branch for the pre-fix `no checks reported` failure mode. If `gh` ever returns that message on `--watch` after a successful `--json` probe (API inconsistency or check-suite reset between phases), operators are steered toward “CI failed” rather than “registration/watch gap,” weakening the diagnostic split this branch introduces. Harnesses assert substring separation for the never-registered path but not for this watch-after-register edge. **Suggested fix:** When `ci_rc -ne 0`, if `ci_wait_out` matches the known `no checks reported` pattern, emit a third diagnostic (e.g. `checks not available for watch after registration`) or re-enter a short registration backoff before failing closed; keep `did not pass` only when watch output reflects an actual failing/pending required check.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_39: **correctness** `scripts/test-design-log-publish.sh:53-71,1037-1059` — Stale-head coverage uses `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` / `GH_STUB_PR_HEAD_OID_MISMATCH` to return the all-zero OID, then `resolve_pr_head_oid` (current `ls-remote`) once the knob expires. That models “headRefOid missing/wrong until GitHub catches up,” but not the #3413 scenario where **required checks are already non-empty for an old head** while `headRefOid` still points at a different real commit. In production, probes 1–2 with `EMPTY_FIRST` never call `pr view` (checks still `[]`); with `MISMATCH_FIRST=2`, registration actually needs **five** `--json` probes and **three** `headRefOid` views, while the test only asserts `head-count == 3`, so a bug that merged after the first mismatched-but-non-empty check row would not be caught by json-probe counting. **Suggested fix:** Add a knob that returns a fixed, valid but non-matching SHA for the first N `headRefOid` responses while `--json` is already non-empty, and assert both `checks-json-count` and `head-count` (or `PUBLISH_OK=false` until alignment) so stale-check gating is tied to real OID inequality, not only the zero-OID sentinel.
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:53-71,1037-1059` — Stale-head coverage uses `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` / `GH_STUB_PR_HEAD_OID_MISMATCH` to return the all-zero OID, then `resolve_pr_head_oid` (current `ls-remote`) once the knob expires. That models “headRefOid missing/wrong until GitHub catches up,” but not the #3413 scenario where **required checks are already non-empty for an old head** while `headRefOid` still points at a different real commit. In production, probes 1–2 with `EMPTY_FIRST` never call `pr view` (checks still `[]`); with `MISMATCH_FIRST=2`, registration actually needs **five** `--json` probes and **three** `headRefOid` views, while the test only asserts `head-count == 3`, so a bug that merged after the first mismatched-but-non-empty check row would not be caught by json-probe counting. **Suggested fix:** Add a knob that returns a fixed, valid but non-matching SHA for the first N `headRefOid` responses while `--json` is already non-empty, and assert both `checks-json-count` and `head-count` (or `PUBLISH_OK=false` until alignment) so stale-check gating is tied to real OID inequality, not only the zero-OID sentinel.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: scripts/design-log-publish.sh:834-840
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Up to three jq invocations per registration probe. 31-probe timeouts multiply subprocess overhead unnecessarily. Single jq -e 'type == "array" and length > 0' for registration detection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_6: code-quality: scripts/test-design-log-publish.sh:811-818
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unused head_probe/checks_probe counters in gh stub. Misleads maintainers about which knobs control stub behavior. Remove dead counters or use them in assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: correctness: scripts/design-log-publish.sh:841-884
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Registration only requires non-empty required-check JSON and matching headRefOid before --watch; stale passing checks on the new head could satisfy registration before new workflows start. After force-push pause reuse, first probe returns green checks and updated headRefOid while new required jobs have not started; script merges via --admin before fresh CI runs. Consider requiring pending/in_progress checks or a post-push freshness signal before calling --watch, if observed in production.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

