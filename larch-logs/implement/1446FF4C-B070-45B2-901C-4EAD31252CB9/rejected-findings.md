### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Duplicate tier launch/probe logic in `run_codex_tier` / `run_claude_tier`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `run_codex_tier` and `run_claude_tier` duplicate launch, probe, empty-raw, and `had_probe_miss` handling; timeout or cap-hit fixes in one tier may not propagate to the other, yielding wrong `SCOUT_STATUS` or missed waterfall fallthrough.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared `run_scout_tier` helper; keep only argv assembly in tier-specific wrappers


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: Scout read-only boundary relies on plan mode, not mechanical sandbox
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Scout read-only boundary relies on `--permission-mode plan` plus `allowedTools Read` without mechanical sandbox; a future Claude CLI widening plan-mode permissions could allow writes despite the allowlist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pin CLI version in verification rule; add regression harness for disallowed tools


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Multi-tier probe exhaustion emits `empty` without diagnostic telemetry
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Multi-tier probe exhaustion emits `SCOUT_STATUS=empty` with no fail reason; large-diff runs get zero dynamic reviewers (including security archetypes) with no `parse-failed` diagnostic when Codex was present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Add WARN/telemetry for probe exhaustion when `--codex-present true`


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: Duplicated fenced-JSON probe vs post-winner validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `tier_raw_is_scout_json` duplicates fenced-JSON probing used again after a winner is chosen; per-tier probe and post-winner validation can diverge so the waterfall accepts raw one path would reject (or the reverse).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Factor `scout_raw_to_parse_input` (or similar) shared by tier probe and post-winner validation


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_21: Plan file list omits `launch-review.sh` Codex sandbox changes
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `launch-review.sh --codex-add-dir` was required for scout but omitted from the plan file list; plan-only reviews may miss Codex sandbox surface when scoping blast radius.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add launch-review.sh and launch-review.md to the plan inventory on the tracking issue


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: Harness checks CMD_JSON substrings only for read-only verification
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Harness checks `CMD_JSON` substrings only while plan acceptance cites verify-external-tool-invocations mechanical verification; host or CLI changes could weaken read-only enforcement while tests still pass on `.meta` shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add stub or documented manual denial check for a forbidden tool per verify-external-tool-invocations


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: No-winner status branching needs a documented truth table
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: No-winner status is a nested branch on `had_probe_miss` and `last_launch_rc`; future status-token changes can mis-classify probe exhaustion vs launcher failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `finalize_waterfall_no_winner` helper with documented truth table matching harness cases


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: Duplicated path canonicalization across coupled launchers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Path canonicalization helpers are duplicated between `launch-claude-subprocess.sh` and `scout-dynamic-archetypes.sh`; validation rules can drift between scout staging and Claude read-tools root checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract `scripts/lib-path-canonical.sh` on next touch of either file


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Default 180s scout timeout may be too low for read-tools on large staged diffs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Default 180s timeout is unchanged for read-tools scout on large staged diffs (~900KB after larch-logs trim); Read loops can time out and yield zero dynamic reviewers (similar to the old 256KB embed gate) without signaling timeout distinctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Raise or scale scout timeout for `--read-tools`; optional distinct read-timeout status
  - From cursor-specialist-edge-cases-output.txt: Raise default or tier timeout when staged WARN fires; document operator override


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Scout waterfall omits Cursor tier despite acceptance text
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Scout waterfall is Codex→Claude only while feature acceptance lists Codex→Cursor→Claude; Cursor-present hosts skip Cursor for dynamic archetypes though panel reviewers may still use Cursor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add Cursor tier when launch-review supports it or update acceptance text


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: Mixed probe-miss plus final launcher failure emits launcher status, not `empty`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: When multiple tiers have probe misses and the final tier’s launcher fails (e.g. Codex non-JSON then Claude exit 7), `SCOUT_STATUS` is `claude-failed` (launcher status) rather than `empty`, diverging from issue acceptance and operator expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align plan with tests or emit `empty` when any probe miss occurred
  - From cursor-specialist-edge-cases-output.txt: Clarify in CHANGELOG/issue close; behavior is already in scout-dynamic-archetypes.md and harness


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

