# Review Round 1

- Mode: `diff`
- 5 accepted, 2 rejected (2 exonerated)

## Accepted Findings

### FINDING_1: SECURITY.md misattributes plan-voter validation and sidecars to `launch-claude-review.sh` instead of the review wrapper → `launch-claude-subprocess.sh` chain
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-doc-claim-accuracy-output.txt
- **Severity**: important
- **Concern**: Readers can infer the wrong implementation owner: adjacent copy may imply two different sidecar producers for the same voter launch; the doc places argv containment, symlink/control-character rejection, and the context-file cap in `launch-claude-review.sh` and says that wrapper “emits” `.meta`, `.done`, and `.dirty-tree`, while the implementation delegates into `launch-claude-subprocess.sh` (where the mechanical checks and primary sidecar writes live) and the review wrapper may only synthesize `.done` when missing—so both audit navigation and sidecar attribution are misleading unless phrased as a launcher/subprocess chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-doc-claim-accuracy-output.txt: Attribute validation to `launch-claude-subprocess.sh` (or describe it as enforced by the `launch-claude-review.sh` → `launch-claude-subprocess.sh` chain) so readers do not search the wrong file for the mechanical checks.
  - From dyn-doc-claim-accuracy-output.txt: Say the subprocess/launcher chain emits those sidecars (or name `launch-claude-subprocess.sh` explicitly) instead of attributing all three to `launch-claude-review.sh` alone.


### FINDING_2: Doc understates when `append-tool-failure` / execution-issues metadata is recorded (non-OK-only vs empty success ballot)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Text ties append-tool-failure capture to non-OK launches only, but `dispatch-plan-voters.sh` also records diagnostics when the wrapper exits successfully yet the ballot file is empty (warning path), which can mislead operators about when warnings append versus hard failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: “Always” sidecar completeness alongside ballot overstates early-fail and wrapper-synthesis behavior
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Claiming `.meta`, `.done`, and `.dirty-tree` are always emitted alongside ballot output ignores early validation failures in `launch-claude-subprocess.sh` (exit before `.meta`) and cases where `launch-claude-review.sh` may synthesize `.done`, which can misrepresent sidecar completeness for triage unless scoped to the post-validation success path or otherwise qualified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: `.dirty-tree` sidecar framed as post-hoc dirty-tree enforcement though subprocess path writes a fixed contract marker
- **Reviewer(s)**: dyn-doc-claim-accuracy-output.txt
- **Severity**: important
- **Concern**: Read-only posture is described as post-hoc enforced via the `.dirty-tree` sidecar as a “backstop,” but the Claude subprocess path emits a contract-shaped marker (e.g. fixed `STATUS=clean` / read-only reason) rather than a git/working-tree probe like the Cursor/Codex review-launcher `${OUTPUT}.dirty-tree` contract summarized elsewhere—readers may equate file presence with a successful dirty-tree scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-claim-accuracy-output.txt: Clarify that this `.dirty-tree` file is a contract-shaped sidecar for collectors/orchestrators, not evidence of a successful post-run dirty-tree scan for the Claude subprocess path, and point to the real post-run checks that apply on the plan-review lane (for example `skills/design/scripts/plan-review-loop.sh` calling `scripts/check-mid-run-dirty-tree.sh` around `skills/design/scripts/plan-review-loop.sh:565-568`) if that is the intended "backstop".


### FINDING_5: Redaction at publish boundary over-attributed to vague “ballot aggregator” / named downstream consumers
- **Reviewer(s)**: dyn-doc-claim-accuracy-output.txt
- **Severity**: important
- **Concern**: Downstream consumers are described as applying the redaction pipeline at the publish boundary in a way that over-generalizes: some named aggregation/tally paths do not run `scripts/redact-secrets.sh` in the way implied, so the security story for where secrets are stripped before persistence/publication is inaccurate unless tied to the actual publisher scripts/paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-claim-accuracy-output.txt: Replace the vague "ballot aggregator" label with concrete publishers that actually pipe voter/plan artifacts through `redact-tmpdir-paths.sh` / `redact-secrets.sh` (notably `scripts/larch-log.sh`'s `stage_round_artifact` / `larch_log_redact_file` path at `scripts/larch-log.sh:104-124` with `scripts/lib-larch-log.sh:88-95`), and keep `compose-review-findings.sh`, `tracking-issue-write.sh`, and `design-log-publish.sh` only where that remains accurate.


