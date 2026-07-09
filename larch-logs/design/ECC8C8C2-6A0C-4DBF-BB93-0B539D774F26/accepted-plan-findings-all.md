### FINDING_1: Missing regression for the new post-`mkdir` guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Codex-dyn-Hook Toctou Security
- **Severity**: major
- **Concern**: The plan adds a guard after `mkdir -p` and before `chmod`, but the proposed regression does not directly exercise that window, so removing or misplacing the new guard could still pass the suite.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a harness assertion on the production hook that `[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0` appears after the mkdir line and before `chmod 700 "$state_dir"`. Fail if that ordering is missing.
  - From Codex-Arch: Add a small swap-after-`mkdir` regression, or extend the harness so one variant fails when the pre-`chmod` guard is absent.
  - From Codex-Innovation: Add a race harness that lets `mkdir -p` succeed, swaps `state_dir` to a symlink before `chmod`, and asserts the hook exits 0 without touching the redirect tree.
  - From Codex-dyn-Hook Toctou Security: Add a second guardless control, or a sibling regression, that removes the pre-`mkdir` check while keeping the new post-`mkdir` check, then assert a leaf symlink at `$TMPDIR/larch-read-poll` is rejected before `chmod` and `mktemp`.


### FINDING_2: `deep_guardless` still needs a tighter guard-retention check
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: The `deep_guardless` variant can still keep an earlier standalone guard copy, so the variant may pass without actually proving the new pre-`mktemp` guard is load-bearing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require deep_guardless to keep only the guard directly adjacent to the mktemp line (for example within one line). Assert that property after variant construction and fail if an earlier standalone guard remains.


### FINDING_1: Guardless race variants still retain load-bearing state-dir checks
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation
- **Severity**: major
- **Concern**: The new guardless regression variants still leave state-dir validation in place in ways that can short-circuit before the intended pre-chmod and pre-mktemp TOCTOU windows, so the negative-control cases may pass without proving attacker-controlled writes or failing when the new guard is removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `fully_guardless` construction, explicitly remove the same pre-mkdir needles as `chmod_guardless`, then strip all standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` checks. Extend the `deep_guardless` post-construction assertions to fail if either pre-mkdir line remains, or if any standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` occurs above the reinserted pre-`mktemp` guard.
  - From Codex-Innovation: In the race variant, bypass or remove the later state-dir checks, or add an assertion that observes a `chmod`-visible side effect on the redirect directory.


