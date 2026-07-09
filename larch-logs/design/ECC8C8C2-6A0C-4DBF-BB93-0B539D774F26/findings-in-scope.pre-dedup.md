### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-hook-anti-read-poll.sh:proposed-fully_guardless/deep_guardless
- **Concern**: FINDING_2 fix incomplete: `fully_guardless`/`deep_guardless` specs omit explicit pre-mkdir guard removal and construction checks. Scenario: The plan builds both variants from a leaf symlink at `$TMPDIR/larch-read-poll`, but only `chmod_guardless` lists removing `[ -L "$state_dir" ] && exit 0` and `[ -e "$state_dir" ] && [ ! -d "$state_dir" ] && exit 0`. `fully_guardless` enumerates only standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` lines. With pre-mkdir guards left in place, the hook exits 0 before `mkdir`/`mktemp`, so the negative control never proves attacker-controlled writes and `deep_guardless` can pass with no redirect files without exercising the new pre-`mktemp` guard. The planned single-occurrence assertion before `mktemp` does not catch a surviving `[ -L "$state_dir" ]` blocker.
- **Proposed resolution**: In `fully_guardless` construction, explicitly remove the same pre-mkdir needles as `chmod_guardless`, then strip all standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` checks. Extend the `deep_guardless` post-construction assertions to fail if either pre-mkdir line remains, or if any standalone `[ -d "$state_dir" ] && [ ! -L "$state_dir" ]` occurs above the reinserted pre-`mktemp` guard.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/test-hook-anti-read-poll.sh:proposed-variant-ordering
- **Concern**: New race-variant tests do not pin harness ordering or per-case `$TMPDIR/larch-read-poll` reset. Scenario: The plan keeps the parent state-dir symlink case and adds `swap_after_mkdir`, `chmod_guardless`, `fully_guardless`, and `deep_guardless`, but only `chmod_guardless` mandates `rm -rf "$TMPDIR/larch-read-poll"`. `swap_after_mkdir` leaves a leaf symlink; a later case that expects a missing path or a real directory can inherit stale layout and flake depending on insertion order.
- **Proposed resolution**: FINDING_3 on parent teardown was rejected earlier; this is a narrower harness-contract gap for the new variants only. Append the new TOCTOU block after the parent symlink test, or require each new case to reset `$TMPDIR/larch-read-poll` in its own setup (and document that order in the test file header).



### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-hook-anti-read-poll.sh:43-79
- **Concern**: The new leaf-symlink and swap-after-`mkdir` regressions still leave the later pre-read and pre-`mktemp` guards in place, so they do not actually fail when the new pre-`chmod` guard is removed.. Scenario: A same-UID swap between `mkdir` and `chmod` can still be masked by the existing later `[ -d "$state_dir" ]` checks before any temp or state file is written, so the race the plan is meant to close remains untested.
- **Proposed resolution**: In the race variant, bypass or remove the later state-dir checks, or add an assertion that observes a `chmod`-visible side effect on the redirect directory.



