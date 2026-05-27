### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/implement-bootstrap.sh:571-799
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] phase_plan_materialize is a ~230-line monolith combining snapshot, gh, bails, slug, redaction, logging, and summary upsert. Phase 4 coder_select will likely extend the same function, increasing merge conflict risk and making bail-order regressions harder to spot in review. Extract focused helpers (copy/fetch, branch, logs, redact-to-file) before Phase 4, matching phase_tracking helper style.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: scripts/implement-bootstrap.sh:767-777
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Summary redaction failure returns 0 without tracking-issue-summary upsert, unlike other best-effort fallbacks. Run completes without larch:plan summary pointer when redaction fails even though plan-goals-test succeeded; operator sees missing GitHub summary marker. Document intentional fail-closed in implement-bootstrap.md or cp raw summary and still attempt upsert like tally path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: security: scripts/implement-bootstrap.sh:730-731
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] plan-review-tally redaction failure copies raw tally body instead of failing closed like larch:plan summary A future tally template that embeds session or issue-derived secrets could commit them via write-tally.sh when redact-secrets.sh or redact-tmpdir-paths.sh errors On redaction failure skip write-tally or use a fixed placeholder and log with append-tool-failure.sh --redact
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: security: scripts/implement-bootstrap.sh:895-897,594-598
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --preflight-tmpdir has no path containment or symlink checks before cp Orchestrator misconfiguration or a symlinked plan-from-issue.txt could copy unintended content into plan.txt and downstream implementer prompts Validate absolute preflight dir and regular non-symlink plan-from-issue.txt under expected session roots before cp
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_20: risk-integration: skills/implement/SKILL.md:468
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Resume tail does not re-run check-mid-run-dirty-tree.sh; cleanliness depends entirely on prompt-side re-check. Orchestrator skips the documented dirty-tree re-check and calls --resume-plan-tail directly; branch creation proceeds on a still-dirty worktree. Re-run checkpoint at resume entry in phase_plan_materialize or add a mandatory orchestrator Bash fence before resume bootstrap.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: correctness: scripts/implement-bootstrap.sh:587-589
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Resume skips snapshot-untracked.sh so untracked-baseline.z can be stale after recovery stash. Operator stashes untracked files during dirty-tree recovery; later phantom probes compare against a pre-stash baseline. Re-snapshot at resume start after clean checkpoint or document stash constraints on untracked sets.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: architecture: scripts/implement-bootstrap.sh:954-958
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] --resume-plan-tail still runs full phase_tracking before plan tail. POSTED=false defer path removed sentinel; resume repeats post-tracking-issue and rename calls. Skip phase_tracking when RESUME_PLAN_TAIL=true or add tmpdir idempotency guards for post/rename.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: correctness: scripts/implement-bootstrap.sh:767-777
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Summary redaction failure returns 0 without tracking-issue-summary upsert. Run continues to Step 2 with local plan logs but no larch:plan GitHub marker. Document as best-effort or surface a prominent execution-issues / routing hint when summary upsert is skipped.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/implement/scripts/test-implement-bootstrap.sh:841-908
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Two harness cases share the B5-plan prefix for unrelated scenarios. Future edits to B5-plan may break the wrong case or confuse failure attribution in CI logs. Rename the tracking-init guard case (e.g. B5-plan-tracking-init) to disambiguate from B5-plan-green.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: scripts/implement-bootstrap.sh:654,691
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] issue_title is read twice from feature-description.txt. Minor duplication only; no functional bug today. Read once and reuse for slug and goal_text composition.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: scripts/implement-bootstrap.sh:730-777
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Summary redaction failure aborts upsert; tally redaction falls back to raw copy. Inconsistent best-effort policy may leave plan-review tally written but larch:plan summary missing after a redactor flake. Align redaction fallback behavior between tally and summary paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: scripts/implement-bootstrap.sh:587-651
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Resume tail skips internal dirty-tree checkpoint by design; external clean re-probe is orchestrator-only with no structural enforcement. Orchestrator skips external check-mid-run-dirty-tree and calls --resume-plan-tail on still-dirty tree; branch/plan logging proceeds on polluted worktree. Add structure test or routing fixture pinning external probe then export IMPLEMENT_TMPDIR then resume bootstrap then KV re-parse.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

