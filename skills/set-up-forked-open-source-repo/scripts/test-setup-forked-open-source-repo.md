# test-setup-forked-open-source-repo.sh

Pointer-only sibling for `test-setup-forked-open-source-repo.sh`.

The full script contract, invariants, test seam, Makefile wiring, and
edit-in-sync rules live in
[`setup-forked-open-source-repo.md`](setup-forked-open-source-repo.md). This
harness creates local bare upstream/fork repositories, stubs `gh`, and exercises
preflight, mirror-sync, remote-classification, rollback, and verification paths
offline.

Current host/concurrency hardening coverage includes GHE URL parsing,
`http://` and malformed-host rejection, `GH_HOST` / `--hostname` forwarding,
github.com baseline preservation, mixed-host refusal before `gh repo view`,
multi-URL `origin` refusal before `gh auth`, linked-worktree dirty and
operation-in-progress refusal, prunable worktree skipping, portable mkdir lock
contention, mixed-mode contention, optional flock contention, and lock sidecar
cleanup.
