### FINDING_1: Guardless race variants still retain load-bearing state-dir checks
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The new guardless regression variants still leave state-dir validation in place in ways that can short-circuit before the intended pre-chmod and pre-mktemp TOCTOU windows, so the negative-control cases may pass without proving attacker-controlled writes or failing when the new guard is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `fully_guardless` construction, explicitly remove the same pre-mkdir needles as `chmod_guardless`, then strip all standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` checks. Extend the `deep_guardless` post-construction assertions to fail if either pre-mkdir line remains, or if any standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` occurs above the reinserted pre-`mktemp` guard.
  - From Codex-Innovation: In the race variant, bypass or remove the later state-dir checks, or add an assertion that observes a `chmod`-visible side effect on the redirect directory.


