### FINDING_1: Duplicate cache version enumeration
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `list_cached_versions` and `list_cached_versions_by_mtime` duplicate cache-dir discovery/filtering logic, so future glob or validation changes could diverge and reintroduce prune-order bugs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Cap-prune tests still assume semver ordering
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Existing cap-prune cases do not seed mtimes while asserting semver-ordered eviction, so they may fail or pass for the wrong reason after mtime-based pruning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Missing design-env CLAUDE_PLUGIN_ROOT rejection tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `write-design-current-env.sh` now validates `CLAUDE_PLUGIN_ROOT`, but the design harness lacks rejection coverage and the stricter contract may break callers that previously relied on permissive exports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: Prune harness markdown omits mtime regression cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-upgrade-larch-prune.md` omits sparse-used-versions and stat-garbage fallback cases, making key mtime regression coverage hard to discover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Session-env roundtrip contract omits sections G/H
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-session-env-roundtrip.md` documents section F but not section G/H coverage for `session-setup` and `write-design-current-env`, risking doc/test drift for touch behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Misplaced Summary header in session-env harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-session-env-roundtrip.sh` has a `# Summary` header before later G/H tests, which misleads maintainers about the harness structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Rm-failure prune test depends on implicit mtime order
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `cap-prune-rm-failure-skips-retry` relies on implicit seed order, so future seed-loop changes could break eviction-order assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Cache touch follows symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `touch -c` follows symlinks, so a cache version directory replaced by a symlink can cause session boot to update the referent mtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Cache touch guard only checks basename
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The cache touch helper allows numeric-looking paths outside the plugin cache, such as a poisoned `CLAUDE_PLUGIN_ROOT` under `/tmp`, because it validates only the basename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: SECURITY.md overstates cache touch protection
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SECURITY.md` describes the basename guard as blocking non-cache paths, which may overstate the current protection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: session-setup touches unvalidated CLAUDE_PLUGIN_ROOT
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `session-setup.sh` calls the cache touch helper before applying the writer validation used elsewhere, so malformed environment values can reach the touch path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Mtime-based retention is same-UID manipulable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Same-UID writers can backdate or freshen cache directories to influence `/upgrade-larch` eviction order under mtime-based retention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Mtime retention preserves install recency rather than actual use
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Upgrade installs can refresh mtimes for never-used intermediate versions, causing dormant but actually used early versions to be evicted before recent install-only directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: Mtime tiebreaker test does not match planned two-phase scenario
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The mtime tiebreaker test does not implement or document equivalence to the plan’s two-step under-cap then ninth-entry scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Dead list_cached_versions cleanup
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `list_cached_versions` is now unused or dead on the prune path after the mtime switch, which may confuse future editors or trip future dead-code validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Pre-existing CLAUDE_PLUGIN_ROOT path validation weakness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Existing `CLAUDE_PLUGIN_ROOT` validation permits `..`-style path oddities, and the new touch side effect makes canonicalization and prefix checks more relevant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Session pin path oddities
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Session pinning uses the basename of `plugin_root` from `session-env`, so pre-existing symlink or unusual path forms may affect pinned roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Pin overflow leaves cache above cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If more than eight distinct versions are pinned by concurrent sessions, the cap-trim loop stops without eviction and the cache remains above the configured cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
