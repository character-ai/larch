## Goal
Implement issue #7734: [IMPLEMENTING] [LEAF OF 7675] Atomically migrate shared Git branch and ref reads.

## Implementation Plan
## Program context

This leaf belongs to #7675 and the #7687 chief Rust migration. Read #7687 and the canonical Git decision in #7671 before implementation.

Atomically migrate the shared read-only commands `git branch-info`, `git check-remote-branch`, `git count-commits`, `git current-branch`, and `git show-stage`. Use the trusted repository and metadata owner from #7731 and the typed status owner from #7732. Also expose the local repository and remote-resolution methods consumed by #7764, but do not take ownership of either `gh` command.

Preserve exact stdout, stderr, exit codes, detached and unborn classifications, reference resolution, object-stage reads, and machine-readable output. Direct production Git reads outside these commands must either move to the same typed methods or be assigned to an exact later-domain migration issue. They must not gain a second Git owner.

This leaf owns the complete cutover for exactly the five listed `git` commands. In one PR, implement and prove the Rust counterparts, switch every production caller, remove their Python registrations from `python/larch/cli.py`, remove their superseded Python entrypoints and command-specific implementation, and mark parity, cutover, and Python removal complete in the command registry. Shared Python helpers may remain only for a verified still-Python command. Do not add a Python bridge, shim, fallback, or raw Git read outside the closed #7671 adapter.

## Acceptance criteria

- Black-box parity covers clean, dirty, detached, unborn, missing-ref, ambiguous-revision, missing stage, non-UTF-8, linked-worktree, and malformed-repository cases that apply to each command.
- Repository and remote resolution for #7764 preserves explicit-repository, no-repository, linked-worktree, absent-origin, and malformed-remote behavior without a raw Git fallback.
- Every production caller of the five commands invokes Rust after this PR.
- The same PR deletes all five Python CLI registrations and their superseded Python command implementations.
- No Python command is removed unless its Rust counterpart and consumer switch are complete in this PR.
- The registry assigns these commands to this issue and records implementation parity, consumer cutover, and Python removal as complete together.
- Lints reject new production Git reads outside the approved adapter and explicit fixture or bootstrap exceptions.
- The change stays near or below 1,500 new non-generated Rust lines, including tests.

Native blockers: #7731 and #7732. Canonical decision: #7671. Parent umbrella: #7675. Chief umbrella: #7687.

## Test plan
(no test plan section in plan-file)
