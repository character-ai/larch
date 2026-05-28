### FINDING_1: Prior audit discovery is capped at 1000 shared audit reports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `since last audit` searches shared `audit-report` issues with `gh issue list --limit 1000`; heavy audit history can hide the newest skill-specific prior report, causing errors or the wrong anchor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: jq failures are silently converted to an empty PR list
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `filter_prs_for_skill` masks `jq` or JSON failures by returning `[]`, so downstream audit modes can report no PRs instead of failing loudly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Rate assertion harness lacks design `-final` fixture coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance expects `skills/report-tokens/scripts/test-rate-assertions.sh` to exercise design `-final` fixture behavior, but it only adds static grep guards, leaving design artifact wiring regressions uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: `--log-root` validation can accept paths outside the intended tree
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Explicit `--log-root` validation relies on suffix patterns and can accept paths such as `../../../tmp/larch-logs/design`, allowing reads outside the repository’s intended `larch-logs/$SKILL` tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: `--plot-from` should reject non-numeric issue identifiers early
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--plot-from` accepts any non-empty string before calling `gh issue view`, producing confusing downstream errors instead of a clear usage failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: Design RUN_ID matching rejects lowercase UUIDs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Design title and `RUN_ID` regexes only allow `[0-9A-F-]`; lowercase UUIDs from Linux-hosted runs can be skipped or mapped with an empty run id.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Closing prior audit reports only checks the first default page
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `audit-close-priors.sh` calls `gh issue list` without an explicit high limit or pagination, so older open matching audit reports can remain open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Implement PR filtering is negative-only and admits non-run-log merges
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-skill-filter-leak-output.txt
- **Severity**: important
- **Concern**: `--skill=implement` keeps PRs that do not match the design title regex rather than positively selecting implement log flushes or mapped implement manifests. Bulk modes can include feature/fix/automation PRs with no implement run log, yielding empty `run_id` rows or scan errors, and the behavior is not clearly documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

### FINDING_9: `--log-root` override can scan the wrong skill tree
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Arbitrary `--log-root` values can skip skill consistency checks unless they happen to match `larch-logs/design` or `larch-logs/implement`, allowing mismatched manual or harness scans.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Shared concurrency lock blocks design and implement independently
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A shared five-minute concurrency lock can make one skill’s audit filing block the other unless `--allow-concurrent` is used; reviewer marked this as a documented follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: `audit-scan-run.sh` header and usage are stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The script header and usage still mention `scans.tsv` and omit `--skill`, diverging from current docs and per-skill scan registries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Implement `--plot-from` lacks legacy title compatibility coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: There is no test proving `--skill implement --plot-from` still accepts legacy `[Analysis Report]` issue titles, so backward compatibility could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_13: Skill filtering happens before `last N` slicing
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: latent
- **Concern**: `fetch_merged_main_prs_json` filters by skill before callers slice the list, so `last N PRs` means last N skill-eligible PRs rather than the last N merges to `main`, contrary to existing docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Main already included broad non-run-log PRs
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that broad inclusion of unmapped feature PRs is pre-existing on `main`; the implement branch mainly narrows by excluding design-titled PRs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] `--log-root` validation bypass is not used by production skill paths
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer marks arbitrary temp `--log-root` validation as non-production because hermetic tests intentionally use temp roots and production SKILL paths do not pass `--log-root`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] `run-dir-invalid` guard catches skill-root paths
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: nit
- **Concern**: The reviewer notes that `audit-scan-run.sh` already rejects skill-root paths such as `larch-logs/design` or `larch-logs/$SKILL/`; per-run UUID paths remain valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Mis-titled design PRs can leak into implement bulk lists
- **Reviewer(s)**: dyn-skill-filter-leak-output.txt
- **Severity**: latent
- **Concern**: A design PR using a flush-style title rather than the expected design publication title would not match the design regex and could be included in implement lists; reviewer frames this as an edge case if title generation diverges.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-skill-filter-leak-output.txt: Address the concern above.
