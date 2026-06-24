# test-step-8-oos-checkpoint.sh

Offline harness for `step-8-oos-checkpoint.sh`.

## Coverage

- The wrapper delegates to `python/cli.py implement step-8-oos-checkpoint`.
- The wrapper exit status is the Python router status, not the diagnostic `OOS_CHECKPOINT_RC` value.
- The wrapper does not truncate child-written `oos-disposition-checkpoint.stderr.log` content.

## Edit-in-sync

Update this harness when `step-8-oos-checkpoint.sh` changes its delegation or stdout contract.
