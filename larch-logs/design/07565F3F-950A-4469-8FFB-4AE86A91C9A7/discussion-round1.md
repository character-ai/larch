## Decision 1: When in /design should OOS issues be filed?
- **Question**: After Step 3 tally vs after Gate C Approve vs both?
- **Resolution**: After Gate C Approve (once final). One-shot per /design invocation. Sentinel guards against /design re-invocation on same issue.
- **Source**: user

## Decision 2: How does /implement Step 9a.1 know which OOS items were already filed?
- **Question**: Add field to oos-accepted-design.md vs new sidecar artifact vs /issue LLM dedup only?
- **Resolution**: Add a per-block `- **Filed URL**: <url>` field to each `### OOS_N:` block in oos-accepted-design.md. /implement Step 9a.1 reads it, skips re-filing items whose Filed URL field is populated, but still files the other OOS sources (Step 5 review OOS, main-agent dual-write OOS).
- **Source**: user

## Decision 3: Step 5 breadcrumb naming
- **Question**: Split Step 5 vs rename Step 5?
- **Resolution**: Split into Step 5 (finalize: write larch:plan to issue + publish + rename to [DESIGNED]) and Step 6 (cleanup: remove tmpdir). Update step-name-registry.tsv. Update SKILL.md step boundaries.
- **Source**: user

## Decision 4: Combine pass + file-conflict deps in /design?
- **Question**: Share helpers with /implement Step 9a.1, skip both, or only file-conflict deps?
- **Resolution**: Share both helpers — oos-issue-cap.sh and oos-file-conflict-deps.sh — so /design's filing pipeline is behaviorally equivalent to today's Step 9a.1 for design-phase OOS, just relocated.
- **Source**: user

## Decision 5: Security-tagged OOS handling
- **Question**: Are security-tagged OOS items affected by this change?
- **Resolution**: No change. The existing tally machinery already excludes security-tagged findings from `oos-accepted-design.md` per plan-review.md:128 (held locally, routed through SECURITY.md). /design only files items that already pass that filter.
- **Source**: codebase

## Decision 6: Fork-mode / repo_unavailable carve-outs
- **Question**: Does /design need fork-mode detection before filing?
- **Resolution**: No. /design has no concept of `forked_target`; that lives in /implement's session state and applies to the implementation/PR phase. /design runs on the consumer repo's tracking issue regardless of /implement's eventual target. Today's /design already writes oos-accepted-design.md unconditionally; this change just adds filing in the same place. Fork-mode users who want to suppress filing can avoid running /design (or file under a separate workflow).
- **Source**: codebase
