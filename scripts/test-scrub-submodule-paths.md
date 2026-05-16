# test-scrub-submodule-paths.sh Contract

Regression harness for `scripts/scrub-submodule-paths.sh`.

It verifies pass-through when no submodules exist, dropping exact and nested submodule paths, preserving sibling paths outside a nested submodule, extracting paths from fenced/code-spanned prose, and empty-input behavior.

Run with `bash scripts/test-scrub-submodule-paths.sh` or `make test-scrub-submodule-paths`.
