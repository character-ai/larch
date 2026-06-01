### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Pre-bootstrap export CLAUDE_PLUGIN_ROOT cardinality no longer checked
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-implement-timing-rehydration.sh` removed export-count parity; a pre-bootstrap fence could drop `export CLAUDE_PLUGIN_ROOT` while keeping source+awk lines, breaking same-fence `${CLAUDE_PLUGIN_ROOT}/` calls until a later block exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: Sourcing write-session-env.sh on resume-tail lacks errexit/argv0 guards in tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No assertion that sourcing `write-session-env.sh` during resume-tail avoids errexit leak or accidental argv0 execution. A top-level `set -e` or guard regression could abort `implement-bootstrap` on benign helper failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: Corrupt plugin-root.env can fail source without fallback
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Truncated or tampered `plugin-root.env` can make the source line fail; unlike legacy awk there is no `|| true` on the canonical path. A bad sibling may abort the fence or leave `CLAUDE_PLUGIN_ROOT` unset while later lines still call `${CLAUDE_PLUGIN_ROOT}/scripts/...`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Duplicated CLAUDE_PLUGIN_ROOT validation in write-session-env.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `emit_plugin_root_env` and the argv0 path duplicate `CLAUDE_PLUGIN_ROOT` validation in `scripts/write-session-env.sh:39-60`, risking future drift if only one path is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: Preflight indented bash fences use CLAUDE_PLUGIN_ROOT without plugin-root rehydration
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Preflight indented bash fences at `skills/implement/SKILL.md:205-210,797-798` use `CLAUDE_PLUGIN_ROOT` without the post-Step-0 `plugin-root.env` pattern; Invariant C skips indented fences. If inherited env were missing before Step 0, plan-block-read / larch-log fences could mis-resolve (pre-existing, not widened by this PR).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: plugin-root.env sourced with -f only, no symlink hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Post-Step-0 rehydration sources `plugin-root.env` with `-f` only, without regular non-symlink checks used elsewhere for sensitive tmpdir reads. Same-UID tmpdir tampering or TOCTOU could turn rehydration into arbitrary shell execution, worse than prior awk-only extraction from `session-env.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=1 JUDGE_ERROR=0

