# test-setup-forked-open-source-repo.sh

Pointer-only sibling for `test-setup-forked-open-source-repo.sh`.

The full script contract, invariants, test seam, Makefile wiring, and
edit-in-sync rules live in
[`setup-forked-open-source-repo.md`](setup-forked-open-source-repo.md). This
harness creates local bare upstream/fork repositories, stubs `gh`, and exercises
preflight, mirror-sync, remote-classification, rollback, and verification paths
offline.
