### FINDING_1: test-cleanup case bullets still imply top-level mtime alone controls directory deletion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-docs-drift-output.txt, dyn-ops-retention-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/test-cleanup.md:10-12` still describes `stale-dir-removed` and `stale-dir-with-keepalive-removed` in terms of stale top-level mtime, which can mislead maintainers into thinking top-level mtime alone drives removal instead of the bounded `maxdepth 5` nested-activity scan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-docs-drift-output.txt: Address the concern above.
  - From dyn-ops-retention-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] README and workflow docs still describe cleanup as age-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-docs-drift-output.txt, dyn-ops-retention-output.txt
- **Severity**: latent
- **Concern**: `README.md:49` and `docs/workflow-lifecycle.md:88` still describe `/cleanup` as removing stale paths by age without the bounded nested-activity model, depth-5 tradeoff, or failure-mode semantics now documented elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-docs-drift-output.txt: Address the concern above.
  - From dyn-ops-retention-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] test harness find stub assumes /usr/bin/find
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/test-cleanup.sh:39-57` hardcodes `/usr/bin/find` in the harness stub, which can fail on hosts where `find` is only available elsewhere such as `/bin/find`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: cleanup retention docs overstate nested-scan protection for loose /tmp files
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-docs-drift-output.txt, dyn-ops-retention-output.txt
- **Severity**: important
- **Concern**: `docs/configuration-and-permissions.md:284`, `docs/skills.md:47`, `SECURITY.md:234`, and `skills/cleanup/SKILL.md:9` apply the bounded nested-scan retention rule too broadly. Runtime applies the nested scan to directories, while stale matching loose `/tmp` files are removed by top-level age plus pattern match.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From dyn-docs-drift-output.txt: Address the concern above.
  - From dyn-ops-retention-output.txt: Address the concern above.

### FINDING_5: enumeration-pass fail-open behavior is documented but untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.md:12` documents silent fail-open behavior for top-level enumeration `find` failures, but the harness lacks a regression case proving exit 0, zero removals, and no nested-scan warning when enumeration fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] documented /tmp fresh deep child case is missing from harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/test-cleanup.md:21` lists `stale-tmp-toplevel-with-fresh-deep-child-kept`, but `test-cleanup.sh` has no matching case, so maintainers may assume `/tmp` nested retention is covered when it is not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] docs sync guard does not catch obsolete cleanup mtime wording
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-quick-mode-docs-sync.sh:97-116` lacks stale phrase coverage for obsolete top-level-mtime-only cleanup retention wording, so future docs edits could reintroduce contradictory retention language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: security and plan reviewers emitted commit summaries rather than actionable findings
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The source entries summarize commits `526b70560` and `ef4758eaa` / plan traceability rather than identifying a concrete behavioral risk requiring a code or docs change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] cleanup.sh uses PATH-resolved find and pgrep
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `skills/cleanup/scripts/cleanup.sh:26-61,99-110` invokes bare `find` and `pgrep` from `PATH`; an attacker who can influence the operator’s `PATH` could substitute malicious commands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] top-level enumeration find failures are silent fail-open
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh:61,110` suppresses top-level enumeration `find` failures and exits successfully with zero removals and no warning, which can make operators believe cleanup ran when stale session state remained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] nested-scan warnings expose full paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `skills/cleanup/scripts/cleanup.sh:26-28` includes the full `$entry` path in nested-scan failure warnings; paths can encode session or layout metadata even when stderr goes through `larch_err`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] maxdepth 5 tradeoff can miss deeper activity
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:18-31` only considers activity within `maxdepth 5`, so activity deeper than five levels does not block deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: /tmp nested-scan failure path is not covered by the new regression test
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/test-cleanup.sh:186-200` covers nested-scan failure for cache entries only; `/tmp` directories share `should_remove_by_age`, but a `/tmp`-specific regression would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] nested find diagnostics are suppressed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-ops-retention-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.sh:26` redirects nested `find` stderr to `/dev/null`, leaving operators with only a generic warning and no underlying diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-ops-retention-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] cache and /tmp enumeration predicates differ
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/cleanup/scripts/cleanup.sh:55-110` uses different enumeration predicates for cache and `/tmp`; `/tmp` directories with fresh top-level mtime but stale contents may never be enumerated, unlike cache entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: cleanup skill prompt omits operator-relevant retention failure semantics
- **Reviewer(s)**: dyn-ops-retention-output.txt
- **Severity**: important
- **Concern**: `skills/cleanup/SKILL.md:9` describes nested-activity retention but omits the depth-bound tradeoff, nested-scan fail-safe, enumeration fail-open, and cache-vs-`/tmp` enumeration asymmetry now treated as part of the cleanup contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ops-retention-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] test-cleanup doc references nonexistent FRESH_DESCENDANT_MAXDEPTH
- **Reviewer(s)**: dyn-docs-drift-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/test-cleanup.md:24` references `FRESH_DESCENDANT_MAXDEPTH`, but the harness and script do not define it; the bound is hardcoded as `maxdepth 5`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-drift-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] cleanup.md omits that cache non-directories are never removed
- **Reviewer(s)**: dyn-docs-drift-output.txt
- **Severity**: nit
- **Concern**: `skills/cleanup/scripts/cleanup.md:9` says the cache pass deletes a directory only via nested scan, but does not explicitly state that non-directory top-level cache entries are never removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-docs-drift-output.txt: Address the concern above.
