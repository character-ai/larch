### FINDING_1: [OUT_OF_SCOPE] architecture: .claude-plugin/plugin.json; CHANGELOG.md; Makefile; agent-lint.toml; larch-logs/implement/**
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plugin version, root changelog, lint registry/Makefile targets, and implement run logs appear in the branch diff. Outside the excerpted implementation plan’s functional file list for conflict auto-resolve. None for this plan-fidelity pass; handle under release/versioning or run-log policy as appropriate.
- **Suggested revision**: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.sh; docs/voting-process.md; scripts/test-lib-vote-tally.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Vote-tally multi-voter fix and docs/tests ride on the same branch as the rebase work. Not part of the supplied changelog auto-resolve plan; no plan requirement to trace. None for this plan-fidelity pass; track under the vote-tally issue/PR if needed.
- **Suggested revision**: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Large committed implement run logs in the diff Reviewer noise only not introduced by the conflict-resolution scripts themselves Treat as expected per docs/run-logs.md when triaging this PR
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: scripts/ship-pr.sh:1098-1104
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] fix role still uses 1800s timeout while resolve-conflict uses 600s; pre-existing asymmetry. N/A if intentional. None unless product wants uniform timeouts.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] correctness: scripts/lib-vote-tally.sh:115-139
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Vote tally exoneration two-path rule from merged #2457 work. Panel outcomes shift for mixed exonerate/yes/no tallies; unrelated to changelog auto-resolve. Track under vote-tally / review process changes, not ship-pr changelog merge.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/launch-cursor-ci.sh:171-177
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Launcher process exit code is always 0. Callers using only $? may miss agent failure; pre-existing. Consider propagating non-zero exit in a dedicated change.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/lib-vote-tally.sh:115-139
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Branch bundles classify_result exoneration policy changes unrelated to ship-pr conflict handling. Downstream consumers of vote labels see different outcomes for some YES/NO/EXONERATE mixes; covered by updated tally tests, not by changelog requirements. Track as its own review/PR if you want isolation from the rebase-conflict feature.
- **Suggested revision**: Address the concern above.

### FINDING_8: architecture: scripts/auto-resolve-changelog.sh:1-237
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Implementation plan estimated ~35 lines; shipped script is much larger with MD/RST/awk. Plan-to-code traceability and sizing expectations for reviewers/scheduling diverge from the written plan without changing the functional checklist. Update the plan artifact or future estimates to reflect dual-format scope and real line count.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unscoped checkout --ours for every version.go and go.sum basename. Secondary version.go or coupled go.mod/go.sum conflicts can lose branch-side intent. Scope to known paths or require paired go.mod handling.
- **Suggested revision**: Address the concern above.

### FINDING_10: code-quality: scripts/auto-resolve-changelog.md:1-24
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Documentation describes Markdown-only merge rules while the script implements RST and bare-CHANGELOG heuristics. Operators misread why auto-resolve skipped or how entries were ordered. Update the sibling doc to cover RST, basename rules, and exit-1 deferral cases.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: scripts/auto-resolve-changelog.md:5-15
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling doc describes only Markdown ## preconditions while the script also implements RST and extensionless heuristics. Operators mis-diagnose auto-resolve behavior for CHANGELOG.rst or bare CHANGELOG paths. Update auto-resolve-changelog.md Preconditions and merge rules to document RST and basename-based mode selection.
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/auto-resolve-changelog.sh:1-237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Implementation is far larger and more general than the plan’s small Markdown-only helper. Higher long-term maintenance and review burden than the plan implied. Match scope to the plan or factor the awk block behind a thin wrapper with an explicit format contract.
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-launch-cursor-ci.sh:33-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Tests only reject bad --conflict-files paths and grep for the flag string, not prompt injection behavior. A future edit could remove CONFLICT_CONTEXT from the prompt without failing CI. Extend tests to assert prompt contents via stubbed agent invocation.
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/auto-resolve-changelog.sh:130-148
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Extensionless CHANGELOG paths fall back to RST parsing when Markdown ## first headings do not match on both sides. A Markdown CHANGELOG without a shared first ## line can be parsed as RST; rare false RST title detection could merge incorrectly instead of exiting 1. Narrow heuristics (e.g. treat bare CHANGELOG as Markdown-only when lines match /^## / anywhere) or default to exit 1 unless .rst or explicit shared ## match.
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/auto-resolve-changelog.sh:131-196
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Extensionless CHANGELOG path uses MD-vs-RST heuristic that can misparse Markdown when first ## headings differ. Rare repos using bare CHANGELOG.md content without extension could get wrong merge or unnecessary vendor escalation. Detect ambiguous cases and exit 1, or only auto-resolve known extensions from ship-pr.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/auto-resolve-changelog.sh:148-188
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Tail after first ## is always taken from stage :2: only; stage :3: tail can differ. Rebase conflict only in a released section while ## Unreleased matches on both sides: script exits 0, writes upstream tail, branch edits to older releases vanish while the path is staged resolved. Compare post-first-section spans of :2: vs :3: (or refuse) and exit 1 when they differ so the vendor does a real merge.
- **Suggested revision**: Address the concern above.

### FINDING_17: correctness: scripts/auto-resolve-changelog.sh:163-182
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Line-keyed dedupe for unreleased bodies. Multi-line or wrapped entries can split, duplicate, or reorder in plausible-looking output. Treat as heuristic and bail to vendor when multi-line bullets detected, or merge at entry granularity.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/auto-resolve-changelog.sh:191-232
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] RST merge repeats upstream-only tail after first section. Same class of bug for RST-shaped logs: matching first title but divergent later sections yields silent loss of :3: content. Guard tail equality or document and enforce upstream-wins-only for released sections with explicit opt-in.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/lib-vote-tally.sh:128-136
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Broader multi-voter exoneration rule More vote mixes become exonerated which can reduce pressure to act on disputed findings including security-tagged ones Document policy tighten with security carve-out or stricter NO-dominance requirement if needed
- **Suggested revision**: Address the concern above.

### FINDING_20: risk-integration: scripts/lib-vote-tally.sh:77-100;Makefile;docs/voting-process.md;agent-lint.toml
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Unrelated vote-tally and doc/tooling changes ride in the same branch as ship-pr changelog auto-resolve. Reviewers and bisect must disambiguate regressions between tally policy and rebase automation; a revert of one concern may drop the other. Split into separate PRs or sequential merges to main so each concern ships independently.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/ship-pr.sh:1336-1340
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Automatic git checkout --ours for any go.sum or version.go conflict without path scoping Replayed-side dependency or version pins could be dropped in favor of upstream without review Narrow to known paths or stop auto-ours for go.sum unless policy explicitly accepts mainline wins
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/ship-pr.sh:1372-1388
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] 600s vendor timeout for all resolve-conflict launches from this path. Large or multi-file conflicts may hit timeout more often than under 1800s. Add env-tunable or conflict-weighted timeout; document trade-off.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-launch-cursor-ci.sh:33-36
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] --conflict-files coverage is grep-based (flag string + static prompt substring), not a full accept path. A regression could drop CSV injection while tests still pass if the static boilerplate remains. Add a hermetic test that passes a benign CSV and asserts it appears in the built resolve-conflict prompt (and optionally mirror in test-launch-codex-ci.sh).
- **Suggested revision**: Address the concern above.

### FINDING_24: security: scripts/launch-codex-ci.sh:71-100
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Same CONFLICT_FILES prompt splice for Codex Same multiline or corrupted CSV could alter how Codex interprets the resolve-conflict task Mirror the same strict validation as the Cursor launcher (shared helper recommended)
- **Suggested revision**: Address the concern above.

### FINDING_25: security: scripts/launch-cursor-ci.sh:71-103
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] CONFLICT_FILES spliced into vendor prompt without rejecting embedded newlines or control characters A conflict path list containing a newline could inject extra prompt lines and blur instruction vs data boundaries for the Cursor agent Reject or sanitize CONFLICT_FILES (e.g. disallow newline/control chars; validate each comma-separated segment)
- **Suggested revision**: Address the concern above.

