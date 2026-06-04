# test-run-analysis-quiet.sh contract

Regression harness for `run-analysis.sh` quiet-mode stream restoration. It builds
a synthetic `larch-logs/implement` tree, shims `git rev-parse --show-toplevel`,
runs the wrapper with issue posting and plots disabled, and asserts that the
Python analyzer's stdout and stderr are caller-visible even when quiet-mode
environment variables are inherited.
