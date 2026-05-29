### FINDING_12: [OUT_OF_SCOPE] concurrent-worktree resolver regression test missing
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The implement tmpdir resolver lacks a dedicated concurrent-worktree harness, so hooks could bind to the wrong tmpdir when multiple clones have active sessions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_16: [OUT_OF_SCOPE] cleanup /tmp sweep lacks ownership check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: The `/tmp` glob sweep does not check current-user ownership before `rm -rf`, which could matter on misconfigured shared `/tmp` systems.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_17: [OUT_OF_SCOPE] implement tmpdir routing trusts writable keepalive metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Hook routing still trusts same-user-writable `.larch-keepalive` metadata under predictable tmp/cache paths, leaving a pre-existing spoofing surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_18: [OUT_OF_SCOPE] version cache prune can remove active plugin roots
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Install-stamp max-8 pruning does not track active design/review or other non-implement plugin roots, so long-running sessions on older versions can lose their plugin directory after newer installs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_23: [OUT_OF_SCOPE] claude-design tmp fallback is not reaped
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `claude-design-*` is absent from `TMP_PATTERNS`, so design `/tmp` fallback dirs are not age-reaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_24: [OUT_OF_SCOPE] concurrent upgrade-larch lacks locking
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Concurrent `upgrade-larch` runs can interleave install and prune operations across worktrees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_7: [OUT_OF_SCOPE] cleanup maxdepth can miss deeper activity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `newest_activity_mtime` scans only to `-maxdepth 5`, so deeper active artifacts such as design plan-review files can be missed and stale-looking session dirs may be deleted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_9: [OUT_OF_SCOPE] latest stable tag selection may not pick max semver
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `LATEST_STABLE` selects the first paginated stable tag rather than the maximum semver, so release ordering changes could target an older stable version.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


