# test-step-5-review.sh

Harness for the `/implement` Step 5 wrapper contract.

It uses a fake plugin root and `python/cli.py` stub, so it does not launch real reviewers. The harness covers normal completion, bg-wait marker publication, argv forwarding for `--new-process-group` and the orphan timeout, signal-detach behavior that withholds false `.completed/step-5-terminal`, reattach normalization, and duplicate-loop prevention.

Update this harness with `skills/implement/scripts/step-5-review.sh` and `step-5-review.md` whenever Step 5 wrapper sidecars, argv, or sentinel rules change.
