### OOS_1:
- **Description**: Security doc omits render-cache symlink fail-closed policy. Scenario: Operators reading SECURITY.md believe only plan-review rejects interior symlinks; render-cache hardening is undocumented
- **Reviewer**: Cursor-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:139
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2904
### OOS_2:
- **Description**: TOCTOU between tree-wide symlink scan and find -type f enumeration. Scenario: Symlink directory created after find -type l but before find -type f is skipped by enumeration; publish succeeds without failing closed (same gap as plan-review)
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/design-log-publish.sh:352-396
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2905
### OOS_3:
- **Description**: No render-cache path-escape harness despite identical case guard. Scenario: Regression in render-cache case "$rc_root"/*) would not be caught; plan-review escape coverage at 590-607 does not transfer
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-design-log-publish.sh:590-607
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2906
### OOS_4:
- **Description**: [OUT_OF_SCOPE] Plan-review has the same symlinked-ancestor race in the existing loop. Scenario: The proposed render-cache fix mirrors plan-review, but plan-review can also follow a parent directory replaced by a symlink after enumeration
- **Reviewer**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/design-log-publish.sh:320-342
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/2907
