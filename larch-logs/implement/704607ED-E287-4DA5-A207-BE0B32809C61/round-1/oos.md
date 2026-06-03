### FINDING_14: [OUT_OF_SCOPE] risk-integration: diff.txt
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Full branch diff mixes unrelated commits with the health-gate fix. CI or reviewers may attribute failures to the wrong change set. Scope review and bisect to b2a221942 for #3369.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_18: [OUT_OF_SCOPE] **`.gitleaks.toml` (branch, not in `b2a221942`)** — Adds `scripts/test-launch-review.sh` to the gitleaks allowlist. That narrows secret scanning for that file; acceptable if the harness contains intentional token-shaped fixtures, but worth confirming the allowlist matches actual fixture content and not live credentials.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **`.gitleaks.toml` (branch, not in `b2a221942`)** — Adds `scripts/test-launch-review.sh` to the gitleaks allowlist. That narrows secret scanning for that file; acceptable if the harness contains intentional token-shaped fixtures, but worth confirming the allowlist matches actual fixture content and not live credentials.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] **`SECURITY.md` design-log-publish paragraph (branch, not in `b2a221942`)** — Documents CI-gated admin merge behavior; documentation-only relative to this feature.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **`SECURITY.md` design-log-publish paragraph (branch, not in `b2a221942`)** — Documents CI-gated admin merge behavior; documentation-only relative to this feature.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] **Pre-existing fail-open in `external_launch_health_gate()`** — Unparseable probe output still returns success and allows launch (`lib-external-launcher-common.sh` ~130–133). Not introduced or amplified by the resolver fallback beyond running the same probe more often by default.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Pre-existing fail-open in `external_launch_health_gate()`** — Unparseable probe output still returns success and allows launch (`lib-external-launcher-common.sh` ~130–133). Not introduced or amplified by the resolver fallback beyond running the same probe more often by default. --- **Verdict:** The #3369 change set does not introduce security vulnerabilities under the injection / secrets / auth / trust-boundary lens. Operators in air-gapped or no-external-CLI environments should set `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` if they need to avoid auth probes—that is operational configuration, not a defect in this diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_27: [OUT_OF_SCOPE] architecture: scripts/lib-external-launcher-common.sh:110-123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] No outer timeout binary leaves probe duration to check-reviewers internal timeout. Hung probe on machine without timeout/gtimeout blocks launch longer than 30s intent. Pre-existing; optional follow-up to bound unwrapped probe.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_28: [OUT_OF_SCOPE] architecture: scripts/lib-external-launcher-common.sh:130-133
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unparseable probe output fail-opens to launch. Probe stderr noise or partial KV → child still runs despite unhealthy tool. Pre-existing; default-on increases exposure frequency only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_29: [OUT_OF_SCOPE] **Branch breadth** — Full `HEAD` vs `main` includes large unrelated changes (release skill, version bumps, run logs, etc.). Plan fidelity for #3369 should be judged on `b2a221942` (and harness prep already on the branch), not the entire megadiff.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **Branch breadth** — Full `HEAD` vs `main` includes large unrelated changes (release skill, version bumps, run logs, etc.). Plan fidelity for #3369 should be judged on `b2a221942` (and harness prep already on the branch), not the entire megadiff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_30: [OUT_OF_SCOPE] **Test execution** — Plan calls for many `make test-harnesses-*` targets; this review did not run them (read-only / ask mode). Implementation matches the plan’s harness edits; pass/fail is not verified here.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **Test execution** — Plan calls for many `make test-harnesses-*` targets; this review did not run them (read-only / ask mode). Implementation matches the plan’s harness edits; pass/fail is not verified here.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_31: [OUT_OF_SCOPE] **Resolver unit tests** — `assert_resolver_timeout` covers env-only default/`0`/positive paths. Session-file `0` opt-out is already covered by `health gate zero opt-out beats session fallback` in the same harness; not a plan gap, only slightly narrower than the plan’s “any source” wording in the new helper alone.
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 3. **Resolver unit tests** — `assert_resolver_timeout` covers env-only default/`0`/positive paths. Session-file `0` opt-out is already covered by `health gate zero opt-out beats session fallback` in the same harness; not a plan gap, only slightly narrower than the plan’s “any source” wording in the new helper alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/lib-external-launcher-common.sh:76-77
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Three copies of literal 30 across resolver and writers Drift if one site changes without the others Plan-accepted; comment + resolver test mitigate
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] risk-integration: scripts/test-collect-agent-retry.sh:18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Opt-out export landed in a87f4c059 not b2a221942 Cherry-pick of feature commit alone may miss harness-16 isolation Ensure retry harness export rides with resolver PR
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/lib-external-launcher-common.sh:53-74` — If `SESSION_ENV_PATH` resolves to `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0`, the session loop returns immediately and never reads `$IMPLEMENT_TMPDIR/session-env.sh`, even if the latter has a positive value. That matches documented “explicit `0` opts out” semantics but can surprise operators who set `0` in a design env file and `30` in implement session-env. **Suggested fix:** No code change required; optional doc note that the first readable session file in order wins for opt-out, not “most specific” implement env.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **risk-integration** (branch scope) — Merging `HEAD` vs `main` carries substantial non–#3369 changes (release skill, ship/finalize, Cursor retry, lint-fix-loop, version bumps, run logs). If the PR is meant to be only the health-gate fix, reviewers should target **`b2a221942`** (16 files) rather than the full branch diff.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **correctness** (operational, intentional) — Standalone `/research` and `/review` will run up to one `check-reviewers.sh` probe per Codex/Cursor `run-external-agent.sh` launch (≤30s each, fail-open on unparseable output). That closes #3369 but adds latency and can fast-fail unhealthy tools before stubs run in production (not in harnesses that export `0`). **Suggested fix:** Documented in `docs/configuration-and-permissions.md`; operators can set `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=0` to opt out. --- **Summary:** The behavioral change is small, internally consistent, and well covered by unit/harness updates. I did not run the test matrix in Ask mode; the plan’s harness list is the right pre-merge checklist, especially `make test-harnesses-1` (not always pulled in by `relevant-checks.sh` on lib-only edits).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

