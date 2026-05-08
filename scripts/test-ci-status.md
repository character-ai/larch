# scripts/test-ci-status.sh — contract

Offline PATH-stub harness for `scripts/ci-status.sh`. It verifies the default empty-checks behavior remains `CI_STATUS=pending`, `--empty-checks-grace` converts persistent empty checks to `CI_STATUS=NO_CHECKS`, and `--base-remote/--base-ref` drive fetch and behind-count refs.
