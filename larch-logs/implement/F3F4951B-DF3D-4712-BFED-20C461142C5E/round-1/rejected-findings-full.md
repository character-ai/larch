### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Merged brainstorm text in plan-review feature context expands prompt-injection surface for reviewers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `brainstorm.md` (from externals plus operator-edited synthesis) is appended into the same artifact as issue context for scout/panel, so adversarial or model-injected instructions in brainstorm prose can bias or jailbreak the review panel without compromising shell scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Separate channels or explicit untrusted annex framing in the renderer, digest/size caps before merge, and argv-safe prompt delivery (--prompt-file) in normative launch docs


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `brainstorm_requested` can diverge from argv when jq/write-run-params is degraded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Persistence that depends on jq plus Step 1d.5 consulting only `run-params.json` can drop argv `--brainstorm` intent when `write-run-params` fails or jq is absent: warnings may print while JSON omits `brainstorm_requested: true`, so Step 1d.5 skips despite the user passing `--brainstorm`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add fail-closed recovery, argv consistency check in brainstorm entry, or mandatory operator prompt when JSON disagrees with argv.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Non-atomic merge write for `plan-review-feature-context.txt`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If the merge write is not atomic, interruption mid-merge can yield truncated context fed to scout/panel without a hard failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use temp file plus atomic mv.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Already-planned ad-hoc Q&A with `--brainstorm` can exit before tier/run-params materialization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When an issue already has `larch:plan`, `/design --brainstorm` without a tier flag, and the operator chooses ad-hoc Q&A, the literal exit path can run Q&A before items that materialize tier/run-params (e.g. items 5–6). That can leave `write-run-params` inputs undefined, omit `brainstorm_requested: true` in run-params, and cause the Step 1d.5 entry guard to skip despite plan acceptance language—unless tier gate and run-params write are enforced (or a single default tier is documented and implemented) before Q&A.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Add jq -e or helper precondition before Q&A exit.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `--brainstorm` orchestration branches are prose-only with no offline harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Pre–Step-0, tier-gate, already-planned Q&A, and related `--brainstorm` flows rely on AskUserQuestion-style prose contracts only; accidental deletion or reordering of upgrade/cancel vs Q&A vs Step 1d.5 would not be caught by grep-based structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Either accept as orchestration-only risk or add minimal structure tests pinning critical literals (option labels, Step 1d.5 MANDATORY pointer before Q&A exit).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

