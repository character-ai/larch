Here is the normalized aggregator output. In-scope clusters are ordered by the smallest original input finding id in each cluster. Out-of-scope items stay separate where the concerns differ; the three `larch-logs/**` observations are merged as one behavioral theme (diff volume / review scope / policy).

### FINDING_1: Pre-commit header misstates CI lint entrypoint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Header still says CI uses `make lint` while the landing plan required reconciling with the CI job using `make lint-only`, so operators may misread which target CI enforces; plan acceptance item OOS_4 called out as left undone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: CHANGElog PATCH bundles unrelated work with foreground-marker lint
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: A single PATCH release aggregates unrelated disposition/OOS/cache work with foreground-marker lint, blurring version semantics and making it hard to map bullets to one change set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Heredoc / backslash-continuation coverage and heredoc false-positive risk
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: No heredoc (or similar) negative fixture: `${CLAUDE_PLUGIN_ROOT}/…denylist…`-shaped text inside a heredoc could false-positive as an anchor and force markers on tutorial fences; the implementation plan also promised heredoc and `\`-continued denylisted-invocation fixtures, but the harness omits them, so regressions on those shapes may ship without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Banner check allows substring-anywhere in window vs docs “immediately above” fence
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Linter allows the canonical banner substring anywhere in a 20-line window while authoring text calls for placement immediately above the fence; CI can pass while burying the banner in unrelated prose, weakening the visibility goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: BASH_AUTHORING section heading vs acceptance wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Section heading differs from acceptance wording “Foreground Default…”, hurting discoverability vs issue/plan language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: AGENTS.md Family B sentence omits Makefile alias
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Family B sentence cites `make lint-foreground-markers` only; operators may miss the `lint-foreground` alias wired in the Makefile.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Duplicate foreground warnings by ship-pr fence in implement skill
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Duplicate foreground warnings adjacent to the `ship-pr.sh` invoke block add readability noise while remaining functionally fine if one canonical banner substring is preserved for the linter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] heavy-worker has no fenced denylisted invocation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: No fenced denylisted invocation was added; plan allowed no edit when fences are absent; not applicable to the foreground diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: Family A harness pins exact counts; any increase breaks CI
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: Family A harness pins exact `grep -cF` equality to fixed counts, which is stricter than plan language that only forbids decreases: adding a legitimate new parallel-launch prose line can fail CI (e.g. 9→10) without a Family B regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Anchor ERE may miss multi-segment paths (e.g. ./scripts/ship-pr.sh)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Anchor ERE allows only one optional path segment before the denylisted basename, so some fenced invocation shapes may skip anchor classification and missing markers would not fail the linter.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Harness/plan doc fixture count (16 vs 22) misaligned
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Implementation plan / sibling doc still claim 16 fixtures while the harness contract lists 22 numbered cases plus Family A checks, creating a false completeness gap for maintainers and plan-adequacy checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Large committed larch-logs trees in diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Large committed run/design logs are normal plugin telemetry per run-logs policy, not review defects for this feature; diff volume is high; operators should still treat logs as potentially sensitive narrative under org policy; no foreground deliverable gap for plan fidelity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] CHANGELOG [42.0.10] editorial grouping
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Unreleased/42.0.10 changelog bundles several behaviors in one section; acceptable as editorial grouping unless release process mandates splitting entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_14: `git ls-files` skips untracked skill Markdown
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Untracked skill Markdown is skipped under `git ls-files` enumeration, so local lint can pass before `git add` while CI/staging would still enforce, risking false confidence unless behavior is documented or enumeration extended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Branch mixes unrelated merges and log flushes with foreground work
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Branch mixes OOS gate merges and `larch-logs` flushes with foreground-marker work, widening diff noise without indicating linter bugs; split PRs if review signal matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: GH_HOST embedded in ERE with incomplete metacharacter safety
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `GH_HOST` is embedded into an ERE with only dot escaping; other ERE metacharacters could skew matching for GitHub Enterprise or odd `GH_HOST` values, mis-counting filed URL counts and disposition gate results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: OOS markdown: issue URL stdout interpolated without strict validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Issue stdout URL values are interpolated into OOS markdown without newline or URL-shape validation; crafted `ISSUE_N_URL` lines with embedded newlines could inject extra markdown into `oos-accepted-design.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: Unreleased CHANGELOG contradicts strict-file / Filed URL line narrative
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Unreleased changelog still describes design OOS URLs satisfying the gate via loose `--filed-urls-file` only, conflicting with the strict-file / Filed URL line rule under [42.0.10] and risking re-opening the disposition loophole narrative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Committed implement plan archive repeats wrong disposition threshold story
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Committed implement plan copies repeat a disposition pass rule (`filed >= non_sec` with strict+loose double-count) that contradicts `oos-disposition-gate.sh` disjunctive branches, misleading future replays or auditors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: `git ls-files` fully silenced: empty path set treated as success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: `git ls-files` enumeration is fully silenced and treated as success even when it returns no paths, so a broken git view could skip all Markdown scans while lint passes; consider failing or falling back with a loud diagnostic when in-worktree but zero paths while skill trees exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Non-marker /design Step 5b and scripts change OOS filing semantics vs marker-only scope
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Non-marker `/design` Step 5b prose and related scripts change OOS filing semantics (e.g. cross-session cache), conflicting with a marker-only skill-edit constraint and widening regression surface under the same version bump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

---

**Merge map (input → output)**  
1→1; 2→2; 3,5,16→3; 4,17,30→4; 6,28→5; 7→6; 8,31→7; 9→8; 10,15→9; 11→10; 12,26,29→11; 13,22,32→12; 14→13; 18→14; 19→15; 20→16; 21→17; 23→18; 24→19; 25→20; 27→21.

Because this output contains one or more `### FINDING_N:` blocks, the line `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` is **not** included.
