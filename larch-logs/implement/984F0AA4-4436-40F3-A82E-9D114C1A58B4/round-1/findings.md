### FINDING_1: Duplicate stat_mtime logic can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Duplicate stat_mtime implementations in production and test code can drift, causing tests to pass while prune ordering differs from production behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_2: Mtime retention can evict long-idle used versions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Directory mtime approximates filesystem recency, not semantic install or usage history. Fresh hop-upgrade directories can outrank older but once-used versions, so sparse used versions like 1.0.1/1.0.2 may still be evicted unless touched or pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Duplicate cached-version collection loops
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: list_cached_versions and list_cached_versions_by_mtime duplicate cache-dir discovery logic, increasing maintenance risk if collection rules change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Missing touch coverage for design/session call sites
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Harness coverage exercises write-session-env.sh touch behavior but not write-design-current-env.sh, and in some reviews not session-setup.sh, so regressions in those touch paths could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] session-setup touches plugin root before writer-grade validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: session-setup.sh calls larch_touch_executing_cache_root on raw CLAUDE_PLUGIN_ROOT before the stronger validation used by writers. A malformed or mis-set path with a numeric basename may be touched even though persistence would later reject it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Dead list_cached_versions helper remains
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: list_cached_versions is unused after the prune path switched to mtime ordering, leaving dead code that may confuse future edits or trip later validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] capture-session-transcript stat probing order differs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: capture-session-transcript.sh keeps a pre-existing BSD-first stat probe order while the new convention is GNU-first, creating cross-script inconsistency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: Docs overstate when cache mtime refresh runs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Documentation implies mtime refresh runs more broadly than it does; /upgrade-larch sessions do not call session-setup or the touch helper directly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Legacy prune tests do not prove mtime ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Several existing cap-trim and pin cases seed mtimes in semver-ascending order, so they can still pass if pruning regresses back to semver ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Missing sparse-used-version regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: No prune test reproduces the sparse-used-versions-over-large-semver-jump scenario, so the session-touch plus prune interaction could regress without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Tiebreaker test omits under-cap retention phase
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The equal-mtime tiebreaker test only checks over-cap eviction and does not first verify equal-mtime directories are retained while the cache is still under or at the cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Missing stat garbage/failure regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not cover GNU stat -f returning non-numeric filesystem-info output when -c fails, so validation regressions could corrupt mtime sort behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: stat_mtime fallback is silent and reverts ordering
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: If both stat probes fail, every entry gets mtime 0, causing eviction to fall back to lexicographic version order without an operator-visible warning or documented expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_14: Prune breadcrumb omits mtime semantics
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Live prune progress text does not mention mtime-first retention and lexicographic tiebreaking, so operators may infer semver-ordered retention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Pin-heavy caches can exceed keep limit silently
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Many stale session pins can block unpinned eviction, leaving more than eight cache directories without a final over-cap warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Numeric-basename guard does not prove cache-parent path
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The touch guard checks only version-shaped basenames, not whether the path is under the plugin cache root. Numeric-basename directories elsewhere could still be touched if the path is trusted or accepted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Missing dedicated mtime prune docs subsection
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: test-upgrade-larch-prune.md lacks the planned dedicated mtime-based prune coverage subsection, making the harness contract harder to discover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
