# test-ci-failed-jobs.sh

Offline regression harness for `scripts/ci-failed-jobs.sh`.

The harness stubs `gh`, verifies failed-job filtering, fixable/unfixable
classification, matrix shard normalization, malformed-name rejection,
exit-code behavior, quiet FD-3 routing, and CI workflow job-name drift.
