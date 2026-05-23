### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: Pre-commit header vs CI lint entrypoint (`make lint` vs `make lint-only`)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The top-of-file comment in `.pre-commit-config.yaml` implies CI runs full `make lint` via pre-commit, while Makefile comments / `docs/linting.md` describe a split where CI uses harness shards and `make lint-only` (pre-commit), with `make lint` as the local aggregate. Operators can misread which target CI runs and mis-triage lint vs harness failures, or skip running the full local aggregate before shipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Very long lines silently skip anchor detection
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Lines over ~12000 characters skip anchor detection silently, so a pathological one-line fence could evade denylist enforcement without notice unless the linter warns/fails on skip or when denylist tokens appear on skipped lines.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: Branch bundles unrelated work (foreground markers, OOS, run logs, version bump)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: `git log merge-base..HEAD` bundles foreground-marker work with unrelated #2648 OOS changes, run-log flushes, and version bump—hurting plan fidelity and review focus when disentangling independent features in one diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: Stderr splits “missing banner” / “missing comment” vs plan’s unified template
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Stderr uses split “missing banner” / “missing comment” messages instead of the plan’s unified template—minor mismatch for anyone grepping or documenting the exact plan error string.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: CHANGELOG 42.0.10 bundles unrelated themes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The `[42.0.10]` release entry mixes unrelated bullets (disposition gate, OOS persistence, harness, foreground lint), making it hard to tell what changed for a given regression without reading the whole list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: BASH_AUTHORING Section 4 title vs acceptance phrase “Foreground Default for Blocking Script Calls”
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Section 4’s visible heading / title does not match the plan acceptance wording (“Foreground Default for Blocking Script Calls” and related §4 phrasing). Cross-doc searches, tracking-issue quotes, and audits that use the acceptance string may miss the normative section unless an alias line is added or the heading is aligned/renamed everywhere consistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_4: Harness case 24 label vs `.sh` substring gate
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Case 24’s label suggests continuation enforcement is covered, but a `.sh` substring gate skips lines without `.sh`, so maintainers may believe continuation anchoring is tested when the linter can skip that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_5: `test-lint-foreground-markers.md` out of sync with harness cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: The markdown doc drifts from the shell harness: fixture count / “16 fixtures” vs more cases, and the numbered contract list order does not match harness case numbers—slowing correlation from PASS/FAIL output to documented cases during debugging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: `*.sh` fast-path and single-line anchors can miss denylisted invocations
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Concern**: The `*'.sh'*` heuristic plus single-line anchor logic can miss rare fenced shapes (general latent risk), and specifically backslash/line breaks can split a denylisted `*.sh` basename so no single fence line contains the full basename token—then the `*.sh` fast-path skips anchor detection, allowing a fenced invocation without markers to pass lint and evade the Family B gate unless continuation joining is implemented, the fast-path removed, and/or a harness case locks the behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Family A harness counts `run_in_background: true` file-wide
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The regression check counts `run_in_background: true` substrings across the whole file, so unrelated literals can satisfy the floor while real Family A Bash fences lose `background=true`, weakening the test’s structural guarantee.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Banner check allows substring-anywhere in window vs leading-line intent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The banner check matches substring-anywhere in the initial window, not a leading-line-only rule aligned with some authoring text and the plan’s operator-first visibility goal—CI can pass with the banner buried in unrelated prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

