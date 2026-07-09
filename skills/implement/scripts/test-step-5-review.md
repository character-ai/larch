# test-step-5-review.sh

Harness for the `/implement` Step 5 wrapper contract.

It uses a fake plugin root and `python/cli.py` stub, so it does not launch real reviewers. The harness covers fresh bgjob launch, cached completed-result reuse, cached stall-result clearing for a fresh review, live-registry rejoin without duplicate launch, stale/dead registry recovery, and bgjob-owned child argv.

Update this harness with `skills/implement/scripts/step-5-review.sh` and `step-5-review.md` whenever Step 5 wrapper sidecars, argv, or sentinel rules change.
