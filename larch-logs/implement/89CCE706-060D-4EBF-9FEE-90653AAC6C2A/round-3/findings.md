### FINDING_1: Static archetype slug source of truth is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Static archetype slugs are hardcoded in multiple places, so adding or renaming an archetype can make dispatch, coverage, and tests disagree about the required static panel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Static reviewer basename normalization is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Static output basename normalization is duplicated between threshold and review-core logic, risking divergent retry/phase suffix handling and inconsistent threshold versus coverage results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Dynamic Codex log inclusion contract conflicts with implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-output.txt
- **Severity**: important
- **Concern**: `dyn-*-codex-output.txt` and related artifacts are excluded from committed run logs despite acceptance/product text expecting dynamic Codex transcripts to remain available for forensics and run-log mining. The current allow/deny patterns may also treat phased and unphased dynamic Codex outputs inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-output.txt: Address the concern above.

### FINDING_4: Misleading `claude_output` variable covers Codex/Cursor files too
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A loop variable named `claude_output` also processes external Codex/Cursor files, which could lead future maintainers to incorrectly narrow the pass to Claude-only outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Dropped-static collection repeatedly rescans the manifest
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `collect_dropped_static_outputs` rescans the full manifest for each dropped row, which is avoidable work if slot counts grow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Dead static focus-area arms remain in tally code
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy `static_focus_area` branches for removed folded specialists remain in `tally-code-votes.sh`, creating minor maintenance confusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Coverage gate can credit invalid static output files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-coverage-gate-output.txt
- **Severity**: important
- **Concern**: The per-archetype coverage gate can treat stale, orphaned, or collector-rejected static output files as successful coverage. This can let a round proceed even when the current manifest has no live substantive peer for an archetype.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-coverage-gate-output.txt: Address the concern above.

### FINDING_8: Dispatch status KVs and docs no longer reflect composite panel fate
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-output.txt
- **Severity**: latent
- **Concern**: `DISPATCH_OK` / `STATIC_DISPATCH_OK` are no longer authoritative hard-stop signals, but dispatch output and documentation can still imply panel failure or success in ways that disagree with threshold plus coverage semantics. Operators and automation may misread partial static drops or degraded dynamic dispatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-output.txt: Address the concern above.

### FINDING_9: Missing both-vendor happy-path threshold harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Tests do not assert that a healthy both-vendor static panel passes `intended-slots=8` and `launched-slots=8` into threshold logic, leaving denominator regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Scout dynamic-archetype tests do not enforce reserved slugs
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The scout prompt reserves historical static slugs, but the harness does not assert that dynamic scouts cannot emit those reserved slugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: External reviewer prompt redaction/escaping is too narrow
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: Plan and feature-description blocks sent to external reviewers are not scrubbed with the repository’s full secret redactor and do not fully neutralize prompt-control markup. Tests mainly assert block presence rather than a negative matrix for secrets and tag injection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Description-mode text is embedded raw in reviewer prompts
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: Operator-supplied `DESCRIPTION_TEXT` can be interpolated into external reviewer prompt preambles without the same escaping/redaction used for other untrusted prompt data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-prompt-context-output.txt: Address the concern above.

### FINDING_13: `launched-slots` is wired equal to `intended-slots`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Review-core always passes launched static slots equal to intended static slots, so missing emitted slots may not be counted through the threshold script’s never-launched path and rely only on coverage as a backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Threshold dedupe lets collector failure override substantive output files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-threshold-output.txt
- **Severity**: important
- **Concern**: `--reviewer-output-files` skips bases already present in collector results even when collector status is failed but the on-disk file is substantive, causing threshold and coverage to disagree and potentially fail recovered static peers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-threshold-output.txt: Address the concern above.

### FINDING_15: Dropped static rows can be double-counted in threshold math
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-threshold-output.txt
- **Severity**: important
- **Concern**: Dropped-slot failures are not deduplicated against prior counted bases or duplicate TSV rows, so logical static slot loss can be inflated past the hard-stop threshold.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-threshold-output.txt: Address the concern above.

### FINDING_16: Static manifest slot IDs are duplicated across vendors
- **Reviewer(s)**: dyn-waterfall-output.txt
- **Severity**: latent
- **Concern**: Cursor and Codex static rows share archetype slug values as `slot` and differ only by `tool`/`output`, so future consumers keying only on `slot` could misattribute drops or successes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-output.txt: Address the concern above.

### FINDING_17: Collector-result pass can double-count duplicate static stems
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: important
- **Concern**: The threshold script’s collector-results pass does not dedupe normalized static basenames before incrementing counts, so duplicate phase/retry records can inflate failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] `log_dropped_slots` uses implement-centric site label
- **Reviewer(s)**: dyn-waterfall-output.txt
- **Severity**: nit
- **Concern**: Dropped static slots are logged with `--site "5"`, which can mislabel standalone `/review` drops as Step 5 issues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Launched-slot padding path appears unused in production
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: nit
- **Concern**: Since review-core passes launched slots equal to intended slots, threshold script documentation about lower launched counts for vendor-unhealthy cases may not match production behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Threshold failure can suppress coverage diagnostics
- **Reviewer(s)**: dyn-threshold-output.txt
- **Severity**: nit
- **Concern**: When aggregate threshold fails first, the coverage gate may not run, so operators may not see missing-archetype diagnostics on heavily degraded panels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-threshold-output.txt: Address the concern above.

### FINDING_21: `cap_hit` is treated as coverage success
- **Reviewer(s)**: dyn-coverage-gate-output.txt
- **Severity**: important
- **Concern**: The coverage gate treats `cap_hit` like `OK`, so an archetype whose peers were skipped by budget caps can be marked covered even though no substantive static lens ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-coverage-gate-output.txt: Address the concern above.

### FINDING_22: Reviewer-testing plan injection can weaken narrowed diff modes
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: important
- **Concern**: `reviewer-testing` now receives plan blocks in narrowed diff modes and description mode, with mode-specific constraints emitted after the untrusted plan, allowing hostile plan text to try to widen review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Dynamic scout notes remain an untrusted prompt surface
- **Reviewer(s)**: dyn-prompt-context-output.txt
- **Severity**: latent
- **Concern**: Dynamic reviewer scout rationale/prompt bodies are embedded in prompt context without the newer redaction path, leaving a separate unchanged untrusted-data surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-context-output.txt: Address the concern above.

### FINDING_24: Public docs use ambiguous “per vendor” panel wording
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: latent
- **Concern**: Documentation and sync markers say “4 specialists per vendor (Cursor + Codex)” without consistently qualifying that rows are emitted per available vendor, which can be read as a fixed eight-row requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

### FINDING_25: New topology row is not linked from consumer docs
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: The new `implement.review_and_fix.panel_hard` topology projection exists, but consumer docs repeat the panel phrase inline instead of linking to the generated topology anchor, weakening drift prevention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

### FINDING_26: Diagram sync checks are not covered by self-test
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: Diagram phrase greps were added to the default docs-sync harness, but `--self-test` does not exercise those positive/negative diagram assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

### FINDING_27: Review runtime docs are not included in panel sync harness
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/review/SKILL.md` and `dispatch-panel.md` are runtime/authority surfaces for the review panel but are not included in the public-doc sync checks, so review-panel drift could escape CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

### FINDING_28: Docs-sync harness removed prior Step 5 anchors
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: The docs-sync harness no longer checks prior `5 rounds` and `--panel hard` anchors, so Step 5 round-cap and delegated-panel wording can drift unless the removal is explicitly documented as intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] Agent headers still claim template derivation
- **Reviewer(s)**: dyn-topology-sync-output.txt
- **Severity**: nit
- **Concern**: Some hand-maintained reviewer agent headers still say they are derived from the shared template, which can confuse contributors now that fold edits are intended directly in those files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-topology-sync-output.txt: Address the concern above.
