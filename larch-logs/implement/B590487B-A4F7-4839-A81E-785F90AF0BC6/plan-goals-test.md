## Goal
Implement issue #7733: [IMPLEMENTING] [LEAF OF 7675] Build the closed typed Git CLI compatibility adapter.

## Implementation Plan
This leaf belongs to #7675, which is part of the #7687 Rust migration program. Build the closed Git CLI compatibility adapter required by the canonical #7671 decision on top of the approved external-process layer from #7666.

Replace the current executable-level enum seam with operation-specific adapter methods and typed request/response values. Production code must not receive a public `run_git(args)` escape hatch. Each method fixes its subcommand, validates refs, paths, remotes, refspecs, and options, applies the operation's environment policy, and classifies diagnostics without relying on unbounded caller-supplied argv.

Cover only the approved exceptions: exact diff rendering; config and remote mutation; index/worktree mutation; commit and trailer operations; checkout, branch, worktree, init, clone, and sparse-checkout mutation; rebase, merge, pull, and stash; fetch, push, and `ls-remote`; tag mutation; submodule update/foreach; and the Git version probe. Keep read-only operations owned by `gix` even when a nearby mutation uses the CLI.

Treat hooks, filters, signing programs, SSH, credential helpers, askpass, merge drivers, and editors as approved but hostile descendants. Preserve installed-Git behavior while bounding output, cancellation, timeouts, process-group termination, environment inheritance, terminal prompts, and secret redaction.

Acceptance criteria:

- Every #7671 exception maps to a typed method, and no method accepts an arbitrary subcommand or opaque argv vector.
- Refs, paths, remotes, refspecs, config keys, and supported option combinations are validated before launch.
- The adapter uses `ExternalProcessRunner`; direct process creation remains mechanically rejected.
- Child environments preserve required Git compatibility without leaking unrelated service credentials or trusting repository-provided executable paths blindly.
- Unit tests prove fixed argv construction, invalid-input rejection, cancellation, timeout, truncation, redaction, and error classification.
- Differential fixtures prove representative success and failure behavior for every method family.
- `SECURITY.md` documents the Git descendant-process and credential boundary.
- The change stays near or below 1,500 new non-generated Rust lines, including tests; split implementation internally by method family without creating another public owner.

Blocked by the Git differential-fixture leaf. Canonical decision: #7671. Parent umbrella: #7675. Chief umbrella: #7687.


Native blockers: #7730.

## Test plan
(no test plan section in plan-file)
