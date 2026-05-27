### FINDING_1: code-quality: scripts/implement-bootstrap.sh:571-799
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] phase_plan_materialize is a ~230-line monolith combining snapshot, gh, bails, slug, redaction, logging, and summary upsert. Phase 4 coder_select will likely extend the same function, increasing merge conflict risk and making bail-order regressions harder to spot in review. Extract focused helpers (copy/fetch, branch, logs, redact-to-file) before Phase 4, matching phase_tracking helper style.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/implement-bootstrap.sh:172-176,587-589
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] snapshot-untracked.sh runs only inside phase_plan_materialize, which is skipped when REPO_UNAVAILABLE=true. On main, snapshot ran before the plan-materialization skip; repo-unavailable local runs no longer get untracked-baseline.z, so later phantom probes may treat pre-existing untracked files differently if the run progresses past Step 0 without plan files. Run snapshot after tracking (or at end of phase_infra) even when plan materialization is skipped; update GP-repo-unavail-plan to expect snapshot but not gh/persist.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/SKILL.md:637
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SKILL bootstrap table does not document that repo_unavailable skips all of Phase 3. Operators reading only SKILL.md may expect plan.txt or snapshot behavior that implement-bootstrap.md and tests intentionally omit. Add a table note that plan materialization (including snapshot) is skipped and PLAN_FILE remains empty.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:841-908
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two harness cases share the B5-plan prefix for unrelated scenarios. Future edits to B5-plan may break the wrong case or confuse failure attribution in CI logs. Rename the tracking-init guard case (e.g. B5-plan-tracking-init) to disambiguate from B5-plan-green.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:654,691
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] issue_title is read twice from feature-description.txt. Minor duplication only; no functional bug today. Read once and reuse for slug and goal_text composition.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/implement-bootstrap.sh:730-777
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Summary redaction failure aborts upsert; tally redaction falls back to raw copy. Inconsistent best-effort policy may leave plan-review tally written but larch:plan summary missing after a redactor flake. Align redaction fallback behavior between tally and summary paths.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dirty-tree recovery lists bootstrap argv flags but omits required export of IMPLEMENT_TMPDIR documented in implement-bootstrap.md. First pass writes plan/feature files under session tmpdir A; recovery runs --resume-plan-tail without IMPLEMENT_TMPDIR in env; phase_infra allocates tmpdir B and resume skips copy/gh; tail uses empty feature file or waterfall blocks on missing artifacts. Add export IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR" to step 468 and a fenced recovery bash block; mirror in implement-bootstrap.md cross-link.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/implement/SKILL.md:464-468,684
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Recovery prose unsets IMPLEMENT_BAIL_REASON and re-runs bootstrap but does not require re-parsing resume bootstrap stdout like Step 2 redispatch does. Orchestrator keeps stale IMPLEMENT_BAIL_REASON=dirty-tree from first KV parse; L684 blocks implementer waterfall after successful resume that emitted BRANCH_NAME. Add fenced recovery bash that re-invokes bootstrap with --resume-plan-tail and re-runs the full _ib_kv_scan/export block on new stdout before continuing Step 0.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/implement-bootstrap.sh:587-651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Resume tail skips internal dirty-tree checkpoint by design; external clean re-probe is orchestrator-only with no structural enforcement. Orchestrator skips external check-mid-run-dirty-tree and calls --resume-plan-tail on still-dirty tree; branch/plan logging proceeds on polluted worktree. Add structure test or routing fixture pinning external probe then export IMPLEMENT_TMPDIR then resume bootstrap then KV re-parse.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/implement-bootstrap.sh:767-777
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Summary redaction failure returns 0 without tracking-issue-summary upsert, unlike other best-effort fallbacks. Run completes without larch:plan summary pointer when redaction fails even though plan-goals-test succeeded; operator sees missing GitHub summary marker. Document intentional fail-closed in implement-bootstrap.md or cp raw summary and still attempt upsert like tally path.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Multiple merged commits and larch-logs flushes outside Phase 3 scope. Phase 3 review signal diluted by unrelated diffs. Keep Phase 3 review scoped to implement-bootstrap + SKILL Step 0 changes when merging.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md:468,678
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] External dirty-tree re-probe during recovery vs no prompt-side checkpoint during normal Step 0 is implicit. Orchestrator may think L678 forbids all checkpoint calls including recovery. Add one-line cross-reference in dirty-tree recovery gate to the external probe exception.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: skills/implement/SKILL.md:464-468
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Dirty-tree recovery re-bootstrap is prose-only; structure lint guards the primary Step 0 bash block but not recovery re-entry with --resume-plan-tail. After IMPLEMENT_BAIL_REASON=dirty-tree the orchestrator may re-run bootstrap without --resume-plan-tail, duplicating snapshot/gh/persist or never completing branch/plan batches on the existing IMPLEMENT_TMPDIR. Add a fenced recovery bash block mirroring _ib_* args plus --resume-plan-tail; extend test-implement-structure.sh to require --resume-plan-tail in SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: skills/implement/SKILL.md:405-431
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No static test asserts _ib_kv_scan case arms for BRANCH_NAME BRANCH_ACTION PLAN_FILE. Dropping those case arms still passes test-implement-bootstrap while Step 2 and post-dispatch branch checks see empty BRANCH_NAME. Add grep or awk guards in test-implement-structure.sh for the three case arms in the Step 0 KV scan.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/implement-bootstrap.sh:602-608
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Missing harness for forked-target plan without --upstream-repo. Forked runs with unset UPSTREAM_REPO fail generically at gh-issue-view without a regression test locking exit 2 and helper short-circuit order. Add B-plan-forked-missing-upstream: expect STEP_FAILED=gh-issue-view exit 2 and no persist/create-branch in invoke log.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Merge base includes unrelated commits and harness/Makefile churn beyond Phase 3. CI failure from sibling changes (e.g. new classification or drop-changelog harnesses) could block the PR despite green implement-bootstrap tests. Run full make lint / test-harnesses on the merged branch or split unrelated commits before merge.
- **Suggested revision**: Address the concern above.

### FINDING_17: security: scripts/implement-bootstrap.sh:730-731
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plan-review-tally redaction failure copies raw tally body instead of failing closed like larch:plan summary A future tally template that embeds session or issue-derived secrets could commit them via write-tally.sh when redact-secrets.sh or redact-tmpdir-paths.sh errors On redaction failure skip write-tally or use a fixed placeholder and log with append-tool-failure.sh --redact
- **Suggested revision**: Address the concern above.

### FINDING_18: security: scripts/implement-bootstrap.sh:895-897,594-598
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --preflight-tmpdir has no path containment or symlink checks before cp Orchestrator misconfiguration or a symlinked plan-from-issue.txt could copy unintended content into plan.txt and downstream implementer prompts Validate absolute preflight dir and regular non-symlink plan-from-issue.txt under expected session roots before cp
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/implement-bootstrap.sh:270-276
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --resume-plan-tail silently allocates a new tmpdir when IMPLEMENT_TMPDIR is unset or session-env.sh is missing. Orchestrator re-runs bootstrap with --resume-plan-tail but without exporting IMPLEMENT_TMPDIR; script exits 0 with PLAN_FILE under a new empty tmpdir while plan.txt and feature-description.txt remain in the first-pass tmpdir. die_usage or exit 2 when RESUME_PLAN_TAIL=true and reuse preconditions fail; add harness asserting failure without IMPLEMENT_TMPDIR in env.
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Resume tail does not re-run check-mid-run-dirty-tree.sh; cleanliness depends entirely on prompt-side re-check. Orchestrator skips the documented dirty-tree re-check and calls --resume-plan-tail directly; branch creation proceeds on a still-dirty worktree. Re-run checkpoint at resume entry in phase_plan_materialize or add a mandatory orchestrator Bash fence before resume bootstrap.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/implement-bootstrap.sh:587-589
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Resume skips snapshot-untracked.sh so untracked-baseline.z can be stale after recovery stash. Operator stashes untracked files during dirty-tree recovery; later phantom probes compare against a pre-stash baseline. Re-snapshot at resume start after clean checkpoint or document stash constraints on untracked sets.
- **Suggested revision**: Address the concern above.

### FINDING_22: architecture: scripts/implement-bootstrap.sh:954-958
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --resume-plan-tail still runs full phase_tracking before plan tail. POSTED=false defer path removed sentinel; resume repeats post-tracking-issue and rename calls. Skip phase_tracking when RESUME_PLAN_TAIL=true or add tmpdir idempotency guards for post/rename.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/implement-bootstrap.sh:767-777
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Summary redaction failure returns 0 without tracking-issue-summary upsert. Run continues to Step 2 with local plan logs but no larch:plan GitHub marker. Document as best-effort or surface a prominent execution-issues / routing hint when summary upsert is skipped.
- **Suggested revision**: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.sh:939-943
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] --preflight-tmpdir required only when --issue-number is set. plan phase without issue-number passes argv validation then fails at copy-plan. Tighten validation to require preflight-tmpdir for all plan/coder/all invocations.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] correctness: scripts/implement-bootstrap.sh:681-687
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] git-current-branch failures use branch-create-failed even when create-branch was skipped. Operators misdiagnose user-branch capture failures as branch creation failures. Use a distinct bail reason for capture-only failures (optional doc-only clarification).
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Dirty-tree recovery prose omits exporting IMPLEMENT_TMPDIR before --resume-plan-tail bootstrap re-run. phase_infra cannot reuse session-env.sh; resume allocates a new tmpdir and plan/feature files from the dirty-tree pass are lost, so recovery appears to succeed in KV terms but Step 2 lacks materialized artifacts. Add explicit export IMPLEMENT_TMPDIR (and optional Bash snippet) to the recovery gate before the --resume-plan-tail call; align with implement-bootstrap.md caller contract.
- **Suggested revision**: Address the concern above.

